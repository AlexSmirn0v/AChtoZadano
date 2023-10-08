import sqlalchemy
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy import orm
from .db_session import SqlAlchemyBase

TRANSFORMER = {
    1: "А",
    2: "Б",
    3: "В",
    4: "Г"
}

RETRANSFORMER = dict()
for key in TRANSFORMER.keys():
    RETRANSFORMER[TRANSFORMER[key]] = key


class Grade(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'grades'
    __table_args__ = {'extend_existing': True}

    id = sqlalchemy.Column(sqlalchemy.Integer, unique=True, primary_key=True)
    subs = orm.relationship("Subject",
                            secondary="grades_to_subjects",
                            backref="grades",
                            lazy='subquery')
    eng_teachers = sqlalchemy.Column(sqlalchemy.String(150))
    
    def name(self) -> None:
        self.namer = f"{str(self.id // 10)}{TRANSFORMER[self.id % 10]}"
        return self.namer

    def name_to_id(self, name:str):
        name = str(name)
        for elem in ['''"''', " ", "'", '.']:
            name = name.replace(elem, "")
        try:
            self.id = int(name[:-1]) * 10 + RETRANSFORMER[name[-1].upper()]
            return True
        except KeyError:
            return False