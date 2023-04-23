import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin 
from .db_session import SqlAlchemyBase
   
association_table = sqlalchemy.Table(
    'grades_to_subjects',
    SqlAlchemyBase.metadata,
    sqlalchemy.Column('grades', sqlalchemy.Integer,
                      sqlalchemy.ForeignKey('grades.id')),
    sqlalchemy.Column('subjects', sqlalchemy.Integer,
                      sqlalchemy.ForeignKey('subjects.id'))
)

class Subject(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'subjects'
    __table_args__ = {'extend_existing': True}
    
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, 
                           autoincrement=True, index=True)
    name = sqlalchemy.Column(sqlalchemy.String, unique=True)
    token = sqlalchemy.Column(sqlalchemy.String, index=True)
    group = sqlalchemy.Column(sqlalchemy.Integer)
    #grades = orm.relationship("Grade", back_populates="subjects")