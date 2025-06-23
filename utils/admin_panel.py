from aiogram.filters import Filter, Command
from database.model import DB
from loader import sender, dp
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from states import UserState
from config import get_env


class AdminFilter(Filter):
    async def __call__(self, message):
        user_id = message.from_user.id
        role = DB.get("select role from users where telegram_id = ?",
                      [user_id], True)
        if not role:
            await sender.message(user_id, "not_allowed")
            return False
        if role[0] != "admin":
            await sender.message(user_id, "not_allowed")
            return False
        return True


# Команда рассылки
@dp.message(Command("mailing"), AdminFilter())
async def command_settings(msg: Message, state: FSMContext) -> None:
    user_id = msg.from_user.id

    await sender.message(user_id, "write_message_for_mailing")
    await state.set_state(UserState.mailing)
    await state.set_data({"status": "begin"})


# Команда получения БД
@dp.message(Command("get"), AdminFilter())
async def command_settings(msg: Message, state: FSMContext) -> None:
    user_id = msg.from_user.id
    await sender.send_media(user_id, "file", "db.sqlite3", path="database", name="db")


# Команда добавления админа
@dp.message(Command("role"), AdminFilter())
async def command_settings(msg: Message, state: FSMContext) -> None:
    user_id = msg.from_user.id
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
    