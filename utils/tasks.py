from loader import sender, bot
from . import kb
from database.model import DB
import logging
from aiogram.utils.markdown import hlink
from aiogram.types import ChatPermissions
from config import get_env
import re


async def send_menu(user_id, name):
    role = DB.get("select role from users where telegram_id = ?", [user_id], True)[0]
    if role != "admin":
        await sender.message(user_id, "start_message", None,
            name, sender.text("no_rights"))
    else:
        if str(user_id) in get_env("admins"):
            reply = kb.table(2, "crosspost", "bond_list", "panel", "admin", is_keys=True)
        else:
            reply = kb.table(2, "crosspost", "bond_list", is_keys=True)
        await sender.message(user_id, "start_message", reply, name, sender.text("menu"))


async def edit_menu(user_id, name, mes):
    role = DB.get("select role from users where telegram_id = ?", [user_id], True)[0]
    if role != "admin":
        await sender.edit_message(mes, "start_message", None,
            name, sender.text("no_rights"))
    else:
        if str(user_id) in get_env("admins"):
            reply = kb.table(2, "crosspost", "bond_list", "panel", "admin", is_keys=True)
        else:
            reply = kb.table(2, "crosspost", "bond_list", is_keys=True)
        await sender.edit_message(mes, "start_message", reply, name, sender.text("menu"))


async def send_bond_info(bond_id, user_id, mes_id):
    bond = DB.get_dict("select * from bonds where id = ?", [bond_id], True)
    if not bond:
        return
    if bond["from_chat_name"]:
        from_chat = bond["from_chat_name"]
    else:
        from_chat = sender.text("not_set_yet")
    
    if bond["to_chat_name"]:
        to_chat = bond["to_chat_name"]
    else:
        to_chat = sender.text("not_set_yet")
    
    if bond["keywords"]:
        keywords = ", ".join(bond["keywords"].split(", "))
    else:
        keywords = sender.text("not_set_yet")
    
    if bond["add_text"]:
        text = bond["add_text"]
    else:
        text = sender.text("no_text")
    
    contacts = sender.text("contacts").split("/")[bond["check_for_contacts"]]
    sub = sender.text("contacts").split("/")[bond["check_sub"]]
    silence = sender.text("silence").split("/")[bond["silence"]]
    active = sender.text("status").split("/")[bond["active"]]

    await bot.edit_message_text(sender.text("bond", bond["name"], from_chat,
        to_chat, keywords, text, contacts, silence, sub, active),
        chat_id=user_id, message_id=mes_id, reply_markup=kb.bond(bond_id))


async def add_chat(chat_id, user_id):
    chat = await bot.get_chat(chat_id)
    title = chat.title
    in_channels = DB.get("select id from channels where \
                         chat_id = ?", [chat.id], True)
    if not in_channels:
        DB.commit("insert into channels (chat_id, name, \
                  username, owner) values (?, ?, ?, ?)",
                  [chat.id, title, chat.username, user_id])
    return chat.id, title


def check_keywords(text, keywords):
    if not keywords:
        return True
    for key in keywords.split(", "):
        if key in text:
            return True
    return False


def check_for_contacts(text, entities):
    for entity in entities:
        if entity.type in ["text_link", "url", "mention", "phone_number", "email"]:
            return True

    comprehensive_pattern = r'(?:(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4}))|(?:\+[1-9]\d{1,14})'
    if re.search(comprehensive_pattern, text):
        return True

    # Or use the verbose version with the VERBOSE flag
    comprehensive_pattern_verbose = r'''
        (?:
            (?:\+?1[-.\s]?)?          # Optional country code with separators
            \(?([0-9]{3})\)?          # Area code with optional parentheses
            [-.\s]?                   # Optional separator
            ([0-9]{3})                # First 3 digits
            [-.\s]?                   # Optional separator
            ([0-9]{4})                # Last 4 digits
        )
        |
        (?:
            \+[1-9]\d{1,14}           # International format (E.164)
        )
    '''
    if re.search(comprehensive_pattern_verbose, text, re.VERBOSE):
        return True

    # For your specific case with Russian number format
    russian_pattern = r'\+7\s?\(?\d{3}\)?\s?\d{3}-?\d{2}-?\d{2}'
    if re.search(russian_pattern, text):
        return True

    # More universal international pattern
    international_pattern = r'\+\d{1,3}\s?\(?\d{1,4}\)?\s?[\d\s\-]{4,14}'
    if re.search(international_pattern, text):
        return True
    return False


async def check_sub(msg, bond, chat_type):
    role = await msg.chat.get_member(msg.from_user.id)
    if role.status == "administrator" or role.status == "creator":
        return True

    if not bond["check_sub"]:
        return True
    try:
        role_in_to = await bot.get_chat_member(bond["to_chat_id"], msg.from_user.id)
        role = role_in_to.status
        if role == "administrator" or role == "creator" or role == "member":
            return True
    except Exception as e:
        logging.debug(e)
    
    prev = DB.get("select id from promotes where user_id = ? and chat_id = ?",
        [msg.from_user.id, bond["to_chat_id"]], True)
    
    if not prev:
        user = "@" + msg.from_user.username if msg.from_user.username else hlink(
            msg.from_user.full_name, "tg://user?id=" + str(msg.from_user.id))
        chat = await bot.get_chat(bond["to_chat_id"])
        chat_link = hlink(chat.title, "t.me/" + chat.username)
        mes = await msg.answer(sender.text("no_sub", user, chat_link), reply_markup=kb.no_sub(
                "t.me/" + chat.username, bond["to_chat_id"], msg.from_user.id))

        DB.commit("insert into promotes (bond_id, user_id, chat_id, delete_message, \
            delete_chat, chat_type) values (?, ?, ?, ?, ?, ?)", [
            bond["id"], msg.from_user.id, bond["to_chat_id"],
            mes.message_id, msg.chat.id, chat_type])

    try:
        await msg.delete()
    except: pass

    return False
