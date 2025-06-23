from aiogram import F
from aiogram.types.callback_query import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.markdown import hlink
from loader import dp, bot, sender
import logging
import asyncio
from os import path
from datetime import datetime, timedelta, timezone

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


# Изменение связки
@dp.callback_query(F.data.startswith("edit_"))
async def edit_handler(clbck: CallbackQuery, state: FSMContext) -> None:
    user_id = clbck.from_user.id
    _, action, bond_id = clbck.data.split("_")
    await state.set_state(UserState.bond)
    data = await state.get_data()
    await state.set_data({"state": action, "id": bond_id,
                    "start_mes_id": clbck.message.message_id})

    if action in ["text", "keywords", "name"]:
        await clbck.message.edit_text(sender.text(f"write_{action}"),
                        reply_markup=kb.buttons(True, "back", "menu"))
    elif action in ["from", "to"]:
        chats = DB.get_dict("select * from channels where owner = ?", [user_id])
        if chats:
            chat_data = []
            for chat in chats:
                chat_data.extend([chat["name"], 
                                f"edit_id{chat['id']}_{bond_id}"])
            await clbck.message.edit_text(sender.text(f"write_{action}_ex"),
                reply_markup=kb.buttons(False, *chat_data, sender.text("back"), "menu"))
        else:
            await clbck.message.edit_text(sender.text(f"write_{action}_no"),
                reply_markup=kb.buttons(True, "back", "menu"))
    elif action in ["status", "contacts", "silence", "sub"]:
        field = ["active", "check_for_contacts", "silence", "check_sub"][[
            "status", "contacts", "silence", "sub"].index(action)]
        bond_status = DB.get(f"select {field} from bonds where \
                        id = ?", [int(bond_id)], True)[0]
        DB.commit(f"update bonds set {field} = ? where \
                        id = ?", [not bond_status, int(bond_id)])
        await send_bond_info(bond_id, user_id, clbck.message.message_id)
    elif action == "delete":
        DB.commit("delete from bonds where id = ?", [int(bond_id)])
        await edit_menu(user_id, clbck.from_user.first_name, clbck.message)
    elif action.startswith("id"):
        channel_id = int(action[2:])
        chat = DB.get_dict("select * from channels where id = ?",
                           [channel_id], True)
        action = data["state"]
        DB.commit(f"update bonds set {action}_chat_name = ?, \
            {action}_chat_id = ? where id = ?", [chat["name"],
            chat["chat_id"], int(bond_id)])
        await state.clear()
        await send_bond_info(bond_id, user_id, clbck.message.message_id)


# Проверка подписки
@dp.callback_query(F.data.startswith("sub_"))
async def sub_handler(clbck: CallbackQuery, state: FSMContext) -> None:
    chat_id, user_id = clbck.data.split("_")[1:]
    if clbck.from_user.id != int(user_id):
        await clbck.answer(sender.text("not_your_sub"))
        return
    try:
        role_in_to = await bot.get_chat_member(chat_id, clbck.from_user.id)
        role = role_in_to.status
        if role == "administrator" or role == "creator" or role == "member":
            promote = DB.get("select id, bond_id from promotes where \
                user_id = ? and chat_id = ?", [user_id, chat_id], True)
            if promote:
                DB.commit("delete from promotes where id = ?", [promote[0]])
                DB.commit("update stats set today_sub = today_sub + 1, \
                          total_sub = total_sub + 1 where id = ?", [promote[1]])

            await clbck.answer(sender.text("subed"), show_alert=True)
            await clbck.message.delete()
            return
    except Exception as e:
        logging.debug(e)
    await clbck.answer(sender.text("sub_dont"))
