from flask import Blueprint, jsonify, request
from .other_utils.subjecter import subjects_tokens

if __name__ == '__main__':
    from db_modules.db_utils import *
else:
    from .db_modules.db_utils import *

blueprint = Blueprint(
    'alice_api',
    __name__
)

subs = subjects_tokens()


def homework_to_string(grade:int, token:str) -> str:
    try:
        homework:dict = get_homework(grade, token)
        if not homework.get('img_links') and (not homework.get('text') or 'не задано' in homework['text'].lower()):
            reply = 'Ничего не задано'
        elif homework.get('text'):
            reply = f"Задано {homework['text']}"
            if len(reply) > 5000:
                end_phrase = " и так далее"
                reply = reply[:4999-len(end_phrase)] + end_phrase
        elif homework.get('img_links'):
            reply = 'Домашнее задание содержит картинки. Чтобы их посмотреть, воспользуйтесь сайтом или ботом "А что задано?"'
    except RecordNotFoundError:
        reply = "Видимо, такого предмета в вашем классе нет"

    return reply


def work(req, resp, sess_state):
    grade = (req.deep_get(['state', 'user', 'grade'], 0)
             or req.deep_get(['state', 'user', 'grade'], 0))
    group = (req.deep_get(['state', 'user', 'group'], 0)
             or req.deep_get(['state', 'user', 'group'], 0))

    sub_name = req.deep_get(
        ['request', 'nlu', 'intents', 'subject', 'slots', 'subject', 'value'])
    if sub_name:
        token = subs[sub_name][group - 1]
        print(grade, token)
        reply = homework_to_string(grade, token)
    else:
        message = req.deep_get(["request", "command"])
        token = str()
        for sub_key in subs.keys():
            if sub_key in message:
                token = subs[sub_key][group - 1]
                break
        if token:
            reply = homework_to_string(grade, token)
        else:
            reply = f"Повтори, пожалуйста, я тебя не поняла"

    return reply, {'step': 'work'}


def grade(req, resp, sess_state):
    number = str(req.deep_get(
        ['request', 'nlu', 'intents', 'grade', 'slots', 'number', 'value']))
    letter = req.deep_get(['request', 'nlu', 'intents',
                          'grade', 'slots', 'letter', 'value'])
    if number and letter:
        letter = letter[0].upper()
        sess_state['number'] = number
        sess_state['letter'] = letter
        try:
            sess_state['grade_id'] = get_grade(str(number) + letter)['id']
            reply = f'''Давай проверим на всякий случай. Ты учишься в {number}{letter} классе?'''
            sess_state['step'] = 'verify_grade'
        except RecordNotFoundError:
            sess_state['step'] = 'grade'
            reply = '''Насколько мне известно, такого класса не существует. Укажи, пожалуйста, другой класс или напиши разработчику'''
    else:
        reply = '''Я тебя не поняла. Повтори, пожалуйста, ещё раз в формате: "Я учусь в таком-то классе"'''

    return reply, sess_state


def verify_grade(req, resp, sess_state):
    if req.deep_get(['request', 'nlu', 'intents', 'yes_or_no', 'slots', 'positive', 'value']):
        sess_state['step'] = 'group'
        reply = '''Теперь можно перейти к следующему этапу. В какой группе ты учишься? Обычно в классе их две, и вы делитесь на них на английском. \nЕсли не знаешь, ты всегда можешь уточнить у преподавателя или посмотреть в расписании и вернуться к регистрации позднее'''
    elif req.deep_get(['request', 'nlu', 'intents', 'yes_or_no', 'slots', 'negative', 'value']):
        sess_state['step'] = 'grade'
        reply = '''Тогда повтори ещё раз, в каком классе ты учишься. Лучше сказать это в формате: "Я учусь в таком-то классе"'''
    else:
        reply = '''Я тебя не поняла. Подтверди, пожалуйста, ещё раз'''

    return reply, sess_state


def group(req, resp, sess_state):
    group = req.deep_get(['request', 'nlu', 'intents',
                         'group', 'slots', 'group', 'value'])
    if group:
        sess_state['group'] = str(group)
        reply = f'Ещё одна проверка на всякий случай. Ты учишься в {group} группе?'
        sess_state['step'] = 'verify_group'
    else:
        reply = '''Я тебя не поняла. Повтори, пожалуйста, ещё раз в формате: "Я учусь в первой группе"'''

    return reply, sess_state


