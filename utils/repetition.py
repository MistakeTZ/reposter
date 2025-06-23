import asyncio
from utils import kb
from loader import bot, sender
from config import time_difference
from database.model import DB
from datetime import datetime, timedelta, timezone
from aiogram.types import ChatPermissions
import logging
from time import time


# Отправка запланированных сообщений
async def send_messages():
    await asyncio.sleep(5)
    while True:
        messages_to_send = DB.get("select chat_id, message_id, \
            button_text, button_link, time_to_send from repetitions \
                where confirmed and not is_send and time_to_send < ?",
                [datetime.now() + time_difference])
        if messages_to_send:
            to_send_tasks = [send_msg(*msg) for msg in messages_to_send]
            await asyncio.gather(*to_send_tasks)
        
        promotes = DB.get("select * from promotes where \
                    registered < ?", [datetime.now(timezone.utc) - timedelta(hours=1, minutes=10)])
        for promote in promotes:
            try:
                if promote[5] == "channel":
                    await bot.promote_chat_member(promote[2], promote[1], can_post_messages=True)
                DB.commit("delete from promotes where id = ?", [promote[0]])
            except Exception as e:
                logging.warning(e)
        
        promotes = DB.get("select * from promotes where registered < ? and promote = 0",
                          [datetime.now(timezone.utc) - timedelta(minutes=10)])
        for promote in promotes:
            try:
                if promote[5] == "group" or promote[5] == "supergroup":
                    new_perms = ChatPermissions(can_send_messages=False)
                    await bot.restrict_chat_member(promote[2], promote[1],
                            new_perms, until_date=int(time() + 60 * 60))
                if promote[5] == "channel":
                    await bot.promote_chat_member(promote[2], promote[1], can_post_messages=False)
                DB.commit("update promotes set promote = 1 where id = ?", [promote[0]])
                try:
                    await bot.delete_message(promote[4], promote[3])
                except:
                    pass
            except Exception as e:
                logging.warning(e)

        await asyncio.sleep(60)


async def send_msg(chat_id, message_id, button_text, button_link, time_to_send):
    DB.commit("update repetitions set is_send = ? where chat_id = ? and message_id = ?", [True, chat_id, message_id])
    users = DB.get("select telegram_id from users")
    for user in users:
        try:
            if button_link:
                await bot.copy_message(user[0], chat_id, message_id, reply_markup=kb.link(button_text, button_link))
            else:
                await bot.copy_message(user[0], chat_id, message_id)
        except:
            continue
