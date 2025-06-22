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
    from_chat = DB.get("select name from channels where chat_id = ?",
                          [bond["from_chat_id"]], True)
    if from_chat:
        from_chat = from_chat[0]
    else:
        from_chat = sender.text("not_set_yet")
    
    to_chat = DB.get("select name from channels where chat_id = ?",
                          [bond["to_chat_id"]], True)
    if to_chat:
        to_chat = to_chat[0]
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
    
    active = sender.text("status").split("/")[bond["active"]]

    await bot.edit_message_text(sender.text("bond", bond["name"], from_chat,
        to_chat, keywords, text, active),
        chat_id=user_id, message_id=mes_id, reply_markup=kb.bond(bond_id))
