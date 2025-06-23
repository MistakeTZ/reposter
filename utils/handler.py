from aiogram import F
from aiogram.filters import Filter
from aiogram.types import (
    Message, InputMediaPhoto, InputMediaVideo,
    InputMediaDocument, InputMediaAudio)
from aiogram.utils.markdown import hlink
from aiogram.fsm.context import FSMContext
from loader import dp, bot, sender
from datetime import datetime
import logging

from os import path
import asyncio

import utils.kb as kb
from states import UserState
from database.model import DB
from .tasks import send_bond_info, add_chat, check_keywords, check_for_contacts, check_sub

media_groups = {}
message_to_edit = {}


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
                    DB.commit("insert into stats (bond_id) values (?)", [bond_id])
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
                    if msg.from_user.username in chat_id:
                        chat_id = msg.from_user.id
                        chat_name = msg.from_user.first_name
                    else:
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
async def no_states(msg: Message, force=False):
    chat_id = msg.chat.id
    user_id = msg.from_user.id
    from_chat_bonds = DB.get_dict("select * from bonds where \
                    from_chat_id = ? and active = 1", [chat_id])
    
    for bond in from_chat_bonds:
        try:
            if not await check_sub(msg, bond, msg.chat.type):
                continue
            if not bond["to_chat_id"]:
                continue
            await check_to_edit(user_id)
            message_text = msg.text
            if message_text:
                if DB.get("select id from forwarded where text like ? and bond_id = ?",
                          [message_text, bond["id"]], True): # TODO check forwarded
                    continue
                if bond["check_for_contacts"]:
                    if not check_for_contacts(message_text, msg.entities):
                        await send_caution(msg)
                        continue
                if not check_keywords(message_text, bond["keywords"]):
                    continue

                if bond["add_text"]:
                    send_text = message_text + "\n\n" + bond["add_text"]
                else:
                    send_text = message_text
                await bot.send_message(bond["to_chat_id"], send_text,
                                       entities=msg.entities, parse_mode=None,
                                       disable_notification=bond["silence"])
                DB.commit("insert into forwarded (bond_id, text, mes_id, user_id, chat_id) \
                            values (?, ?, ?, ?, ?)", [bond["id"],
                            message_text, msg.message_id, user_id, chat_id])

            elif msg.caption:
                if msg.media_group_id:
                    if msg.media_group_id in media_groups:
                        media_groups[msg.media_group_id].append(msg)
                        if force:
                            await send_media_group(msg.media_group_id, bond)
                        continue
                    else:
                        media_groups[msg.media_group_id] = [msg]
                        await asyncio.sleep(1)
                        await send_media_group(msg.media_group_id, bond)
                        continue
                if DB.get("select id from forwarded where text like ? and bond_id != ?",
                          [msg.caption, bond["id"]], True):
                    continue
                if bond["check_for_contacts"]:
                    if not check_for_contacts(msg.caption, msg.caption_entities):
                        await send_caution(msg)
                        continue
                if not check_keywords(msg.caption, bond["keywords"]):
                    continue

                if bond["add_text"]:
                    send_text = msg.caption + "\n\n" + bond["add_text"]
                else:
                    send_text = msg.caption
                if msg.photo:
                    await bot.send_photo(bond["to_chat_id"], msg.photo[-1].file_id,
                                        caption=send_text, parse_mode=None,
                                       disable_notification=bond["silence"])
                elif msg.video:
                    await bot.send_video(bond["to_chat_id"], msg.video.file_id,
                                        caption=send_text, parse_mode=None,
                                       disable_notification=bond["silence"])
                elif msg.document:
                    await bot.send_document(bond["to_chat_id"], msg.document.file_id,
                                            caption=send_text, parse_mode=None,
                                            disable_notification=bond["silence"])
                elif msg.audio:
                    await bot.send_audio(bond["to_chat_id"], msg.audio.file_id,
                                        caption=send_text, parse_mode=None,
                                        disable_notification=bond["silence"])
                DB.commit("insert into forwarded (bond_id, text, mes_id, user_id, chat_id) \
                            values (?, ?, ?, ?, ?)", [bond["id"],
                            msg.caption, msg.message_id, user_id, chat_id])

            else:
                if msg.media_group_id:
                    if msg.media_group_id in media_groups:
                        media_groups[msg.media_group_id].append(msg)
                        continue
                    else:
                        media_groups[msg.media_group_id] = [msg]
                        await asyncio.sleep(1)
                        await send_media_group(msg.media_group_id, bond)
                        continue
                if bond["check_for_contacts"]:
                    await send_caution(msg)
                    continue
                if bond["keywords"]:
                    continue
                if msg.photo:
                    await bot.send_photo(bond["to_chat_id"], msg.photo[-1].file_id,
                                        caption=bond["add_text"],
                                        disable_notification=bond["silence"])
                elif msg.video:
                    await bot.send_video(bond["to_chat_id"], msg.video.file_id,
                                        caption=bond["add_text"],
                                        disable_notification=bond["silence"])
                elif msg.document:
                    await bot.send_document(bond["to_chat_id"], msg.document.file_id,
                                            caption=bond["add_text"],
                                            disable_notification=bond["silence"])
                elif msg.audio:
                    await bot.send_audio(bond["to_chat_id"], msg.audio.file_id,
                                        caption=bond["add_text"],
                                        disable_notification=bond["silence"])
                DB.commit("insert into forwarded (bond_id, mes_id, user_id, chat_id) \
                            values (?, ?)", [bond["id"], msg.message_id, user_id, chat_id])
        except Exception as e:
            logging.warning(e)
            await sender.message(bond["owner"], "cant_send_bond",
                                None, msg.chat.title, e)


