from flask import render_template, redirect, url_for, flash, abort
from flask_login import login_required
from app.admin import bp
from app.admin.forms import ServiceForm, MasterForm
from app.decorators import admin_required
from app.extensions import db
from app.models.car import Car
from app.models.master import Master, MasterSkill
from app.models.request import Request
from app.models.service import Service
from app.models.user import User
from app.services.statistics_service import get_all_stats


@bp.get('/')
@login_required
@admin_required
def dashboard():
    return render_template('admin/dashboard.html')


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------

@bp.get('/services')
@login_required
@admin_required
def services():
    all_services = Service.query.order_by(Service.name).all()
    return render_template('admin/services.html', services=all_services)


@bp.get('/services/add')
@bp.post('/services/add')
@login_required
@admin_required
def service_add():
    form = ServiceForm()
    if form.validate_on_submit():
        svc = Service(
            name=form.name.data,
            description=form.description.data or None,
            price=form.price.data,
        )
        db.session.add(svc)
        db.session.commit()
        flash(f'Услуга «{svc.name}» добавлена.', 'success')
        return redirect(url_for('admin.services'))

    return render_template('admin/service_form.html', form=form, title='Добавить услугу')


@bp.post('/services/<int:service_id>/delete')
@login_required
@admin_required
def service_delete(service_id: int):
    svc = db.session.get(Service, service_id)
    if svc is None:
        abort(404)

    # Запрет удаления если есть связанные заявки
    linked_requests = Request.query.filter_by(service_id=service_id).count()
    if linked_requests:
        flash(
            f'Нельзя удалить услугу «{svc.name}»: '
            f'она используется в {linked_requests} заявке(ах).',
            'danger',
        )
        return redirect(url_for('admin.services'))

    # Запрет удаления если есть связанные навыки мастеров
    linked_skills = MasterSkill.query.filter_by(service_id=service_id).count()
    if linked_skills:
        flash(
            f'Нельзя удалить услугу «{svc.name}»: '
            f'она назначена {linked_skills} мастеру(ам). '
            f'Сначала снимите навык.',
            'danger',
        )
        return redirect(url_for('admin.services'))

    db.session.delete(svc)
    db.session.commit()
    flash(f'Услуга «{svc.name}» удалена.', 'info')
    return redirect(url_for('admin.services'))


# ---------------------------------------------------------------------------
# Masters
# ---------------------------------------------------------------------------

@bp.get('/masters')
@login_required
@admin_required
def masters():
    all_masters = Master.query.join(User, User.id == Master.user_id).all()
    return render_template('admin/masters.html', masters=all_masters)


@bp.get('/masters/add')
@bp.post('/masters/add')
@login_required
@admin_required
def master_add():
    form = MasterForm()
    form.skill_ids.choices = [
        (s.id, s.name) for s in Service.query.order_by(Service.name).all()
    ]

    if form.validate_on_submit():
        # 1. Создать пользователя с ролью master
        user = User(
            username=form.username.data,
            email=form.email.data,
            role='master',
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        # 2. Создать запись Master
        master = Master(
            user_id=user.id,
            specialization=form.specialization.data,
            is_available=True,
        )
        db.session.add(master)
        db.session.flush()

        # 3. Назначить навыки
        for svc_id in form.skill_ids.data:
            db.session.add(MasterSkill(master_id=master.id, service_id=svc_id))

        db.session.commit()
        flash(f'Мастер {user.username} создан.', 'success')
        return redirect(url_for('admin.masters'))

    return render_template('admin/master_form.html', form=form, title='Добавить мастера')


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@bp.get('/users')
@login_required
@admin_required
def users():
    all_users = User.query.order_by(User.role, User.username).all()
    return render_template('admin/users.html', users=all_users)


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------

@bp.get('/requests')
@login_required
@admin_required
def requests_all():
    all_requests = (
        Request.query
        .join(Car, Car.id == Request.car_id)
        .order_by(Request.created_at.desc())
        .all()
    )
    return render_template('admin/requests.html', requests=all_requests)


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

@bp.get('/stats')
@login_required
@admin_required
def stats():
    data = get_all_stats()
    return render_template('admin/stats.html', **data)
