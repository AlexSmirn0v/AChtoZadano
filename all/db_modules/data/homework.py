import datetime
import sqlalchemy
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy import orm 
from .db_session import SqlAlchemyBase


class Homework(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'homework'
    __table_args__ = {'extend_existing': True}

    creat_time = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now, primary_key=True)
    author = orm.relationship('User')
    author_tg = sqlalchemy.Column(sqlalchemy.String, 
                                sqlalchemy.ForeignKey("users.tg"))
    grade = orm.relationship('Grade')   
    grade_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("grades.id"))
    sub = orm.relationship('Subject')
    sub_token = sqlalchemy.Column(sqlalchemy.String, sqlalchemy.ForeignKey("subjects.token"))
    text = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    img_links = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    alt_text = sqlalchemy.Column(sqlalchemy.String, nullable=True)