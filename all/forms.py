from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed
from wtforms import *
from wtforms.validators import DataRequired, InputRequired
from .db_modules.db_utils import get_homework_by_grade, get_grade
from .db_modules.db_utils import *

        
class SimpleRegisterForm(FlaskForm):
    grade_numb = SelectField('Номер класса', choices=range(1, 12))
    grade_let = SelectField('Литера класса', choices=[(1, 'А'), (2, 'Б'), (3, 'В'), (4, 'Г')])
    eng_teachers = SelectField('Выберите вашего учителя английского', coerce=int)
    submit = SubmitField('Войти')

    def validate_grade_let(form, field):
        try:
            print(int(form.grade_numb.data + field.data))
            print(get_grade(int(form.grade_numb.data + field.data), name=False))
            return True
        except Exception:
            raise ValidationError("Некорректно указан класс")


class AdminLoginForm(FlaskForm):
    name = StringField('Введите ваше имя', validators=[DataRequired()])
    surname = StringField('Введите вашу фамилию', validators=[DataRequired()])
    password = PasswordField('Введите пароль, который вы указывали при регистрации через бота', validators=[DataRequired()])
    remember_me = BooleanField('Запомни меня')
    submit = SubmitField('Войти')

class HomeworkForm(FlaskForm):
    subject = SelectField("Предмет", validators=[DataRequired()], coerce=str)
    text = TextAreaField('Домашнее задание')
    images = MultipleFileField('Загрузите фотографии')
    submit = SubmitField('Отправить')