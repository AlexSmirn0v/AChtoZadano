from datetime import datetime
import json 
import os
import csv
from time import sleep
from data import db_session
from data.grades import Grade
from data.timetable import Timetable
from data.homework import Homework
from data.subjects import Subject
from data.users import User

all_dir = os.path.dirname(os.path.dirname(__file__))
path = os.path.join(all_dir, "db_modules", "db", "116.db")
print(path)
db_session.global_init(path)

grades_subjects = json.load(open(all_dir + '/db_modules/def_data/grades_and_subs.json', 'r', encoding='utf8'))
print(grades_subjects)

def def_values(def_sub=True, def_grades=True, def_admins=True, def_timetable=True, def_homework=True):
    if def_sub:
        for sub in open(all_dir + "/db_modules/def_data/subjects.txt", 'r', encoding='utf8').readlines():
            subject = Subject()
            subject.name, subject.token = sub.rstrip().split('-')
            if subject.name.endswith('1 группа'):
                subject.group = 1
            elif subject.name.endswith('2 группа'):
                subject.group = 2
            else:
                subject.group = 0
            db_sess = db_session.create_session()
            db_sess.add(subject)
            db_sess.commit()
    if def_grades:
        for grade_name in grades_subjects.keys():
            db_grade = Grade()
            db_grade.name_to_id(grade_name)
            grades_subjects[grade_name].append('info')
            for sub_token in grades_subjects[grade_name]:
                db_sess = db_session.create_session()
                sub = db_sess.query(Subject).filter(Subject.token == sub_token).first()
                if sub not in db_grade.subs:
                    db_sess.commit()
                    db_grade.subs.append(sub)
                db_sess.close()
            db_sess = db_session.create_session()
            db_sess.add(db_grade)
            db_sess.commit()
    if def_admins:
        admins = 0
        with open(all_dir + '/db_modules/def_data/superadmins.csv', 'r', encoding='utf8') as file:
            for user in csv.DictReader(file, delimiter=';'):
                db_sess = db_session.create_session()
                if not db_sess.query(User).filter(User.tg == user['tg']).all():
                    admins += 1
                    grade = Grade()
                    grade.name_to_id(user['grade'])
                    if not db_sess.query(Grade).filter(Grade.id == grade.id).all():
                        db_sess.add(grade)
                    db_user = User()
                    db_user.tg = user['tg']
                    db_user.grade_id = grade.id
                    db_user.group = user['group']
                    db_user.is_admin = True
                    db_user.name, db_user.surname = user['name'], user['surname']
                    db_user.homework_added = 0
                    db_sess.add(db_user)

                    db_sess.commit()
        variables = {
            'admins_registered': admins,
            'admins_registered_today': admins,
            'users_registered': admins,
            'users_registered_today': admins,
            'alice_registered': 0,
            'alice_registered_today': 0,
            'homework_added': 0,
            'homework_added_today': 0,
            'homework_requested': 0,
            'homework_requested_today': 0
        }
        json.dump(variables, open(os.path.join(all_dir, 'dynamic', 'logs', 'variables.json'), 'w'))
    if def_timetable:
        pass
    if def_homework:
        db_sess = db_session.create_session()
        for grade in db_sess.query(Grade).all():
            for sub in grade.subs:
                hw = Homework()
                hw.author_tg = '@alex010407'
                hw.grade = grade
                hw.sub = sub
                hw.text = 'Пока здесь ничего нет, но уже скоро твои одноклассники начнут добавлять домашние задания. Не забудьте назначить админов в классе и напомните им про собрание, которое состоится 3 сентября в 15:30'
                sleep(0.0001)
                hw.creat_time = datetime.now()
                db_sess.add(hw)
                db_sess.commit()


def_values()