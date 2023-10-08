import asyncio
from os import getenv
import dotenv
import aiohttp

dotenv.load_dotenv()
photo_dump = getenv("REACT_APP_URL") + '/content/'

async def send_messages(id_list: list, text: str=None, img_links: list=None):
    token = getenv("TG_TOKEN")

    async with aiohttp.ClientSession('https://api.telegram.org') as session:
        if img_links and len(img_links) > 1:
            params = {
                "media": list()
            }
            for image in img_links:
                media_object = {
                    "type": "photo",
                    "media": photo_dump + image
                }
                if image == img_links[0] and text:
                    media_object["caption"] = text
                params["media"].append(media_object)

            for chat_id in id_list:
                params["chat_id"] = chat_id
                await asyncio.sleep(1 / 40)
                await session.post(f'/bot{token}/sendMediaGroup', json=params)
        elif img_links and len(img_links) == 1:
            photo = {
                "photo": photo_dump + img_links[0]
            }
            if text:
                photo["caption"] = text
            for chat_id in id_list:
                photo["chat_id"] = chat_id
                await asyncio.sleep(1 / 40)
                await session.get(f'/bot{token}/sendPhoto', params=photo)
        elif text:
                params = {
                    "text": text
                }
                for chat_id in id_list:
                    params['chat_id'] = chat_id
                    await asyncio.sleep(1 / 40)
                    await session.get(f'/bot{token}/sendMessage', params=params)

if __name__ == '__main__':
    asyncio.run(send_messages([getenv("MY_CHAT_ID")], 'Оно работает'))