import csv
import logging
import os
import queue
import time
from datetime import datetime
from logging.handlers import (QueueHandler, QueueListener, SMTPHandler,
                              TimedRotatingFileHandler)
from pprint import pprint
from random import randint
from threading import Thread

import dotenv

if __name__ == '__main__':
    from data import db_session
    from data.grades import Grade
    from data.homework import Homework
    from data.subjects import Subject
    from data.timetable import Timetable
    from data.users import User
    from other_utils.emailer import SSLSMTPHandler    
else:
    from .data import db_session
    from .data.grades import Grade
    from .data.timetable import Timetable
    from .data.homework import Homework
    from .data.subjects import Subject
    from .data.users import User  
    from ..other_utils.emailer import SSLSMTPHandler     

import json

dotenv.load_dotenv()
all_dir = os.path.dirname(os.path.dirname(__file__))
path = os.path.join(all_dir, "db_modules", "db", "116.db")
db_session.global_init(path)
alice = 0

the_logger = logging.getLogger()
the_logger.setLevel(logging.INFO)

log_queue = queue.Queue()
queue_handler = QueueHandler(log_queue)

with open(os.path.join(os.path.dirname(__file__), 'def_data', 'prod_team.csv'), encoding='utf8') as admins:
    a = list(csv.reader(admins, delimiter=';'))
    prod_team = a[0]

handler = TimedRotatingFileHandler(os.path.join(all_dir, 'dynamic', 'logs', 'actions'), when='midnight', interval=1, backupCount=14, encoding='utf8')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
smtp_handler = SSLSMTPHandler(mailhost=('smtp.yandex.com', 465),
                            subject='Проблемы в работе achtozadano',
                            fromaddr=os.getenv('YAN_LOGIN'),
                            toaddrs=prod_team,
                            credentials=(os.getenv('YAN_LOGIN'), os.getenv('YAN_PASSWORD')),
                            secure=())

handler.setFormatter(formatter)
smtp_handler.setFormatter(formatter)
smtp_handler.setLevel(logging.WARNING)
the_logger.addHandler(queue_handler)

queue_listener = QueueListener(log_queue, handler, smtp_handler, respect_handler_level=True) 
queue_listener.start()

class AccessNotAllowedError(Exception):
    pass


class RecordNotFoundError(Exception):
    pass


class RecordExistsError(Exception):
    pass


def add_values(what_add):
    variables = json.load(open(os.path.join(all_dir, 'dynamic', 'logs', 'variables.json'), encoding='utf8'))
    if what_add == 'admin':
        variables['admins_registered'] += 1
        variables['admins_registered_today'] += 1
        variables['users_registered'] += 1
        variables['users_registered_today'] += 1
    elif what_add == 'user':
        variables['users_registered'] += 1
        variables['users_registered_today'] += 1
    elif what_add == 'homework':
        variables['homework_added'] += 1
        variables['homework_added_today'] += 1
    elif what_add == 'homework_requested':
        variables['homework_requested'] += 1
        variables['homework_requested_today'] += 1
    elif what_add == 'alice':
        global alice
        variables['alice_registered'] += 1
        variables['alice_registered_today'] += 1
        variables['users_registered'] += 1
        variables['users_registered_today'] += 1
        alice += 1
    else:
        raise KeyError
    json.dump(variables, open(os.path.join(all_dir, 'dynamic', 'logs', 'variables.json'), 'w', encoding='utf8'))


