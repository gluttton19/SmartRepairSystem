from flask import render_template, redirect, url_for, flash, abort, request as flask_request
from flask_login import login_required, current_user
from app.master import bp
from app.decorators import master_required
from app.extensions import db
from app.models.master import Master
from app.models.notification import Notification
from app.models.request import Request, RequestStatus, MASTER_TRANSITIONS
from app.models.car import Car
from app.services import record_status_change


def _get_current_master() -> Master:
    """Возвращает Master для текущего пользователя или 404."""
    master = Master.query.filter_by(user_id=current_user.id).first()
    if master is None:
        abort(404)
    return master


@bp.get('/')
@login_required
@master_required
def dashboard():
    master = _get_current_master()
    assigned = (
        Request.query
        .filter_by(master_id=master.id)
        .join(Car, Car.id == Request.car_id)
        .order_by(Request.created_at.desc())
        .all()
    )
    return render_template('master/dashboard.html', requests=assigned, master=master)


@bp.get('/request/<int:req_id>')
@login_required
@master_required
def request_detail(req_id: int):
    master = _get_current_master()
    req = db.session.get(Request, req_id)
    if req is None:
        abort(404)
    if req.master_id != master.id:
        abort(403)

    allowed_next = MASTER_TRANSITIONS.get(req.status, [])
    return render_template(
        'master/request_detail.html',
        req=req,
        master=master,
        allowed_next=allowed_next,
    )


@bp.post('/request/<int:req_id>/status')
@login_required
@master_required
def request_status(req_id: int):
    master = _get_current_master()
    req = db.session.get(Request, req_id)
    if req is None:
        abort(404)
    if req.master_id != master.id:
        abort(403)

    new_status_value = flask_request.form.get('new_status', '')
    comment = flask_request.form.get('comment', '').strip()

    # Найти RequestStatus по значению Enum
    try:
        new_status = RequestStatus(new_status_value)
    except ValueError:
        flash('Неизвестный статус.', 'danger')
        return redirect(url_for('master.request_detail', req_id=req_id))

    allowed = MASTER_TRANSITIONS.get(req.status, [])
    if new_status not in allowed:
        flash(
            f'Переход из "{req.status.value}" в "{new_status.value}" недопустим.',
            'danger',
        )
        return redirect(url_for('master.request_detail', req_id=req_id))

    record_status_change(
        request=req,
        new_status=new_status,
        changed_by_id=current_user.id,
        comment=comment,
    )

    # Уведомление владельцу автомобиля (клиенту)
    client_id = req.car.owner_id
    db.session.add(Notification(
        user_id=client_id,
        message=f"Статус заявки №{req.id} изменён на '{new_status.value}'.",
    ))

    db.session.commit()
    flash(f'Статус изменён на "{new_status.value}".', 'success')
    return redirect(url_for('master.request_detail', req_id=req_id))
