from aiogram import F
from aiogram.types.callback_query import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.markdown import hlink
from loader import dp, bot, sender
import asyncio
from os import path

from config import get_env, get_config
import utils.kb as kb
from states import UserState
from database.model import DB
from .tasks import edit_menu, send_bond_info


# Мои связки
@dp.callback_query(F.data == "bond_list")
async def menu_handler(clbck: CallbackQuery, state: FSMContext) -> None:
    user_id = clbck.from_user.id
    bonds = DB.get("select * from bonds where owner = ?", [user_id])
    if not bonds:
        await sender.edit_message(clbck.message, "no_bonds", kb.table(
            2, "add_bond", "add_bond", "back", "menu", is_keys=True))
        return
    else:
        await sender.edit_message(clbck.message, "your_bonds", kb.bonds(bonds))


# Возвращение в меню
@dp.callback_query(F.data == "menu")
async def start_handler(clbck: CallbackQuery, state: FSMContext) -> None:
    user_id = clbck.from_user.id
    await edit_menu(user_id, clbck.from_user.first_name, clbck.message)


# Добавление связки
@dp.callback_query(F.data == "add_bond")
async def add_handler(clbck: CallbackQuery, state: FSMContext) -> None:
    user_id = clbck.from_user.id
    await clbck.message.edit_text(sender.text("write_bond_name"),
                            reply_markup=kb.buttons(True, "back", "menu"))
    await state.set_state(UserState.bond)
    await state.set_data({"state": "name", "start_mes_id": clbck.message.message_id})


# Вывод связки
@dp.callback_query(F.data.startswith("bond_"))
async def bond_handler(clbck: CallbackQuery, state: FSMContext) -> None:
    user_id = clbck.from_user.id
    bond_id = clbck.data.split("_")[1]
    await send_bond_info(bond_id, user_id, clbck.message.message_id)
