import asyncio
import json
import os
from datetime import datetime, timedelta
from random import randint

import matplotlib.pyplot as plt
import pandas as pd

from other_utils.emailer import send_email

plot_headers = {
    "admins_registered_today": "Количество зарегистрированных админов",
    "users_registered_today": "Количество зарегистрированных пользователей",
    "homework_added_today": "Количество опубликованных домашних заданий",
    "homework_requested_today": "Количество запрошенных домашних заданий", 
    "alice_registered_today": "Количество пользователей, зарегистрировавшихся из Алисы"
}


def clear_archive():
    directory = os.path.join(os.path.dirname(__file__), 'dynamic', 'img', 'archive')
    for file in os.listdir(directory):
        filepath = os.path.join(directory, file)
        age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(filepath))
        if age > timedelta(days=14):
            os.remove(filepath)

def routine():
    today_dict = json.load(open(os.path.join(os.path.dirname(__file__), 'dynamic', 'logs', 'variables.json')))
    day_stat_dict = json.load(open(os.path.join(os.path.dirname(__file__), 'dynamic', 'logs', 'day_stats.json')))
    stat_images = list()
    email_text = list()
    for key in today_dict.keys():
        if key.endswith('_today'):
            day_stat_dict[key].append(today_dict[key])
            email_text.append(f"{plot_headers[key]}: {today_dict[key]}")
            today_dict[key] = 0
            maxer = max(day_stat_dict[key])
            df = pd.DataFrame(day_stat_dict[key])
            x = range(len(day_stat_dict[key]))

            plt.axis([0, len(x), 0, maxer])
            plt.plot(x, df)
            plt.suptitle(plot_headers[key])
            filepath = f'{os.path.dirname(__file__)}/dynamic/logs/{key}.png'
            stat_images.append(filepath)
            plt.savefig(filepath)
            plt.close()

    json.dump(today_dict, open(os.path.join(os.path.dirname(__file__), 'dynamic', 'logs', 'variables.json'), 'w'))
    json.dump(day_stat_dict, open(os.path.join(os.path.dirname(__file__), 'dynamic', 'logs', 'day_stats.json'), 'w'))
    send_email('Отчёт о работе achtozadano', '\n'.join(email_text), attachments=stat_images)
    print('Reports are succesfully sent')
    clear_archive()
    print('Routine is succesfully completed')


def exec_dt(now:datetime, hour=23, minute=50, second=0):
    try:
        exec_datetime = datetime(now.year, now.month, now.day + 1, hour, minute, second)
    except ValueError:
        if now.month != 12:
            exec_datetime = datetime(now.year, now.month + 1, 1, hour, minute, second)
        else:
            exec_datetime = datetime(now.year + 1, 1, 1, hour, minute, second)
    return exec_datetime


async def main():
    while True:
        routine()
        exec_datetime = exec_dt(datetime.now(), 23, 50, 0)
        now_datetime = datetime.now()
    
        delta = (exec_datetime - now_datetime).seconds
        await asyncio.sleep(float(delta))

if __name__ == '__main__':
    asyncio.run(main())