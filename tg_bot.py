import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaDocument, InputMediaPhoto, ReplyKeyboardRemove, Update, ReplyKeyboardMarkup
from telegram.ext import Application, MessageHandler, CommandHandler, ConversationHandler, CallbackQueryHandler, filters, ContextTypes
import dotenv
import random
from all.other_utils.subjecter import subjects_tokens
from all.other_utils.emailer import send_email
from all.db_modules.send_tg import send_messages
from all.db_modules.db_utils import *
from werkzeug.utils import secure_filename
from uuid import uuid4

dotenv.load_dotenv()
subs = subjects_tokens()
photo_dump = os.getenv("REACT_APP_URL") + '/content/'
temp_code = None

with open(all_dir + '/db_modules/def_data/superadmins.csv', 'r', encoding='utf8') as file:
    db_sess = db_session.create_session()
    superadmins_id = list()
    for user in csv.DictReader(file, delimiter=';'):
        superadmins_id.append(int(user['tg']))

save_path = os.path.join(os.path.dirname(__file__), 'all', 'dynamic', 'img', 'actual') + '/'
application = Application.builder().token(os.getenv('TG_TOKEN')).build()


def generate_verification():
    code = ''.join([str(random.randint(0, 9)) for _ in range(4)])
    print(code)
    return code
    

async def asker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.message.from_user.id)
    message = update.message.text.lower()
    group = user['group']
    grade_id = user['grade']['id']
    token = str()
    for sub_key in subs.keys():
        if sub_key in message:
            token = subs[sub_key][group - 1]
            break
    if token:
        try:
            hw = get_homework(grade_id, token)
            print(hw)
            if hw.get('img_links'):
                images = list()
                for image in hw['img_links']:
                    print(photo_dump + image)
                    images.append(InputMediaPhoto(photo_dump + image))
                await update.message.reply_media_group(media=images, caption=hw['text'])
            elif hw.get('text'):
                await update.message.reply_text(hw['text'])
            else:
                await update.message.reply_text('Ничего не задано')
        except RecordNotFoundError:
            await update.message.reply_text('Ты уверен, что у твоего класса есть такой предмет?')
    else:
        await update.message.reply_text('Я не нашёл такого предмета')
    return ConversationHandler.END


