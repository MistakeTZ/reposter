from aiogram import F
from aiogram.filters import Filter, Command
from database.model import DB
from loader import sender, dp
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.types.callback_query import CallbackQuery
from aiogram.utils.markdown import hlink
from states import UserState
from config import get_config
from . import kb


class Restricted(Filter):
    async def __call__(self, message):
        user = DB.get("select id from users where telegram_id = ? and \
                      restricted = 1", [message.from_user.id], True)
        return bool(user)


# Команда бана
@dp.message(Restricted())
async def ban_handler(msg: Message, state: FSMContext) -> None:
    user_id = msg.from_user.id
    await sender.message(user_id, "you_banned")