async def check_to_edit(user_id):
    for key in message_to_edit.keys():
        if message_to_edit[key][1].from_user.id == user_id:
            try:
                await message_to_edit[key][0].delete()
            except:
                pass
            try:
                await message_to_edit[key][1].delete()
            except:
                pass
            del message_to_edit[key]
            return


async def send_media_group(media_group_id, bond):
    group = media_groups[media_group_id]
    media = []
    text = ""
    entities = None
    for message in group:
        if message.caption:
            text = message.caption
            entities = message.caption_entities
    
    if not text:
        if bond["check_for_contacts"]:
            await send_caution(group[0], media_group_id)
            return
        if not bond["keywords"]:
            return
        text = bond["add_text"]
    else:
        if bond["check_for_contacts"]:
            if not check_for_contacts(text, entities):
                await send_caution(group[0], media_group_id)
                return
        if not check_keywords(text, bond["keywords"]):
            return
        if bond["add_text"]:
            text = text + "\n\n" + bond["add_text"]

    for message in group:
        if message.photo:
            media.append(InputMediaPhoto(media=message.photo[-1].file_id))
        elif message.video:
            media.append(InputMediaVideo(media=message.video.file_id))
        elif message.document:
            media.append(InputMediaDocument(media=message.document.file_id))
        elif message.audio:
            media.append(InputMediaAudio(media=message.audio.file_id))
    media[-1].caption = text
    media[-1].caption_entities = entities
    media[-1].parse_mode = None
    await bot.send_media_group(bond["to_chat_id"], media, disable_notification=bond["silence"])


@dp.edited_message()
async def edited_handler(msg: Message):
    if message_to_edit.get(msg.message_id, None):
        try:
            await message_to_edit[msg.message_id][0].delete()
        except Exception as e:
            logging.warning(e)
        del message_to_edit[msg.message_id]
        await no_states(msg)
    elif message_to_edit.get(msg.media_group_id, None):
        try:
            await message_to_edit[msg.media_group_id][0].delete()
        except Exception as e:
            logging.warning(e)
        del message_to_edit[msg.media_group_id]

        for message in media_groups[msg.media_group_id]:
            if message.message_id == msg.message_id:
                media_groups[msg.media_group_id].remove(message)
                break
        await no_states(msg, force=True)


async def send_caution(msg, key=None):
    role = await msg.chat.get_member(msg.from_user.id)
    if role.status == "administrator" or role.status == "creator":
        return
    user = "@" + msg.from_user.username if msg.from_user.username else hlink(
        msg.from_user.full_name, "tg://user?id=" + str(msg.from_user.id))
    ans = await msg.answer(sender.text("your_message_no_bio", user))
    if not key:
        key = msg.message_id
    message_to_edit[key] = [ans, msg]

    await asyncio.sleep(60 * 10)
    try:
        await ans.delete()
    except Exception as e:
        logging.warning(e)
    try:
        if msg.media_group_id:
            for message in media_groups[msg.media_group_id]:
                try:
                    await message.delete()
                except Exception as e:
                    logging.warning(e)
        else:
            await msg.delete()
    except Exception as e:
        logging.warning(e)
