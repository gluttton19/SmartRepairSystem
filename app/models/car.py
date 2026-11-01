from app.extensions import db


class Car(db.Model):
    __tablename__ = 'cars'

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    brand = db.Column(db.String(64), nullable=False)
    model = db.Column(db.String(64), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    registration_number = db.Column(db.String(20), nullable=False)
    vin = db.Column(db.String(17), nullable=True)

    # Владелец автомобиля
    owner = db.relationship('User', back_populates='cars')

    # Заявки на этот автомобиль; при удалении авто — удаляем заявки
    requests = db.relationship(
        'Request',
        back_populates='car',
        cascade='all, delete-orphan',
    )

    def __repr__(self) -> str:
        return f'<Car {self.brand} {self.model} ({self.year}) [{self.registration_number}]>'
