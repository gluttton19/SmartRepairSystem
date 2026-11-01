from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DecimalField, PasswordField, SelectMultipleField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Email, ValidationError
from app.models.user import User


class ServiceForm(FlaskForm):
    name = StringField(
        'Название',
        validators=[DataRequired(), Length(max=128)],
    )
    description = TextAreaField(
        'Описание',
        validators=[Length(max=1000)],
    )
    price = DecimalField(
        'Цена (₽)',
        places=2,
        validators=[DataRequired(), NumberRange(min=0)],
    )
    submit = SubmitField('Сохранить')

    def validate_name(self, field):
        from app.models.service import Service
        svc = Service.query.filter_by(name=field.data).first()
        if svc and getattr(self, '_edit_id', None) != svc.id:
            raise ValidationError('Услуга с таким названием уже существует.')


class MasterForm(FlaskForm):
    username = StringField(
        'Имя пользователя',
        validators=[DataRequired(), Length(min=3, max=64)],
    )
    email = StringField(
        'Email',
        validators=[DataRequired(), Email()],
    )
    password = PasswordField(
        'Пароль',
        validators=[DataRequired(), Length(min=8)],
    )
    specialization = StringField(
        'Специализация',
        validators=[DataRequired(), Length(max=128)],
    )
    skill_ids = SelectMultipleField(
        'Навыки (услуги)',
        coerce=int,
    )
    submit = SubmitField('Создать мастера')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Это имя пользователя уже занято.')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Этот email уже зарегистрирован.')
