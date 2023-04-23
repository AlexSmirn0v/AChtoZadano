from flask_restful import reqparse, abort, Api, Resource
from flask import jsonify
import dotenv
from os import getenv
if __name__ == '__main__':
    from db_modules.db_utils import *
else:
    from .db_modules.db_utils import *

dotenv.load_dotenv()
parser = reqparse.RequestParser()
parser.add_argument('api_key', required=True, type=str)
parser.add_argument('author_tg', required=True, type=str)
parser.add_argument('text', required=True, type=str)
parser.add_argument('img_links', required=True, type=list)
parser.add_argument('alt_text', required=False, type=str)

user_parser = reqparse.RequestParser()
parser.add_argument('api_key', required=True, type=str)
user_parser.add_argument('user_tg', required=True, type=str)
user_parser.add_argument('grade_name', required=True, type=str)
user_parser.add_argument('group', required=True, type=int)
user_parser.add_argument('is_admin', required=True, type=bool)
user_parser.add_argument('name', required=False, type=str)
user_parser.add_argument('surname', required=False, type=str)
user_parser.add_argument('password', required=False, type=str)


class HomeworkResource(Resource):
    def get(self, grade:int, subject, key:str):
        if key == getenv["API_KEY"]:
            try:
                res = jsonify(get_homework(grade, subject))
                return res
            except RecordNotFoundError:
                abort(404, message="Your requested homework wasn't found")
        else:
            abort(403, "Wrong api-key")
    def delete(self, grade:int, subject:int, key:str):
        if key == getenv["API_KEY"]:
            try:
                delete_homework(grade, subject)
                return jsonify({'success': 'OK'})
            except RecordNotFoundError:
                abort(404, message="Your requested homework wasn't found")
        else:
            abort(403, "Wrong api-key")
    def update(self, grade:int, subject:int, key:str):
        if key == getenv["API_KEY"]:
            args = parser.parse_args()
            try:
                add_homework(grade, subject, args['author_tg'], args['text'], args['img_links'], args['alt_text'])
                return jsonify({'success': 'OK'})
            except RecordNotFoundError:
                abort(404, message="The homework you wanted to edit homework wasn't found")
            except AccessNotAllowedError:
                abort(403, message="You don't have right to add homework for this subject")
        else:
            abort(403, "Wrong api-key")

        
class HomeworkListResource(Resource):
    def get(self, grade:int, key:str):
        if key == getenv["API_KEY"]:
            try:
                return jsonify(get_all_homework(grade))
            except RecordNotFoundError:
                abort(404, message="The requested grade wasn't found")
        else:
            abort(403, "Wrong api-key")
    

class UserResource(Resource):
    def get(self, user_tg, key:str):
        if key == getenv["API_KEY"]:
            user_tg = '@' + user_tg
            try:
                return jsonify(get_user(user_tg))
            except RecordNotFoundError:
                abort(404, message="Requested user wasn't found")
        else:
            abort(403, "Wrong api-key")
    def delete(self, user_tg, key:str):
        if key == getenv["API_KEY"]:
            user_tg = '@' + user_tg
            try:
                delete_user(user_tg)
                return jsonify({'success': 'OK'})
            except RecordNotFoundError:
                abort(404, message="Requested user wasn't found")
        else:
            abort(403, "Wrong api-key")


class UserListResource(Resource):
    def get(self, key:str):
        if key == getenv["API_KEY"]:
            return jsonify(get_all_users())
        else:
            abort(403, "Wrong api-key")
    def post(self, key:str):
        if key == getenv["API_KEY"]:
            args = user_parser.parse_args()
            try:
                add_user(args['user_tg'], args['grade_name'], args['group'], args['is_admin'], args['name'], args['surname'], args['password'])
                return jsonify({'success': 'OK'})
            except AccessNotAllowedError:
                abort(403, message="You don't have right to add users")
        else:
            abort(403, "Wrong api-key")