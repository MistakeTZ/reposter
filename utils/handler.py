from aiogram import F
from aiogram.filters import Filter
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.utils.markdown import hlink
from aiogram.fsm.context import FSMContext
from loader import dp, bot, sender
from datetime import datetime

from os import path
from config import get_env, get_config, time_difference
import asyncio

import utils.kb as kb
from states import UserState
from database.model import DB


# Установка электронной почты
@dp.message(UserState.email)
async def email_check(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    if not msg.entities:
        await sender.message(user_id, "wrong_email")
        return
    email_entity = msg.entities[0]
    if email_entity.type != "email":
        await sender.message(user_id, "wrong_email")
        return
    email = msg.text[email_entity.offset:email_entity.length]


# Установка времени
@dp.message(UserState.time)
async def time_check(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    try:
        time = datetime.strptime(msg.text, "%H:%M")
    except ValueError:
        await sender.message(user_id, "wrong_time")
        return


# Установка телефона
@dp.message(UserState.phone, F.contact)
async def phone_check(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    phone = msg.contact.phone_number


# Проверка на отсутствие состояний
class NoStates(Filter):
    async def __call__(self, msg: Message, state: FSMContext):
        stat = await state.get_state()
        return stat is None


# Добавление в чат
@dp.my_chat_member()
async def member_handler(msg: Message, state: FSMContext):
    chat_id = msg.chat.id
    chat_info = DB.get("select * from channels where chat_id = ?", [chat_id], True)
    if chat_info:
        if msg.new_chat_member.status == "left" or msg.new_chat_member.status == "kicked":
            DB.commit("delete from channels where chat_id = ?", [chat_id])
    else:
        from_user = msg.from_user.id
        from_user_info = DB.get("select id from users where telegram_id = ?", [from_user], True)
        if not from_user_info:
            return

        if msg.new_chat_member.status == "member" or msg.new_chat_member.status == "administrator":
            DB.commit("insert into channels (chat_id, name, username, owner) values (?, ?, ?, ?)",
                      [chat_id, msg.chat.title, msg.chat.username, from_user])
        await state.set_state(UserState.default)


# Установка базы данных
@dp.message(F.document)
async def set_databse(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    role = DB.get('select role from users where telegram_id = ?', [user_id], True)
    if not role:
        return
    if role[0] != "admin":
        return
    
    doc = msg.document
    if doc.file_name.split(".")[-1] != "sqlite3":
        return
    
    file = await bot.get_file(doc.file_id)
    await bot.download_file(file.file_path, path.join("database", "db.sqlite3"))
