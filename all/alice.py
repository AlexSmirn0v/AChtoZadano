import os

from flask import Blueprint, jsonify, request

if __name__ == '__main__':
    from db_modules.db_utils import *
else:
    from .db_modules.db_utils import *

blueprint = Blueprint(
    'alice_api',
    __name__
)

subs = dict()
with open(os.path.join(os.path.dirname(__file__), "db_modules", "def_data", "subjects.txt"), encoding='utf8') as text:
    for line in text.readlines():
        if not line.startswith("ИНФОРМАЦИЯ"):
            sub_name, sub_token, sub_name_datv = line.strip().split('-')
            if sub_name.endswith('группа'):
                sub_token_1 = sub_token[:-1] + '1'
                sub_token_2 = sub_token[:-1] + '2'
            else:
                sub_token_1 = sub_token
                sub_token_2 = sub_token
            sub_name = sub_name.split(' ')[0] 
            subs[sub_name.lower()] = [sub_token_1, sub_token_2]
            subs[sub_name_datv.lower()] = [sub_token_1, sub_token_2]


class DeepDict(dict):
    def deep_get(self, keys:list, default=False):
        copy = self.copy()
        for key in keys:
            copy = copy.get(key, {})
        if copy == {}:
            return default
        else:
            return copy


@blueprint.route('/api/116/alice', methods=['POST'])
def alice():
    req = DeepDict(request.json)
    resp = DeepDict({
        'version': req['version'],
        'response': {
            'end_session': False
        }
    })

    handle_dialog(req, resp)
    add_values('alice')
    return jsonify(resp)


def handle_dialog(req, resp):
    grade = (req.deep_get(['state', 'user', 'grade'], 0) or req.deep_get(['state', 'user', 'grade'], 0))
    group = (req.deep_get(['state', 'user', 'group'], 0) or req.deep_get(['state', 'user', 'group'], 0))
    step = req.deep_get(['state', 'session', 'step'])
    if req.deep_get(['state', 'session']):
        sess_state = req.deep_get(['state', 'session'])
    else:
        sess_state = dict()

    if (req.deep_get(['session', 'new']) and not grade) or req.deep_get(['request', 'nlu', 'intents', 'change_settings']):
        resp['user_state_update'] = {"grade": None, "group": None}
        resp['application_state'] = {"grade": None, "group": None}
        resp["response"]["text"] = '''Привет! Чтобы начать работу, скажи, в каком ты классе? К примеру: "Я учусь в 10В"'''
        sess_state['step'] = 'grade'
    elif req.deep_get(['session', 'new']):
        resp["response"]["text"] = '''Привет! Какое домашнее задание ты бы хотел узнать?'''
        sess_state['step'] = 'work'
    elif step == 'work':
        sub_name = req.deep_get(['request', 'nlu', 'intents', 'subject', 'slots', 'subject', 'value'])
        if sub_name:
            token = subs[sub_name][group - 1]
            print(grade, token)
            homework = get_homework(grade, token)
            resp["response"]["text"] = f"Задано {homework['text']}"
        else:
            resp["response"]["text"] = f"Повторите, пожалуйста, я вас не поняла"
    elif step == 'grade':
        number = str(req.deep_get(['request', 'nlu', 'intents', 'grade', 'slots', 'number', 'value']))
        letter = req.deep_get(['request', 'nlu', 'intents', 'grade', 'slots', 'letter', 'value'])
        if number and letter:
            letter = letter[0].upper()
            sess_state['number'] = number
            sess_state['letter'] = letter
            grade = Grade()
            grade.name_to_id(str(9) + 'В')
            print(grade.id)
            sess_state['grade_id'] = grade.id
            resp["response"]["text"] = f'''Давай проверим на всякий случай. Ты учишься в {number}{letter} классе?'''
            sess_state['step'] = 'verify_grade'
        else:
            resp["response"]["text"] = '''Я тебя не поняла. Повтори, пожалуйста, ещё раз в формате: "Я учусь в таком-то классе"'''
    elif step == 'verify_grade':
        if req.deep_get(['request', 'nlu', 'intents', 'yes_or_no', 'slots', 'positive', 'value']):
            sess_state['step'] = 'group'
            resp["response"]["text"] = '''Теперь можно перейти к следующему этапу. В какой группе ты учишься? Обычно в классе их две, и вы делитесь на них на английском. 
            Если не знаешь, ты всегда можешь уточнить у преподавателя или посмотреть в расписании и вернуться к регистрации позднее'''
        elif req.deep_get(['request', 'nlu', 'intents', 'yes_or_no', 'slots', 'negative', 'value']):
            sess_state['step'] = 'grade'
            resp["response"]["text"] = '''Тогда повтори ещё раз, в каком классе ты учишься. Лучше сказать это в формате: "Я учусь в таком-то классе"'''
        else:
            resp["response"]["text"] = '''Я тебя не поняла. Подтверди, пожалуйста, ещё раз'''
    elif step == 'group':
        group = req.deep_get(['request', 'nlu', 'intents', 'group', 'slots', 'group', 'value'])
        if group:
            sess_state['group'] = str(group)
            resp["response"]["text"] = f'Ещё одна проверка на всякий случай. Ты учишься в {group} группе?'
            sess_state['step'] = 'verify_group'
        else:
            resp["response"]["text"] = '''Я тебя не поняла. Повтори, пожалуйста, ещё раз в формате: "Я учусь в первой группе"'''
    elif step == 'verify_group':
        if req.deep_get(['request', 'nlu', 'intents', 'yes_or_no', 'slots', 'positive', 'value']):
            sess_state['step'] = 'work'
            grade = (req.deep_get(['state', 'session', 'number'])) + req.deep_get(['state', 'session', 'letter'])
            group = int(req.deep_get(['state', 'session', 'group']))
            user_id = req['session']['user_id']
            try:
                add_user(user_id, grade, group)

                resp['user_state_update'] = {
                    "grade": req.deep_get(['state', 'session', 'grade_id']),
                    "group": group
                }
                resp['application_state'] = {
                    "grade": req.deep_get(['state', 'session', 'grade_id']),
                    "group": group
                }
                resp["response"]["text"] = '''Отлично! Теперь я всегда готова ответить на твои вопросы по домашнему заданию'''
            except RecordExistsError:
                resp["response"]["text"] = '''Пользователь под вашей учётной записью уже добавлен. Если ты хочешь изменить класс или группу, просто скажи "Настройки"'''
        elif req.deep_get(['request', 'nlu', 'intents', 'yes_or_no', 'slots', 'negative', 'value']):
            sess_state['step'] = 'group'
            resp["response"]["text"] = '''Тогда повтори ещё раз, в какой ты учебной группе. К примеру, "Я учусь в первой группе"'''
        else:
            resp["response"]["text"] = '''Я тебя не поняла. Подтверди, пожалуйста, ещё раз'''
    else:
        resp["response"]["text"] = 'Ничего не понятно, но очень интересно'
    resp['session_state'] = sess_state

    