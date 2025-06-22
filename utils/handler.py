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
from .tasks import send_bond_info, add_chat, check_keywords, check_for_contacts


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


# Сообщение без состояний
@dp.message(NoStates())
async def no_states(msg: Message):
    chat_id = msg.chat.id
    from_chat_bonds = DB.get_dict("select * from bonds where \
                    from_chat_id = ? and active = 1", [chat_id])
    for bond in from_chat_bonds:
        try:
            message_text = msg.text
            if message_text:
                if DB.get("select id from forwarded where text like ?",
                          [message_text], True):
                    continue
                if not check_keywords(message_text, bond["keywords"]):
                    continue
                if bond["check_for_contacts"]:
                    if not check_for_contacts(message_text, msg.entities):
                        continue

                if bond["add_text"]:
                    send_text = message_text + "\n\n" + bond["add_text"]
                else:
                    send_text = message_text
                await bot.send_message(bond["to_chat_id"], send_text,
                                       entities=msg.entities, parse_mode=None)
                DB.commit("insert into forwarded (bond_id, text, mes_id) \
                            values (?, ?, ?)", [bond["id"],
                            message_text, msg.message_id])
        except Exception as e:
            logging.warning(e)
            await sender.message(bond["owner"], "cant_send_bond",
                                None, msg.chat.title, e)
