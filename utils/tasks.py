from loader import sender, bot
from . import kb
from database.model import DB


async def send_menu(user_id, name):
    role = DB.get("select role from users where telegram_id = ?", [user_id], True)[0]
    if role != "admin":
        await sender.message(user_id, "start_message", None,
            name, sender.text("no_rights"))
    else:
        await sender.message(user_id, "start_message", kb.table(2,
            "my_bonds", "bond_list", "add_bond", "add_bond",
            is_keys=True), name, sender.text("menu"))


async def edit_menu(user_id, name, mes):
    role = DB.get("select role from users where telegram_id = ?", [user_id], True)[0]
    if role != "admin":
        await sender.edit_message(mes, "start_message", None,
            name, sender.text("no_rights"))
    else:
        await sender.edit_message(mes, "start_message", kb.table(2,
            "my_bonds", "bond_list", "add_bond", "add_bond",
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
    active = sender.text("status").split("/")[bond["active"]]

    await bot.edit_message_text(sender.text("bond", bond["name"], from_chat,
        to_chat, keywords, text, contacts, active),
        chat_id=user_id, message_id=mes_id, reply_markup=kb.bond(bond_id))


async def add_chat(chat_id, user_id):
    chat = await bot.get_chat(chat_id)
    in_channels = DB.get("select id from channels where \
                         chat_id = ?", [chat.id], True)
    if not in_channels:
        DB.commit("insert into channels (chat_id, name, \
                  username, owner) values (?, ?, ?, ?)",
                  [chat.id, chat.title, chat.username, user_id])
    return chat.id, chat.title


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
