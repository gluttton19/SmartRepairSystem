from datetime import datetime, timezone
from app.extensions import db
from app.models.request import RequestStatus


class RequestStatusHistory(db.Model):
    __tablename__ = 'request_status_history'

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('requests.id'), nullable=False)
    old_status = db.Column(db.Enum(RequestStatus), nullable=True)   # NULL для первой записи
    new_status = db.Column(db.Enum(RequestStatus), nullable=False)
    changed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    comment = db.Column(db.Text, nullable=True)

    # Кто изменил статус (мастер или администратор)
    changed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    request = db.relationship('Request', back_populates='status_history')

    # Пользователь, изменивший статус
    changed_by = db.relationship(
        'User',
        back_populates='status_changes',
        foreign_keys=[changed_by_id],
    )

    def __repr__(self) -> str:
        old = self.old_status.value if self.old_status else '—'
        return f'<StatusHistory req={self.request_id} {old} → {self.new_status.value}>'
