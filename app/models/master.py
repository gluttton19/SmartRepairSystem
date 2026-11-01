from app.extensions import db


class Master(db.Model):
    __tablename__ = 'masters'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    specialization = db.Column(db.String(128), nullable=False)
    is_available = db.Column(db.Boolean, nullable=False, default=True)

    # Профиль пользователя мастера
    user = db.relationship('User', back_populates='master')

    # Навыки мастера (услуги, которые он может выполнять)
    skills = db.relationship(
        'MasterSkill',
        back_populates='master',
        cascade='all, delete-orphan',
    )

    # Все заявки, назначенные этому мастеру
    requests = db.relationship(
        'Request',
        back_populates='master',
        foreign_keys='Request.master_id',
    )

    def __repr__(self) -> str:
        return f'<Master user_id={self.user_id} spec={self.specialization}>'


class MasterSkill(db.Model):
    """Связь многие-ко-многим: мастер умеет выполнять услугу."""
    __tablename__ = 'master_skills'

    id = db.Column(db.Integer, primary_key=True)
    master_id = db.Column(db.Integer, db.ForeignKey('masters.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('master_id', 'service_id', name='uq_master_service'),
    )

    master = db.relationship('Master', back_populates='skills')
    service = db.relationship('Service', back_populates='master_skills')

    def __repr__(self) -> str:
        return f'<MasterSkill master={self.master_id} service={self.service_id}>'
