from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMIN_ID
from database import (
    get_stats, get_recent_orders, get_recent_users,
    get_order_by_id, update_order_status, get_orders_by_status,
    block_user, unblock_user, get_user
)


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


async def show_order_card(query, order_id: int):
    """Отображает карточку заявки"""
    order = get_order_by_id(order_id)

    if not order:
        await query.edit_message_text("❌ Заявка не найдена.")
        return

    # Автоматически помечаем прочитанной
    if order["status"] == "new":
        update_order_status(order_id, "in_progress")
        order["status"] = "in_progress"

    status_icons = {
        "new": "🆕 Новая",
        "in_progress": "🔄 В работе",
        "done": "✅ Выполнена",
        "cancelled": "❌ Отменена"
    }

    uname = f"@{order['username']}" if order['username'] != "нет_username" else "без username"
    note_text = f"\n\n📝 *Заметки:*\n{order['admin_note']}" if order.get("admin_note") else ""

    text = (
        f"📋 *ЗАЯВКА #{order['id']}*\n━━━━━━━━━━━━━━━━\n\n"
        f"📌 Статус: *{status_icons.get(order['status'], order['status'])}*\n"
        f"📅 {order['date']}\n"
        f"📡 Источник: {order.get('source', '—')}\n\n"
        f"👤 *{order['full_name']}*\n"
        f"🆔 {uname}\n"
        f"🔢 `{order['user_id']}`\n\n"
        f"📂 {order['category']} → {order['subcategory']}\n\n"
        f"💬 *Сообщение:*\n{order['message']}"
        f"{note_text}\n\n"
        f"[✉️ Написать в Telegram](tg://user?id={order['user_id']})"
    )

    keyboard = []

    # Ответить клиенту через бота
    keyboard.append([InlineKeyboardButton(
        "💬 Ответить клиенту", callback_data=f"adm_reply_{order['id']}"
    )])

    # Заметка
    keyboard.append([InlineKeyboardButton(
        "📝 Добавить заметку", callback_data=f"adm_note_{order['id']}"
    )])

    # Статусы
    if order["status"] != "done":
        keyboard.append([InlineKeyboardButton(
            "✅ Выполнена", callback_data=f"adm_st_{order['id']}_done"
        )])
    if order["status"] != "cancelled":
        keyboard.append([InlineKeyboardButton(
            "❌ Отменить", callback_data=f"adm_st_{order['id']}_cancelled"
        )])
    if order["status"] != "in_progress":
        keyboard.append([InlineKeyboardButton(
            "🔄 В работу", callback_data=f"adm_st_{order['id']}_in_progress"
        )])
    if order["status"] != "new":
        keyboard.append([InlineKeyboardButton(
            "🆕 В новые", callback_data=f"adm_st_{order['id']}_new"
        )])

    # Заблокировать пользователя
    db_user = get_user(order["user_id"])
    if db_user and db_user.get("blocked"):
        keyboard.append([InlineKeyboardButton(
            "🔓 Разблокировать", callback_data=f"adm_unblock_{order['user_id']}"
        )])
    else:
        keyboard.append([InlineKeyboardButton(
            "🚫 Заблокировать", callback_data=f"adm_block_{order['user_id']}"
        )])

    keyboard.append([
        InlineKeyboardButton("◀️ К заявкам", callback_data="adm_orders"),
        InlineKeyboardButton("🏠 Меню", callback_data="adm_back_main")
    ])

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
        disable_web_page_preview=True
    )


