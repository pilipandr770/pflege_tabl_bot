"""
Модуль для автоматической очистки временных файлов данных
в соответствии с политикой конфиденциальности и GDPR.
"""

import os
import threading
import time
from datetime import datetime, timedelta
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

# Константы для настройки очистки
DATA_RETENTION_MINUTES = 15  # Время хранения данных в минутах
CLEANUP_INTERVAL_SECONDS = 300  # Интервал проверки файлов для очистки (5 минут)

# Файловые шаблоны для очистки
FILE_PATTERNS = [
    "empty_cells_*.json",
    "findings_*.json",
    "all_cells_*.json"
]

def get_file_age_minutes(file_path):
    """Определяет возраст файла в минутах"""
    try:
        file_mtime = os.path.getmtime(file_path)
        file_datetime = datetime.fromtimestamp(file_mtime)
        age = datetime.now() - file_datetime
        return age.total_seconds() / 60
    except Exception as e:
        logger.error(f"Ошибка при определении возраста файла {file_path}: {e}")
        return 0

def is_data_file(filename):
    """Проверяет, является ли файл файлом данных, подлежащим очистке"""
    from fnmatch import fnmatch
    return any(fnmatch(filename, pattern) for pattern in FILE_PATTERNS)

def delete_old_files():
    """Удаляет старые файлы данных"""
    try:
        current_dir = os.getcwd()
        deleted_count = 0
        
        for filename in os.listdir(current_dir):
            if os.path.isfile(filename) and is_data_file(filename):
                file_path = os.path.join(current_dir, filename)
                age_minutes = get_file_age_minutes(file_path)
                
                if age_minutes > DATA_RETENTION_MINUTES:
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                        logger.info(f"Удален устаревший файл данных: {filename} (возраст: {age_minutes:.1f} минут)")
                    except Exception as e:
                        logger.error(f"Ошибка при удалении файла {filename}: {e}")
        
        if deleted_count > 0:
            logger.info(f"Очистка завершена. Удалено файлов: {deleted_count}")
            
    except Exception as e:
        logger.error(f"Ошибка при очистке старых файлов: {e}")

def cleanup_thread():
    """Фоновый поток для периодической очистки старых файлов"""
    logger.info(f"Запущен поток автоматической очистки данных (интервал: {CLEANUP_INTERVAL_SECONDS} сек., хранение: {DATA_RETENTION_MINUTES} мин.)")
    
    while True:
        try:
            # Выполняем очистку
            delete_old_files()
            
            # Ожидаем до следующего цикла очистки
            time.sleep(CLEANUP_INTERVAL_SECONDS)
        except Exception as e:
            logger.error(f"Ошибка в потоке очистки: {e}")
            # Даже в случае ошибки продолжаем работу потока
            time.sleep(CLEANUP_INTERVAL_SECONDS)

def start_cleanup_thread():
    """Запускает фоновый поток очистки данных"""
    cleanup_thread_obj = threading.Thread(target=cleanup_thread, daemon=True)
    cleanup_thread_obj.start()
    return cleanup_thread_obj

def cleanup_now():
    """Немедленная очистка старых файлов (может быть вызвана вручную)"""
    logger.info("Запущена ручная очистка старых файлов данных...")
    delete_old_files()
