import asyncio
import csv
import email
from email.message import EmailMessage
import logging
import os
import queue
import time
import smtplib
from datetime import datetime, timedelta
from logging.handlers import (QueueHandler, QueueListener, SMTPHandler,
                              TimedRotatingFileHandler)
from pprint import pprint
from threading import Thread

import dotenv

if __name__ == '__main__':
    from data import db_session
    from data.grades import Grade
    from data.homework import Homework
    from data.subjects import Subject
    from data.timetable import Timetable
    from data.users import User
    from send_tg import send_messages
else:
    from .data import db_session
    from .data.grades import Grade
    from .data.timetable import Timetable
    from .data.homework import Homework
    from .data.subjects import Subject
    from .data.users import User
    from .send_tg import send_messages

import json


class SSLSMTPHandler(SMTPHandler):
    def emit(self, record):
        try:
            port = self.mailport
            if not port:
                port = smtplib.SMTP_PORT
            smtp = smtplib.SMTP_SSL(self.mailhost, port)
            msg = EmailMessage()
            msg['From'] = self.fromaddr
            msg['To'] = ','.join(self.toaddrs)
            msg['Subject'] = self.getSubject(record)
            msg['Date'] = email.utils.localtime()
            msg.set_content(self.format(record))
            if self.username:
                smtp.login(self.username, self.password)
            smtp.send_message(msg, self.fromaddr, self.toaddrs)
            smtp.quit()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


dotenv.load_dotenv()
all_dir = os.path.dirname(os.path.dirname(__file__))
path = os.path.join(all_dir, "db_modules", "db", "116.db")
db_session.global_init(path)
alice = 0

with open(all_dir + '/db_modules/def_data/superadmins.csv', 'r', encoding='utf8') as file:
    db_sess = db_session.create_session()
    superadmins_id = list()
    for user in csv.DictReader(file, delimiter=';'):
        superadmins_id.append(int(user['tg']))

if not int(os.getenv("DEBUG")):
    the_logger = logging.getLogger()
    the_logger.setLevel(logging.INFO)

    log_queue = queue.Queue()
    queue_handler = QueueHandler(log_queue)

    with open(os.path.join(os.path.dirname(__file__), 'def_data', 'prod_team.csv'), encoding='utf8') as admins:
        a = list(csv.reader(admins, delimiter=';'))
        prod_team = a[0]

    handler = TimedRotatingFileHandler(os.path.join(
        all_dir, 'dynamic', 'logs', 'actions'), when='midnight', interval=1, backupCount=14, encoding='utf8')
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    smtp_handler = SSLSMTPHandler(mailhost=('smtp.yandex.com', 465),
                                  subject='Проблемы в работе achtozadano',
                                  fromaddr=os.getenv('YAN_LOGIN'),
                                  toaddrs=prod_team,
                                  credentials=(os.getenv('YAN_LOGIN'),
                                               os.getenv('YAN_PASSWORD')),
                                  secure=())

    handler.setFormatter(formatter)
    smtp_handler.setFormatter(formatter)
    smtp_handler.setLevel(logging.WARNING)
    the_logger.addHandler(queue_handler)

    queue_listener = QueueListener(
        log_queue, handler, smtp_handler, respect_handler_level=True)
    queue_listener.start()


class AccessNotAllowedError(Exception):
    pass


class RecordNotFoundError(Exception):
    pass


class RecordExistsError(Exception):
    pass


def add_values(what_add):
    try:
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
        json.dump(variables, open(os.path.join(all_dir, 'dynamic',
                'logs', 'variables.json'), 'w', encoding='utf8'))
    except json.decoder.JSONDecodeError:
        pass


def get_homework(grade_id: int, sub, find_by='token', log=True, to_dict=True):
    db_sess = db_session.create_session()
    if find_by == 'id':
        subject = db_sess.query(Subject).filter(Subject.id == int(sub)).first()
        hw = db_sess.query(Homework).filter(
            Homework.grade_id == grade_id, Homework.sub == subject).all()
    elif find_by == 'token':
        hw = db_sess.query(Homework).filter(
            Homework.grade_id == grade_id, Homework.sub_token == sub).all()
    elif find_by == 'name':
        subject = db_sess.query(Subject).filter(Subject.name == sub).first()
        hw = db_sess.query(Homework).filter(
            Homework.grade_id == grade_id, Homework.sub == subject).all()
    else:
        db_sess.close()
        raise KeyError
    if not hw:
        db_sess.close()
        raise RecordNotFoundError
    hw_list = list()
    for homework in hw:
        if to_dict:
            hw_dict = homework.to_dict(only=('author.name', 'author.surname', 'grade.id', 'grade.name', 'text', 'img_links',
                                       'creat_time', 'sub', '-sub.grades'), datetime_format="%d.%m.%Y в %H:%M")
            if hw_dict['img_links']:
                hw_dict['img_links'] = hw_dict['img_links'].split(';')
        else:
            hw_dict = homework
        hw_list.append(hw_dict)
    if len(hw_list) == 1:
        hw_list = hw_list[0]
    db_sess.close()
    if log:
        t = Thread(target=add_values, args=[
                   'homework_requested'], daemon=False)
        t.start()
    return hw_list


def get_homework_by_date(grade_id: int, group: int, weekday: int, include_info: bool=False) -> list:
    db_sess = db_session.create_session()
    table = db_sess.query(Timetable).filter(Timetable.grade_id == grade_id, Timetable.weekday == weekday).all()
    if table:
        table = list(filter(lambda tt: tt.sub.group in [0, group], table))
        table.sort(key=lambda tt: tt.lesson)
        subj_list = list(map(lambda tt: [tt.sub_token, tt.lesson], table))
        grade = Grade()
        grade.id = grade_id
        grade_name = grade.name()
        res = list()
        if include_info:
            info_hw = get_homework(grade_id, 'info')
            if type(info_hw) == dict:
                res.append([info_hw])
            else:
                res.append(info_hw)

        now = datetime.now()
        now_weekday = now.weekday()
        #this thing definitely needs comments))
        #if time is more than 2 o'clock, than we don't need to look for subjects for this day - school day is already over
        #also if it's a weekend we should count straight from Monday
        if now_weekday == 6 or (now_weekday == 5 and now.hour > 14):
            now_weekday = 0
        elif now.hour > 14:
            now_weekday += 1

        if now_weekday > weekday:
            week_range = list(range(0, weekday))
            week_range.extend(range(now_weekday, 6))
        else:
            week_range = list(range(now_weekday, weekday))

        for sub_token, lesson in subj_list:
            if db_sess.query(Timetable).filter(Timetable.sub_token == sub_token, 
                                            Timetable.grade_id == grade_id, 
                                            Timetable.weekday.in_(week_range)).first():
                sub = db_sess.query(Subject).filter(Subject.token == sub_token).first()
                homework = {
                    'grade': {
                        'id': grade_id,
                        'name': grade_name
                    },
                    'sub': sub.to_dict(only=('group', 'id', 'name', 'token')),
                    'is_available': False
                }
            else:
                homework = get_homework(grade_id, sub_token)
                homework['is_available'] = True
            homework['lesson'] = lesson
            res.append(homework)
    else:
        res = list()

    db_sess.close()
    return res



