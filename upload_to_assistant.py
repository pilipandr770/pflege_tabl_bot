#!/usr/bin/env python
"""
Скрипт для загрузки документации о структуре таблиц в OpenAI Assistant.
Этот скрипт берет сгенерированный файл документации и загружает его как базу знаний в
указанного ассистента OpenAI для обеспечения контекста при анализе пустых ячеек.
"""

import os
import sys
import logging
import argparse
import json
from datetime import datetime
from dotenv import load_dotenv
import openai

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем API ключ OpenAI и ID ассистента из переменных окружения
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_ASSISTANT_ID = os.getenv('OPENAI_ASSISTANT_ID')

def upload_to_assistant(doc_file, assistant_id=None, purpose="table_documentation"):
    """
    Загружает файл документации в OpenAI Assistant
    
    Args:
        doc_file (str): Путь к файлу документации
        assistant_id (str, optional): ID ассистента OpenAI
        purpose (str, optional): Назначение файла
        
    Returns:
        dict: Результат загрузки
    """
    if not OPENAI_API_KEY:
        logger.error("Не задан API ключ OpenAI. Добавьте OPENAI_API_KEY в файл .env")
        return None
    
    assistant_id = assistant_id or OPENAI_ASSISTANT_ID
    
    if not assistant_id:
        logger.error("Не задан ID ассистента OpenAI. Добавьте OPENAI_ASSISTANT_ID в файл .env или укажите через параметр --assistant-id")
        return None
    
    try:        # Инициализируем клиент OpenAI с API ключом
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        # Загружаем файл
        with open(doc_file, "rb") as file:
            file_upload = client.files.create(
                file=file,
                purpose="assistants"
            )
        
        logger.info(f"Файл успешно загружен. ID файла: {file_upload.id}")
        
        # Подключаем файл к ассистенту
        current_assistant = client.beta.assistants.retrieve(
            assistant_id=assistant_id
        )
        
        # Получаем список уже имеющихся файлов
        existing_files = getattr(current_assistant, 'file_ids', [])
        
        # Добавляем новый файл
        updated_assistant = client.beta.assistants.update(
            assistant_id=assistant_id,
            file_ids=[file_upload.id] + existing_files
        )
        
        # Создаем сообщение для залогирования успешной операции
        file_count = len(getattr(updated_assistant, 'file_ids', []))
        
        result = {
            "success": True,
            "file_id": file_upload.id,
            "assistant_id": assistant_id,
            "total_files": file_count,
            "message": f"Документация успешно загружена в ассистента. Теперь у ассистента {file_count} файлов."
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Ошибка при загрузке документации: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def main():
    """
    Основная функция скрипта
    """
    parser = argparse.ArgumentParser(description='Загрузка документации о структуре таблиц в OpenAI Assistant')
    parser.add_argument('--file', '-f', help='Путь к файлу документации (по умолчанию - последний созданный file_documentation_*.md)')
    parser.add_argument('--assistant-id', '-a', help='ID ассистента OpenAI (если не указан в .env)')
    args = parser.parse_args()
    
    # Если файл не указан, ищем последний созданный
    if not args.file:
        doc_files = [f for f in os.listdir('.') if f.startswith('table_documentation_') and f.endswith('.md')]
        if not doc_files:
            logger.error("Не найдено файлов документации. Запустите сначала generate_tables_docs.py")
            return
        
        # Сортируем по дате создания (самый новый первый)
        latest_file = max(doc_files, key=lambda f: os.path.getctime(f))
        doc_file = latest_file
        logger.info(f"Используем самый свежий файл документации: {doc_file}")
    else:
        doc_file = args.file
        
    # Проверяем существование файла
    if not os.path.exists(doc_file):
        logger.error(f"Файл {doc_file} не найден")
        return
    
    # Загружаем в ассистента
    result = upload_to_assistant(doc_file, args.assistant_id)
    
    if result and result.get("success"):
        print("\n" + "=" * 70)
        print(f"Документация успешно загружена в OpenAI Assistant!")
        print(f"ID файла: {result['file_id']}")
        print(f"ID ассистента: {result['assistant_id']}")
        print(f"Всего файлов у ассистента: {result['total_files']}")
        print("=" * 70 + "\n")
    else:
        print("\n" + "=" * 70)
        print("Не удалось загрузить документацию в ассистента.")
        print("Проверьте файл .env и наличие API ключа.")
        print("=" * 70 + "\n")

if __name__ == "__main__":
    main()
