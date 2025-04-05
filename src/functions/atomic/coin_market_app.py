"""Module implementation of the atomic function for cryptocurrency market data using CoinMarketCap API."""

import os
import logging
import requests
from typing import List, Dict, Any, Optional
import telebot
from telebot import types
from telebot.callback_data import CallbackData
from bot_func_abc import AtomicBotFunctionABC

class AtomicCoinMarketFunction(AtomicBotFunctionABC):
    """Implementation of atomic function for cryptocurrency market data
    """

    commands: List[str] = ["crypto", "market"]
    authors: List[str] = ["Nick"]
    about: str = "Получение информации о криптовалютах!"
    description: str = """Функция предоставляет актуальную информацию о криптовалютах с CoinMarketCap.
    
    Примеры использования:
    /crypto - показать топ-5 криптовалют
    /market - общая информация о рынке
    """
    state: bool = True

    bot: telebot.TeleBot
    coin_keyboard_factory: CallbackData
    
    # API configuration
    API_URL_BASE = "https://pro-api.coinmarketcap.com/v1/"
    SANDBOX_URL_BASE = "https://sandbox-api.coinmarketcap.com/v1/"
    
    def set_handlers(self, bot: telebot.TeleBot):
        """Set message handlers"""

        self.bot = bot
        self.coin_keyboard_factory = CallbackData('action', 'coin_id', prefix='crypto')

        @bot.message_handler(commands=self.commands)
        def crypto_message_handler(message: types.Message):
            try:
                command = message.text.split()[0][1:]  # Remove the '/' and get the command
                
                if command == "crypto":
                    self.__handle_top_coins(message)
                elif command == "market":
                    self.__handle_market_info(message)
                else:
                    self.__send_help(message)
            except Exception as ex:
                logging.exception(ex)
                bot.reply_to(message, f"Произошла ошибка: {str(ex)}")

        @bot.callback_query_handler(func=None, config=self.coin_keyboard_factory.filter())
        def coin_keyboard_callback(call: types.CallbackQuery):
            callback_data: dict = self.coin_keyboard_factory.parse(callback_data=call.data)
            action = callback_data['action']
            coin_id = callback_data['coin_id']

            try:
                if action == "info":
                    self.__send_coin_details(call.message.chat.id, coin_id)
                elif action == "price":
                    self.__send_coin_price(call.message.chat.id, coin_id)
                elif action == "back":
                    self.__handle_top_coins(call.message)
                else:
                    bot.answer_callback_query(call.id, "Неизвестное действие")
            except Exception as ex:
                logging.exception(ex)
                bot.answer_callback_query(call.id, f"Ошибка: {str(ex)}")

    def __get_api_key(self) -> str:
        """Get CoinMarketCap API key from environment variables"""
        api_key = os.environ.get("COINMARKETCAP_API_KEY")
        if not api_key:
            logging.warning("COINMARKETCAP_API_KEY not found in environment variables")
            # Fallback to sandbox key for development
            return "b54bcf4d-1bca-4e8e-9a24-22ff2c3d462c"
        return api_key

    def __make_api_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make a request to the CoinMarketCap API"""
        headers = {
            'Accepts': 'application/json',
            'X-CMC_PRO_API_KEY': self.__get_api_key(),
        }
        
        # Use sandbox for development, production for real deployment
        use_sandbox = os.environ.get("USE_SANDBOX", "False").lower() == "true"
        base_url = self.SANDBOX_URL_BASE if use_sandbox else self.API_URL_BASE
        url = f"{base_url}{endpoint}"
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"API request error: {e}")
            raise Exception(f"Ошибка API запроса: {str(e)}")

    def __handle_top_coins(self, message: types.Message) -> None:
        """Handle request for top cryptocurrencies"""
        chat_id = message.chat.id
        
        self.bot.send_message(chat_id, "Получаю данные о топ-5 криптовалютах...")
        
        try:
            data = self.__make_api_request("cryptocurrency/listings/latest", {
                'start': '1',
                'limit': '5',
                'convert': 'USD'
            })
            
            if 'data' not in data or not data['data']:
                self.bot.send_message(chat_id, "Не удалось получить данные о криптовалютах.")
                return
            
            response = "🔝 *Топ-5 криптовалют:*\n\n"
            
            for coin in data['data']:
                price = coin['quote']['USD']['price']
                change_24h = coin['quote']['USD']['percent_change_24h']
                
                # Format price based on value
                if price < 1:
                    price_formatted = f"${price:.6f}"
                elif price < 10:
                    price_formatted = f"${price:.4f}"
                else:
                    price_formatted = f"${price:.2f}"
                
                # Add emoji based on 24h change
                emoji = "🟢" if change_24h >= 0 else "🔴"
                
                response += (f"*{coin['name']}* ({coin['symbol']})\n"
                            f"Цена: {price_formatted}\n"
                            f"Изменение (24ч): {emoji} {change_24h:.2f}%\n\n")
            
            markup = self.__gen_coins_markup(data['data'])
            self.bot.send_message(chat_id, response, parse_mode="Markdown", reply_markup=markup)
            
        except Exception as ex:
            logging.exception(ex)
            self.bot.send_message(chat_id, f"Ошибка при получении данных: {str(ex)}")

    def __handle_market_info(self, message: types.Message) -> None:
        """Handle request for global market information"""
        chat_id = message.chat.id
        
        self.bot.send_message(chat_id, "Получаю данные о глобальном рынке криптовалют...")
        
        try:
            data = self.__make_api_request("global-metrics/quotes/latest")
            
            if 'data' not in data:
                self.bot.send_message(chat_id, "Не удалось получить данные о рынке.")
                return
            
            market_data = data['data']
            
            # Format market cap
            market_cap = market_data['quote']['USD']['total_market_cap']
            market_cap_formatted = f"${market_cap/1000000000:.2f} млрд"
            
            # Format 24h volume
            volume_24h = market_data['quote']['USD']['total_volume_24h']
            volume_24h_formatted = f"${volume_24h/1000000000:.2f} млрд"
            
            # Get market dominance
            btc_dominance = market_data['btc_dominance']
            eth_dominance = market_data['eth_dominance']
            
            response = (f"📊 *Глобальный рынок криптовалют*\n\n"
                       f"Капитализация: {market_cap_formatted}\n"
                       f"Объем (24ч): {volume_24h_formatted}\n"
                       f"Активные криптовалюты: {market_data['active_cryptocurrencies']}\n"
                       f"Доминирование BTC: {btc_dominance:.2f}%\n"
                       f"Доминирование ETH: {eth_dominance:.2f}%\n")
            
            self.bot.send_message(chat_id, response, parse_mode="Markdown")
            
        except Exception as ex:
            logging.exception(ex)
            self.bot.send_message(chat_id, f"Ошибка при получении данных: {str(ex)}")

    def __send_coin_details(self, chat_id: int, coin_id: str) -> None:
        """Send detailed information about a specific coin"""
        try:
            # Get coin metadata
            metadata = self.__make_api_request("cryptocurrency/info", {
                'id': coin_id
            })
            
            # Get coin quotes
            quotes = self.__make_api_request("cryptocurrency/quotes/latest", {
                'id': coin_id,
                'convert': 'USD'
            })
            
            if ('data' not in metadata or not metadata['data'] or 
                'data' not in quotes or not quotes['data']):
                self.bot.send_message(chat_id, "Не удалось получить данные о криптовалюте.")
                return
            
            coin_data = metadata['data'][coin_id]
            quote_data = quotes['data'][coin_id]
            
            # Format price
            price = quote_data['quote']['USD']['price']
            if price < 1:
                price_formatted = f"${price:.6f}"
            elif price < 10:
                price_formatted = f"${price:.4f}"
            else:
                price_formatted = f"${price:.2f}"
            
            # Format market cap
            market_cap = quote_data['quote']['USD']['market_cap']
            if market_cap >= 1000000000:
                market_cap_formatted = f"${market_cap/1000000000:.2f} млрд"
            else:
                market_cap_formatted = f"${market_cap/1000000:.2f} млн"
            
            # Get price changes
            change_1h = quote_data['quote']['USD']['percent_change_1h']
            change_24h = quote_data['quote']['USD']['percent_change_24h']
            change_7d = quote_data['quote']['USD']['percent_change_7d']
            
            # Format response
            response = (f"🪙 *{coin_data['name']}* ({coin_data['symbol']})\n\n"
                       f"💰 *Цена:* {price_formatted}\n"
                       f"📊 *Рыночная капитализация:* {market_cap_formatted}\n"
                       f"🔄 *Объем (24ч):* ${quote_data['quote']['USD']['volume_24h']/1000000:.2f} млн\n\n"
                       f"📈 *Изменение цены:*\n"
                       f"1ч: {change_1h:.2f}%\n"
                       f"24ч: {change_24h:.2f}%\n"
                       f"7д: {change_7d:.2f}%\n\n")
            
            # Add description if available
            if coin_data.get('description') and coin_data['description']:
                description = coin_data['description']
                # Truncate if too long
                if len(description) > 200:
                    description = description[:197] + "..."
                response += f"ℹ️ *О криптовалюте:*\n{description}\n\n"
            
            # Add website and explorer links
            if coin_data.get('urls'):
                urls = coin_data['urls']
                if urls.get('website') and urls['website']:
                    response += f"🌐 [Официальный сайт]({urls['website'][0]})\n"
                if urls.get('explorer') and urls['explorer']:
                    response += f"🔍 [Обозреватель блокчейна]({urls['explorer'][0]})\n"
            
            # Create markup with actions
            markup = types.InlineKeyboardMarkup(row_width=2)
            price_callback = self.coin_keyboard_factory.new(action="price", coin_id=coin_id)
            back_callback = self.coin_keyboard_factory.new(action="back", coin_id="0")
            
            markup.add(
                types.InlineKeyboardButton("📊 График цены", callback_data=price_callback),
                types.InlineKeyboardButton("🔙 Назад", callback_data=back_callback)
            )
            
            self.bot.send_message(chat_id, response, parse_mode="Markdown", 
                                 disable_web_page_preview=True, reply_markup=markup)
            
        except Exception as ex:
            logging.exception(ex)
            self.bot.send_message(chat_id, f"Ошибка при получении данных: {str(ex)}")

    def __send_coin_price(self, chat_id: int, coin_id: str) -> None:
        """Send price information and chart for a specific coin"""
        try:
            # Get coin data
            data = self.__make_api_request("cryptocurrency/quotes/latest", {
                'id': coin_id,
                'convert': 'USD'
            })
            
            if 'data' not in data or not data['data']:
                self.bot.send_message(chat_id, "Не удалось получить данные о цене.")
                return
            
            coin_data = data['data'][coin_id]
            symbol = coin_data['symbol']
            
            # Create TradingView chart URL
            chart_url = f"https://www.tradingview.com/chart/?symbol=BINANCE:{symbol}USDT"
            
            # Format price changes
            price = coin_data['quote']['USD']['price']
            change_24h = coin_data['quote']['USD']['percent_change_24h']
            change_7d = coin_data['quote']['USD']['percent_change_7d']
            change_30d = coin_data['quote']['USD']['percent_change_30d']
            
            # Format price based on value
            if price < 1:
                price_formatted = f"${price:.6f}"
            elif price < 10:
                price_formatted = f"${price:.4f}"
            else:
                price_formatted = f"${price:.2f}"
            
            response = (f"📊 *{coin_data['name']} ({symbol}) - Цена*\n\n"
                       f"💰 *Текущая цена:* {price_formatted}\n\n"
                       f"*Изменение:*\n"
                       f"24ч: {change_24h:.2f}%\n"
                       f"7д: {change_7d:.2f}%\n"
                       f"30д: {change_30d:.2f}%\n\n"
                       f"[Открыть график на TradingView]({chart_url})")
            
            # Create markup with back button
            markup = types.InlineKeyboardMarkup()
            back_callback = self.coin_keyboard_factory.new(action="info", coin_id=coin_id)
            markup.add(types.InlineKeyboardButton("🔙 Назад к информации", callback_data=back_callback))
            
            self.bot.send_message(chat_id, response, parse_mode="Markdown", 
                                 disable_web_page_preview=False, reply_markup=markup)
            
        except Exception as ex:
            logging.exception(ex)
            self.bot.send_message(chat_id, f"Ошибка при получении данных о цене: {str(ex)}")

    def __gen_coins_markup(self, coins_data: List[Dict[str, Any]]) -> types.InlineKeyboardMarkup:
        """Generate keyboard markup for coin selection"""
        markup = types.InlineKeyboardMarkup()
        markup.row_width = 2
        
        for coin in coins_data:
            coin_id = str(coin['id'])
            callback_data = self.coin_keyboard_factory.new(action="info", coin_id=coin_id)
            markup.add(types.InlineKeyboardButton(
                f"{coin['name']} ({coin['symbol']})", 
                callback_data=callback_data
            ))
        
        return markup

    def __send_help(self, message: types.Message) -> None:
        """Send help information about available commands"""
        help_text = (
            "*Команды для работы с криптовалютами:*\n\n"
            "/crypto - показать топ-5 криптовалют по капитализации\n"
            "/market - общая информация о рынке криптовалют\n\n"
            "Используйте эти команды для получения актуальной информации о криптовалютах."
        )
        
        self.bot.send_message(message.chat.id, help_text, parse_mode="Markdown")
