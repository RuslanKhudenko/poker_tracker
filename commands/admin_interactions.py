from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from config import CHANNEL_ID

async def send_approval_request_to_admins(context, user_name, action_type="buyin"):
    """
    Отправить запрос на одобрение действия всем администраторам канала.

    :param context: Контекст Telegram
    :param user_name: Имя пользователя, запрашивающего действие
    :param action_type: Тип действия, по умолчанию "buyin"
    """
    # Получаем список администраторов канала
    chat_administrators = await context.bot.get_chat_administrators(CHANNEL_ID)
    admin_ids = [admin.user.id for admin in chat_administrators if not admin.user.is_bot]

    # Создаём кнопки для одобрения или отклонения
    keyboard = [
        [
            InlineKeyboardButton("Да", callback_data=f"approve:{user_name}:{action_type}"),
            InlineKeyboardButton("Нет", callback_data=f"reject:{user_name}:{action_type}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Отправляем сообщение каждому админу
    for admin_id in admin_ids:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"Пользователь {user_name} хочет сделать действие: {action_type}. Разрешить?",
                reply_markup=reply_markup
            )
        except Exception as e:
            print(f"Ошибка отправки запроса администратору {admin_id}: {e}")


async def handle_admin_response(update: Update, context):
    """
    Обработать нажатие кнопки администратором.

    :param update: Обновление Telegram
    :param context: Контекст Telegram
    """
    query = update.callback_query
    await query.answer()

    # Удаляем сообщение с кнопками
    try:
        await query.message.delete()
    except Exception as e:
        print(f"Ошибка при удалении сообщения: {e}")

    # Отправляем админу подтверждение на его действие
    await query.message.reply_text(f"Вы нажали кнопку \"{query.data}\"")

    # Дополнительная обработка действия может быть добавлена здесь

