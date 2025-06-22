from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from datetime import datetime

from loader import dp, bot, sender
from database.model import DB
from config import time_difference
from . import kb
from states import UserState


# Рассылка
@dp.message(UserState.mailing)
async def mailing(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    data = await state.get_data()

    match data["status"]:
        case "begin":
            DB.commit("insert into repetitions (chat_id, message_id) values (?, ?)", [user_id, msg.message_id])
            zapis_id = DB.get("select id from repetitions where message_id = ?", [msg.message_id], True)[0]
            await state.set_data({"status": "is_button", "id": zapis_id})
            await sender.message(user_id, "want_to_add_button", kb.reply_table(2, *sender.text("yes_not").split(), is_keys=False))

        case "is_button":
            is_true = sender.text("yes_not").split().index(msg.text) == 0
            if is_true:
                await state.set_data({"status": "link", "id": data["id"]})
                await sender.message(user_id, "write_button_link", kb.ReplyKeyboardMarkup())
            else:
                await state.set_data({"status": "time", "id": data["id"], "link": "", "text": ""})
                await sender.message(user_id, "write_time", kb.reply("now"))
        
        case "link":
            await state.set_data({"status": "text", "id": data["id"], "link": msg.text})
            await sender.message(user_id, "write_button_text")

        case "text":
            if len(msg.text) > 30:
                await sender.message(user_id, "wrong_text")
            else:
                await state.set_data({"status": "time", "id": data["id"], "link": data["link"], "text": msg.text})
                await sender.message(user_id, "write_time", kb.reply("now"))
        
        case "time":
            try:
                if msg.text == sender.text("now"):
                    date = datetime.now() - time_difference
                else:
                    date = datetime.strptime(msg.text, "%d.%m.%Y %H:%M") - time_difference
                DB.commit("update repetitions set button_text = ?, button_link = ?, time_to_send = ? where id = ?",
                          [data["text"], data["link"], date, data["id"]])
                await sender.message(user_id, "message_to_send")

                message_id = DB.get("select message_id from repetitions where id = ?", [data["id"]], True)[0]
                await bot.copy_message(user_id, user_id, message_id, reply_markup=kb.link(data["text"], data["link"]) if data["link"] else None)
                await sender.message(user_id, "type_confirm", kb.ReplyKeyboardRemove(), sender.text("confirm"))
                await state.set_data({"status": "confirm", "id": data["id"]})
            except:
                await sender.message(user_id, "wrong_date")

        case "confirm":
            await state.set_state(UserState.default)
            if msg.text.lower() == sender.text("confirm").lower():
                await sender.message(user_id, "message_sended")
                DB.commit("update repetitions set confirmed = ? where id = ?",
                          [True, data["id"]])
            else:
                await sender.message(user_id, "aborted")