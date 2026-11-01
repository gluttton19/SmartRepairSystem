import random
from sqlalchemy import func
from app.extensions import db
from app.models.master import Master, MasterSkill
from app.models.request import Request, ACTIVE_STATUSES


def assign_master(service_id: int, preferred_date) -> Master | None:
    """
    Алгоритм автоматического назначения мастера:
    1. Найти мастеров с навыком для данной услуги и is_available=True.
    2. Подсчитать активные заявки каждого на preferred_date (или вообще, если дата не задана).
    3. Выбрать мастера(ов) с минимальной загрузкой.
    4. При равенстве — выбрать случайного.
    Возвращает Master или None если подходящих нет.
    """
    # Мастера с нужным навыком и флагом доступности
    candidates = (
        Master.query
        .join(MasterSkill, MasterSkill.master_id == Master.id)
        .filter(MasterSkill.service_id == service_id)
        .filter(Master.is_available == True)
        .all()
    )
    if not candidates:
        return None

    candidate_ids = [m.id for m in candidates]

    # Подсчёт активных заявок на дату (или общих, если дата не указана)
    q = (
        db.session.query(Request.master_id, func.count(Request.id).label('cnt'))
        .filter(Request.master_id.in_(candidate_ids))
        .filter(Request.status.in_(list(ACTIVE_STATUSES)))
    )
    if preferred_date is not None:
        q = q.filter(Request.preferred_date == preferred_date)

    load_map: dict[int, int] = {row.master_id: row.cnt for row in q.group_by(Request.master_id).all()}

    # Мастера без заявок получают 0
    for m_id in candidate_ids:
        load_map.setdefault(m_id, 0)

    min_load = min(load_map.values())
    least_busy = [m for m in candidates if load_map[m.id] == min_load]

    return random.choice(least_busy)
