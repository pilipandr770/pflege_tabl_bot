import telebot
from telebot import types
import os
from dotenv import load_dotenv
import logging
from scraper import get_empty_cells, dump_all_cells
import json
from datetime import datetime
import openai
import re
from collections import defaultdict
from config import (
    DEMO_URL, REAL_URL, TABLE_DESCRIPTIONS, MAX_CELLS_PER_CATEGORY
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Get bot token from environment variable
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Получаем ключи OpenAI и ассистента из переменных окружения
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_ASSISTANT_ID = os.getenv('OPENAI_ASSISTANT_ID')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4.1-Nano')

# Initialize OpenAI client if API key is available
openai_client = None
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
    try:
        openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
        logger.info("OpenAI client initialized using new API")
    except Exception as e:
        logger.warning(f"Error initializing OpenAI client: {e}")
        openai_client = None
        logger.warning("OpenAI client could not be initialized. AI explanation features will be disabled.")
else:
    logger.warning("OpenAI API key not found. AI explanation features will be disabled.")

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN)

# Storage for user comments
comments_db = {}

@bot.message_handler(commands=['start'])
def start_command(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    item1 = types.KeyboardButton('/check')
    item2 = types.KeyboardButton('/stats')
    item3 = types.KeyboardButton('/columns')
    item4 = types.KeyboardButton('/comments')
    item5 = types.KeyboardButton('/help')
    markup.add(item1, item2, item3, item4, item5)
    
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
            
        # Организуем ячейки по категориям и присваиваем ID каждой находке
        organized_cells = organize_empty_cells(unique_cells)
        
        # Добавляем ID для каждой находки
        findings_with_ids = {}
        finding_id = 1
        
        for table_id, cells in organized_cells.items():
            findings_with_ids[table_id] = []
            for cell in cells:
                findings_with_ids[table_id].append({
                    "id": finding_id,
                    "description": cell
                })
                finding_id += 1
        
        # Сохраняем детальную информацию о находках с ID
        findings_data = {
            "timestamp": datetime.now().isoformat(),
            "findings": findings_with_ids
        }
        
        findings_filename = f"findings_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
        with open(findings_filename, 'w', encoding='utf-8') as f:
            json.dump(findings_data, f, ensure_ascii=False, indent=2)
        
        # Сохраняем также сырые данные пустых ячеек
        raw_filename = save_empty_cells_to_file(empty_cells)
        
        # Формируем ответное сообщение
        response = f"Найдены незаполненные ячейки: {len(unique_cells)}\n\n"
        
        # Получаем AI анализ для наиболее значимых находок
        # Выбираем до 10 наиболее характерных находок для анализа
        sample_findings = {}
        for table_id, cells in findings_with_ids.items():
            sample_findings[table_id] = cells[:min(3, len(cells))]  # Берем максимум 3 примера с каждой таблицы
        
        # Запрос анализа от AI
        ai_explanation = get_ai_explanation(sample_findings)
        
        # Telegram имеет ограничение в 4096 символов на сообщение
        messages = []
        current_message = response
        
        # Формируем сообщения по категориям
        for table_id, cells in findings_with_ids.items():
            # Если добавление категории превысит лимит, создаем новое сообщение
            category_header = f"📊 {table_id} ({len(cells)} ячеек):\n"
            
            if len(current_message) + len(category_header) > 3900:
                messages.append(current_message)
                current_message = category_header
            else:
                current_message += category_header
                
            # Добавляем первые 5 ячеек из категории с ID
            for i, cell_data in enumerate(cells[:MAX_CELLS_PER_CATEGORY]):
                finding_id = cell_data["id"]
                cell_description = cell_data["description"]
                cell_text = f"   - #{finding_id} {cell_description}\n"
                
                if len(current_message) + len(cell_text) > 3900:
                    messages.append(current_message)
                    current_message = cell_text
                else:
                    current_message += cell_text
            
            # Если в категории больше установленного лимита ячеек, добавляем информацию об остальных
            if len(cells) > MAX_CELLS_PER_CATEGORY:
                remaining_text = f"   - ... и еще {len(cells) - MAX_CELLS_PER_CATEGORY} пустых ячеек\n\n"
                
                if len(current_message) + len(remaining_text) > 3900:
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
                    if len(current_message) + len(info) > 3900:
                        messages.append(current_message)
                        current_message = info
                    else:
                        current_message += info
                    break
        
        # Добавляем информация для комментирования находок
        comment_info = "\n💬 Для комментирования конкретной находки, ответьте на это сообщение, указав ID находки (например, для находки #5: 'Требуется заполнить телефон пациента').\n"
        
        if len(current_message) + len(comment_info) > 3900:
            messages.append(current_message)
            current_message = comment_info
        else:
            current_message += comment_info
            
        # Добавляем информацию о сохраненных файлах
        if raw_filename:
            file_info = f"💾 Полный список сохранен в файл: {raw_filename}\n"
            
            if len(current_message) + len(file_info) > 3900:
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
        if raw_filename:
            with open(raw_filename, 'rb') as f:
                bot.send_document(message.chat.id, f, caption="Полный список пустых ячеек в формате JSON")
                
        # Отправляем AI анализ, если доступен
        if ai_explanation and len(ai_explanation) > 0:
            # Разбиваем длинный анализ на части, если нужно
            ai_parts = [ai_explanation[i:i+3900] for i in range(0, len(ai_explanation), 3900)]
            
            for i, part in enumerate(ai_parts):
                header = "🧠 Анализ пустых ячеек от ИИ:\n\n" if i == 0 else "🧠 Продолжение анализа:\n\n"
                bot.send_message(message.chat.id, header + part)
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
/columns - Показать список всех колонок таблиц
/comments - Показать все комментарии к находкам
/dumpall - Выгрузить все ячейки и колонки в файл
/help - Показать это сообщение с помощью

Функциональность:
- Анализ таблиц на наличие пустых ячеек
- ИИ-анализ причин и важности пустых полей
- Возможность комментирования находок (ответьте на сообщение с находкой)
- Структурированный вывод по категориям
- Вывод названий колонок и содержимого таблиц

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

# Function to generate AI explanations for empty cells
def get_ai_explanation(empty_cells_data):
    """
    Generate an AI explanation for empty cells using OpenAI
    
    Args:
        empty_cells_data (dict): Dictionary with table data and empty cells info
        
    Returns:
        str: AI-generated explanation or error message
    """
    if not openai_client:
        return "ИИ не может предоставить объяснение: API ключ OpenAI не настроен или клиент не инициализирован."
    
    if not OPENAI_ASSISTANT_ID:
        # Use completion API instead of Assistant API
        try:
            # Create a structured prompt for the model
            prompt = f"""Анализ пустых ячеек в медицинских таблицах:
\nНайдены следующие пустые ячейки:\n{json.dumps(empty_cells_data, indent=2, ensure_ascii=False)}\n\nПожалуйста, опишите на русском языке, какие проблемы могут возникнуть из-за этих пустых ячеек\nв контексте медицинского ухода и что следует предпринять. Укажите, какие поля наиболее критичны \nдля заполнения и почему. Если есть закономерности в пустых полях, укажите их.\n"""
            # OpenAI API v1.x requires chat.completions
            try:
                response = openai_client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": "Вы - аналитик данных в системе управления медицинскими данными. Ваша задача - анализировать незаполненные поля в таблицах и объяснять их значимость."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=800,
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"Error using OpenAI chat completions: {e}")
                return f"Ошибка при получении объяснения от ИИ: {e}"
        except Exception as e:
            logger.error(f"Error generating AI explanation: {str(e)}")
            return f"Ошибка при получении объяснения от ИИ: {str(e)}"
    else:
        # Use Assistant API with better error handling
        try:
            # Check if we have access to the beta namespace
            if not hasattr(openai_client, 'beta'):
                logger.warning("Beta namespace not available in OpenAI client")
                return "Функция ассистентов недоступна в текущей версии API OpenAI. Используйте обычный режим без указания OPENAI_ASSISTANT_ID."
            # Try the beta API implementation
            try:
                thread = openai_client.beta.threads.create()
                openai_client.beta.threads.messages.create(
                    thread_id=thread.id,
                    role="user",
                    content=f"Проанализируйте следующие пустые ячейки в медицинских таблицах и объясните их значимость: {json.dumps(empty_cells_data, indent=2, ensure_ascii=False)}"
                )
                run = openai_client.beta.threads.runs.create(
                    thread_id=thread.id,
                    assistant_id=OPENAI_ASSISTANT_ID
                )
                # Wait for the assistant to complete with timeout
                import time
                max_wait_time = 60  # Maximum wait time in seconds
                start_time = time.time()
                while run.status in ["queued", "in_progress"]:
                    # Check timeout
                    if time.time() - start_time > max_wait_time:
                        logger.warning(f"Timeout waiting for assistant response after {max_wait_time} seconds")
                        return "Время ожидания ответа от ассистента истекло. Попробуйте позже."
                    time.sleep(1)
                    run = openai_client.beta.threads.runs.retrieve(
                        thread_id=thread.id,
                        run_id=run.id
                    )
                if run.status == "completed":
                    messages = openai_client.beta.threads.messages.list(
                        thread_id=thread.id
                    )
                    for message in messages.data:
                        if message.role == "assistant":
                            # Handle the possibility of missing content or different data structure
                            try:
                                return message.content[0].text.value
                            except (IndexError, AttributeError) as e:
                                logger.error(f"Error extracting message content: {e}")
                                return "ИИ не смогла сформулировать объяснение в правильном формате."
                    return "ИИ не смогла сформулировать объяснение."
                else:
                    return f"Ошибка при получении ответа ассистента. Статус: {run.status}"
            except Exception as e:
                logger.error(f"Error in beta.threads API flow: {e}")
                return f"Ошибка в работе API ассистента: {e}"
        except Exception as e:
            logger.error(f"Error using Assistant API: {e}")
            return f"Ошибка при использовании API ассистента: {e}"

