from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField, TextAreaField, DateField, SelectField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class RequestForm(FlaskForm):
    """
    Поля car_id, service_id, master_id заполняются динамически в маршруте
    через form.car_id.choices = [...] чтобы ограничить выбор текущим пользователем.
    """
    car_id = SelectField(
        'Автомобиль',
        coerce=int,
        validators=[DataRequired()],
    )
    service_id = SelectField(
        'Услуга',
        coerce=int,
        validators=[DataRequired()],
    )
    preferred_date = DateField(
        'Предпочтительная дата',
        validators=[Optional()],
    )
    description = TextAreaField(
        'Описание проблемы',
        validators=[Optional(), Length(max=1000)],
    )
    master_id = SelectField(
        'Мастер (необязательно)',
        coerce=int,
        validators=[Optional()],
    )
    submit = SubmitField('Создать заявку')


class CarForm(FlaskForm):
    brand = StringField(
        'Марка',
        validators=[DataRequired(), Length(max=64)],
    )
    model = StringField(
        'Модель',
        validators=[DataRequired(), Length(max=64)],
    )
    year = IntegerField(
        'Год выпуска',
        validators=[DataRequired(), NumberRange(min=1900, max=2100)],
    )
    registration_number = StringField(
        'Регистрационный номер',
        validators=[DataRequired(), Length(max=20)],
    )
    vin = StringField(
        'VIN',
        validators=[Optional(), Length(min=17, max=17)],
    )
    submit = SubmitField('Сохранить')
