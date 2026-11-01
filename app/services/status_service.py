from app.extensions import db
from app.models.request import Request, RequestStatus
from app.models.status_history import RequestStatusHistory


def record_status_change(
    request: Request,
    new_status: RequestStatus,
    changed_by_id: int | None = None,
    comment: str = '',
) -> RequestStatusHistory:
    """Фиксирует переход статуса и добавляет запись в историю."""
    entry = RequestStatusHistory(
        request_id=request.id,
        old_status=request.status if request.status != new_status else None,
        new_status=new_status,
        changed_by_id=changed_by_id,
        comment=comment or None,
    )
    request.status = new_status
    db.session.add(entry)
    return entry
