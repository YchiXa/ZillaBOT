from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import ContextTypes
from config import ADMIN_ID, SPAM_COOLDOWN, AUTO_REPLY_DELAY, REFERRAL_BONUS_PERCENT
from database import (
    add_user, add_order, is_blocked, can_submit_order,
    set_user_last_category, get_user, get_all_faq, get_faq_by_id
)
from texts import *


def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("🌐 Сайт", callback_data="cat_site")],
        [InlineKeyboardButton("🎨 Дизайн", callback_data="cat_design")],
        [InlineKeyboardButton("⚙️ Другое", callback_data="cat_other")],
        [InlineKeyboardButton("❓ Частые вопросы", callback_data="faq_menu")],
        [InlineKeyboardButton("🎁 Реферальная программа", callback_data="referral")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_waiting_keyboard():
    """Клавиатура в состоянии ожидания текста"""
    keyboard = [
        [InlineKeyboardButton("➡️ Продолжить без описания", callback_data="skip_message")],
        [InlineKeyboardButton("❌ Отмена", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    context.user_data.clear()

    # Парсим UTM / реферальный параметр
    source = ""
    referred_by = 0

    if context.args and len(context.args) > 0:
        param = context.args[0]
        if param.startswith("ref_"):
            try:
                referred_by = int(param.replace("ref_", ""))
            except ValueError:
                pass
        else:
            source = param  # vk, instagram, avito и т.д.

    is_new = add_user(
        user_id=user.id,
        full_name=user.full_name,
        username=user.username or "нет",
        source=source,
        referred_by=referred_by
    )

    # Сохраняем источник в контексте
    if source:
        context.user_data["source"] = source

    # Уведомляем админа о новом пользователе
    if is_new:
        try:
            source_text = f"📡 Источник: *{source}*" if source else "📡 Прямой переход"
            ref_text = f"👥 Приглашён: `{referred_by}`" if referred_by else ""

            admin_text = (
                f"🆕 *Новый пользователь!*\n\n"
                f"👤 {user.full_name}\n"
                f"🆔 @{user.username or 'нет'}\n"
                f"🔢 ID: `{user.id}`\n"
                f"{source_text}\n"
                f"{ref_text}\n\n"
                f"[Написать](tg://user?id={user.id})"
            )
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_text,
                parse_mode="Markdown"
            )
        except Exception:
            pass

    # Выбираем приветствие
    if referred_by:
        welcome = WELCOME_REFERRAL_TEXT.format(name=user.first_name)
    else:
        welcome = WELCOME_TEXT.format(name=user.first_name)

    await update.message.reply_text(welcome, reply_markup=get_main_menu())


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user

    if query.data.startswith("adm_"):
        return

    await query.answer()
    data = query.data

    # Проверка блокировки
    if is_blocked(user.id):
        await query.edit_message_text(BLOCKED_TEXT)
        return

    # ----- ГЛАВНОЕ МЕНЮ -----

    if data == "cat_site":
        set_user_last_category(user.id, "Сайт")
        keyboard = [
            [InlineKeyboardButton("🟢 Простой — от 15 000₽", callback_data="site_simple")],
            [InlineKeyboardButton("🟡 Средний — от 40 000₽", callback_data="site_medium")],
            [InlineKeyboardButton("🔴 Сложный — от 100 000₽", callback_data="site_complex")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_main")],
        ]
        await query.edit_message_text(
            SITE_LEVEL_TEXT,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "cat_design":
        set_user_last_category(user.id, "Дизайн")
        context.user_data["category"] = "Дизайн"
        context.user_data["subcategory"] = "—"
        context.user_data["state"] = "waiting_message"

        await query.edit_message_text(
            DESIGN_TEXT,
            reply_markup=get_waiting_keyboard()
        )

    elif data == "cat_other":
        set_user_last_category(user.id, "Другое")
        keyboard = [
            [InlineKeyboardButton("🤖 Telegram-бот", callback_data="other_bot")],
            [InlineKeyboardButton("💻 Различное ПО", callback_data="other_software")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_main")],
        ]
        await query.edit_message_text(
            OTHER_TEXT,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ----- САЙТЫ -----

    elif data == "site_simple":
        context.user_data["category"] = "Сайт"
        context.user_data["subcategory"] = "Простой (от 15 000₽)"
        keyboard = [
            [InlineKeyboardButton("✅ Заказать", callback_data="order_site")],
            [InlineKeyboardButton("◀️ Назад", callback_data="cat_site")],
        ]
        await query.edit_message_text(
            SITE_SIMPLE_TEXT,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif data == "site_medium":
        context.user_data["category"] = "Сайт"
        context.user_data["subcategory"] = "Средний (от 40 000₽)"
        keyboard = [
            [InlineKeyboardButton("✅ Заказать", callback_data="order_site")],
            [InlineKeyboardButton("◀️ Назад", callback_data="cat_site")],
        ]
        await query.edit_message_text(
            SITE_MEDIUM_TEXT,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif data == "site_complex":
        context.user_data["category"] = "Сайт"
        context.user_data["subcategory"] = "Сложный (от 100 000₽)"
        keyboard = [
            [InlineKeyboardButton("✅ Заказать", callback_data="order_site")],
            [InlineKeyboardButton("◀️ Назад", callback_data="cat_site")],
        ]
        await query.edit_message_text(
            SITE_COMPLEX_TEXT,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif data == "order_site":
        context.user_data["state"] = "waiting_message"
        await query.edit_message_text(
            CONFIRM_SITE_TEXT,
            reply_markup=get_waiting_keyboard(),
            parse_mode="Markdown"
        )

    # ----- ДРУГОЕ -----

    elif data == "other_bot":
        context.user_data["category"] = "Другое"
        context.user_data["subcategory"] = "Telegram-бот"
        context.user_data["state"] = "waiting_message"
        await query.edit_message_text(
            OTHER_BOT_TEXT,
            reply_markup=get_waiting_keyboard(),
            parse_mode="Markdown"
        )

    elif data == "other_software":
        context.user_data["category"] = "Другое"
        context.user_data["subcategory"] = "Различное ПО"
        context.user_data["state"] = "waiting_message"
        await query.edit_message_text(
            OTHER_SOFTWARE_TEXT,
            reply_markup=get_waiting_keyboard(),
            parse_mode="Markdown"
        )

    # ----- ПРОДОЛЖИТЬ БЕЗ ОПИСАНИЯ -----

    elif data == "skip_message":
        if context.user_data.get("state") == "waiting_message":
            await submit_order(
                update, context,
                message_text="[Без описания — клиент не написал детали]"
            )
        else:
            await query.edit_message_text(
                WELCOME_TEXT.format(name=user.first_name),
                reply_markup=get_main_menu()
            )

    # ----- FAQ -----

    elif data == "faq_menu":
        faq_list = get_all_faq()
        keyboard = []
        for f in faq_list:
            keyboard.append([
                InlineKeyboardButton(f["question"], callback_data=f"faq_{f['id']}")
            ])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_main")])

        await query.edit_message_text(
            "❓ *Частые вопросы*\n\nВыберите вопрос:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif data.startswith("faq_"):
        faq_id = int(data.replace("faq_", ""))
        faq = get_faq_by_id(faq_id)
        if faq:
            keyboard = [
                [InlineKeyboardButton("◀️ К вопросам", callback_data="faq_menu")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")],
            ]
            await query.edit_message_text(
                f"*{faq['question']}*\n\n{faq['answer']}",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )

    # ----- РЕФЕРАЛЬНАЯ ПРОГРАММА -----

    elif data == "referral":
        db_user = get_user(user.id)
        ref_count = db_user["referral_count"] if db_user else 0
        bot_info = await context.bot.get_me()
        link = f"https://t.me/{bot_info.username}?start=ref_{user.id}"

        text = REFERRAL_TEXT.format(
            percent=REFERRAL_BONUS_PERCENT,
            link=link,
            count=ref_count
        )

        keyboard = [
            [InlineKeyboardButton("◀️ Назад", callback_data="back_main")]
        ]
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    # ----- НАЗАД -----

    elif data == "back_main":
        context.user_data.clear()
        await query.edit_message_text(
            WELCOME_TEXT.format(name=user.first_name),
            reply_markup=get_main_menu()
        )


# ===== ОТПРАВКА ЗАЯВКИ =====

async def submit_order(update: Update, context: ContextTypes.DEFAULT_TYPE,
                       message_text: str):
    """Общая функция отправки заявки"""
    if update.callback_query:
        user = update.callback_query.from_user
    else:
        user = update.effective_user

    category = context.user_data.get("category", "Не указана")
    subcategory = context.user_data.get("subcategory", "Не указана")
    source = context.user_data.get("source", "")

    # Антиспам
    if not can_submit_order(user.id, SPAM_COOLDOWN):
        text = SPAM_COOLDOWN_TEXT
        keyboard = [[InlineKeyboardButton("🏠 Меню", callback_data="back_main")]]
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text, reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text(
                text, reply_markup=InlineKeyboardMarkup(keyboard)
            )
        context.user_data.clear()
        return

    # Получаем источник из БД если нет в контексте
    if not source:
        db_user = get_user(user.id)
        if db_user:
            source = db_user.get("source", "прямой")

    # Сохраняем заявку
    order_id = add_order(
        user_id=user.id,
        full_name=user.full_name,
        username=user.username or "нет_username",
        category=category,
        subcategory=subcategory,
        message=message_text,
        source=source or "прямой"
    )

    # Отправляем админу
    admin_text = ADMIN_ORDER_TEXT.format(
        order_id=order_id,
        full_name=user.full_name,
        username=user.username or "нет_username",
        user_id=user.id,
        category=category,
        subcategory=subcategory,
        message=message_text,
        source=source or "прямой"
    )

    try:
        admin_keyboard = [
            [InlineKeyboardButton(
                f"📋 Открыть заявку #{order_id}",
                callback_data=f"adm_order_{order_id}"
            )]
        ]
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(admin_keyboard)
        )
    except Exception as e:
        print(f"Ошибка отправки админу: {e}")

    # Подтверждаем пользователю
    keyboard = [[InlineKeyboardButton("📋 Новая заявка", callback_data="back_main")]]
    text = ORDER_RECEIVED_TEXT.format(order_id=order_id)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    # Планируем авто-ответ через 60 секунд
    context.job_queue.run_once(
        auto_reply_callback,
        when=AUTO_REPLY_DELAY,
        data={"user_id": user.id, "order_id": order_id},
        name=f"auto_reply_{order_id}"
    )

    context.user_data.clear()


async def auto_reply_callback(context: ContextTypes.DEFAULT_TYPE):
    """Авто-ответ клиенту через минуту"""
    data = context.job.data
    try:
        await context.bot.send_message(
            chat_id=data["user_id"],
            text=AUTO_REPLY_TEXT,
            parse_mode="Markdown"
        )
    except Exception:
        pass


# ===== ОБРАБОТКА ТЕКСТА =====

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if is_blocked(user.id):
        await update.message.reply_text(BLOCKED_TEXT)
        return

    # Режим ответа админа клиенту
    admin_reply = context.user_data.get("admin_reply_to")
    if admin_reply and user.id == ADMIN_ID:
        try:
            await context.bot.send_message(
                chat_id=admin_reply["user_id"],
                text=f"💬 *Сообщение от менеджера:*\n\n{update.message.text}",
                parse_mode="Markdown"
            )
            await update.message.reply_text(
                f"✅ Сообщение отправлено клиенту {admin_reply['full_name']}!"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {e}")
        context.user_data.clear()
        return

    # Режим заметки к заявке
    admin_note = context.user_data.get("admin_note_to")
    if admin_note and user.id == ADMIN_ID:
        from database import add_order_note
        add_order_note(admin_note, update.message.text)
        await update.message.reply_text(
            f"📝 Заметка добавлена к заявке #{admin_note}!"
        )
        context.user_data.clear()
        return

    # Обычный пользователь
    state = context.user_data.get("state")
    if state != "waiting_message":
        await update.message.reply_text(
            "Используйте меню для навигации.\nНажмите /start"
        )
        return

    await submit_order(update, context, message_text=update.message.text)


async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if is_blocked(user.id):
        await update.message.reply_text(BLOCKED_TEXT)
        return

    state = context.user_data.get("state")
    if state != "waiting_message":
        await update.message.reply_text("Сначала выберите категорию.\nНажмите /start")
        return

    caption = update.message.caption or "[Файл без описания]"

    # Сохраняем заявку
    category = context.user_data.get("category", "Не указана")
    subcategory = context.user_data.get("subcategory", "Не указана")
    source = context.user_data.get("source", "")

    if not source:
        db_user = get_user(user.id)
        if db_user:
            source = db_user.get("source", "прямой")

    if not can_submit_order(user.id, SPAM_COOLDOWN):
        await update.message.reply_text(SPAM_COOLDOWN_TEXT)
        context.user_data.clear()
        return

    order_id = add_order(
        user_id=user.id,
        full_name=user.full_name,
        username=user.username or "нет_username",
        category=category,
        subcategory=subcategory,
        message=caption + " [+файл]",
        source=source or "прямой"
    )

    admin_text = ADMIN_ORDER_TEXT.format(
        order_id=order_id,
        full_name=user.full_name,
        username=user.username or "нет_username",
        user_id=user.id,
        category=category,
        subcategory=subcategory,
        message=caption + "\n\n📎 *Файл ниже*",
        source=source or "прямой"
    )

    try:
        admin_keyboard = [
            [InlineKeyboardButton(
                f"📋 Заявка #{order_id}",
                callback_data=f"adm_order_{order_id}"
            )]
        ]
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(admin_keyboard)
        )
        await update.message.forward(chat_id=ADMIN_ID)
    except Exception as e:
        print(f"Ошибка: {e}")

    keyboard = [[InlineKeyboardButton("📋 Новая заявка", callback_data="back_main")]]
    await update.message.reply_text(
        ORDER_RECEIVED_TEXT.format(order_id=order_id),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

    context.job_queue.run_once(
        auto_reply_callback,
        when=AUTO_REPLY_DELAY,
        data={"user_id": user.id, "order_id": order_id},
        name=f"auto_reply_{order_id}"
    )

    context.user_data.clear()