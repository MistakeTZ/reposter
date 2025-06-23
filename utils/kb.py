from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from config import get_config, get_env
from loader import sender


# Inline клавиатура с n количеством кнопок
# Вызывается buttons(Текст 1-ой кнопки, Дата 1-ой кнопки, Текст 2-ой кнопки...)
def buttons(is_keys: bool, *args) -> InlineKeyboardMarkup:
    if is_keys:
        in_buttons = [[InlineKeyboardButton(
            text=sender.text(args[i * 2]),
            callback_data=args[i * 2 + 1] if len(args) >= (i + 1) * 2
            else args[i * 2])] for i in range((len(args) + 1) // 2)]
    else:
        in_buttons = [[InlineKeyboardButton(
            text=args[i * 2],
            callback_data=args[i * 2 + 1] if len(args) >= (i + 1) * 2
            else args[i * 2])] for i in range((len(args) + 1) // 2)]
    return InlineKeyboardMarkup(inline_keyboard=in_buttons)


# Reply клавиатура с одной кнопкой
def reply(name) -> ReplyKeyboardMarkup:
    in_buttons = [[KeyboardButton(text=sender.text(name))]]
    return ReplyKeyboardMarkup(keyboard=in_buttons,
                               one_time_keyboard=True, resize_keyboard=True)


# Таблица inline кнопок
def table(width: int, *args, **kwards) -> InlineKeyboardMarkup:
    in_buttons = []
    index = 0

    while len(args) > index:
        in_buttons.append([])

        for _ in range(width):
            if kwards.get("is_keys", False):
                text = sender.text(args[index])
            else:
                text = args[index]
            in_buttons[-1].append(
                InlineKeyboardButton(text=text,
                                     callback_data=args[index+1]))
            index += 2
            if len(args) == index:
                break

    return InlineKeyboardMarkup(inline_keyboard=in_buttons)


# Таблица reply кнопок
def reply_table(width: int, *args, **kwards
                ) -> ReplyKeyboardMarkup:
    if "one_time" in kwards:
        one_time = kwards["one_time"]
    else:
        one_time = True
    
    if "is_keys" in kwards:
        is_keys = kwards["is_keys"]
    else:
        is_keys = True
    
    in_buttons = []
    index = 0

    while len(args) > index:
        in_buttons.append([])

        for _ in range(width):
            if is_keys:
                in_buttons[-1].append(KeyboardButton(text=sender.text(args[index])))
            else:
                in_buttons[-1].append(KeyboardButton(text=args[index]))
            index += 1
            if len(args) == index:
                break

    return ReplyKeyboardMarkup(
        keyboard=in_buttons, one_time_keyboard=one_time, resize_keyboard=True)


# Клавиатура телефона
def phone() -> ReplyKeyboardMarkup:
    in_buttons = [[KeyboardButton(
        text=sender.text("send_contact"), request_contact=True)]]
    return ReplyKeyboardMarkup(keyboard=in_buttons,
                               one_time_keyboard=True, resize_keyboard=True)


# Кнопки ссылки
def link(text, url) -> InlineKeyboardMarkup:
    in_buttons = [[InlineKeyboardButton(text=text, url=url)]]
    return InlineKeyboardMarkup(inline_keyboard=in_buttons)


# Клавиатура связок
def bonds(bonds) -> InlineKeyboardMarkup:
    button_list = []
    for bond in bonds:
        button_list.append([InlineKeyboardButton(text=bond[1],
                                callback_data=f"bond_{bond[0]}")])
    button_list.append([InlineKeyboardButton(text=sender.text("add_bond"), callback_data="add_bond"),
                        InlineKeyboardButton(text=sender.text("back"), callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=button_list)


# Клавиатура связки
def bond(bond_id) -> InlineKeyboardMarkup:
    return buttons(True, "look_stat", f"stat_{bond_id}", 
                   "set_name", f"edit_name_{bond_id}", "set_from",
                   f"edit_from_{bond_id}", "set_to", f"edit_to_{bond_id}",
                   "set_keywords", f"edit_keywords_{bond_id}", "set_text",
                   f"edit_text_{bond_id}", "set_status",
                   f"edit_status_{bond_id}", "set_contacts",
                   f"edit_contacts_{bond_id}", "set_silence",
                   f"edit_silence_{bond_id}", "set_sub",
                   f"edit_sub_{bond_id}", "set_delete",
                   f"edit_delete_{bond_id}", "back", "menu")


def no_sub(link, chat_id, user_id) -> InlineKeyboardMarkup:
    buttons = [[
        InlineKeyboardButton(text=sender.text("subscribe"),
                             url=link),
        InlineKeyboardButton(text=sender.text("already"),
                             callback_data=f"sub_{chat_id}_{user_id}")
    ]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def add_to_chat(chats, bond_id, my_username, data):
    buttons = []
    buttons.append([InlineKeyboardButton(text="Добавить в чат", url=
        f"https://t.me/{my_username}?startgroup={data}&admin=delete_messages+restrict_members")])
    for chat in chats:
        buttons.append([InlineKeyboardButton(text=chat["name"],
                        callback_data=f"edit_id{chat['id']}_{bond_id}")])
    buttons.append([InlineKeyboardButton(text=sender.text("back"),
                                callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