def verify_group(req, resp, sess_state):
    if req.deep_get(['request', 'nlu', 'intents', 'yes_or_no', 'slots', 'positive', 'value']):
        sess_state['step'] = 'work'
        grade = (req.deep_get(['state', 'session', 'number'])
                 ) + req.deep_get(['state', 'session', 'letter'])
        group = int(req.deep_get(['state', 'session', 'group']))
        user_id = req['session']['user_id']
        try:
            add_values('alice')
            add_user(user_id, grade, group, from_alice=True)

            resp['user_state_update'] = {
                "grade": req.deep_get(['state', 'session', 'grade_id']),
                "group": group
            }
            resp['application_state'] = {
                "grade": req.deep_get(['state', 'session', 'grade_id']),
                "group": group
            }
            reply = '''Отлично! Теперь я всегда готова ответить на твои вопросы по домашнему заданию'''
        except RecordExistsError:
            resp['user_state_update'] = {
                "grade": req.deep_get(['state', 'session', 'grade_id']),
                "group": group
            }
            resp['application_state'] = {
                "grade": req.deep_get(['state', 'session', 'grade_id']),
                "group": group
            }
            reply = '''Пользователь под твоей учётной записью уже добавлен. Если ты хочешь изменить класс или группу, просто скажи "Настройки"'''
    elif req.deep_get(['request', 'nlu', 'intents', 'yes_or_no', 'slots', 'negative', 'value']):
        sess_state['step'] = 'group'
        reply = '''Тогда повтори ещё раз, в какой ты учебной группе. К примеру, "Я учусь в первой группе"'''
    else:
        reply = '''Я тебя не поняла. Подтверди, пожалуйста, ещё раз'''

    return reply, sess_state


commands = {
    "work": work,
    "grade": grade,
    "verify_grade": verify_grade,
    "group": group,
    "verify_group": verify_group,
}


class DeepDict(dict):
    def deep_get(self, keys: list, default=False):
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


def handle_dialog(req: DeepDict, resp: DeepDict):
    grade = (req.deep_get(['state', 'user', 'grade'], 0)
             or req.deep_get(['state', 'user', 'grade'], 0))
    step = req.deep_get(['state', 'session', 'step'])
    if req.deep_get(['state', 'session']):
        sess_state = dict(req.deep_get(['state', 'session']))
    else:
        sess_state = dict()

    if req.deep_get(['request', 'nlu', 'intents', 'help']):
        resp["response"]["text"] = '''Я могу рассказать тебе твоё домашнее задание. Для этого спроси меня в свободной форме, обязательно упомянув название предмета. К примеру, "А есть ли дз по английскому?"'''
        resp['session_state'] = sess_state
    elif (req.deep_get(['session', 'new']) and not grade) or req.deep_get(['request', 'nlu', 'intents', 'change_settings']):
        try:
            user_id = req['session']['user_id']
            delete_user(user_id)
        except RecordNotFoundError:
            pass
        resp['user_state_update'] = {"grade": None, "group": None}
        resp['application_state'] = {"grade": None, "group": None}
        resp["response"]["text"] = '''Привет! Я - бот "А что задано?" и, поверь мне, я хорошо знаю ответ на этот вопрос! Я всегда могу рассказать тебе твое домашнее задание, если ты, конечно, учишься в 116 гимназии. Чтобы начать работу, скажи, в каком ты классе? К примеру: "Я учусь в 10Б"'''
        sess_state['step'] = 'grade'
        resp['session_state'] = sess_state
    elif req.deep_get(['session', 'new']) and req.deep_get(['request', 'nlu', 'intents', 'subject', 'slots', 'subject', 'value']):
        resp["response"]["text"], resp['session_state'] = commands['work'](
            req, resp, sess_state)
    elif req.deep_get(['session', 'new']):
        resp["response"]["text"] = '''Привет! Какое домашнее задание ты бы хотел узнать?'''
        sess_state['step'] = 'work'
        resp['session_state'] = sess_state
    else:
        try:
            resp["response"]["text"], resp['session_state'] = commands[step](
                req, resp, sess_state)
        except KeyError:
            resp["response"]["text"] = 'Ничего не понятно, но очень интересно'
            resp['session_state'] = sess_state
