from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from loader import dp, bot, sender
from os import path
from datetime import datetime
import logging

from utils.tasks import send_menu
from config import get_env, get_config
from states import UserState
from database.model import DB
from .tasks import send_bond_info


# Команда старта бота
@dp.message(CommandStart())
async def command_start_handler(msg: Message, state: FSMContext) -> None:
    user_id = msg.from_user.id
    if len(msg.text.split()) > 1:
        data = msg.text.split()[1]
        if data.startswith("add"):
            await msg.delete()

            action, bond_id, message = data.split("_")[1:]
            chat = msg.chat
            if not DB.get_dict("select * from channels where chat_id = ? \
                            and owner = ?", [chat.id, user_id], True):
                DB.commit("insert into channels (chat_id, name, \
                    username, owner) values (?, ?, ?, ?)", [chat.id,
                    chat.title, chat.username, user_id])

            DB.commit(f"update bonds set {action}_chat_name = ?, \
                {action}_chat_id = ? where id = ?", [chat.title,
                chat.id, int(bond_id)])
            await send_bond_info(bond_id, user_id, message)
            return

    role = DB.get("select role from users \
        where telegram_id = ?", [user_id], True)
    if not role:
        logging.info("New user:", user_id)
        DB.commit("insert into users (telegram_id, name, username, registered) values (?, ?, ?, ?)", 
                  [user_id, msg.from_user.full_name, msg.from_user.username, datetime.now()])
        if str(user_id) in get_env("admins"):
            DB.commit("update users set role = ? where telegram_id = ?", ["admin", user_id])

    first_name = msg.from_user.first_name
    await state.set_state(UserState.default)
    await send_menu(user_id, first_name)
