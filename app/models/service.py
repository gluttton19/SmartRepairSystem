from app.extensions import db


class Service(db.Model):
    __tablename__ = 'services'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)

    # Навыки мастеров, связанные с этой услугой
    master_skills = db.relationship(
        'MasterSkill',
        back_populates='service',
        cascade='all, delete-orphan',
    )

    # Заявки на эту услугу (без каскадного удаления — услугу нельзя удалить,
    # пока есть связанные заявки; это нужно проверять в сервисном слое)
    requests = db.relationship(
        'Request',
        back_populates='service',
    )

    def __repr__(self) -> str:
        return f'<Service {self.name} {self.price}>'
