import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, Update, ReplyKeyboardMarkup
from telegram.ext import Application, MessageHandler, CommandHandler, ConversationHandler, CallbackQueryHandler, filters, ContextTypes
import dotenv
import random
from other_utils.subjecter import subjects_tokens
from other_utils.emailer import send_email

if __name__ == '__main__':
    from db_modules.db_utils import *
else:
    from .db_modules.db_utils import *

dotenv.load_dotenv()
subs = subjects_tokens()


def generate_verification():
    code = ''.join([str(random.randint(0, 9)) for _ in range(4)])
    print(code)
    return code


async def echo(update, context):
    message = get_homework(93, update.message.text)['text']
    try:
        await context.bot.send_message(update.message.from_user.id, 'text')
    except Exception:
        print('Не смогла')
    await update.message.reply_text(message)

async def start(update:Update, context:ContextTypes.DEFAULT_TYPE):
    reply = f'''Привет, {update.message.from_user.first_name}!\nЧтобы начать работу, выбери класс, в котором ты учишься в этом году'''

    keyboard = list()
    prev_grade = 3
    same_grade = list()
    for grade in get_all_grades():
        if grade['id'] // 10 == prev_grade:
            same_grade.append(InlineKeyboardButton(grade['name'], callback_data=grade['id']))
        else:
            prev_grade = grade['id'] // 10
            keyboard.append(same_grade)
            same_grade = list()
            same_grade.append(InlineKeyboardButton(grade['name'], callback_data=grade['id']))
    keyboard.append(same_grade)

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(reply, reply_markup=reply_markup)
    return "grade"

async def grade(update:Update, context:ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    grade_id = int(query.data)
    context.user_data['grade'] = grade_id
    keyboard = ReplyKeyboardMarkup([['1', '2']], one_time_keyboard=True)
    grade_name = get_grade(grade_id, name=False)['name']
    await query.answer(f"Ваш класс: {grade_name}")
    context.user_data['grade_name'] = grade_name
    await query.get_bot().send_message(query.from_user.id, '''Теперь выбери свою учебную группу. Обычно в классе их две, и вы делитесь на них на английском. \nЕсли не знаешь, ты всегда можешь уточнить у преподавателя или посмотреть в расписании и вернуться к регистрации позднее''', reply_markup=keyboard)
    return "group"

async def group(update:Update, context:ContextTypes.DEFAULT_TYPE):
    reply = '''Отлично! Ещё один вопрос. Ты выбран как администратор в своём классе?\nУчти, что врать здесь лучше не стоит, так как для входа необходимо подтверждение суперадмина'''
    group = update.message.text[0]
    context.user_data['group'] = group
    keyboard = ReplyKeyboardMarkup([['Да', 'Нет']], one_time_keyboard=True)
    await update.message.reply_text(reply, reply_markup=keyboard)
    return "is_admin"
    
async def is_admin(update:Update, context:ContextTypes.DEFAULT_TYPE):
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

        update.message.reply_text('На этом всё')
        return ConversationHandler.END
    

async def user_name(update:Update, context:ContextTypes.DEFAULT_TYPE):
    if ' ' in update.message.text:
        name, surname = update.message.text.split(' ')
        context.user_data['name'], context.user_data['surname'] = name, surname
        await update.message.reply_text(f'Приятно познакомиться, {name}!\nСейчас на почту суперадминам придёт код подтверждения. Введи его, пожалуйста')
        code = generate_verification()
        message = f'''Новый пользователь {context.user_data['name']} {context.user_data['surname']} с ником {update.message.from_user.username} хочет стать админом в {context.user_data['grade_name']} классе.\nЕсли вы хотите разрешить ему это сделать, сообщите ему код {code}'''
        send_email('Подтверждение верификации', message)
        context.user_data['id'] = code
        return "verify"
    
async def verify(update:Update, context:ContextTypes.DEFAULT_TYPE):
    right_code = context.user_data['id']
    if update.message.text == right_code:
        await update.message.reply_text('Поздравляю! Теперь ты полноправный админ! Осталось только придумать пароль, чтобы ты мог добавлять домашние задания через веб-версию achtozadano.ru')
        return "password"
    

async def stop(update:Update, context:ContextTypes.DEFAULT_TYPE):
    print('we re here')
    query = update.callback_query
    await query.get_bot().send_message(query.from_user.id, 'На этом всё. Теперь я всегда готов ответить на твои вопросы по домашнему заданию', reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    update.message.reply_text('На этом всё')
    return ConversationHandler.END

async def password(update:Update, context:ContextTypes.DEFAULT_TYPE):
    user_password = update.message.text
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
    update.message.reply_text('На этом всё')
    return ConversationHandler.END


def main():
    application = Application.builder().token(os.getenv('TG_TOKEN')).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={
            "grade": [CallbackQueryHandler(grade)],
            "group": [MessageHandler(filters.TEXT & ~filters.COMMAND, group)],
            "is_admin": [MessageHandler(filters.TEXT & ~filters.COMMAND, is_admin)],
            "name_surname": [MessageHandler(filters.TEXT & ~filters.COMMAND, user_name)],
            "verify": [MessageHandler(filters.TEXT & ~filters.COMMAND, verify)],
            "password": [MessageHandler(filters.TEXT & ~filters.COMMAND, password)],
            "stop": [MessageHandler(filters.TEXT & ~filters.COMMAND, stop)]
        },

        fallbacks=[CommandHandler('stop', stop)]
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("new", start))
    application.add_handler(CommandHandler("reset", start))
    application.add_handler(CommandHandler("info", start))
    application.add_handler(CommandHandler("globinfo", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    application.run_polling()



if __name__ == '__main__':
    main()