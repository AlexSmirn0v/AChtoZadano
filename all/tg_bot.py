import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaDocument, InputMediaPhoto, ReplyKeyboardRemove, Update, ReplyKeyboardMarkup
from telegram.ext import Application, MessageHandler, CommandHandler, ConversationHandler, CallbackQueryHandler, filters, ContextTypes
import dotenv
import random
from other_utils.subjecter import subjects_tokens
from other_utils.emailer import send_email
from werkzeug.utils import secure_filename
from uuid import uuid4

if __name__ == '__main__':
    from db_modules.db_utils import *
else:
    from .db_modules.db_utils import *

dotenv.load_dotenv()
subs = subjects_tokens()
photo_dump = os.getenv("REACT_APP_URL") + '/content/'
save_path = os.path.join(os.path.dirname(__file__), 'dynamic', 'img', 'actual') + '/'


def generate_verification():
    code = ''.join([str(random.randint(0, 9)) for _ in range(4)])
    print(code)
    return code


async def asker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.message.from_user.username)
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
            if hw.get('img_links'):
                images = list()
                for image in hw['img_links']:
                    if image.endswith('.png'):
                        images.append(InputMediaPhoto(photo_dump + image))
                    else:
                        images.append(InputMediaDocument(photo_dump + image))
                await update.message.reply_media_group(media=images, caption=hw['text'])
            elif hw.get('text'):
                await update.message.reply_text(hw['text'])
            else:
                await update.message.reply_text('Ничего не задано')
        except RecordNotFoundError:
            await update.message.reply_text('Ты уверен, что у твоего класса есть такой предмет?')
    else:
        await update.message.reply_text('Я не нашёл такого предмета')


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply = 'Ты уверен, что хочешь изменить класс? Если ты был админом, все добавленные тобой домашние задания будут удалены'
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
    reply = f'''Привет, {update.message.from_user.first_name}!\nЧтобы начать работу, выбери класс, в котором ты учишься в этом году'''

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
    await update.message.reply_text(reply, reply_markup=reply_markup)
    return "grade"


async def grade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    grade_id = int(query.data)
    context.user_data['grade'] = grade_id
    keyboard = ReplyKeyboardMarkup([['1', '2']], one_time_keyboard=True)
    grade_name = get_grade(grade_id, name=False)['name']
    await query.answer(f"Ваш класс: {grade_name}")
    context.user_data['grade_name'] = grade_name
    await query.get_bot().send_message(query.from_user.id, '''Теперь выбери свою учебную группу. Обычно в классе их две, и вы делитесь на них на английском. \nЕсли не знаешь, ты всегда можешь уточнить у преподавателя или посмотреть в расписании и вернуться к регистрации позднее''', reply_markup=keyboard)
    return "group"


async def group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text[0] in ['1', '2']:
        reply = '''Отлично! Ещё один вопрос. Ты выбран как администратор в своём классе?\nУчти, что врать здесь лучше не стоит, так как для входа необходимо подтверждение суперадмина'''
        group = update.message.text[0]
        context.user_data['group'] = group
        keyboard = ReplyKeyboardMarkup(
            [['Да', 'Нет']], one_time_keyboard=True)
        await update.message.reply_text(reply, reply_markup=keyboard)
        return "is_admin"
    else:
        await update.message.reply_text('Насколько мне известно, такой группы не существует. Введи ещё раз')
        return "group"


async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "Да" in update.message.text:
        await update.message.reply_text('''Пожалуйста, укажи в ответном сообщении своё настоящее имя и фамилию в формате "(имя) (фамилия)". К примеру: 'Александр Смирнов' ''', reply_markup=ReplyKeyboardRemove())
        return "name_surname"
    else:
        if not get_user(update.message.from_user.username, return_error=False):
            add_user(update.message.from_user.username,
                     context.user_data['grade_name'],
                     int(context.user_data['group']))
        else:
            delete_user(update.message.from_user.username),
            add_user(update.message.from_user.username,
                     context.user_data['grade_name'],
                     int(context.user_data['group']))

        await stop(update, context)
        return ConversationHandler.END