def add_homework(grade_id: int, sub, author_id: int, text: str = None, img_links=None, alt_text=None, find_by='token'):
    db_sess = db_session.create_session()
    if find_by == 'id':
        subject = db_sess.query(Subject).filter(Subject.id == int(sub)).first()
        hw = db_sess.query(Homework).filter(
            Homework.grade_id == grade_id, Homework.sub == subject).first()
    elif find_by == 'token':
        hw = db_sess.query(Homework).filter(
            Homework.grade_id == grade_id, Homework.sub_token == sub).first()
    elif find_by == 'name':
        subject = db_sess.query(Subject).filter(Subject.name == sub).first()
        hw = db_sess.query(Homework).filter(
            Homework.grade_id == grade_id, Homework.sub == subject).first()
    else:
        db_sess.close()
        raise KeyError
    if not hw:
        db_sess.close()
        raise RecordNotFoundError
    author = get_user(author_id)
    if (author['is_admin'] and author['grade']['id'] == grade_id and (author['group'] == hw.sub.group or hw.sub.group == 0 or hw.sub.group == 3)) or author_id in superadmins_id:
        if hw.sub_token == 'info':
            infos = sorted(db_sess.query(Homework).filter(
                Homework.grade_id == grade_id, Homework.sub_token == 'info').all(), key=lambda x: x.creat_time)
            if len(infos) < 3:
                hw = Homework()
                hw.sub_token = 'info'
                hw.grade_id = grade_id
            else:
                hw = infos[0]

        if hw.img_links and hw.img_links != 'logo.png':
            for filename in hw.img_links.split(';'):
                os.remove(os.path.join(all_dir, 'dynamic', 'img', 'actual', filename))
        hw.img_links = None

        user = db_sess.query(User).filter(User.id == author_id).first()
        user.homework_added += 1
        hw.author_id = author_id
        hw.text = text
        hw.creat_time = datetime.now()
        if type(img_links) == str:
            hw.img_links = img_links
        elif img_links:
            hw.img_links = ';'.join(img_links)
        db_sess.add(hw)
        db_sess.commit()
        t = Thread(target=add_values, args=['homework'], daemon=False)
        recipients = get_users_by_grade(grade_id, hw.sub.group)
        if hw.author_id in recipients:
            recipients.remove(hw.author_id)
        mess_text = f"{hw.sub.name}, {hw.author.name} {hw.author.surname}"
        if text:
            mess_text += f'\n{text}'

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:  # 'RuntimeError: There is no current event loop...'
            loop = None

        if loop and loop.is_running():
            print('Async event loop already running. Adding coroutine to the event loop.')
            loop.create_task(send_messages(
                recipients,
                mess_text,
                img_links))
            # ^-- https://docs.python.org/3/library/asyncio-task.html#task-object
            # Optionally, a callback function can be executed when the coroutine completes
        else:
            print('Starting new event loop')
            asyncio.run(send_messages(
                recipients,
                mess_text,
                img_links))

        t.start()
        if not int(os.getenv('DEBUG')):
            the_logger.info(
                f'Новое дз по предмету {hw.sub.name} в {hw.grade.name()} опубликовал {hw.author.name} {hw.author.surname}')
        db_sess.close()
    else:
        db_sess.close()
        raise AccessNotAllowedError


def add_user(user_id: str, grade_name: str, group: int, is_admin=False, name=None, surname=None, password=None, from_alice=False):
    if from_alice:
        alice_dict: dict = json.load(open(os.path.join(all_dir, "db_modules", "db", "alice_dict.json")))
        if alice_dict:
            dict_id = max(alice_dict.values()) + 1
        else:
            dict_id = 5
            alice_dict = dict()
        alice_dict[user_id] = dict_id
        json.dump(alice_dict, open(os.path.join(all_dir, "db_modules", "db", "alice_dict.json"), 'w'))
        user_id = dict_id

    db_sess = db_session.create_session()
    if not db_sess.query(User).filter(User.id == user_id).all():
        grade = Grade()
        check = grade.name_to_id(grade_name)
        if not db_sess.query(Grade).filter(Grade.id == grade.id).all() or not check:
            db_sess.close()
            raise RecordNotFoundError
        user = User()
    else:
        db_sess.close()
        raise RecordExistsError
    user.id = user_id
    user.grade_id = grade.id
    user.group = group
    if from_alice:
        user.from_tg = False
    if is_admin:
        user.is_admin = True
        user.name, user.surname = name, surname
        user.homework_added = 0
        if password:
            user.set_password(password)
    db_sess.add(user)
    db_sess.commit()
    if not int(os.getenv('DEBUG')):
        if is_admin:
            the_logger.info(
                f'Новый админ {user.name} {user.surname} в {user.grade.name()} зарегистрировался')
            t = Thread(target=add_values, args=['admin'], daemon=False)
        elif not from_alice:
            the_logger.info(
                f'Новый пользователь {user.id} в {user.grade.name()} зарегистрировался')
            t = Thread(target=add_values, args=['user'], daemon=False)
        else:
            the_logger.info(
                f'Новый пользователь в {user.grade.name()} зарегистрировался через Алису')
            t = Thread(target=add_values, args=['alice'], daemon=False)
        t.start()
    db_sess.close()


def change_user_mode(user_id: int):
    user_id = int(user_id)
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.id == user_id).first()
    if not user:
        db_sess.close()
        raise RecordNotFoundError
    
    state = not user.is_chatmode
    user.is_chatmode = state
    
    db_sess.commit()
    db_sess.close()
    return state


def get_user(user_id: int=None, password=None, to_dict=True, return_error=True, name=None, surname=None):
    db_sess = db_session.create_session()
    if name and surname:
        users = db_sess.query(User).filter(User.name == name and User.surname == surname).all()
        user = None
        for single_user in users:
            if single_user.check_password(password):
                user = single_user
                break
    elif user_id:
        user_id = int(user_id)
        user = db_sess.query(User).filter(User.id == user_id).first()
    else:
        if return_error:
            raise AttributeError
        else:
            return False

    if not user:
        if return_error:
            db_sess.close()
            raise RecordNotFoundError
        else:
            return False
    if to_dict:
        res = user.to_dict(rules=('-grade.subs', 'grade.name',
                           '-hashed_password', '-grade_id'))
    else:
        res = user
    db_sess.close()
    return res


def get_subs(grade, group=0, return_name=False, grade_name=False, return_token=False):
    db_sess = db_session.create_session()
    if grade_name:
        prot_grade = Grade()
        check = prot_grade.name_to_id(grade)
        if check:
            grade_id = prot_grade.id
        else:
            db_sess.close()
            raise RecordNotFoundError
    else:
        grade_id = grade
    grade = db_sess.query(Grade).filter(Grade.id == grade_id).first()
    if not grade:
        db_sess.close()
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
    elif return_token and group == 0:
        res = [sub.token for sub in grade.subs]
    elif return_token:
        res = list()
        for subject in grade.subs:
            if subject.group == 0 or subject.group == group:
                res.append(subject.token)
    else:
        res = list()
        for subject in grade.subs:
            if subject.group == 0 or subject.group == group:
                res.append(subject.id)
    db_sess.close()
    return res


def get_grade(grade, name=True):
    db_sess = db_session.create_session()
    if name:
        prot_grade = Grade()
        check = prot_grade.name_to_id(grade)
        if check:
            grade_id = prot_grade.id
        else:
            db_sess.close()
            raise RecordNotFoundError
    else:
        grade_id = grade
    grade = db_sess.query(Grade).filter(Grade.id == grade_id).first()
    if not grade:
        db_sess.close()
        raise RecordNotFoundError
    res = {
        "name": grade.name(),
        "id": grade.id,
        "eng_teachers": grade.eng_teachers.split('&')
    }
    return res


def delete_homework(grade_id: int, sub, text='Домашнее задание было удалено по решению администрации за нарушение правил публикации'):
    db_sess = db_session.create_session()
    try:
        subject = db_sess.query(Subject).filter(Subject.id == int(sub)).first()
        hw = db_sess.query(Homework).filter(
            Homework.grade_id == grade_id, Homework.sub == subject).first()
    except ValueError:
        hw = db_sess.query(Homework).filter(
            Homework.grade_id == grade_id, Homework.sub_token == sub).first()
    if not hw:
        db_sess.close()
        raise RecordNotFoundError
    hw.author_id = 1
    hw.text = text
    hw.creat_time = datetime.now()
    if hw.img_links and hw.img_links != 'logo.png':
        for i, filename in enumerate(hw.img_links.split(';')):
            os.replace(os.path.join(all_dir, 'dynamic', 'img', 'actual', filename),
                       os.path.join(all_dir, 'dynamic', 'img', 'archive', f"{hw.author.name}-{hw.author.surname}-{hw.sub_token}-{i + 1}.png"))
    hw.img_links = 'logo.png'
    db_sess.close()


def delete_user(user_id: int=None, name: str=None, surname: str=None, grade_id: int=None):
    db_sess = db_session.create_session()
    if user_id:
        user = db_sess.query(User).filter(User.id == user_id).first()
    else:
        user = db_sess.query(User).filter(User.name == name and User.surname == surname and User.grade_id == grade_id).first()
    if not user:
        db_sess.close()
        raise RecordNotFoundError
    added_hw = db_sess.query(Homework).filter(Homework.author_id == user.id)
    for hw in added_hw:
        hw.author_id = 1
        hw.creat_time = datetime.now()
        hw.img_links = 'logo.png'
        hw.text = 'Пользователь удалил свой аккаунт на AChtoZadano или перерегистрировался'
        time.sleep(0.0001)
    db_sess.commit()
    db_sess.delete(user)
    db_sess.commit()
    db_sess.close()


def get_all_users():
    db_sess = db_session.create_session()
    res = [get_user(user.id) for user in db_sess.query(User).all()]
    db_sess.close()
    return res


def get_users_by_grade(grade: int, group: int=0, only_id=True, only_chatmode:bool = True):
    db_sess = db_session.create_session()
    
    if group == 3: #info should have group 3, that means top priority
        users_list = db_sess.query(User).filter(User.grade_id == grade, User.from_tg).all()
    elif group == 0:
        users_list = db_sess.query(User).filter(User.grade_id == grade, User.from_tg).all()
    else:
        users_list = db_sess.query(User).filter(User.grade_id == grade, User.group == group, User.from_tg).all()
    if only_chatmode and group != 3:
        users_list = filter(lambda user: user.is_chatmode, users_list)
    if only_id:
        res = [user.id for user in users_list]
    else:
        res = [get_user(user.id) for user in users_list]
    db_sess.close()
    return res


def get_homework_by_grade(grade: int, group=0, to_dict=True, include_info=True):
    t = Thread(target=add_values, args=['homework_requested'], daemon=False)
    t.start()
    if group == 0:
        return [get_homework(grade, subject, find_by='id', log=False, to_dict=to_dict) for subject in get_subs(grade)]
    else:
        res = list()
        db_sess = db_session.create_session()
        for subject in get_subs(grade, group):
            homework = get_homework(grade, subject, find_by='id', log=False)
            obj_homework = get_homework(grade, subject, find_by='id', log=False, to_dict=False)

            res.append([obj_homework.creat_time, homework if to_dict else obj_homework])
        res.sort(key=lambda x: x[0], reverse=True)
        res = list(map(lambda x: x[1], res))
        if include_info:
            info_hw = get_homework(grade, 'info')
            if type(info_hw) == dict:
                res.insert(0, [info_hw])
            else:
                res.insert(0, info_hw)
        db_sess.close()
        return res


def get_all_grades():
    db_sess = db_session.create_session()
    res = sorted([get_grade(grade.id, name=False) for grade in db_sess.query(Grade).all()],
                 key=lambda x: x['id'])
    db_sess.close()
    return res


def get_list_of_dates(grade_id: int):
    weekday_full = [
        "Понедельник",
        "Вторник",
        "Среда",
        "Четверг",
        "Пятница",
        "Суббота"
    ]
    today = datetime.now()
    today_date = today.date()
    today_weekday = today_date.weekday()
    date_list = list()
    if today.hour <= 15:
        week_range = range(0, 7)
    else:
        week_range = range(1, 8)
    for day in week_range:
        date = today_date + timedelta(days=day)
        if not (date.weekday() == 6 or (grade_id // 10 < 6 and date.weekday() == 5)):
            date_list.append((date.weekday(), f"{weekday_full[date.weekday()]}, {date.strftime('%d.%m')}"))
    return list(date_list)


if __name__ == '__main__':
    start_time = time.time()
    today = datetime.now()
    print(get_list_of_dates(93))
    print(get_homework(93, 'info'))
    #print(get_homework_by_date(93, 2, date.today()))
    # add_user('@kate', '3А', 2, True, 'Катя', 'Смирнова', "why not")
    pprint(get_user(name='Александр', surname='Смирнов', password=os.getenv('DEF_PASSWORD')))
    print(get_grade('''11"А"'''))
    #pprint(get_subs(93, 2))
    #add_homework(93, 'info', os.getenv('MY_CHAT_ID'), 'Срочное собрание всех админов в 10 кабинете, ')
    #pprint(get_homework_by_grade(93, group=2))
    #print(get_users_by_grade(93))
    #pprint(get_homework(93, 'info'))
    pprint(get_homework_by_date(93, 2, 1))
    print("--- %s seconds ---" % (time.time() - start_time))
    #print(get_all_grades())
    #pprint(get_homework_by_date(93, 2, 0))
