from datetime import datetime, timezone
from engine import Session
from telegram import Update
from domain.entity.game import Game
from domain.entity.player_action import PlayerAction
from domain.repository.game_repository import GameRepository
from domain.repository.player_action_repository import PlayerActionRepository
from telegram.ext import ContextTypes
from decorators import restrict_to_members_and_private
from config import CHANNEL_ID


class GameManagement:

    @staticmethod
    @restrict_to_members_and_private
    async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
        session = Session()

        # Проверяем, есть ли незавершённая игра в базе данных
        if "current_game_id" in context.bot_data:
            if update.message:
                await update.message.reply_text("Игра уже начата!")
            session.close()
            return

        current_game = GameRepository(session).find_active_game()

        if current_game:
            context.bot_data["current_game_id"] = current_game.id
            if update.message:
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
        if update.effective_user:
            action = PlayerAction(
                game_id=new_game.id,
                user_id=update.effective_user.id,
                username=update.effective_user.username,
                action="start_game",
                timestamp=datetime.now(timezone.utc),
            )

            PlayerActionRepository(session).save(action)

        session.close()
        if update.message:
            await update.message.reply_text("Игра начата! Закупки открыты.")
        await context.bot.send_message(CHANNEL_ID, "Игра начата! Закупки открыты.")

    @staticmethod
    @restrict_to_members_and_private
    async def end_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
        session = Session()
        current_game = GameRepository(session).find_active_game()
        if not current_game:
            if update.message:
                await update.message.reply_text("Игра не начата.")
            session.close()
            return

        current_game.end_time = datetime.now(timezone.utc)  # type: ignore
        GameRepository(session).save(current_game)

        # Удаляем текущий game_id из контекста
        context.bot_data.pop("current_game_id", None)

        # Логируем завершение игры
        if update.effective_user:
            action = PlayerAction(
                game_id=current_game.id,
                user_id=update.effective_user.id,
                username=update.effective_user.username,
                action="end_game",
                timestamp=datetime.now(timezone.utc),
            )
            PlayerActionRepository(session).save(action)

        session.close()
        if update.message:
            await update.message.reply_text("Игра завершена.")

        await context.bot.send_message(CHANNEL_ID, "Игра завершена.")