async def user_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ' ' in update.message.text:
        splitted = update.message.text.split(' ')
        name, surname = splitted[0], splitted[1]
        context.user_data['name'], context.user_data['surname'] = name, surname
        await update.message.reply_text(f'Приятно познакомиться, {name}!\nСейчас на почту суперадминам придёт код подтверждения. Введи его, пожалуйста')
        code = generate_verification()
        message = f'''Новый пользователь {context.user_data['name']} {context.user_data['surname']} с ником {update.message.from_user.username} хочет стать админом в {context.user_data['grade_name']} классе.\nЕсли вы хотите разрешить ему это сделать, сообщите ему код {code}'''
        send_email('Подтверждение верификации', message)
        context.user_data['id'] = code
        return "verify"
    else:
        await update.message.reply_text(f'Не забудь, что надо указать и имя, и фамилию! Попробуй ещё раз')
        return "name_surname"


async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    right_code = context.user_data['id']
    if update.message.text == right_code:
        await update.message.reply_text('Поздравляю! Теперь ты полноправный админ! Осталось только придумать пароль, чтобы ты мог добавлять домашние задания через веб-версию achtozadano.ru')
        return "password"


async def password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_password = update.message.text
    print(context.user_data)
    if not get_user(update.message.from_user.username, return_error=False):
        add_user(update.message.from_user.username,
                 context.user_data['grade_name'],
                 int(context.user_data['group']),
                 True, context.user_data['name'], context.user_data['surname'],
                 user_password)
    else:
        delete_user(update.message.from_user.username),
        add_user(update.message.from_user.username,
                 context.user_data['grade_name'],
                 int(context.user_data['group']),
                 True, context.user_data['name'], context.user_data['surname'],
                 user_password)
    await stop(update, context)
    return ConversationHandler.END


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('На этом всё. Теперь я всегда готов ответить на твои вопросы по домашнему заданию', reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END


async def new_homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_dict = get_user('@' + update.message.from_user.username)
    print(user_dict)
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
    token = str()
    for sub_key in subs.keys():
        if sub_key in message:
            token = subs[sub_key][group - 1]
            break
    if token:
        context.user_data['sub_token'] = token
        reply = 'Теперь отправь домашнее задание'
        await update.message.reply_text(reply)
        return "analyze_homework"
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
                                   data=update.message.from_user.username, chat_id=update.message.chat_id)
        return "media_cycle"
    else:
        add_homework(
            context.user_data['grade'],
            context.user_data['sub_token'],
            update.effective_user.username,
            text
        )
        await update.message.reply_text('Задание успешно добавлено')
    return ConversationHandler.END


async def back_to_normal(context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('text'):
        text = context.user_data.get('text')
    else:
        text = None
    add_homework(
        context.user_data['grade'],
        context.user_data['sub_token'],
        context.job.data,
        text,
        context.user_data['images'].split(';')
    )
    await context.bot.send_message(chat_id=context.job.chat_id, text='Задание успешно добавлено')
    context.user_data.clear()
    return ConversationHandler.END


async def media_cycle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        ready_file = await update.message.photo[-1].get_file()
        file_name = secure_filename(uuid4().hex + '.png')
        await ready_file.download_to_drive(save_path + file_name)
        context.user_data['images'] = context.user_data['images'] + \
            ';' + file_name
        return "media_cycle"


def main():
    application = Application.builder().token(os.getenv('TG_TOKEN')).build()
    conv_handler = ConversationHandler(
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
            "media_cycle": [MessageHandler(filters.ALL & ~filters.COMMAND & ~filters.TEXT, media_cycle)]
        },

        fallbacks=[CommandHandler('stop', stop)]
    )
    application.add_handler(conv_handler)
    application.add_handler(hw_handler)
    application.add_handler(CommandHandler("reset", start))
    application.add_handler(CommandHandler("info", start))
    application.add_handler(CommandHandler("globinfo", start))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, asker))

    application.run_polling()


if __name__ == '__main__':
    main()
