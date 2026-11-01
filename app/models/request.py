import enum
from datetime import datetime, timezone
from app.extensions import db


class RequestStatus(enum.Enum):
    CREATED   = 'Создана'
    CONFIRMED = 'Подтверждена'
    ASSIGNED  = 'Назначен мастер'
    IN_WORK   = 'В работе'
    WAITING   = 'Ожидает запчасти'
    READY     = 'Готова к выдаче'
    DONE      = 'Завершена'
    CANCELLED = 'Отменена'


# Статусы, которые считаются незавершёнными (используются в алгоритме загрузки)
ACTIVE_STATUSES = {
    RequestStatus.CONFIRMED,
    RequestStatus.ASSIGNED,
    RequestStatus.IN_WORK,
    RequestStatus.WAITING,
    RequestStatus.READY,
}

# Допустимые переходы статусов для мастера
MASTER_TRANSITIONS: dict[RequestStatus, list[RequestStatus]] = {
    RequestStatus.CONFIRMED:  [RequestStatus.IN_WORK, RequestStatus.CANCELLED],
    RequestStatus.ASSIGNED:   [RequestStatus.IN_WORK, RequestStatus.CANCELLED],
    RequestStatus.IN_WORK:    [RequestStatus.WAITING, RequestStatus.READY],
    RequestStatus.WAITING:    [RequestStatus.IN_WORK, RequestStatus.READY],
    RequestStatus.READY:      [RequestStatus.DONE],
}


class Request(db.Model):
    __tablename__ = 'requests'

    id = db.Column(db.Integer, primary_key=True)
    car_id = db.Column(db.Integer, db.ForeignKey('cars.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False)

    # Назначенный мастер (может быть NULL до подтверждения)
    master_id = db.Column(db.Integer, db.ForeignKey('masters.id'), nullable=True)

    # Если клиент выбрал мастера вручную — сохраняем его id.
    # master_id может быть перезаписан логикой; selected_master_id — неизменное намерение клиента.
    selected_master_id = db.Column(db.Integer, db.ForeignKey('masters.id'), nullable=True)

    preferred_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    status = db.Column(
        db.Enum(RequestStatus),
        nullable=False,
        default=RequestStatus.CREATED,
    )
    description = db.Column(db.Text, nullable=True)

    # Автомобиль, на который оформлена заявка
    car = db.relationship('Car', back_populates='requests')

    # Услуга
    service = db.relationship('Service', back_populates='requests')

    # Назначенный мастер
    master = db.relationship(
        'Master',
        back_populates='requests',
        foreign_keys=[master_id],
    )

    # Мастер, выбранный клиентом вручную (read-only после создания)
    selected_master = db.relationship(
        'Master',
        foreign_keys=[selected_master_id],
    )

    # История изменений статуса
    status_history = db.relationship(
        'RequestStatusHistory',
        back_populates='request',
        cascade='all, delete-orphan',
        order_by='RequestStatusHistory.changed_at',
    )

    @property
    def is_manual_assignment(self) -> bool:
        """True, если клиент выбрал мастера сам."""
        return self.selected_master_id is not None

    @property
    def is_active(self) -> bool:
        return self.status in ACTIVE_STATUSES

    @property
    def is_done(self) -> bool:
        return self.status == RequestStatus.DONE

    def __repr__(self) -> str:
        return f'<Request #{self.id} [{self.status.value}]>'
