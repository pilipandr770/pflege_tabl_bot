import telebot
from telebot import types
import os
from dotenv import load_dotenv
import logging
from scraper import get_empty_cells
import json
from datetime import datetime
from config import DEMO_URL, REAL_URL, TABLE_DESCRIPTIONS, MAX_CELLS_PER_CATEGORY

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Get bot token from environment variable
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start_command(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    item1 = types.KeyboardButton('/check')
    item2 = types.KeyboardButton('/stats')
    item3 = types.KeyboardButton('/help')
    markup.add(item1, item2, item3)
    
    bot.reply_to(message, 
                "Привет! Я бот для проверки незаполненных ячеек в таблице.\n"
                "Используйте /check чтобы проверить пустые ячейки.\n"
                "Нажмите на кнопку ниже или используйте команду из меню.",
                reply_markup=markup)

def organize_empty_cells(empty_cells):
    """Организует пустые ячейки в структурированный формат по категориям"""
    organized_cells = {}
    
    for cell in empty_cells:
        parts = cell.split(',', 1)  # Разделяем на идентификатор таблицы и остальную информацию
        
        if len(parts) > 1:
            table_id = parts[0].strip()
            info = parts[1].strip()
            
            if table_id not in organized_cells:
                organized_cells[table_id] = []
            
            organized_cells[table_id].append(info)
        else:
            # Если формат не соответствует ожидаемому, добавляем в "Другое"
            if "Другое" not in organized_cells:
                organized_cells["Другое"] = []
            
            organized_cells["Другое"].append(cell)
    
    return organized_cells

def save_empty_cells_to_file(empty_cells):
    """Сохраняет список пустых ячеек в JSON-файл с датой и временем"""
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"empty_cells_{current_time}.json"
    
    data = {
        "timestamp": datetime.now().isoformat(),
        "empty_cells": empty_cells
    }
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        return filename
    except Exception as e:
        logger.error(f"Error saving empty cells to file: {str(e)}")
        return None

@bot.message_handler(commands=['check'])
def check_empty_cells(message):
    # Проверяем, не запущена ли уже проверка для этого чата
    chat_id = message.chat.id
    if hasattr(bot, 'checking_chats') and chat_id in bot.checking_chats:
        bot.reply_to(message, "Проверка уже выполняется. Пожалуйста, дождитесь её завершения.")
        return
    
    # Отмечаем, что для этого чата запущена проверка
    if not hasattr(bot, 'checking_chats'):
        bot.checking_chats = set()
    bot.checking_chats.add(chat_id)
    
    # Сообщаем пользователю о начале проверки
    sent_msg = bot.reply_to(message, "Начинаю проверку незаполненных ячеек...\nЭто может занять до 30 секунд.")
    
    try:
        # Проверяем наличие реального URL
        url = REAL_URL if REAL_URL else DEMO_URL
        
        # Получаем аргументы команды (если переданы)
        command_args = message.text.split()
        if len(command_args) > 1 and command_args[1].lower() == "demo":
            url = DEMO_URL
            bot.reply_to(message, f"Использую демо-URL: {DEMO_URL}")
        
        # Получаем пустые ячейки
        empty_cells = get_empty_cells(url)
        
        # Удаляем дубликаты для уменьшения объема вывода
        unique_cells = []
        unique_cell_texts = set()
        for cell in empty_cells:
            # Создаем ключ для определения уникальности ячейки
            # (берем только части без служебной информации)
            key_parts = []
            for part in cell.split(','):
                if not any(x in part.lower() for x in ["item", "row", "column"]):
                    continue
                key_parts.append(part.strip())
            
            cell_key = '|'.join(key_parts)
            
            if cell_key not in unique_cell_texts:
                unique_cells.append(cell)
                unique_cell_texts.add(cell_key)
        
        if not unique_cells:
            bot.reply_to(message, "Все ячейки заполнены!")
            return
            
        # Организуем ячейки по категориям
        organized_cells = organize_empty_cells(unique_cells)
        
        # Сохраняем в файл
        filename = save_empty_cells_to_file(empty_cells)
        
        # Формируем ответное сообщение
        response = f"Найдены незаполненные ячейки: {len(unique_cells)}\n\n"
        
        # Telegram имеет ограничение в 4096 символов на сообщение
        messages = []
        current_message = response
        
        # Формируем сообщения по категориям
        for table_id, cells in organized_cells.items():
            # Если добавление категории превысит лимит, создаем новое сообщение
            category_header = f"📊 {table_id} ({len(cells)} ячеек):\n"
            
            if len(current_message) + len(category_header) > 4000:
                messages.append(current_message)
                current_message = category_header
            else:
                current_message += category_header
                
            # Добавляем первые 5 ячеек из категории
            for i, cell in enumerate(cells[:5]):
                cell_text = f"   - {cell}\n"
                
                if len(current_message) + len(cell_text) > 4000:
                    messages.append(current_message)
                    current_message = cell_text
                else:
                    current_message += cell_text
            
            # Если в категории больше 5 ячеек, добавляем информацию об остальных
            if len(cells) > 5:
                remaining_text = f"   - ... и еще {len(cells) - 5} пустых ячеек\n\n"
                
                if len(current_message) + len(remaining_text) > 4000:
                    messages.append(current_message)
                    current_message = remaining_text
                else:
                    current_message += remaining_text
            else:
                current_message += "\n"
                
            # Добавляем дополнительную информацию из конфигурации
            for keyword, description in TABLE_DESCRIPTIONS.items():
                if keyword in table_id.lower():
                    info = f"{description}\n"
                    if len(current_message) + len(info) > 4000:
                        messages.append(current_message)
                        current_message = info
                    else:
                        current_message += info
                    break
        
        # Добавляем информацию о сохраненном файле
        if filename:
            file_info = f"💾 Полный список сохранен в файл: {filename}\n"
            
            if len(current_message) + len(file_info) > 4000:
                messages.append(current_message)
                current_message = file_info
            else:
                current_message += file_info
        
        # Добавляем последнее сообщение, если оно не пустое
        if current_message:
            messages.append(current_message)
        
        # Отправляем все сообщения
        for msg in messages:
            bot.reply_to(message, msg)
            
        # Отправляем файл, если он был создан
        if filename:
            with open(filename, 'rb') as f:
                bot.send_document(message.chat.id, f, caption="Полный список пустых ячеек в формате JSON")
    except Exception as e:
        logger.error(f"Error checking empty cells: {str(e)}")
        bot.reply_to(message, f"Произошла ошибка при проверке таблицы: {str(e)}")
    finally:
        # Убираем отметку о проверке для этого чата
        if hasattr(bot, 'checking_chats'):
            bot.checking_chats.discard(chat_id)

@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = """
Я бот для анализа таблицы на сайте meinpflegedienst.com.

Доступные команды:
/start - Начать работу с ботом
/check - Проверить пустые ячейки в таблице
/check demo - Проверить пустые ячейки в демо-таблице
/stats - Показать статистику пустых ячеек
/help - Показать это сообщение с помощью

Этот бот анализирует таблицу и находит незаполненные ячейки. 
По умолчанию используется тестовый вариант, в дальнейшем будет настроен доступ к реальным данным.
"""
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['stats'])
def stats_command(message):
    try:
        # Ищем самый последний файл с результатами
        files = [f for f in os.listdir(".") if f.startswith("empty_cells_") and f.endswith(".json")]
        
        if not files:
            bot.reply_to(message, "Нет данных о проверках. Используйте /check для запуска проверки.")
            return
        
        # Сортируем по дате создания
        latest_file = max(files, key=lambda f: os.path.getctime(f))
        
        # Загружаем данные из файла
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        empty_cells = data["empty_cells"]
        timestamp = data.get("timestamp", "Неизвестно")
        
        # Организуем ячейки по категориям
        organized_cells = organize_empty_cells(empty_cells)
        
        # Формируем статистику
        response = f"📊 Статистика пустых ячеек (последняя проверка: {timestamp})\n\n"
        response += f"Всего найдено: {len(empty_cells)} пустых ячеек\n"
        response += f"Затронуто разделов: {len(organized_cells)}\n\n"
        
        # Добавляем детальную статистику по разделам
        response += "Разбивка по разделам:\n"
        for table_id, cells in organized_cells.items():
            response += f"- {table_id}: {len(cells)} ячеек\n"
        
        bot.reply_to(message, response)
        
    except Exception as e:
        logger.error(f"Error showing stats: {str(e)}")
        bot.reply_to(message, f"Произошла ошибка при получении статистики: {str(e)}")

# Start the bot
if __name__ == '__main__':
    logger.info("Starting bot...")
    bot.infinity_polling()