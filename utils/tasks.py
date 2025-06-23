from loader import sender, bot
from . import kb
from database.model import DB
import logging
from aiogram.utils.markdown import hlink
from aiogram.types import ChatPermissions
import time


async def send_menu(user_id, name):
    role = DB.get("select role from users where telegram_id = ?", [user_id], True)[0]
    if role != "admin":
        await sender.message(user_id, "start_message", None,
            name, sender.text("no_rights"))
    else:
        await sender.message(user_id, "start_message", kb.table(2,
            "crosspost", "bond_list",
            is_keys=True), name, sender.text("menu"))


async def edit_menu(user_id, name, mes):
    role = DB.get("select role from users where telegram_id = ?", [user_id], True)[0]
    if role != "admin":
        await sender.edit_message(mes, "start_message", None,
            name, sender.text("no_rights"))
    else:
        await sender.edit_message(mes, "start_message", kb.table(2,
            "crosspost", "bond_list",
            is_keys=True), name, sender.text("menu"))


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
    active = sender.text("status").split("/")[bond["active"]]

    await bot.edit_message_text(sender.text("bond", bond["name"], from_chat,
        to_chat, keywords, text, contacts, sub, active),
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
    if not entities:
        return False
    for entity in entities:
        if entity.type in ["text_link", "url", "mention", "phone_number", "email"]:
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
    
    user = "@" + msg.from_user.username if msg.from_user.username else hlink(
        msg.from_user.full_name, "tg://user?id=" + str(msg.from_user.id))
    chat = await bot.get_chat(bond["to_chat_id"])
    chat_link = hlink(chat.title, "t.me/" + chat.username)
    mes = await msg.answer(sender.text("no_sub", user, chat_link), reply_markup=kb.no_sub(
            "t.me/" + chat.username, bond["to_chat_id"], msg.from_user.id))
    
    if chat_type == "group" or chat_type == "supergroup":
        new_perms = ChatPermissions(can_send_messages=False)
        await bot.restrict_chat_member(msg.chat.id, msg.from_user.id,
                new_perms, until_date=int(time.time() + 60 * 60))
    elif chat_type == "channel":
        await bot.promote_chat_member(msg.chat.id, msg.from_user.id, can_post_messages=False)

    DB.commit("insert into promotes (user_id, chat_id, delete_message, \
        delete_chat, chat_type) values (?, ?, ?, ?, ?)", [msg.from_user.id,
        bond["to_chat_id"], mes.message_id, msg.chat.id, chat_type])

    await msg.delete()

    return False
