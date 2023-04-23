import os
from telegram.ext import Application, MessageHandler, CommandHandler, filters
import dotenv
from other_utils.subjecter import subjects_tokens

if __name__ == '__main__':
    from db_modules.db_utils import *
else:
    from .db_modules.db_utils import *

dotenv.load_dotenv()
subs = subjects_tokens()


async def echo(update, context):
    message = get_homework(93, update.message.text)['text']
    try:
        print(update.message.from_user.id)
        await context.bot.send_message(update.message.from_user.id, 'text')
    except Exception:
        print('Не смогла')
    await update.message.reply_text(message)

async def start(update, context):
    print(update.message.text)
    try:
        print(update.message.from_user.username)
        await context.bot.send_message(update.message.from_user.id, 'text')
    except Exception:
        print('Не смогла')
    await update.message.reply_text('Here')


def main():
    application = Application.builder().token(os.getenv('TG_TOKEN')).build()
 
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("new", start))
    application.add_handler(CommandHandler("reset", start))
    application.add_handler(CommandHandler("info", start))
    application.add_handler(CommandHandler("global_info", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    application.run_polling()



if __name__ == '__main__':
    main()