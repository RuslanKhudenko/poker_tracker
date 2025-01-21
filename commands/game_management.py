from datetime import datetime, timezone
from engine import Session
from telegram import Update
from domain.entity.game import Game
from domain.entity.player_action import PlayerAction
from domain.repository.game_repository import GameRepository
from domain.repository.player_action_repository import PlayerActionRepository
from telegram.ext import ContextTypes
from decorators import restrict_to_channel
from config import CHANNEL_ID

class GameManagement:

    @staticmethod
    async def startgame_action(context: ContextTypes.DEFAULT_TYPE, user_name: str):
        """
        Действие запуска игры после одобрения администратора.
        """
        session = Session()

        # Проверяем, есть ли незавершённая игра
        unfinished_game = session.query(Game).filter(Game.end_time.is_(None)).first()

        if unfinished_game:
            context.bot_data["current_game_id"] = unfinished_game.id
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=f"Игра уже была начата ранее. Восстанавливаем контекст по запросу {user_name}."
            )
        else:
            # Создаём новую игру
            new_game = Game(start_time=datetime.now())
            session.add(new_game)
            session.commit()

            context.bot_data["current_game_id"] = new_game.id
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=f"Новая игра успешно начата по запросу {user_name}!"
            )

        session.close()

    @staticmethod
    async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
        session = Session()

        # Отправляем запрос админам на одобрение действия "startgame"
        user_name = update.effective_user.username or "Unknown User"
        await send_approval_request_to_admins(context, user_name, action_type="startgame")

        # Проверяем, есть ли незавершённая игра в базе данных
        if "current_game_id" in context.bot_data:
            await update.message.reply_text("Игра уже начата!")
            session.close()
            return

        current_game = GameRepository(session).find_active_game()

        if current_game:
            context.bot_data["current_game_id"] = current_game.id
            await update.message.reply_text(
                "Игра уже начата! Это восстановленная игра."
            )
            session.close()
            return

        new_game = Game(start_time=datetime.now(timezone.utc))
        GameRepository(session).save(new_game)

        # Сохраняем game_id в контексте бота
        context.bot_data["current_game_id"] = new_game.id

        # Логируем старт игры
        action = PlayerAction(
            game_id=new_game.id,
            user_id=update.effective_user.id,
            username=update.effective_user.username,
            action="start_game",
            timestamp=datetime.now(timezone.utc),
        )

        PlayerActionRepository(session).save(action)

        session.close()
        await update.message.reply_text("Игра начата! Закупки открыты.")

    @staticmethod
    @restrict_to_channel
    async def end_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
        session = Session()
        current_game = GameRepository(session).find_active_game()
        if not current_game:
            await update.message.reply_text("Игра не начата.")
            session.close()
            return

        current_game.end_time = datetime.now(timezone.utc)
        GameRepository(session).save(current_game)

        # Удаляем текущий game_id из контекста
        context.bot_data.pop("current_game_id", None)

        # Логируем завершение игры
        action = PlayerAction(
            game_id=current_game.id,
            user_id=update.effective_user.id,
            username=update.effective_user.username,
            action="end_game",
            timestamp=datetime.now(timezone.utc),
        )
        PlayerActionRepository(session).save(action)

        session.close()
        await update.message.reply_text("Игра завершена.")
