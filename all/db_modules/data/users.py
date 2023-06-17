import datetime
import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from flask_login import UserMixin
from .db_session import SqlAlchemyBase
from werkzeug.security import generate_password_hash, check_password_hash


class User(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = 'users'
    __table_args__ = {'extend_existing': True}
    
    tg = sqlalchemy.Column(sqlalchemy.String, nullable=False, index=True, primary_key=True)
    grade = orm.relationship('Grade')
    grade_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("grades.id"))
    group = sqlalchemy.Column(sqlalchemy.Integer)
    is_admin = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=True) 
    surname = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    homework_added = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)
    hashed_password = sqlalchemy.Column(sqlalchemy.String, nullable=True)

    def get_id(self):
        return self.tg

    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        if self.hashed_password:
            return check_password_hash(self.hashed_password, password)
        else:
            return False