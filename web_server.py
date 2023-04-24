from datetime import timedelta
import os
import subprocess
from sys import executable
from uuid import uuid4

import dotenv
from flask import (Flask, Response, abort, jsonify, make_response, redirect,
                   render_template, request, send_from_directory, url_for)
from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user)
from flask_restful import Api, Resource, abort, reqparse
from werkzeug.utils import secure_filename

from all.alice import blueprint
from all.api_resources import *
from all.db_modules.db_utils import *
from all.forms import *

for file_loc in ['tg_bot.py']:
   subprocess.Popen([executable, os.path.join(os.path.dirname(__file__), 'all', file_loc)])


app = Flask(__name__, static_url_path='', static_folder='all/static/img', template_folder='all/templates')
dotenv.load_dotenv()
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.register_blueprint(blueprint)

login_manager = LoginManager()
login_manager.init_app(app)
api = Api(app)
api.add_resource(HomeworkResource, '/api/116/<int:grade>/<subject>')
api.add_resource(HomeworkListResource, '/api/116/<int:grade>')
api.add_resource(UserResource, '/api/116/user/<user_tg>')
api.add_resource(UserListResource, '/api/116/users')

@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.get(User, user_id)

@app.route('/content/<path:filepath>')
def content(filepath):
    return send_from_directory('all/dynamic/img/actual', filepath)

@app.route('/116')
def start_page():
    user_grade = int(request.cookies.get("grade", 0))
    if user_grade:
        return redirect(f'/116/{user_grade}')
    else:
        return redirect('/116/register')


@app.route('/116/register', methods=['GET', 'POST'])
def simple_reg():
    form = SimpleRegisterForm()
    if form.validate_on_submit():
        user_grade = int(form.grade_numb.data + form.grade_let.data)
        resp = make_response(redirect(f'/116/{user_grade}'))
        resp.set_cookie("grade", str(user_grade), max_age=15552000)
        resp.set_cookie("group", form.group.data, max_age=15552000)
        return resp
    return render_template('simple_form.html', form=form)


@app.route('/116/<grade>')
def grade_page(grade:int):
    grade = int(grade)
    try:
        user_grade = int(request.cookies.get('grade'))
        if grade == user_grade:
            return render_template('homework.html', hw=get_all_homework(grade, group=int(request.cookies.get("group", 0))))
        else:
            return redirect(f'/116/{user_grade}')
    except RecordNotFoundError:
        return abort(404)


@app.route('/116/<grade>/<sub>')
def homework_page(grade:int, sub: str):
    try:
        return render_template('lon_hw.html', hw=get_homework(grade, sub))
    except RecordNotFoundError:
        return abort(404)
    

@app.route('/116/login', methods=['GET', 'POST'])
def admin_login():
    form = AdminLoginForm()
    if form.validate_on_submit():
        try:
            user = get_user(form.tg.data, form.password.data, to_dict=False)
            login_user(user, remember=form.remember_me.data)
            resp = make_response(redirect(f'/116/{user.grade_id}'))
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
        

@app.route('/116/new', methods=['GET', 'POST'])
@login_required
def new_homework():
    form = HomeworkForm()
    form.subject.choices = get_subs(int(request.cookies.get('grade')), int(request.cookies.get('group')), return_name=True)
    if form.validate_on_submit():
        image = []
        print(form.images.data)
        for file in form.images.data:
            if file:
                file_name = secure_filename(uuid4().hex + '.png')
                file.save(os.path.join('all', 'dynamic', 'img', 'actual', file_name))
                image.append(file_name)
        add_homework(current_user.grade_id, form.subject.data, current_user.tg, form.text.data, ';'.join(image), find_by='name')
        return redirect(f'/116/{current_user.grade_id}')
    return render_template('simple_form.html', form=form)


if __name__ == '__main__':
    app.run(port=8080, host='127.0.0.1')