# Function to extract finding ID from a message
def extract_finding_id(text):
    """Extract finding ID from text using regex"""
    match = re.search(r'#(?P<id>\d+)', text)
    if match:
        return match.group('id')
    return None

# Handler for comments to findings
@bot.message_handler(func=lambda message: message.reply_to_message and 
                   hasattr(message.reply_to_message, 'text') and
                   '#ID' in message.reply_to_message.text)
def handle_comment(message):
    """Handle user comments on findings"""
    finding_id = extract_finding_id(message.reply_to_message.text)
    if finding_id:
        # Save the comment
        if 'comments' not in comments_db:
            comments_db['comments'] = {}
        
        comments_db['comments'][finding_id] = {
            'user_id': message.from_user.id,
            'user_name': message.from_user.username or message.from_user.first_name,
            'comment': message.text,
            'timestamp': datetime.now().isoformat()
        }
        
        # Save comments to file
        with open('comments.json', 'w', encoding='utf-8') as f:
            json.dump(comments_db, f, ensure_ascii=False, indent=2)
            
        bot.reply_to(message, f"✅ Комментарий к находке #{finding_id} сохранен.")
    else:
        bot.reply_to(message, "❌ Не удалось определить ID находки. Комментарий не сохранен.")

# Handler to view comments
@bot.message_handler(commands=['comments'])
def view_comments(message):
    """View all comments for findings"""
    if not os.path.exists('comments.json'):
        bot.reply_to(message, "Комментарии к находкам отсутствуют.")
        return
        
    try:
        with open('comments.json', 'r', encoding='utf-8') as f:
            comments_data = json.load(f)
            
        if not comments_data.get('comments'):
            bot.reply_to(message, "Комментарии к находкам отсутствуют.")
            return
            
        response = "💬 Комментарии к находкам:\n\n"
        
        for finding_id, comment_info in comments_data.get('comments', {}).items():
            response += f"📌 Находка #{finding_id}:\n"
            response += f"  - Комментарий: {comment_info['comment']}\n"
            response += f"  - От: @{comment_info['user_name']}\n"
            response += f"  - Время: {datetime.fromisoformat(comment_info['timestamp']).strftime('%d.%m.%Y %H:%M')}\n\n"
            
        bot.reply_to(message, response)
    except Exception as e:
        logger.error(f"Error viewing comments: {str(e)}")
        bot.reply_to(message, f"Ошибка при загрузке комментариев: {str(e)}")

