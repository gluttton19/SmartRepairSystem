from flask import render_template, redirect, url_for, flash, abort, request as flask_request
from flask_login import login_required, current_user
from app.client import bp
from app.client.forms import CarForm, RequestForm
from app.decorators import client_required
from app.extensions import db
from app.models.car import Car
from app.models.master import Master, MasterSkill
from app.models.notification import Notification
from app.models.request import Request, RequestStatus
from app.models.service import Service
from app.services import assign_master, record_status_change


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _car_choices(user_id: int) -> list[tuple[int, str]]:
    cars = Car.query.filter_by(owner_id=user_id).all()
    return [(c.id, f'{c.brand} {c.model} ({c.registration_number})') for c in cars]


def _service_choices() -> list[tuple[int, str]]:
    return [(s.id, f'{s.name} — {s.price} ₽') for s in Service.query.order_by(Service.name).all()]


def _master_choices(service_id: int | None = None) -> list[tuple[int, str]]:
    """Возвращает [(0, 'Назначить автоматически'), ...мастера...]."""
    choices = [(0, 'Назначить автоматически')]
    q = Master.query.join(MasterSkill, MasterSkill.master_id == Master.id)
    if service_id:
        q = q.filter(MasterSkill.service_id == service_id)
    q = q.filter(Master.is_available == True)
    for m in q.all():
        choices.append((m.id, m.user.username))
    return choices


def _populate_request_form(form: RequestForm, user_id: int) -> None:
    form.car_id.choices = _car_choices(user_id)
    form.service_id.choices = _service_choices()
    form.master_id.choices = _master_choices()


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@bp.get('/')
@login_required
@client_required
def dashboard():
    return render_template('client/dashboard.html')


# ---------------------------------------------------------------------------
# Cars
# ---------------------------------------------------------------------------

@bp.get('/cars')
@login_required
@client_required
def cars():
    user_cars = Car.query.filter_by(owner_id=current_user.id).all()
    return render_template('client/cars.html', cars=user_cars)


@bp.get('/cars/add')
@bp.post('/cars/add')
@login_required
@client_required
def car_add():
    form = CarForm()
    if form.validate_on_submit():
        car = Car(
            owner_id=current_user.id,
            brand=form.brand.data,
            model=form.model.data,
            year=form.year.data,
            registration_number=form.registration_number.data,
            vin=form.vin.data or None,
        )
        db.session.add(car)
        db.session.commit()
        flash(f'Автомобиль {car.brand} {car.model} добавлен.', 'success')
        return redirect(url_for('client.cars'))

    return render_template('client/car_form.html', form=form, title='Добавить автомобиль')


@bp.post('/cars/<int:car_id>/delete')
@login_required
@client_required
def car_delete(car_id: int):
    car = db.session.get(Car, car_id)
    if car is None:
        abort(404)
    if car.owner_id != current_user.id:
        abort(403)

    if car.requests:
        flash('Невозможно удалить автомобиль: существуют связанные заявки.', 'danger')
        return redirect(url_for('client.cars'))

    db.session.delete(car)
    db.session.commit()
    flash('Автомобиль удалён.', 'info')
    return redirect(url_for('client.cars'))


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------

@bp.get('/requests')
@login_required
@client_required
def requests_list():
    # User → Car → Request: только заявки на автомобили текущего пользователя
    user_requests = (
        Request.query
        .join(Car, Car.id == Request.car_id)
        .filter(Car.owner_id == current_user.id)
        .order_by(Request.created_at.desc())
        .all()
    )
    return render_template('client/requests.html', requests=user_requests)


@bp.get('/requests/create')
@bp.post('/requests/create')
@login_required
@client_required
def request_create():
    form = RequestForm()
    _populate_request_form(form, current_user.id)

    if form.validate_on_submit():
        # Проверка: автомобиль принадлежит текущему пользователю
        car = db.session.get(Car, form.car_id.data)
        if car is None or car.owner_id != current_user.id:
            abort(403)

        selected_master_id = form.master_id.data or None  # 0 → None
        master_id = selected_master_id

        # Автоматическое назначение если мастер не выбран
        if not selected_master_id:
            found = assign_master(form.service_id.data, form.preferred_date.data)
            master_id = found.id if found else None

        # Начальный статус зависит от того, назначен ли мастер:
        # если мастер найден — ASSIGNED (мастер может сразу работать),
        # если нет — CREATED (требует ручного вмешательства администратора).
        initial_status = RequestStatus.ASSIGNED if master_id else RequestStatus.CREATED

        req = Request(
            car_id=car.id,
            service_id=form.service_id.data,
            master_id=master_id,
            selected_master_id=selected_master_id,
            preferred_date=form.preferred_date.data,
            description=form.description.data or None,
            status=initial_status,
        )
        db.session.add(req)
        db.session.flush()  # получить req.id до записи истории

        # Первая запись в историю статусов
        record_status_change(
            request=req,
            new_status=initial_status,
            changed_by_id=current_user.id,
            comment='Заявка создана клиентом',
        )

        # Уведомление клиенту
        db.session.add(Notification(
            user_id=current_user.id,
            message=f'Заявка #{req.id} успешно создана.',
        ))

        db.session.commit()
        flash(f'Заявка #{req.id} создана.', 'success')
        return redirect(url_for('client.requests_list'))

    return render_template('client/request_form.html', form=form, title='Создать заявку')


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

@bp.get('/history')
@login_required
@client_required
def history():
    # Базовый запрос: User → Cars → Requests, только текущий пользователь
    q = (
        Request.query
        .join(Car, Car.id == Request.car_id)
        .filter(Car.owner_id == current_user.id)
    )

    # Фильтр по автомобилю (car_id из query string)
    car_id_filter = flask_request.args.get('car_id', type=int)
    if car_id_filter:
        # Дополнительная проверка: автомобиль принадлежит текущему пользователю
        car_check = db.session.get(Car, car_id_filter)
        if car_check and car_check.owner_id == current_user.id:
            q = q.filter(Request.car_id == car_id_filter)

    # Фильтр по статусу (status_value из query string)
    status_filter = flask_request.args.get('status')
    if status_filter:
        try:
            q = q.filter(Request.status == RequestStatus(status_filter))
        except ValueError:
            pass  # неизвестный статус — игнорируем

    # Сортировка: новые сначала
    requests = q.order_by(Request.created_at.desc()).all()

    # Для фильтра в шаблоне: только автомобили текущего пользователя
    user_cars = Car.query.filter_by(owner_id=current_user.id).all()

    return render_template(
        'client/history.html',
        requests=requests,
        user_cars=user_cars,
        all_statuses=list(RequestStatus),
        selected_car_id=car_id_filter,
        selected_status=status_filter,
    )
