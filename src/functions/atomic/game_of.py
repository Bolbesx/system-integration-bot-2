"""Module implementation of the atomic function for Telegram Bot."""

import logging
from typing import List
import requests
import telebot
from telebot import types
from telebot.callback_data import CallbackData
from bot_func_abc import AtomicBotFunctionABC

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class GameOfThronesQuotesBotFunction(AtomicBotFunctionABC):
    """Function to get Game of Thrones quotes from API by command"""

    commands: List[str] = ["got", "gots"]
    authors: List[str] = ["bolse119"]
    about: str = "Цитаты из Игры Престолов!"
    description: str = (
        "Функция позволяет получить цитаты персонажей Игры Престолов.\n"
        "Использование:\n"
        "/gots - показать доступных персонажей\n"
        "/got <имя персонажа> - получить цитату\n"
        "Пример: /got tyrion\n"
        "API: https://api.gameofthronesquotes.xyz"
    )
    state: bool = True

    bot: telebot.TeleBot
    keyboard_factory: CallbackData

    characters: List[dict] = [
        {"name": "Tyrion Lannister", "slug": "tyrion"},
        {"name": "Jon Snow", "slug": "jon"},
        {"name": "Daenerys Targaryen", "slug": "daenerys"},
        {"name": "Jaime Lannister", "slug": "jaime"},
        {"name": "Sansa Stark", "slug": "sansa"},
        {"name": "Petyr Baelish", "slug": "petyr"},
        {"name": "Cersei Lannister", "slug": "cersei"},
        {"name": "Arya Stark", "slug": "arya"},
        {"name": "Eddard Stark", "slug": "eddard"},
        {"name": "Theon Greyjoy", "slug": "theon"},
        {"name": "Samwell Tarly", "slug": "samwell"},
        {"name": "Varys", "slug": "varys"}
    ]

    def set_handlers(self, bot: telebot.TeleBot):
        """Set message handlers"""
        logger.info("Инициализация обработчиков команд: %s", self.commands)
        self.bot = bot
        self.keyboard_factory = CallbackData('action', prefix=self.commands[0])

        @self.bot.message_handler(commands=self.commands)
        def got_message_handler(message: types.Message):
            logger.info("Получена команда %s", message.text)

            command = message.text.split()[0].lower()

            if command == "/gots":
                characters_list = ", ".join(char["name"] for char in self.characters)
                self.bot.send_message(
                    message.chat.id,
                    f"📜 Доступные персонажи: {characters_list}\n"
                    "Используйте команду `/got <имя персонажа>`",
                    reply_markup=self.__gen_markup()
                )
                return

            command_args = message.text.split(maxsplit=1)
            if len(command_args) < 2:
                self.bot.send_message(
                    message.chat.id,
                    "⛔ Укажите персонажа!\n"
                    "Пример: `/got tyrion`",
                    reply_markup=self.__gen_markup()
                )
                return

            character_input = command_args[1].lower().strip()
            character = next(
                (char for char in self.characters
                 if char["name"].lower().startswith(character_input) or
                    char["slug"].lower() == character_input),
                None
            )

            if not character:
                self.bot.send_message(
                    message.chat.id,
                    f"❌ Персонаж `{character_input}` не найден!\n"
                    f"Доступные персонажи: {', '.join(char['name'] for char in self.characters)}",
                    reply_markup=self.__gen_markup()
                )
                return

            quote = self.__get_got_quote(character["slug"])

            if quote:
                self.bot.send_message(
                    message.chat.id,
                    f"📜 \"{quote['sentence']}\"\n"
                    f"— {quote['character']['name']}"
                )
            else:
                self.bot.send_message(
                    message.chat.id,
                    f"😔 Не удалось получить цитату для {character['name']}.\n"
                    "Попробуйте еще раз.",
                    reply_markup=self.__gen_markup()
                )

    @staticmethod
    def __get_got_quote(slug: str) -> dict:
        """Get random quote for specific character"""
        try:
            response = requests.get(
                f"https://api.gameofthronesquotes.xyz/v1/author/{slug}/2",
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            return data[0] if isinstance(data, list) and len(data) > 0 else None
        except requests.RequestException:
            return None

    def __gen_markup(self):
        """Generate inline keyboard markup"""
        markup = types.InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            types.InlineKeyboardButton(
                "🔄 Случайная цитата",
                callback_data=self.keyboard_factory.new(action="random_quote")
            ),
            types.InlineKeyboardButton(
                "📜 Список персонажей",
                callback_data=self.keyboard_factory.new(action="list_characters")
            )
        )
        return markup
