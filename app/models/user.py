from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(16), nullable=False, default='client')  # client | master | admin
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Один пользователь — один профиль мастера (если role == 'master')
    master = db.relationship(
        'Master',
        back_populates='user',
        uselist=False,          # one-to-one
        cascade='all, delete-orphan',
    )

    # Автомобили клиента
    cars = db.relationship(
        'Car',
        back_populates='owner',
        cascade='all, delete-orphan',
    )

    # Уведомления пользователя
    notifications = db.relationship(
        'Notification',
        back_populates='user',
        cascade='all, delete-orphan',
        order_by='Notification.created_at.desc()',
    )

    # Записи истории, где этот пользователь изменил статус
    status_changes = db.relationship(
        'RequestStatusHistory',
        back_populates='changed_by',
        foreign_keys='RequestStatusHistory.changed_by_id',
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f'<User {self.username} [{self.role}]>'