def get_admin_menu():
    keyboard = [
        [InlineKeyboardButton("📋 Заявки", callback_data="adm_orders"),
         InlineKeyboardButton("👥 Пользователи", callback_data="adm_users")],
        [InlineKeyboardButton("📊 Статистика", callback_data="adm_stats"),
         InlineKeyboardButton("���� Источники", callback_data="adm_sources")],
        [InlineKeyboardButton("🆕 Новые", callback_data="adm_orders_new"),
         InlineKeyboardButton("🔄 В работе", callback_data="adm_orders_progress")],
        [InlineKeyboardButton("✅ Выполненные", callback_data="adm_orders_done"),
         InlineKeyboardButton("❌ Отменённые", callback_data="adm_orders_cancelled")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Нет доступа.")
        return

    stats = get_stats()
    new_count = stats["by_status"].get("new", 0)

    text = (
        "🔐 *АДМИН-ПАНЕЛЬ*\n"
        "━━━━━━━━━━━━━━━━\n\n"
        f"👥 Пользователей: *{stats['total_users']}*\n"
        f"📋 Заявок: *{stats['total_orders']}*\n"
        f"🆕 Необработанных: *{new_count}*\n"
        f"🚫 Заблокировано: *{stats['blocked_users']}*\n\n"
        f"📅 *Сегодня:*\n"
        f"  • Пользователей: *{stats['users_today']}*\n"
        f"  • Заявок: *{stats['orders_today']}*\n\n"
        "Выберите раздел 👇"
    )

    await update.message.reply_text(
        text, reply_markup=get_admin_menu(), parse_mode="Markdown"
    )


async def admin_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user

    if not is_admin(user.id):
        await query.answer("⛔ Нет доступа", show_alert=True)
        return

    data = query.data
    await query.answer()

    # ===== СТАТИСТИКА =====

    if data == "adm_stats":
        stats = get_stats()

        cat_text = ""
        for cat, count in stats["by_category"].items():
            cat_text += f"  • {cat}: *{count}*\n"
        if not cat_text:
            cat_text = "  • Пока нет\n"

        status_names = {
            "new": "🆕 Новые",
            "in_progress": "🔄 В работе",
            "done": "✅ Выполненные",
            "cancelled": "❌ Отменённые"
        }
        status_text = ""
        for st, name in status_names.items():
            count = stats["by_status"].get(st, 0)
            status_text += f"  • {name}: *{count}*\n"

        text = (
            "📊 *СТАТИСТИКА*\n━━━━━━━━━━━━━━━━\n\n"
            f"👥 Пользователей: *{stats['total_users']}*\n"
            f"📋 Заявок: *{stats['total_orders']}*\n"
            f"👥 Рефералов: *{stats['total_referrals']}*\n\n"
            f"📅 *Сегодня:*\n"
            f"  • Пользователей: *{stats['users_today']}*\n"
            f"  • Заявок: *{stats['orders_today']}*\n\n"
            f"📂 *По категориям:*\n{cat_text}\n"
            f"📌 *По статусам:*\n{status_text}"
        )

        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="adm_back_main")]]
        await query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    # ===== ИСТОЧНИКИ (UTM) =====

    elif data == "adm_sources":
        stats = get_stats()

        if not stats["by_source"]:
            source_text = "Пока нет данных по источникам.\n\nИспользуйте ссылки:\n`t.me/бот?start=vk`\n`t.me/бот?start=instagram`\n`t.me/бот?start=avito`"
        else:
            source_text = ""
            total = sum(stats["by_source"].values())
            for src, count in sorted(stats["by_source"].items(), key=lambda x: x[1], reverse=True):
                pct = round(count / total * 100)
                bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
                source_text += f"*{src}*: {count} чел. ({pct}%)\n{bar}\n\n"

        text = f"📡 *ИСТОЧНИКИ ТРАФИКА*\n━━━━━━━━━━━━━━━━\n\n{source_text}"

        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="adm_back_main")]]
        await query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    # ===== ПОЛЬЗОВАТЕЛИ =====

    elif data == "adm_users":
        users = get_recent_users(15)

        if not users:
            text = "👥 *ПОЛЬЗОВАТЕЛИ*\n\nПока никого."
        else:
            text = "👥 *ПОСЛЕДНИЕ ПОЛЬЗОВАТЕЛИ*\n━━━━━━━━━━━━━━━━\n\n"
            for i, u in enumerate(users, 1):
                uname = f"@{u['username']}" if u['username'] != "нет" else "без username"
                blocked_mark = " 🚫" if u.get("blocked") else ""
                source_mark = f" 📡{u['source']}" if u.get("source") else ""
                text += (
                    f"*{i}.* {u['full_name']}{blocked_mark}\n"
                    f"    {uname}{source_mark}\n"
                    f"    📅 {u['registered']} | 👁 {u['visits']}\n"
                    f"    [Написать](tg://user?id={u['user_id']})\n\n"
                )

        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="adm_back_main")]]
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
            disable_web_page_preview=True
        )

    # ===== ЗАЯВКИ =====

    elif data == "adm_orders":
        await show_orders_list(query, get_recent_orders(10), "📋 ПОСЛЕДНИЕ ЗАЯВКИ")

    elif data == "adm_orders_new":
        orders = get_orders_by_status("new")[:10]
        await show_orders_list(query, orders, "🆕 НОВЫЕ ЗАЯВКИ")

    elif data == "adm_orders_progress":
        orders = get_orders_by_status("in_progress")[:10]
        await show_orders_list(query, orders, "🔄 В РАБОТЕ")

    elif data == "adm_orders_done":
        orders = get_orders_by_status("done")[:10]
        await show_orders_list(query, orders, "✅ ВЫПОЛНЕННЫЕ")

    elif data == "adm_orders_cancelled":
        orders = get_orders_by_status("cancelled")[:10]
        await show_orders_list(query, orders, "❌ ОТМЕНЁННЫЕ")

    # ===== ДЕТАЛИ ЗАЯВКИ =====

    elif data.startswith("adm_order_"):
        order_id = int(data.replace("adm_order_", ""))
        await show_order_card(query, order_id)

    # ===== ОТВЕТИТЬ КЛИЕНТУ =====

    elif data.startswith("adm_reply_"):
        order_id = int(data.replace("adm_reply_", ""))
        order = get_order_by_id(order_id)
        if order:
            context.user_data["admin_reply_to"] = {
                "user_id": order["user_id"],
                "full_name": order["full_name"],
                "order_id": order_id
            }
            await query.edit_message_text(
                f"💬 *Ответ клиенту {order['full_name']}*\n\n"
                f"Напишите сообщение — бот отправит его клиенту от своего имени.\n\n"
                f"Или /cancel для отмены.",
                parse_mode="Markdown"
            )

    # ===== ЗАМЕТКА К ЗАЯВКЕ =====

    elif data.startswith("adm_note_"):
        order_id = int(data.replace("adm_note_", ""))
        context.user_data["admin_note_to"] = order_id
        await query.edit_message_text(
            f"📝 *Заметка к заявке #{order_id}*\n\n"
            f"Напишите текст заметки.\n\n"
            f"Или /cancel для отмены.",
            parse_mode="Markdown"
        )

    # ===== СМЕНА СТАТУСА =====

    elif data.startswith("adm_st_"):
        raw = data.replace("adm_st_", "")
        for status in ["in_progress", "done", "cancelled", "new"]:
            if raw.endswith(f"_{status}"):
                order_id = int(raw.replace(f"_{status}", ""))
                update_order_status(order_id, status)

                status_names = {
                    "new": "🆕 Новая",
                    "in_progress": "🔄 В работе",
                    "done": "✅ Выполнена",
                    "cancelled": "❌ Отменена"
                }

                await query.answer(
                    f"Статус: {status_names.get(status, status)}",
                    show_alert=True
                )

                # Перезагружаем карточку заявки
                await show_order_card(query, order_id)
                return

    # ===== БЛОКИРОВКА =====

    elif data.startswith("adm_block_"):
        uid = int(data.replace("adm_block_", ""))
        block_user(uid)
        await query.answer("🚫 Пользователь заблокирован!", show_alert=True)

        # Возвращаемся к заявкам
        await show_orders_list(query, get_recent_orders(10), "📋 ПОСЛЕДНИЕ ЗАЯВКИ")

    elif data.startswith("adm_unblock_"):
        uid = int(data.replace("adm_unblock_", ""))
        unblock_user(uid)
        await query.answer("🔓 Пользователь разблокирован!", show_alert=True)

        await show_orders_list(query, get_recent_orders(10), "📋 ПОСЛЕДНИЕ ЗАЯВКИ")

    # ===== НАЗАД =====

    elif data == "adm_back_main":
        stats = get_stats()
        new_count = stats["by_status"].get("new", 0)

        text = (
            "🔐 *АДМИН-ПАНЕЛЬ*\n━━━━━━━━━━━━━━━━\n\n"
            f"👥 Пользователей: *{stats['total_users']}*\n"
            f"📋 Заявок: *{stats['total_orders']}*\n"
            f"🆕 Необработанных: *{new_count}*\n\n"
            f"📅 *Сегодня:*\n"
            f"  • Пользователей: *{stats['users_today']}*\n"
            f"  • Заявок: *{stats['orders_today']}*\n\n"
            "Выберите раздел 👇"
        )

        await query.edit_message_text(
            text, reply_markup=get_admin_menu(), parse_mode="Markdown"
        )


async def show_orders_list(query, orders, title):
    if not orders:
        text = f"*{title}*\n\nЗаявок нет."
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="adm_back_main")]]
        await query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )
        return

    status_icons = {
        "new": "🆕", "in_progress": "🔄", "done": "✅", "cancelled": "❌"
    }

    text = f"*{title}*\n━━━━━━━━━━━━━━━━\n\n"
    keyboard = []

    for o in orders:
        icon = status_icons.get(o["status"], "❓")
        short = o["message"][:35] + "..." if len(o["message"]) > 35 else o["message"]
        text += (
            f"{icon} *#{o['id']}* | {o['category']}\n"
            f"  👤 {o['full_name']} | 📅 {o['date']}\n"
            f"  💬 _{short}_\n\n"
        )
        keyboard.append([InlineKeyboardButton(
            f"{icon} #{o['id']} — {o['full_name']}",
            callback_data=f"adm_order_{o['id']}"
        )])

    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="adm_back_main")])

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )