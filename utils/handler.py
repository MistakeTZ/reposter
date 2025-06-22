from aiogram import F
from aiogram.filters import Filter
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.utils.markdown import hlink
from aiogram.fsm.context import FSMContext
from loader import dp, bot, sender
from datetime import datetime
import logging

from os import path
from config import get_env, get_config, time_difference
import asyncio

import utils.kb as kb
from states import UserState
from database.model import DB
from .tasks import send_bond_info, add_chat


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


# Добавление пересылки
@dp.message(UserState.bond)
async def bond_handler(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    data = await state.get_data()
    status = data.get("state", None)
    bond_id = data.get("id", None)
    start_mes_id = data.get("start_mes_id", None)

    match status:
        case "name":
            try:
                name = msg.text
                if len(name) > 50:
                    raise ValueError("Too long name")
                if bond_id is None:
                    if not DB.get("select id from \
                                bonds where name = ?", [name], True):
                        DB.commit("insert into bonds (name, \
                                owner) values (?, ?)", [name, user_id])
                    bond_id = DB.get("select id from bonds \
                                where name = ?", [name], True)[0]
                else:
                    DB.commit("update bonds set name = ? where id = ?",
                              [name, bond_id])
                await msg.delete()
                await send_bond_info(bond_id, user_id, start_mes_id)
            except Exception as e:
                logging.debug(e)
                try:
                    await msg.delete()
                except: pass
                await bot.edit_message_text(sender.text("wrong_name"),
                    chat_id=user_id, message_id=start_mes_id,
                    reply_markup=kb.buttons(True, "back", "menu"))
                return
        
        case "text":
            try:
                text = msg.text
                if text.lower() == "нет":
                    text = None
                DB.commit("update bonds set add_text = ? where id = ?",
                          [text, bond_id])
                await msg.delete()
                await send_bond_info(bond_id, user_id, start_mes_id)
            except Exception as e:
                logging.debug(e)
                try:
                    await msg.delete()
                except: pass
                await bot.edit_message_text(sender.text("wrong_add_text"),
                    chat_id=user_id, message_id=start_mes_id,
                    reply_markup=kb.buttons(True, "back", "menu"))
                return
        
        case "keywords":
            try:
                keywords = msg.text
                if keywords.lower() == "нет":
                    keywords = None
                DB.commit("update bonds set keywords = ? where id = ?",
                          [keywords, bond_id])
                await msg.delete()
                await send_bond_info(bond_id, user_id, start_mes_id)
            except Exception as e:
                logging.debug(e)
                try:
                    await msg.delete()
                except: pass
                await bot.edit_message_text(sender.text("wrong_keywords"),
                    chat_id=user_id, message_id=start_mes_id,
                    reply_markup=kb.buttons(True, "back", "menu"))
                return
        
        case "from" | "to":
            try:
                chat_id = msg.text
                await msg.delete()
                try:
                    chat_id, chat_name = await add_chat(chat_id, user_id)
                except Exception as e:
                    logging.debug(e)
                    await bot.edit_message_text(sender.text("bot_not_in_chat"),
                        chat_id=user_id, message_id=start_mes_id,
                        reply_markup=kb.buttons(True, "back", "menu"))
                    return

                DB.commit(f"update bonds set {status}_chat_name = ?, \
                        {status}_chat_id = ? where id = ?", [chat_name,
                        chat_id, bond_id])
                await send_bond_info(bond_id, user_id, start_mes_id)
            except Exception as e:
                logging.debug(e)
                try:
                    await msg.delete()
                except: pass
                await bot.edit_message_text(sender.text("wrong_from"),
                    chat_id=user_id, message_id=start_mes_id,
                    reply_markup=kb.buttons(True, "back", "menu"))
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