def get_homework(grade_id:int, sub, find_by='token', log=True, to_dict=True):
    db_sess = db_session.create_session()
    if find_by == 'id':
        subject = db_sess.query(Subject).filter(Subject.id == int(sub)).first()
        hw = db_sess.query(Homework).filter(Homework.grade_id == grade_id, Homework.sub == subject).all()
    elif find_by == 'token':
        hw = db_sess.query(Homework).filter(Homework.grade_id == grade_id, Homework.sub_token == sub).all()
    elif find_by == 'name':
        subject = db_sess.query(Subject).filter(Subject.name == sub).first()
        hw = db_sess.query(Homework).filter(Homework.grade_id == grade_id, Homework.sub == subject).all()
    else:
        raise KeyError
    if not hw:
        raise RecordNotFoundError
    hw_list = list()
    for homework in hw:
        if to_dict:
            hw_dict = homework.to_dict(only=('author_tg', 'grade.id', 'grade.name', 'text', 'img_links', 'creat_time', 'sub', '-sub.grades'), datetime_format="%d.%m.%Y, %H:%M:%S")
            if hw_dict['img_links']:
                hw_dict['img_links'] = hw_dict['img_links'].split(';')
        else:
            hw_dict = homework
        hw_list.append(hw_dict)
    if len(hw_list) == 1:
        hw_list = hw_list[0]
    db_sess.close()
    if log:
        t = Thread(target=add_values, args=['homework_requested'], daemon=False)
        t.start()
    return hw_list


def add_homework(grade_id:int, sub, author_tg:str, text:str=None, img_links=None, alt_text=None, find_by='token'):
    db_sess = db_session.create_session()
    if find_by == 'id':
        subject = db_sess.query(Subject).filter(Subject.id == int(sub)).first()
        hw = db_sess.query(Homework).filter(Homework.grade_id == grade_id, Homework.sub == subject).first()
    elif find_by == 'token':
        hw = db_sess.query(Homework).filter(Homework.grade_id == grade_id, Homework.sub_token == sub).first()
    elif find_by == 'name':
        subject = db_sess.query(Subject).filter(Subject.name == sub).first()
        hw = db_sess.query(Homework).filter(Homework.grade_id == grade_id, Homework.sub == subject).first()
    else:
        raise KeyError
    if not hw:
        raise RecordNotFoundError
    author = get_user(author_tg)
    if author['is_admin'] and author['grade']['id'] == grade_id and (author['group'] == hw.sub.group or hw.sub.group == 0):
        if hw.sub_token == 'info':
            infos = sorted(db_sess.query(Homework).filter(Homework.grade_id == grade_id, Homework.sub_token == 'info').all(), key=lambda x: x.creat_time)
            if len(infos) < 3:
                hw = Homework()
                hw.sub_token = 'info'
                hw.grade_id = grade_id
            else:
                hw = infos[0]
        
        if hw.img_links:
            for i, filename in enumerate(hw.img_links.split(';')):
                os.replace(os.path.join(all_dir, 'dynamic', 'img', 'actual', filename),
                        os.path.join(all_dir, 'dynamic', 'img', 'archive', f"{hw.author_tg.lstrip('@')}-{hw.sub_token}-{i + 1}.png"))
                
        user = db_sess.query(User).filter(User.tg == author_tg).first()
        user.homework_added += 1
        hw.author_tg = author_tg
        hw.text = text
        hw.creat_time = datetime.now()
        if type(img_links) == str or not img_links:
            hw.img_links = img_links
        else:
            hw.img_links = ';'.join(img_links)
        db_sess.add(hw)
        db_sess.commit()
        t = Thread(target=add_values, args=['homework'], daemon=False)
        t.start()
        the_logger.info(f'Новое дз по предмету {hw.sub.name} в {hw.grade.name()} опубликовал {hw.author_tg}')
        db_sess.close()
    else:
        db_sess.close()
        raise AccessNotAllowedError


def add_user(user_tg:str, grade_name:str, group:int, is_admin=False, name=None, surname=None, password=None):
    db_sess = db_session.create_session()
    if not db_sess.query(User).filter(User.tg == user_tg).all():
        grade = Grade()
        grade.name_to_id(grade_name)
        if not db_sess.query(Grade).filter(Grade.id == grade.id).all():
            db_sess.add(grade)
        user = User()
        user.tg = user_tg
    else:
        db_sess.close()
        raise RecordExistsError
    user.tg = user_tg
    user.grade_id = grade.id
    user.group = group
    if is_admin:
        user.is_admin = True
        user.name, user.surname = name, surname
        user.homework_added = 0
        if password:
            user.set_password(password)
    db_sess.add(user)
    db_sess.commit()
    if is_admin:
        the_logger.info(f'Новый админ {user.name} {user.surname}({user.tg}) в {user.grade.name()} зарегистрировался')
        t = Thread(target=add_values, args=['admin'], daemon=False)
    elif not user.tg.startswith('alice'):
        the_logger.info(f'Новый пользователь {user.tg} в {user.grade.name()} зарегистрировался')
        t = Thread(target=add_values, args=['user'], daemon=False)
    else:
        the_logger.info(f'Новый пользователь в {user.grade.name()} зарегистрировался через сайт')
        t = Thread(target=add_values, args=['alice'], daemon=False)
    db_sess.close()
    t.start()


