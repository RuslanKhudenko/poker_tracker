from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from commands.game_management import GameManagement
from config import CHANNEL_ID

@staticmethod
async def approve_action(update: Update, context: ContextTypes.DEFAULT_TYPE, action_type: str):
    """
    Общая функция для обработки действий, требующих одобрения администратора.

    :param update: Объект Update от Telegram
    :param context: Контекст Telegram
    :param action_type: Тип действия (например, "startgame")
    """
    user_name = update.effective_user.username or "Unknown User"

    # Проверяем активный запрос
    active_requests = context.bot_data.setdefault("approval_requests", {})
    if (user_name, action_type) in active_requests:
        await update.message.reply_text(f"Ваш запрос на {action_type} уже находится на рассмотрении администратора.")
        return

    # Отправляем запрос на аппрув
    approved = await send_approval_request_to_admins(context, user_name, action_type=action_type)
    if not approved:
        await update.message.reply_text(f"Ваш запрос на {action_type} уже находится на рассмотрении администратора.")

async def send_approval_request_to_admins(context, user_name, action_type="buyin"):
    """
    Отправить запрос на одобрение действия всем администраторам канала.

    :param context: Контекст Telegram
    :param user_name: Имя пользователя, запрашивающего действие
    :param action_type: Тип действия, по умолчанию "buyin"
    """
    # Проверяем, есть ли уже активный запрос для пользователя
    active_requests = context.bot_data.setdefault("approval_requests", {})
    if (user_name, action_type) in active_requests:
        return False  # Запрос уже отправлен

    # Добавляем запрос в активные
    active_requests[(user_name, action_type)] = True

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
    return True

async def handle_admin_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action_data = query.data.split(":")
    action = action_data[0]  # approve/reject
    user_name = action_data[1]
    action_type = action_data[2]

    # Удаляем сообщение с кнопками
    try:
        await query.message.delete()
    except Exception as e:
        print(f"Ошибка при удалении сообщения: {e}")

    # Удаляем запрос из активных
    active_requests = context.bot_data.setdefault("approval_requests", {})
    active_requests.pop((user_name, action_type), None)

    if action == "approve":
        # Действие разрешено, выполняем соответствующую функцию
        if action_type == "startgame":
            await GameManagement.startgame_action(context, user_name)
        else:
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=f"Действие {action_type} для пользователя {user_name} выполнено."
            )
    elif action == "reject":
        # Действие отклонено
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"Администратор отклонил действие {action_type} для пользователя {user_name}."
        )
