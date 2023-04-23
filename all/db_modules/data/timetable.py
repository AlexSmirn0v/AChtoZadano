import sqlalchemy
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy import orm 
from .db_session import SqlAlchemyBase


class Timetable(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'timetable'
    __table_args__ = {'extend_existing': True}

    weekday = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    lesson = sqlalchemy.Column(sqlalchemy.Integer)
    sub = orm.relationship("Subject")
    sub_token = sqlalchemy.Column(sqlalchemy.String, sqlalchemy.ForeignKey("subjects.token"))
    grade = orm.relationship("Grade")
    grade_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("grades.id"))