def get_user(user_tg:str, password=False, to_dict=True):
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.tg == user_tg).first()
    if not user:
        raise RecordNotFoundError
    elif password:
        if not user.check_password(password):
            raise AccessNotAllowedError
    if to_dict:
        res = user.to_dict(rules=('-grade.subs', 'grade.name', '-hashed_password', '-grade_id'))
    else:
        res = user
    db_sess.close()
    return res


def get_subs(grade_id:int, group=0, return_name=False):
    db_sess = db_session.create_session()
    grade = db_sess.query(Grade).filter(Grade.id == grade_id).first()
    if not grade:
        raise RecordNotFoundError
    elif return_name and group == 0:
        res = [sub.name for sub in grade.subs]
    elif return_name:
        res = list()
        for subject in grade.subs:
            if subject.group == 0 or subject.group == group:
                res.append(subject.name)
    elif not return_name and group == 0:
        res = [sub.id for sub in grade.subs]
    else:
        for subject in grade.subs:
            if subject.group == 0 or subject.group == group:
                res.append(subject.id)
    db_sess.close()
    return res
    

def delete_homework(grade_id:int, sub):
    db_sess = db_session.create_session()
    try:
        subject = db_sess.query(Subject).filter(Subject.id == int(sub)).first()
        hw = db_sess.query(Homework).filter(Homework.grade_id == grade_id, Homework.sub == subject).first()
    except ValueError:
        hw = db_sess.query(Homework).filter(Homework.grade_id == grade_id, Homework.sub_token == sub).first()
    if not hw:
        raise RecordNotFoundError
    hw.author_tg = '@alex010407'
    hw.text = 'Домашнее задание было удалено по решению администрации за нарушение правил публикации'
    hw.creat_time = datetime.now()
    hw.img_links = None
    db_sess.close()


def delete_user(user_tg):
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.tg == user_tg).first()
    if not user:
        raise RecordNotFoundError
    db_sess.delete(user)
    db_sess.commit()


def get_all_users():
    db_sess = db_session.create_session()
    res = [get_user(user.tg) for user in db_sess.query(User).all()]
    db_sess.close()
    return res


def get_all_homework(grade:int, to_dict=True, group=0):
    t = Thread(target=add_values, args=['homework_requested'], daemon=False)
    t.start()
    if group == 0:
        return [get_homework(grade, subject, find_by='id', log=False, to_dict=to_dict) for subject in get_subs(grade)]
    else:
        res = list()
        db_sess = db_session.create_session()
        for subject in get_subs(grade):
            homework = get_homework(grade, subject, find_by='id', log=False)
            if type(homework) == list or homework['sub']['group'] in [0, group]:
                res.append(get_homework(grade, subject, find_by='id', log=False, to_dict=to_dict))
        db_sess.close()
        return res

    
    
if __name__ == '__main__':
    start_time = time.time()
    #add_user('@kate', '3А', 2, True, 'Катя', 'Смирнова', "why not")
    pprint(get_user('@alex010407'))
    pprint(get_subs(93, 2, True))
    pprint(get_all_homework(93))
    #get_all_homework(93)
    #add_homework(93, 'info', '@alex010407', 'Срочное собрание всех админов в 10 кабинете, ' + str(randint(0, 300)))
    pprint(get_homework(93, 'info'))
    print("--- %s seconds ---" % (time.time() - start_time))