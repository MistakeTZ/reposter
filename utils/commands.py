from aiogram import F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.utils.markdown import hlink
from loader import dp, bot, sender
from os import path
from datetime import datetime

from utils.tasks import send_menu
from config import get_env, get_config
import utils.kb as kb
from states import UserState
from database.model import DB


# Команда старта бота
@dp.message(CommandStart())
async def command_start_handler(msg: Message, state: FSMContext) -> None:
    user_id = msg.from_user.id
    if not DB.get("select id from users where telegram_id = ?", [user_id]):
        print("New user:", user_id)
        DB.commit("insert into users (telegram_id, name, username, registered) values (?, ?, ?, ?)", 
                  [user_id, msg.from_user.full_name, msg.from_user.username, datetime.now()])
        if str(user_id) in get_env("admins"):
            DB.commit("update users set role = ? where telegram_id = ?", ["admin", user_id])

    first_name = msg.from_user.first_name
    await state.set_state(UserState.default)
    await send_menu(user_id, first_name)


# Команда рассылки
@dp.message(Command("mailing"))
async def command_settings(msg: Message, state: FSMContext) -> None:
    user_id = msg.from_user.id
    role = DB.get("select role from users where telegram_id = ?", [user_id], True)
    if not role:
        await sender.message(user_id, "not_allowed")
        return
    if role[0] != "admin":
        await sender.message(user_id, "not_allowed")
        return

    await sender.message(user_id, "write_message_for_mailing")
    await state.set_state(UserState.mailing)
    await state.set_data({"status": "begin"})


# Команда получения БД
@dp.message(Command("get"))
async def command_settings(msg: Message, state: FSMContext) -> None:
    user_id = msg.from_user.id
    role = DB.get('select role from users where telegram_id = ?', [user_id], True)
    if not role:
        return
    if role[0] != "admin":
        await sender.message(user_id, "not_allowed")
        return
    await sender.send_media(user_id, "file", "db.sqlite3", path="database", name="db")


# Команда добавления админа
@dp.message(Command("role"))
async def command_settings(msg: Message, state: FSMContext) -> None:
    user_id = msg.from_user.id
    if not str(user_id) in get_env("admins"):
        await sender.message(user_id, "not_allowed")
        return
    if len(msg.text.split()) == 1:
        await sender.message(user_id, "write_admin_id")
        return
    if len(msg.text.split()) == 3:
        role = msg.text.split()[2]
    else:
        role = "admin"
    username = msg.text.split()[1]
    if username.startswith("@"):
        username = username[1:]
    user = DB.get("select id from users where username like ?",
                [username], True)
    if not user:
        await sender.message(user_id, "not_found")
        return
    DB.commit("update users set role = ? where id = ?", [role, user[0]])
    await sender.message(user_id, f"user_added")
