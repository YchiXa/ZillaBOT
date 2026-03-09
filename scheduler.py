from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import (
    get_users_for_nudge_no_action,
    get_users_for_nudge_no_order,
    set_nudge_sent
)
from texts import NUDGE_NO_ACTION_TEXT, NUDGE_NO_ORDER_TEXT


def get_main_menu_for_nudge():
    keyboard = [
        [InlineKeyboardButton("🌐 Сайт", callback_data="cat_site")],
        [InlineKeyboardButton("🎨 Дизайн", callback_data="cat_design")],
        [InlineKeyboardButton("⚙️ Другое", callback_data="cat_other")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def nudge_no_action(context: ContextTypes.DEFAULT_TYPE):
    """Пришёл, ничего не нажал — напоминаем через 1 час"""
    users = get_users_for_nudge_no_action(hours=1)

    for u in users:
        try:
            await context.bot.send_message(
                chat_id=u["user_id"],
                text=NUDGE_NO_ACTION_TEXT,
                reply_markup=get_main_menu_for_nudge()
            )
            set_nudge_sent(u["user_id"])
        except Exception:
            set_nudge_sent(u["user_id"])


async def nudge_no_order(context: ContextTypes.DEFAULT_TYPE):
    """Нажимал кнопки, но не оставил заявку — напоминаем через 24 часа"""
    users = get_users_for_nudge_no_order(hours=24)

    for u in users:
        try:
            category = u.get("last_category", "услуги")
            text = NUDGE_NO_ORDER_TEXT.format(category=category)
            await context.bot.send_message(
                chat_id=u["user_id"],
                text=text,
                reply_markup=get_main_menu_for_nudge()
            )
            set_nudge_sent(u["user_id"])
        except Exception:
            set_nudge_sent(u["user_id"])