# Command to list all table columns
@bot.message_handler(commands=['columns'])
def list_columns(message):
    """List all columns from the last scan"""
    try:
        # Find the latest results file
        files = [f for f in os.listdir(".") if f.startswith("empty_cells_") and f.endswith(".json")]
        
        if not files:
            bot.reply_to(message, "Нет данных о проверках. Используйте /check для запуска проверки.")
            return
            
        # Get the latest file
        latest_file = max(files, key=lambda f: os.path.getctime(f))
        
        # Load data
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        empty_cells = data.get("empty_cells", [])
        
        # Extract all column names
        column_names = defaultdict(set)
        
        for cell in empty_cells:
            # Parse cell text to extract table and column information
            parts = cell.split(',')
            if len(parts) >= 3:
                table_id = parts[0].strip()
                col_info = ','.join(parts[2:]).strip()
                
                # Extract column name using regex
                col_match = re.search(r'Колонка \d+\s*\(([^)]+)\)', col_info) or re.search(r'Column \d+\s*\(([^)]+)\)', col_info)
                if col_match:
                    column_names[table_id].add(col_match.group(1))
                else:
                    # Try another pattern
                    col_match = re.search(r'\(Колонка:\s*([^)]+)\)', col_info) or re.search(r'\(Header:\s*([^)]+)\)', col_info)
                    if col_match:
                        column_names[table_id].add(col_match.group(1))
        
        if not column_names:
            bot.reply_to(message, "Не удалось извлечь информацию о колонках из последней проверки.")
            return
            
        # Prepare response
        response = "📋 Список колонок в таблицах:\n\n"
        
        for table_id, columns in column_names.items():
            response += f"📊 {table_id}:\n"
            for i, column in enumerate(sorted(columns), 1):
                response += f"  {i}. {column}\n"
            response += "\n"
            
        bot.reply_to(message, response)
    except Exception as e:
        logger.error(f"Error listing columns: {str(e)}")
        bot.reply_to(message, f"Ошибка при получении списка колонок: {str(e)}")

@bot.message_handler(commands=['dumpall'])
def dump_all_cells_command(message):
    """Сохраняет все ячейки всех таблиц с названиями колонок и отправляет файл пользователю"""
    try:
        url = REAL_URL if REAL_URL else DEMO_URL
        filename = dump_all_cells(url)
        with open(filename, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="Все ячейки всех таблиц с названиями колонок")
    except Exception as e:
        logger.error(f"Ошибка при выгрузке всех ячеек: {e}")
        bot.reply_to(message, f"Ошибка при выгрузке всех ячеек: {e}")

# Start the bot
if __name__ == '__main__':
    logger.info("Starting bot...")
    bot.infinity_polling()