from sqlalchemy import func
from app.extensions import db
from app.models.user import User
from app.models.master import Master
from app.models.request import Request, RequestStatus
from app.models.service import Service


def get_users_by_role() -> dict[str, int]:
    """Количество пользователей по каждой роли."""
    rows = (
        db.session.query(User.role, func.count(User.id).label('cnt'))
        .group_by(User.role)
        .all()
    )
    base = {'client': 0, 'master': 0, 'admin': 0}
    for row in rows:
        base[row.role] = row.cnt
    return base


def get_requests_by_status() -> list[dict]:
    """Количество заявок по каждому статусу; статусы без заявок тоже включены."""
    rows = (
        db.session.query(Request.status, func.count(Request.id).label('cnt'))
        .group_by(Request.status)
        .all()
    )
    count_map = {row.status: row.cnt for row in rows}
    return [
        {'status': s, 'label': s.value, 'count': count_map.get(s, 0)}
        for s in RequestStatus
    ]


def get_master_workload() -> list[dict]:
    """
    Количество заявок у каждого мастера (все статусы).
    Возвращает список, отсортированный по убыванию заявок.
    """
    rows = (
        db.session.query(
            Master.id,
            User.username,
            Master.specialization,
            func.count(Request.id).label('total'),
        )
        .join(User, User.id == Master.user_id)
        .outerjoin(Request, Request.master_id == Master.id)
        .group_by(Master.id, User.username, Master.specialization)
        .order_by(func.count(Request.id).desc())
        .all()
    )
    return [
        {
            'master_id':      row.id,
            'username':       row.username,
            'specialization': row.specialization,
            'total':          row.total,
        }
        for row in rows
    ]


def get_popular_services(limit: int = 10) -> list[dict]:
    """
    Услуги, отсортированные по количеству заявок (убывание).
    Включает услуги с нулём заявок.
    """
    rows = (
        db.session.query(
            Service.id,
            Service.name,
            Service.price,
            func.count(Request.id).label('cnt'),
        )
        .outerjoin(Request, Request.service_id == Service.id)
        .group_by(Service.id, Service.name, Service.price)
        .order_by(func.count(Request.id).desc())
        .limit(limit)
        .all()
    )
    return [
        {
            'service_id': row.id,
            'name':       row.name,
            'price':      row.price,
            'count':      row.cnt,
        }
        for row in rows
    ]


def get_all_stats() -> dict:
    """Единая точка входа — собирает всю статистику за один вызов."""
    return {
        'users_by_role':      get_users_by_role(),
        'requests_by_status': get_requests_by_status(),
        'master_workload':    get_master_workload(),
        'popular_services':   get_popular_services(),
    }
