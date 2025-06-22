from loader import sender
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