async def end_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply = [
        f'Из-за технических особенностей Telegram тебе нужно отправить команду {update.message.text} ещё раз',
        'Не переживай, это нормально)))'
    ]
    await update.message.reply_text('\n'.join(reply), reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply = 'Ты уверен, что хочешь изменить класс? Если ты был админом, тебе придётся регистрироваться заново'
    keyboard = ReplyKeyboardMarkup(
        [['Да', 'Нет']], one_time_keyboard=True)
    await update.message.reply_text(reply, reply_markup=keyboard)
    return "approve"


async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "Да" in update.message.text:
        await start(update, context)
        return "grade"
    else:
        await update.message.reply_text('Хорошо. Если что, я всегда на связи', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply = [
        f'Привет, {update.message.from_user.first_name}!',
        'Чтобы начать работу, выбери класс, в котором ты учишься в этом году'
    ]

    keyboard = list()
    prev_grade = 3
    same_grade = list()
    for grade in get_all_grades():
        if grade['id'] // 10 == prev_grade:
            same_grade.append(InlineKeyboardButton(
                grade['name'], callback_data=grade['id']))
        else:
            prev_grade = grade['id'] // 10
            keyboard.append(same_grade)
            same_grade = list()
            same_grade.append(InlineKeyboardButton(
                grade['name'], callback_data=grade['id']))
    keyboard.append(same_grade)

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('\n'.join(reply), reply_markup=reply_markup)
    return "grade"


async def grade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    grade_id = int(query.data)
    context.user_data['grade'] = grade_id
    grade = get_grade(grade_id, name=False)
    grade_name = grade['name']
    grade_eng = grade['eng_teachers']
    keyboard = ReplyKeyboardMarkup([[grade_eng[0], grade_eng[1]]], one_time_keyboard=True)
    await query.answer(f"Ваш класс: {grade_name}")
    context.user_data['grade_name'] = grade_name
    context.user_data['eng_teachers'] = grade_eng
    reply = 'Теперь выбери своего учителя английского. Это позволит определить твою учебную группу'
    await query.get_bot().send_message(query.from_user.id, reply, reply_markup=keyboard)
    return "group"


async def group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text in context.user_data['eng_teachers']:
        reply = [
            'Отлично! Ещё один вопрос. Ты выбран как администратор в своём классе?',
            'Схитрить не получится -  для входа необходимо подтверждение суперадмина'
        ]
        group = 1 if update.message.text == context.user_data['eng_teachers'][0] else 2
        context.user_data['group'] = group
        keyboard = ReplyKeyboardMarkup(
            [['Да', 'Нет']], one_time_keyboard=True)
        await update.message.reply_text('\n'.join(reply), reply_markup=keyboard)
        return "is_admin"
    else:
        await update.message.reply_text('Насколько мне известно, такой группы не существует. Введи ещё раз')
        return "group"


async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "Да" in update.message.text:
        await update.message.reply_text('''Пожалуйста, укажи в ответном сообщении своё настоящее имя и фамилию в формате "(имя) (фамилия)". К примеру: 'Александр Смирнов' ''', reply_markup=ReplyKeyboardRemove())
        return "name_surname"
    else:
        context.user_data['is_registered'] = True
        if not get_user(update.message.from_user.id, return_error=False):
            add_user(update.message.from_user.id,
                     context.user_data['grade_name'],
                     int(context.user_data['group']))
        else:
            delete_user(update.message.from_user.id),
            add_user(update.message.from_user.id,
                     context.user_data['grade_name'],
                     int(context.user_data['group']))

        await stop(update, context)
        return ConversationHandler.END


async def user_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ' ' in update.message.text:
        splitted = update.message.text.strip().split(' ')
        name, surname = splitted[0], splitted[1]
        context.user_data['name'], context.user_data['surname'] = name, surname

        reply = [
            f'Приятно познакомиться, {name}!',
            'Сейчас на почту суперадминам придёт код подтверждения. Введи его, пожалуйста',
            'Узнать код можно либо найдя меня лично(Саша Смирнов, 10Б), либо спросив через Телеграм @alex010407'
        ]
        await update.message.reply_text('\n'.join(reply))
        code = generate_verification()
        message = [
            f'''Новый пользователь {name} {surname} с ником {update.message.from_user.username} хочет стать админом в {context.user_data['grade_name']} классе.''',
            f'Если вы хотите разрешить ему это сделать, сообщите ему код {code}'
        ]
        send_email('Подтверждение верификации', '\n'.join(message))
        send_messages(superadmins_id, '\n'.join(message))
        context.user_data['id'] = code
        return "verify"
    else:
        await update.message.reply_text(f'Не забудь, что надо указать и имя, и фамилию! Попробуй ещё раз')
        return "name_surname"


async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    right_code = context.user_data['id']
    if update.message.text.strip(' ') == right_code or (temp_code and update.message.text.strip(' ') == temp_code):
        reply = [
            'Почти закончили))',
            'Чтобы стать полноправным админом, придумай и введи пароль, с помощью которого ты сможешь добавлять домашние задания через сайт'
        ]
        await update.message.reply_text('\n'.join(reply), reply_markup=ReplyKeyboardRemove())
        return "password"
    else:
        await update.message.reply_text("Пароль не совпадает, попробуй ещё раз", reply_markup=ReplyKeyboardRemove())
        return "verify"


async def password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_password = update.message.text.strip(' ')
    print(context.user_data)
    if not get_user(update.message.from_user.id, return_error=False):
        add_user(update.message.from_user.id,
                 context.user_data['grade_name'],
                 int(context.user_data['group']),
                 True, context.user_data['name'], context.user_data['surname'],
                 user_password)
    else:
        delete_user(update.message.from_user.id),
        add_user(update.message.from_user.id,
                 context.user_data['grade_name'],
                 int(context.user_data['group']),
                 True, context.user_data['name'], context.user_data['surname'],
                 user_password)
    reply = [
        'Давай расскажу тебе, как добавлять домашние задания',
        '\t1. Отправь команду /new',
        '\t2. Введи предмет, по которому хочешь добавить домашнее задание',
        '\t3. Следующим сообщением отправь домашнее задание',
        '\tВАЖНО: Если есть и текст, и картинки, то текст надо вставить как описание, а не писать отдельным сообщением. Если картинок несколько - их нужно отправлять группой, а не по одной',
        '\t4. Проверь, что домашнее задание добавилось',
        'Что-то забыл или не понял? Не переживай, я буду подсказывать))) К тому же, есть полезная команда /help с описанием всех команд'
    ]
    await stop(update, context)
    await update.message.reply_text('\n'.join(reply))
    return ConversationHandler.END


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data:
        reply = [
            'На этом всё. Теперь я всегда готов ответить на твои вопросы по домашнему заданию. Чтобы узнать домашнее задание, отправь вопрос в произвольной форме, обязательно упомянув название предмета',
            f'А если вдруг у тебя не будет возможности спросить меня, все домашние задания доступны через сайт {os.getenv("REACT_APP_URL")}',
            'И не забывай - описание всех доступных функций всегда доступно через команду /help'
        ]
    else:
        reply = "Окей, процесс публикации прерван"
    await update.message.reply_text('\n'.join(reply), reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END


async def new_homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_dict = get_user(update.message.from_user.id)
    context.user_data['group'] = user_dict['group']
    context.user_data['grade'] = user_dict['grade']['id']
    if user_dict['is_admin']:
        reply = 'Напиши, по какому предмету ты бы хотел добавить домашнее задание'
        await update.message.reply_text(reply)
        return "subject"
    else:
        reply = 'Ты не админ, поэтому не можешь добавлять домашние задания'
        await update.message.reply_text(reply)
        return ConversationHandler.END


async def subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text.lower()
    group = int(context.user_data['group'])
    grade = int(context.user_data['grade'])
    token = str()
    for sub_key in subs.keys():
        if sub_key in message:
            token = subs[sub_key][group - 1]
            break
    if token and (token in get_subs(grade, group, return_token=True)):
        context.user_data['sub_token'] = token
        reply = 'Теперь отправь домашнее задание'
        await update.message.reply_text(reply)
        return "analyze_homework"
    elif token:
        reply = 'Похоже, такого предмета нет в вашем классе'
    else:
        reply = 'Я не знаю такого предмета'
    await update.message.reply_text(reply)
    return ConversationHandler.END


async def analyze_homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or update.message.caption
    context.user_data['text'] = text
    if update.message.photo:
        context.user_data['media_group'] = update.message.media_group_id
        ready_file = await update.message.photo[-1].get_file()
        file_name = secure_filename(uuid4().hex + '.png')
        await ready_file.download_to_drive(save_path + file_name)
        context.user_data['images'] = file_name
        context.job_queue.run_once(back_to_normal, when=3, user_id=update.message.from_user.id,
                                   data=update.message.from_user.id, chat_id=update.message.chat_id)
        return "media_cycle"
    elif context.user_data.get('is_global'):
        for grade in get_all_grades():
            grade_id = grade['id']
            add_homework(
                grade_id,
                context.user_data['sub_token'],
                update.effective_user.id,
                text
            )
    else:
        add_homework(
            context.user_data['grade'],
            context.user_data['sub_token'],
            update.effective_user.id,
            text
        )
        await update.message.reply_text('Задание успешно добавлено')
    return ConversationHandler.END


async def back_to_normal(context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('text'):
        text = context.user_data.get('text')
    else:
        text = None
    if context.user_data.get('is_global'):
        for grade in get_all_grades():
            grade_id = grade['id']
            add_homework(
                grade_id,
                context.user_data['sub_token'],
                context.job.data,
                text,
                context.user_data['images'].split(';')
            )
    else:
        add_homework(
            context.user_data['grade'],
            context.user_data['sub_token'],
            context.job.data,
            text,
            context.user_data['images'].split(';')
        )
    await context.bot.send_message(chat_id=context.job.chat_id, text='Задание успешно добавлено')
    context.user_data.clear()


async def media_cycle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        ready_file = await update.message.photo[-1].get_file()
        file_name = secure_filename(uuid4().hex + '.png')
        await ready_file.download_to_drive(save_path + file_name)
        context.user_data['images'] = context.user_data['images'] + \
            ';' + file_name
        return "media_cycle"


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_dict = get_user(update.message.from_user.id)

    if user_dict['is_admin']:
        context.user_data['grade'] = user_dict['grade']['id']
        context.user_data['is_global'] = False
        context.user_data['sub_token'] = 'info'
        reply = 'Теперь отправь информацию, которую тебе необходимо сообщить одноклассникам'
        await update.message.reply_text(reply)
        return "analyze_homework"
    else:
        reply = 'Ты не админ, поэтому не можешь публиковать информацию'
        await update.message.reply_text(reply)
        return ConversationHandler.END


async def glob_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_dict = get_user(update.message.from_user.id)

    if user_dict['id'] in superadmins_id:
        context.user_data['grade'] = user_dict['grade']['id']
        context.user_data['is_global'] = True
        context.user_data['sub_token'] = 'info'
        reply = 'Теперь отправь информацию, о которой необходимо оповестить'
        await update.message.reply_text(reply)
        return "analyze_homework"
    else:
        reply = 'Ты не суперадмин, поэтому не можешь публиковать глобальную информацию'
        await update.message.reply_text(reply)
        return ConversationHandler.END
    
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_dict = get_user(update.message.from_user.id)
    reply = [
        'Давай расскажу об основных доступных тебе командах "А что задано?"',
        ''
    ]
    if user_dict['id'] in superadmins_id:
        reply.extend([
            'Доступны только суперадминам:',
            '/globinfo позволяет делиться важной информацией, которая автоматически придёт всем ученикам школы, а также будет отображаться на сайте в разделе "Информация"',
            '/generate позволяет генерировать 5-минутные коды верификации для регистрации новых админов, чтобы не приходилось говорить каждому уникальный код',
            ''
        ])
    if user_dict['is_admin']:
        reply.extend([
            'Доступны только админам:',
            '/new позволяет добавлять новые домашние задания',
            '/info позволяет публиковать важную информацию, которая автоматически придёт всем ученикам твоего класса, а также будет отображаться на сайте в разделе "Информация"',
            '/stop позволяет прервать процесс публикации домашнего задания или информации',
            '',
            'Команды, доступные всем:'
        ])
    reply.extend([
        '/reset позволяет удалить свой текущий профиль и настроить новый, с другим классом или админством',
        '/tomorrow позволяет посмотреть домашнее задание на следующий рабочий день',
        '/chatmode позволяет переключиться в режим чата (или вернуться в обычный режим). В этом режиме домашние задания будут приходить к вам сами тогда, когда их кто-то опубликует',
        '+',
        'Вопросы к боту. К примеру, "А что задано по русскому?"'
    ])
    await update.message.reply_text('\n'.join(reply), reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


async def tomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now()
    if today.weekday() == 5 or today.weekday() == 6:
        weekday = 0
    else:
        weekday = today.weekday() + 1
    user_dict = get_user(update.message.from_user.id)
    new_line = ':\n'
    for homework in get_homework_by_date(user_dict['grade']['id'], user_dict['group'], weekday):
        text = f"{homework['lesson']}. {homework['sub']['name']}{new_line + homework['text'] if homework.get('text') else ''}"
        if homework.get('img_links'):
            images = list()
            for image in homework['img_links']:
                if image.endswith('.png'):
                    images.append(InputMediaPhoto(photo_dump + image))
                else:
                    images.append(InputMediaDocument(photo_dump + image))
            await update.message.reply_media_group(media=images, caption=text)
        else:
            await update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())
    
    return ConversationHandler.END


async def chatmode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now_state = change_user_mode(update.message.from_user.id)
    if now_state:
        reply = [
            'Режим отправки домашнего задания изменён.', 
            'Теперь все домашние задания будут приходить к тебе так же, как в классном чате - ровно в тот момент, когда их опубликовал админ. При этом ты и сам можешь спрашивать бота при необходимости',
            'Если тебе это не понравится, ты всегда можешь вернуться в обычный режим, использовав команду /chatmode ещё раз']
    else:
        reply = [
            'Режим отправки домашнего задания изменён.', 
            'Теперь ты сам можешь спрашивать бота, когда тебе нужно узнать конкретное домашнее задание.',
            'Если тебе это не понравится, ты всегда можешь перейти в режим чата, использовав команду /chatmode ещё раз']
    await update.message.reply_text('\n'.join(reply), reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


async def generate_temporary_verification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global temp_code
    user_dict = get_user(update.message.from_user.id)

    if user_dict['id'] in superadmins_id:
        temp_code = generate_verification()
        context.job_queue.run_once(disable_code, when=300)
        message = f'Был создан новый временный код верификации {temp_code}. Он будет действовать 5 минут'
        send_email('Подтверждение верификации', message)
        for admin_id in superadmins_id:
            await update.get_bot().send_message(admin_id, message)
    else:
        reply = 'Ты не суперадмин, поэтому не можешь генерировать коды верификации'
        await update.message.reply_text(reply)
    return ConversationHandler.END


async def disable_code(context: ContextTypes.DEFAULT_TYPE):
    global temp_code
    message = f'Временный код верификации {temp_code} удалён'
    for admin_id in superadmins_id:
        await context.bot.send_message(admin_id, message)
    temp_code = None
    

def main():
    one_line_handlers = [
        MessageHandler(filters.TEXT & ~filters.COMMAND, asker),
        CommandHandler('tomorrow', tomorrow),
        CommandHandler('chatmode', chatmode),
        CommandHandler('generate', generate_temporary_verification),
        CommandHandler('help', help)
    ]
    long_conv_handlers = [CommandHandler(command, end_conversation) for command in ['new', 'info', 'globinfo']]

    reg_handler = ConversationHandler(
        entry_points=[CommandHandler(
            'start', start), CommandHandler("reset", reset)],

        states={
            "restart": [CallbackQueryHandler(start)],
            "approve": [MessageHandler(filters.TEXT & ~filters.COMMAND, approve)],
            "grade": [CallbackQueryHandler(grade)],
            "group": [MessageHandler(filters.TEXT & ~filters.COMMAND, group)],
            "is_admin": [MessageHandler(filters.TEXT & ~filters.COMMAND, is_admin)],
            "name_surname": [MessageHandler(filters.TEXT & ~filters.COMMAND, user_name)],
            "verify": [MessageHandler(filters.TEXT & ~filters.COMMAND, verify)],
            "password": [MessageHandler(filters.TEXT & ~filters.COMMAND, password)]
        },

        fallbacks=[CommandHandler('stop', stop)]
    )

    hw_handler = ConversationHandler(
        entry_points=[CommandHandler('new', new_homework)],

        states={
            "subject": [MessageHandler(filters.TEXT & ~filters.COMMAND, subject)],
            "analyze_homework": [MessageHandler(filters.ALL & ~filters.COMMAND, analyze_homework)],
            "media_cycle": [
                MessageHandler(filters.ALL & ~filters.COMMAND & ~filters.TEXT, media_cycle), 
                *one_line_handlers,
                *long_conv_handlers
            ]
        },

        fallbacks=[CommandHandler('stop', stop)],
        conversation_timeout=300
    )

    info_handler = ConversationHandler(
        entry_points=[CommandHandler('info', info), CommandHandler('globinfo', glob_info)],

        states={
            "analyze_homework": [MessageHandler(filters.ALL & ~filters.COMMAND, analyze_homework)],
            "media_cycle": [
                MessageHandler(filters.ALL & ~filters.COMMAND & ~filters.TEXT, media_cycle), 
                *one_line_handlers,
                *long_conv_handlers
            ]
        },

        fallbacks=[CommandHandler('stop', stop)],
        conversation_timeout=300
    )

    application.add_handler(reg_handler)
    application.add_handler(hw_handler)
    application.add_handler(info_handler)

    for handler in one_line_handlers: 
        application.add_handler(handler)


    application.run_polling()


if __name__ == '__main__':
    main()
