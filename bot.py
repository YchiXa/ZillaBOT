from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from config import BOT_TOKEN
from database import init_db
from handlers import start, button_handler, message_handler, file_handler
from admin import admin_panel, admin_button_handler
from scheduler import nudge_no_action, nudge_no_order


async def cancel(update, context):
    """Отмена режима ответа/заметки для админа"""
    context.user_data.clear()
    await update.message.reply_text("❌ Отменено. Напишите /admin")


def main():
    print("🚀 Бот запускается...")

    init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("cancel", cancel))

    # Кнопки админки
    app.add_handler(CallbackQueryHandler(admin_button_handler, pattern="^adm_"))

    # Кнопки пользователя
    app.add_handler(CallbackQueryHandler(button_handler))

    # Текст
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    # Файлы
    app.add_handler(MessageHandler(
        filters.PHOTO | filters.Document.ALL | filters.VIDEO, file_handler
    ))

    # Планировщик: дожим
    job_queue = app.job_queue

    # Проверяем каждые 30 минут
    job_queue.run_repeating(nudge_no_action, interval=1800, first=60)

    # Проверяем каждый час
    job_queue.run_repeating(nudge_no_order, interval=3600, first=120)

    print("✅ Бот запущен!")
    print("📋 /start — клиентское меню")
    print("🔐 /admin — админ-панель")
    print("📡 UTM: t.me/бот?start=vk")
    print("🎁 Реферал: t.me/бот?start=ref_ID")

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()