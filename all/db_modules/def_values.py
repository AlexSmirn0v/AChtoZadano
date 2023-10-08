from datetime import datetime
import json 
import os
import csv
import dotenv
from time import sleep
from data import db_session
from data.grades import Grade
from data.timetable import Timetable
from data.homework import Homework
from data.subjects import Subject
from data.users import User

dotenv.load_dotenv()

all_dir = os.path.dirname(os.path.dirname(__file__))
path = os.path.join(all_dir, "db_modules", "db", "116.db")
db_session.global_init(path)

grades_subjects = json.load(open(all_dir + '/db_modules/def_data/grades_and_subs.json', 'r', encoding='utf8'))


def timetable_parser(filename='timetable.csv', delimiter=';', teacher_delimiter='&', group_delimiter='/', date_delimiter='_'):
    with open(all_dir + f'/db_modules/def_data/{filename}', 'r', encoding='utf-8-sig') as file:
        db_sess = db_session.create_session()
        info = db_sess.query(Subject).filter(Subject.token == 'info').first()
        for line in csv.DictReader(file, delimiter=delimiter):
            print(line)
            grade = Grade()
            grade.name_to_id(line['grade'])
            grade = db_sess.query(Grade).filter(Grade.id == grade.id).all()
            if grade:
                grade: Grade = grade[0]
            else:
                if line.get('eng_teacher_1'):
                    grade.eng_teachers = line['eng_teacher_1'] + teacher_delimiter + line['eng_teacher_2']
                grade.subs = [info]

                db_sess.add(grade)
                db_sess.commit()
            for date in line.keys():
                if date[0].isnumeric() and line[date]:
                    weekday, lesson = map(int, date.split(date_delimiter))
                    line[date] = line[date].strip()
                    if group_delimiter in line[date]:
                        sub_names = line[date].split(group_delimiter)
                        for group, sub_name in enumerate(sub_names):
                            if '-' in sub_name:
                                continue
                            sub_name = sub_name + f', {group + 1} группа'
                            subject = db_sess.query(Subject).filter(Subject.name == sub_name).first()
                            if subject and subject not in grade.subs:
                                grade.subs.append(subject)

                            single_lesson = Timetable()
                            single_lesson.weekday = weekday
                            single_lesson.lesson = lesson
                            single_lesson.grade = grade
                            single_lesson.sub = subject
                            db_sess.add(single_lesson)
                    else:
                        subject = db_sess.query(Subject).filter(Subject.name == line[date]).first()
                        
                        if subject and subject not in grade.subs:
                            grade.subs.append(subject)

                        single_lesson = Timetable()
                        single_lesson.weekday = weekday
                        single_lesson.lesson = lesson
                        single_lesson.grade = grade
                        single_lesson.sub = subject
                        db_sess.add(single_lesson)
            db_sess.commit()


def def_values(def_sub=False, def_grades=False, def_timetable=False, def_admins=False, def_homework=False):
    if def_sub:
        for sub in open(all_dir + "/db_modules/def_data/subjects.txt", 'r', encoding='utf8').readlines():
            subject = Subject()
            subject.name, subject.token, nothing = sub.rstrip().split('-')
            db_sess = db_session.create_session()
            if not db_sess.query(Subject).filter(Subject.token == subject.token).all():
                if subject.name.endswith('1 группа'):
                    subject.group = 1
                elif subject.name.endswith('2 группа'):
                    subject.group = 2
                elif subject.token == 'info':
                    subject.group = 3
                else:
                    subject.group = 0
                db_sess = db_session.create_session()
                db_sess.add(subject)
                db_sess.commit()
    if def_grades:
        db_sess = db_session.create_session()
        for grade_name in grades_subjects.keys():
            grade = Grade()
            grade.name_to_id(grade_name)
            db_grade = db_sess.query(Grade).filter(Grade.id == grade.id).all()
            if db_grade:
                grade = db_grade[0]
            grade.subs = list()
            grades_subjects[grade_name].append('info')
            for sub_token in grades_subjects[grade_name]:
                if type(sub_token) == str:
                    sub = db_sess.query(Subject).filter(Subject.token == sub_token).first()
                    if sub not in grade.subs:
                        grade.subs.append(sub)
                else:
                    eng_teachers = sub_token
                    grade.eng_teachers = '&'.join(eng_teachers)
            db_sess.add(grade)
            db_sess.commit()
        db_sess.close()
    if def_timetable:
        db_sess = db_session.create_session()
        if not db_sess.query(Timetable).all():
            timetable_parser()
        db_sess.close()
    if def_admins:
        admins = 0
        with open(all_dir + '/db_modules/def_data/superadmins.csv', 'r', encoding='utf8') as file:
            db_sess = db_session.create_session()
            for user in csv.DictReader(file, delimiter=';'):
                if not db_sess.query(User).filter(User.id == user['tg']).all():
                    admins += 1
                    grade = Grade()
                    grade.name_to_id(user['grade'])
                    if not db_sess.query(Grade).filter(Grade.id == grade.id).all():
                        db_sess.add(grade)
                    db_user = User()
                    db_user.id = user['tg']
                    db_user.grade_id = grade.id
                    db_user.group = user['group']
                    db_user.is_admin = True
                    db_user.name, db_user.surname = user['name'], user['surname']
                    db_user.set_password(os.getenv('DEF_PASSWORD'))
                    db_user.homework_added = 0
                    db_sess.add(db_user)

                    db_sess.commit()
            print(db_sess.query(User).first().to_dict(only=('name', 'surname', 'grade_id')))
            db_sess.close()
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
    if def_homework:
        db_sess = db_session.create_session()
        if not db_sess.query(User).all():
            author = User()
            author.is_admin = True
            author.id = 1
            author.name = 'superadmin'
            db_sess.add(author)
            db_sess.commit()
        for grade in db_sess.query(Grade).all():
            for sub in grade.subs:
                if db_sess.query(Homework).filter(Homework.grade_id == grade.id, Homework.sub == sub).all():
                    continue
                hw = Homework()
                hw.author_id = 1
                hw.grade = grade
                hw.sub = sub
                hw.text = 'Пока здесь ничего нет, но уже скоро твои одноклассники начнут добавлять домашние задания. Не забудьте назначить админов в классе и напомните им про собрание, которое состоится 6 сентября после третьего урока'
                hw.img_links = 'logo.png'
                sleep(0.0001)
                hw.creat_time = datetime.now()
                db_sess.add(hw)
                db_sess.commit()
        db_sess.close()

def_values(def_sub=True,
           def_grades=False,
           def_admins=False,
           def_timetable=True,
           def_homework=True)