from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed
from wtforms import *
from wtforms.validators import DataRequired, InputRequired
from .db_modules.db_utils import get_all_homework

class SimpleRegisterForm(FlaskForm):
    grade_numb = SelectField('Номер класса', validators=[DataRequired()], choices=range(1, 12))
    grade_let = SelectField('Литера класса', validators=[DataRequired()], choices=[(1, 'А'), (2, 'Б'), (3, 'В'), (4, 'Г')])
    group = RadioField('Группа обучения (если не знаете, уточните в расписании)',
                       choices=[('1', '1 группа'), ('2', '2 группа')],
                       default='1',
                       validators=[InputRequired()])
    submit = SubmitField('Войти')

    def validate_grade_let(form, field):
        try:
            get_all_homework(form.grade_numb.data + field.data)
        except Exception:
            raise ValidationError("Некорректно указан класс")

class AdminLoginForm(FlaskForm):
    tg = StringField('Введите ваш ник в Telegram', validators=[DataRequired()])
    password = PasswordField('Введите пароль, который вы указывали при регистрации через бота', validators=[DataRequired()])
    remember_me = BooleanField('Запомни меня')
    submit = SubmitField('Войти')
    def validate_tg(form, field):
        if field.data[0] != '@':
            field.data = '@' + field.data
        return True

class HomeworkForm(FlaskForm):
    subject = SelectField(validators=[DataRequired()], coerce=str)
    text = TextAreaField('Домашнее задание')
    images = MultipleFileField('Загрузите фотографии')
    submit = SubmitField('Отправить')