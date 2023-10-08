import os
from uuid import uuid4

import dotenv
from flask import (Flask, abort, make_response, redirect,
                   render_template, request, send_from_directory)
from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user)
from flask_restful import Api, abort
from werkzeug.utils import secure_filename

from all.alice import blueprint
from all.api_resources import *
from all.db_modules.db_utils import *
from all.forms import *

app = Flask(__name__, static_url_path='',
            static_folder='all/static/img', template_folder='all/templates')
dotenv.load_dotenv()
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.register_blueprint(blueprint)

login_manager = LoginManager()
login_manager.init_app(app)
api = Api(app)
api.add_resource(HomeworkResource, '/api/116/<int:grade>/<subject>/<api_key>')
api.add_resource(HomeworkListResource, '/api/116/<int:grade>/<api_key>')
api.add_resource(UserResource, '/api/116/user/<user_tg>/<api_key>')
api.add_resource(UserListResource, '/api/116/users/<api_key>')


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.get(User, user_id)


@app.route('/content/<path:filepath>')
def content(filepath):
    return send_from_directory('all/dynamic/img/actual', filepath)

@app.route('/')
def start_page():
    user_grade = int(request.cookies.get("grade", 0))
    if user_grade:
        return redirect(f'/{user_grade}')
    else:
        return redirect('/register')


@app.route('/register', methods=['GET', 'POST'])
@app.route('/register/<string:error>', methods=['GET', 'POST'])
def simple_reg(error=None):
    if current_user:
        logout_user()
    form = SimpleRegisterForm()

    eng_teachers = set()
    for grade in get_all_grades():
        for teacher in grade['eng_teachers']:
            eng_teachers.add(teacher)
    eng_teachers = [elem for elem in eng_teachers]
    form.eng_teachers.choices = [(i, x) for i, x in enumerate(eng_teachers)]
    if request.method == 'POST' and form.validate_on_submit():
        user_grade = int(form.grade_numb.data + form.grade_let.data)
        dict_grade = get_grade(user_grade, name=False)
        chosen_teacher = eng_teachers[form.eng_teachers.data]
        if chosen_teacher not in dict_grade['eng_teachers']:
            return redirect('/errors/wrong_teacher')
        else:
            user_group = dict_grade['eng_teachers'].index(chosen_teacher) + 1
            resp = make_response(redirect(f'/{user_grade}'))
            resp.set_cookie("grade", str(user_grade), max_age=15552000)
            resp.set_cookie("group", str(user_group), max_age=15552000)
            return resp
    if error:
        return render_template('simple_form.html', form=form, error='В вашем классе нет такого учителя')
    else:
        return render_template('simple_form.html', form=form)

@app.route('/errors/<error>', methods=['GET', 'POST'])
def errors_handler(error: str):
    if error == 'wrong_teacher':
        return redirect(f'/register/{error}')


@app.route('/favicon.ico')
def favicon():
    return send_from_directory("all/dynamic/img/actual", "logo.png")

@app.route('/login', methods=['GET', 'POST'])
def admin_login():
    form = AdminLoginForm()
    if form.validate_on_submit():
        if current_user:
            logout_user()
        try:
            user = get_user(name=form.name.data, surname=form.surname.data, password=form.password.data, to_dict=False)
            login_user(user, remember=form.remember_me.data)
            resp = make_response(redirect(f'/{user.grade_id}'))
            resp.delete_cookie("grade")
            resp.delete_cookie("group")
            resp.set_cookie("grade", str(user.grade_id), max_age=15552000)
            resp.set_cookie("group", str(user.group), max_age=15552000)
            return resp
        except AccessNotAllowedError:
            return abort(403, description='Вы ввели неправильный пароль или не указали его при регистрации в боте')
        except RecordNotFoundError:
            return abort(404)
    return render_template('simple_form.html', form=form)


@app.route('/new', methods=['GET', 'POST'])
@login_required
def new_homework():
    form = HomeworkForm()
    form.subject.choices = get_subs(int(request.cookies.get('grade')), int(
        request.cookies.get('group')), return_name=True)
    if form.validate_on_submit():
        image = []
        print(form.images.data)
        for file in form.images.data:
            if file:
                file_name = secure_filename(uuid4().hex + '.png')
                file.save(os.path.join('all', 'dynamic',
                          'img', 'actual', file_name))
                image.append(file_name)
        add_homework(current_user.grade_id, form.subject.data,
                     current_user.id, form.text.data, image, find_by='name')
        return redirect(f'/{current_user.grade_id}')
    return render_template('simple_form.html', form=form)

@app.route('/<int:grade>')
@app.route('/<int:grade>/weekday/<int:weekday>')
def grade_page(grade: int, weekday: int=7):
    grade = int(grade)
    try:
        if request.cookies.get('grade'):
            user_grade = int(request.cookies.get('grade'))
        else:
            return redirect('/register')

        if grade == user_grade:
            week_list = get_list_of_dates(grade)
            if weekday != 7:
                for i, item in enumerate(week_list):
                    if item[0] == weekday:
                        index = i
                        break
                homework = get_homework_by_date(user_grade, group=int(request.cookies.get("group", 0)), weekday=int(weekday), include_info=True)
                print(homework)
            else:
                index = 7
                homework = get_homework_by_grade(grade, group=int(request.cookies.get("group", 0)))
            for hw in homework:
                try:
                    hw['text'].replace('\n', '<br />')
                except Exception:
                    pass
            return render_template('homework.html', 
                                   hw=homework, 
                                   request=request, 
                                   grade=grade,
                                   index=index,
                                   week_list=week_list)
        else:
            return redirect(f'/{user_grade}')
    except RecordNotFoundError:
        return abort(404)

@app.route('/<int:grade>/<sub>')
def homework_page(grade: int, sub: str):
    try:
        return render_template('lon_hw.html', hw=get_homework(grade, sub))
    except RecordNotFoundError:
        return abort(404)

if __name__ == '__main__' and int(os.getenv("DEBUG")):
   app.run(port=8080, host='127.0.0.1')
