"""
Скрипт для создания документации о структуре таблиц для ассистента OpenAI.
Этот скрипт собирает информацию о всех таблицах, их колонках, структуре, и часто
встречающихся пустых ячейках. Создает документацию, которую можно загрузить
в ассистента OpenAI для лучшего понимания контекста данных и помощи в анализе
пустых ячеек в медицинских таблицах.
"""

import os
import json
import logging
import glob
from datetime import datetime
from collections import defaultdict, Counter
import re
import argparse
from scraper import dump_all_cells
from config import REAL_URL, DEMO_URL

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_all_cells(data_file):
    """
    Анализирует файл с данными всех ячеек и создает структурированное описание таблиц.
    
    Args:
        data_file (str): Путь к файлу с данными всех ячеек
        
    Returns:
        dict: Структурированное описание таблиц, их колонок и примеров значений
    """
    logger.info(f"Анализируем данные из файла: {data_file}")
    
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Ошибка при чтении файла: {e}")
        return None

    tables_structure = {}
    
    # Анализируем таблицы и их колонки
    for table_name, table_data in data.items():
        if isinstance(table_data, list):
            # Обработка таблиц в формате списка словарей
            columns = {}
            column_samples = defaultdict(list)
            
            for row_data in table_data:
                if "data" in row_data and isinstance(row_data["data"], dict):
                    for col_name, cell_value in row_data["data"].items():
                        if col_name not in columns:
                            columns[col_name] = col_name
                        
                        # Собираем примеры значений (до 3 уникальных для каждой колонки)
                        cell_value = cell_value.strip() if isinstance(cell_value, str) else str(cell_value)
                        if (cell_value and len(cell_value) > 1 and 
                            len(column_samples[col_name]) < 3 and 
                            cell_value not in column_samples[col_name]):
                            column_samples[col_name].append(cell_value)
            
            if columns:  # Добавляем таблицу только если нашли колонки
                tables_structure[table_name] = {
                    "columns": columns,
                    "samples": dict(column_samples)
                }
        elif isinstance(table_data, dict):
            # Обработка таблиц в формате словаря
            columns = {}
            column_samples = {}
            
            # Извлекаем информацию о колонках
            for column_id, column_info in table_data.items():
                if isinstance(column_info, dict) and "header" in column_info:
                    header = column_info["header"]
                    columns[column_id] = header
                    
                    # Собираем примеры значений для каждой колонки
                    cell_values = []
                    for row_id, cell_info in table_data.items():
                        if row_id.startswith("row_") and isinstance(cell_info, dict) and column_id in cell_info:
                            cell_value = cell_info[column_id].strip() if isinstance(cell_info[column_id], str) else str(cell_info[column_id])
                            if cell_value and len(cell_value) > 1 and len(cell_values) < 3 and cell_value not in cell_values:
                                cell_values.append(cell_value)
                                
                    column_samples[column_id] = cell_values
            
            if columns:  # Добавляем таблицу только если нашли колонки
                tables_structure[table_name] = {
                    "columns": columns,
                    "samples": column_samples
                }
    
    return tables_structure

def analyze_empty_cells_patterns():
    """
    Анализирует файлы с пустыми ячейками для выявления общих паттернов
    
    Returns:
        dict: Структурированная информация о часто встречающихся пустых ячейках
    """
    logger.info("Анализируем историю пустых ячеек...")
    empty_cells_files = glob.glob("empty_cells_*.json")
    
    if not empty_cells_files:
        logger.warning("Не найдено файлов с историей пустых ячеек")
        return {}
    
    # Счетчики для различных паттернов
    table_counters = Counter()
    column_counters = defaultdict(Counter)
    table_column_pairs = Counter()
    
    # Анализ всех файлов с пустыми ячейками
    for file_path in empty_cells_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if "empty_cells" not in data:
                continue
                
            for cell_desc in data["empty_cells"]:
                # Попытка извлечь имя таблицы
                parts = cell_desc.split(',', 1)
                if len(parts) < 2:
                    continue
                    
                table_name = parts[0].strip()
                rest_info = parts[1].strip()
                
                # Учитываем встречаемость таблиц
                table_counters[table_name] += 1
                
                # Пытаемся извлечь имя колонки
                column_match = re.search(r'Колонка:\s*([^)]+)', rest_info)
                if column_match:
                    column_name = column_match.group(1).strip()
                    column_counters[table_name][column_name] += 1
                    table_column_pairs[(table_name, column_name)] += 1
        
        except Exception as e:
            logger.error(f"Ошибка при анализе файла {file_path}: {e}")
    
    # Формируем структурированные данные о часто встречающихся пустых ячейках
    empty_cells_patterns = {
        "common_tables": [{"table": table, "count": count} 
                          for table, count in table_counters.most_common(10)],
        "common_columns": [{"table": table, "columns": [{"name": col, "count": count} 
                                                      for col, count in counter.most_common(5)]}
                          for table, counter in column_counters.items()],
        "common_table_column_pairs": [{"table": table, "column": column, "count": count}
                                     for (table, column), count in table_column_pairs.most_common(15)]
    }
    
    return empty_cells_patterns

def generate_documentation(tables_structure):
    """
    Создает документацию на основе структуры таблиц и анализа пустых ячеек
    
    Args:
        tables_structure (dict): Структурированное описание таблиц
        
    Returns:
        str: Текст документации в формате Markdown
    """
    doc = []
    doc.append("# Документация о структуре таблиц медицинской системы MeinPflegedienst")
    doc.append(f"\nДата создания: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n")
    
    doc.append("## Введение")
    doc.append("\nЭтот документ содержит информацию о структуре таблиц в медицинской системе MeinPflegedienst. " +
              "Он предназначен для лучшего понимания контекста данных при анализе незаполненных ячеек.\n")
    
    doc.append("Система работает с сайтом https://app.meinpflegedienst.com/ и содержит " +
              "данные о пациентах, медицинском персонале, назначениях и процедурах.\n")
    
    doc.append("## Общая информация")
    doc.append("\nСистема содержит несколько таблиц, каждая из которых хранит различные аспекты " +
              "данных о пациентах, их медицинском обслуживании, лечении и другой связанной информации.\n")
    
    doc.append("### Основные категории таблиц:")
    doc.append("\n- **Пациенты** - информация о пациентах, их личные данные")
    doc.append("\n- **Персонал** - информация о медицинском персонале")
    doc.append("\n- **Назначения** - информация о назначенных процедурах и лечении")
    doc.append("\n- **Расписание** - информация о запланированных встречах и посещениях")
    doc.append("\n- **Документы** - информация о медицинской документации\n")
    
    # Анализ паттернов пустых ячеек
    empty_cells_patterns = analyze_empty_cells_patterns()
    
    if empty_cells_patterns:
        doc.append("## Часто встречающиеся пустые ячейки")
        doc.append("\nНа основе анализа исторических данных, следующие таблицы и колонки " +
                  "чаще всего содержат незаполненные данные:\n")
        
        # Наиболее частые таблицы с пустыми ячейками
        if empty_cells_patterns.get("common_tables"):
            doc.append("### Таблицы с наибольшим количеством пустых ячеек:")
            for item in empty_cells_patterns["common_tables"][:5]:
                doc.append(f"\n- **{item['table']}** - {item['count']} незаполненных ячеек")
        
        # Наиболее частые пары таблица-колонка
        if empty_cells_patterns.get("common_table_column_pairs"):
            doc.append("\n### Наиболее часто пустующие поля:")
            for item in empty_cells_patterns["common_table_column_pairs"][:10]:
                doc.append(f"\n- **{item['table']} / {item['column']}** - {item['count']} случаев")
                # Добавляем пояснение значимости, если можем определить
                importance = get_field_importance(item['column'])
                if importance:
                    doc.append(f"  - *{importance}*")
            
    doc.append("\n## Структура таблиц\n")
    
    # Сортируем таблицы по имени
    if not tables_structure:
        doc.append("\n*Информация о структуре таблиц недоступна или анализ не выявил корректных таблиц.*\n")
    else:
        for table_name in sorted(tables_structure.keys()):
            table_info = tables_structure[table_name]
            columns = table_info["columns"]
            samples = table_info["samples"]
            
            doc.append(f"### Таблица: {table_name}")
            doc.append("\n#### Описание")
            doc.append("\nЭта таблица содержит данные " + 
                    generate_table_description(table_name) + "\n")
            
            doc.append("#### Колонки")
            
            if not columns:
                doc.append("\n*Не удалось определить колонки для этой таблицы.*\n")
            else:
                # Сортируем колонки по ID
                for column_id in sorted(columns.keys()):
                    header = columns[column_id]
                    doc.append(f"\n##### {header} ({column_id})")
                    
                    # Добавляем описание колонки на основе ее названия
                    column_desc = generate_column_description(header, table_name)
                    doc.append("\n" + column_desc)
                    
                    # Добавляем важность поля
                    importance = get_field_importance(header)
                    if importance:
                        doc.append("\n**Важность:** " + importance)
                    
                    # Добавляем примеры значений
                    if column_id in samples and samples[column_id]:
                        doc.append("\nПримеры значений:")
                        for sample in samples[column_id]:
                            sample_text = sample
                            if len(sample_text) > 100:  # Ограничиваем длину длинных примеров
                                sample_text = sample_text[:100] + "..."
                            doc.append(f"- {sample_text}")
                    
                    doc.append("")  # Пустая строка для разделения
    
    # Добавляем рекомендации для анализа пустых ячеек
    doc.append("## Рекомендации по анализу пустых ячеек")
    doc.append("\nПри анализе пустых ячеек рекомендуется обратить внимание на следующие аспекты:\n")
    doc.append("\n1. **Критичность информации** - насколько критична отсутствующая информация для лечения пациента.")
    doc.append("\n2. **Нормативные требования** - какие поля должны быть заполнены согласно медицинским стандартам.")
    doc.append("\n3. **Потенциальные риски** - какие риски возникают при отсутствии информации в конкретных полях.")
    doc.append("\n4. **Приоритет заполнения** - какие поля следует заполнить в первую очередь.")
    doc.append("\n5. **Возможные причины** - почему информация может отсутствовать (технические проблемы, человеческий фактор).\n")
    
    return "\n".join(doc)

def get_field_importance(field_name):
    """
    Определяет важность поля на основе его названия
    
    Args:
        field_name (str): Название поля/колонки
        
    Returns:
        str: Описание важности или None, если невозможно определить
    """
    field_name_lower = field_name.lower()
    
    # Критически важные поля
    critical_fields = {
        "diagnose": "Критически важная информация для лечения. Отсутствие диагноза может привести к неправильному лечению.",
        "allergien": "Критически важная информация о наличии аллергических реакций. Отсутствие может угрожать жизни пациента.",
        "medikament": "Критически важная информация о назначенных лекарствах. Влияет на лечение и возможные взаимодействия.",
        "dosis": "Критически важная информация о дозировке лекарств. Неправильная дозировка может навредить пациенту."
    }
    
    # Очень важные поля
    important_fields = {
        "geburtsdatum": "Важная информация для идентификации пациента и расчета возрастных особенностей лечения.",
        "name": "Важная информация для идентификации пациента или сотрудника.",
        "vorname": "Важная информация для идентификации пациента или сотрудника.",
        "nachname": "Важная информация для идентификации пациента или сотрудника.",
        "versicherung": "Важная информация для оплаты услуг и документооборота.",
        "termin": "Важная информация для планирования работы персонала и обслуживания пациентов."
    }
    
    # Стандартные поля
    standard_fields = {
        "telefon": "Стандартная контактная информация. Важна для связи с пациентом или его представителями.",
        "email": "Стандартная контактная информация.",
        "adresse": "Стандартная информация о месте проживания. Может быть важна для планирования выездов.",
        "bemerkung": "Дополнительная информация, которая может содержать важные детали.",
        "notiz": "Дополнительная информация, которая может содержать важные детали."
    }
    
    # Проверяем соответствие
    for word, desc in critical_fields.items():
        if word in field_name_lower:
            return "Критически важное поле. " + desc
            
    for word, desc in important_fields.items():
        if word in field_name_lower:
            return "Очень важное поле. " + desc
            
    for word, desc in standard_fields.items():
        if word in field_name_lower:
            return "Стандартное поле. " + desc
            
    return None

def generate_table_description(table_name):
    """
    Генерирует описание таблицы на основе ее имени
    
    Args:
        table_name (str): Название таблицы
        
    Returns:
        str: Описание таблицы
    """
    # Словарь с описаниями распространенных типов таблиц
    descriptions = {
        "patient": "о пациентах, их личной и контактной информации",
        "patientdata": "о пациентах, включая их личные данные и медицинскую информацию",
        "pflege": "о медицинском уходе и лечебных процедурах",
        "pfleger": "о медицинском персонале и ухаживающих",
        "mitarbeiter": "о сотрудниках медицинского учреждения",
        "termin": "о назначенных визитах, встречах и процедурах",
        "termine": "о назначенных визитах, встречах и процедурах",
        "medikament": "о лекарственных препаратах и их применении",
        "medikamente": "о лекарственных препаратах и их применении",
        "behandlung": "о методах лечения и терапии",
        "diagnose": "о диагнозах пациентов",
        "anamnese": "об анамнезе пациентов",
        "personal": "о персонале медицинского учреждения",
        "dokument": "о документах и медицинской документации",
        "schein": "о медицинских направлениях и рецептах",
        "kontakt": "о контактах и связанных лицах",
        "date": "о датах и временных метках событий",
        "geburtstage": "о днях рождения пациентов или персонала",
        "uebersicht": "обзорная информация о различных аспектах работы",
        "grid": "табличные данные о различных аспектах работы",
        "gridview": "представление данных в табличном формате",
        "treeview": "иерархически организованные данные"
    }
    
    table_name_lower = table_name.lower()
    
    # Находим наиболее подходящее описание
    matched_descriptions = []
    for key, desc in descriptions.items():
        if key in table_name_lower:
            matched_descriptions.append(desc)
    
    if matched_descriptions:
        if len(matched_descriptions) > 1:
            # Если нашли несколько совпадений, объединяем их
            return ", ".join(matched_descriptions)
        else:
            return matched_descriptions[0]
    
    # Специальные случаи для конкретных таблиц MeinPflegedienst
    if "mp-uebersicht-termine" in table_name_lower:
        return "о назначенных визитах и встречах в обзорном представлении"
    elif "mp-uebersicht-geburtstage" in table_name_lower:
        return "о днях рождения пациентов или персонала в обзорном представлении"
    
    return "связанные с медицинским обслуживанием"

def generate_column_description(header, table_name):
    """
    Генерирует описание колонки на основе ее названия и контекста таблицы
    
    Args:
        header (str): Название колонки
        table_name (str): Название таблицы (для контекста)
        
    Returns:
        str: Описание колонки
    """
    header_lower = header.lower()
    table_name_lower = table_name.lower()
    
    # Словарь с описаниями распространенных типов колонок
    descriptions = {
        "name": "Имя пациента или сотрудника",
        "vorname": "Имя пациента или сотрудника",
        "nachname": "Фамилия пациента или сотрудника",
        "geburtsdatum": "Дата рождения пациента или сотрудника",
        "geburtstag": "Дата рождения пациента или сотрудника",
        "adresse": "Адрес проживания",
        "straße": "Улица проживания",
        "plz": "Почтовый индекс",
        "ort": "Населенный пункт",
        "telefon": "Контактный телефон",
        "tel": "Контактный телефон",
        "handy": "Мобильный телефон",
        "email": "Адрес электронной почты",
        "versicherung": "Информация о страховке",
        "versicherungsnummer": "Номер страхового полиса",
        "krankenkasse": "Медицинская страховая компания",
        "diagnose": "Поставленный диагноз",
        "medikament": "Назначенное лекарство или препарат",
        "dosis": "Дозировка препарата",
        "datum": "Дата события или записи",
        "uhrzeit": "Время события или записи",
        "anmerkung": "Дополнительные примечания или комментарии",
        "status": "Статус записи или процедуры",
        "id": "Уникальный идентификатор записи",
        "patient": "Идентификатор или ссылка на пациента",
        "arzt": "Врач, ответственный за лечение или назначение",
        "pfleger": "Медицинский работник, осуществляющий уход",
        "service": "Тип услуги или сервиса",
        "leistung": "Оказанная услуга или процедура",
        "kosten": "Стоимость услуги или процедуры",
        "bemerkung": "Замечания или комментарии",
        "notiz": "Заметки или примечания",
        "geschlecht": "Пол пациента или сотрудника",
        "alter": "Возраст пациента или сотрудника",
        "jahre": "Количество лет (возраст)",
        "bereich": "Область или отделение",
        "abteilung": "Отдел или подразделение",
        "termin": "Запланированная встреча, визит или процедура",
        "zeit": "Время события",
        "von": "Время начала",
        "bis": "Время окончания",
        "duration": "Продолжительность",
        "dauer": "Продолжительность",
        "art": "Тип или категория",
        "typ": "Тип или категория",
        "kategorie": "Категория",
        "mitarbeiter": "Сотрудник, ответственный за процедуру или запись"
    }
    
    # Контекстно-зависимые описания
    context_descriptions = {
        # Колонки в контексте таблиц о пациентах
        ("name", "patient"): "Полное имя пациента",
        ("alter", "patient"): "Возраст пациента в годах",
        ("geschlecht", "patient"): "Пол пациента",
        
        # Колонки в контексте таблиц о персонале
        ("name", "personal"): "Полное имя сотрудника",
        ("name", "mitarbeiter"): "Полное имя сотрудника",
        ("name", "pfleger"): "Полное имя медицинского работника",
        
        # Колонки в контексте таблиц о встречах/визитах
        ("datum", "termin"): "Дата назначенного визита или процедуры",
        ("zeit", "termin"): "Время назначенного визита или процедуры",
        
        # Колонки в контексте таблиц о днях рождения
        ("name", "geburtstag"): "Имя человека, у которого день рождения",
        ("datum", "geburtstag"): "Дата дня рождения",
        ("alter", "geburtstag"): "Исполняющийся возраст",
        ("jahre", "geburtstag"): "Исполняющееся количество лет"
    }
    
    # Проверяем контекстные описания
    for (col, context), desc in context_descriptions.items():
        if col in header_lower and context in table_name_lower:
            return desc
    
    # Находим наиболее подходящее описание
    for key, desc in descriptions.items():
        if key in header_lower:
            return desc
    
    # Если не нашли подходящего описания, возвращаем более умное общее описание
    if "mp-uebersicht-termine" in table_name_lower:
        return f"Информация о {header} в контексте запланированных визитов"
    elif "mp-uebersicht-geburtstage" in table_name_lower:
        return f"Информация о {header} в контексте дней рождения"
    elif "mitarbeiter" in table_name_lower or "personal" in table_name_lower:
        return f"Данные о {header} сотрудника"
    elif "patient" in table_name_lower:
        return f"Данные о {header} пациента"
    
    return f"Данные, относящиеся к полю '{header}' в таблице {table_name}"

def create_documentation_file(tables_structure, output_file=None, empty_cells_data=None):
    """
    Создает файл документации на основе структуры таблиц
    
    Args:
        tables_structure (dict): Структурированное описание таблиц
        output_file (str, optional): Путь для сохранения файла документации
        empty_cells_data (dict, optional): Дополнительные данные о пустых ячейках
        
    Returns:
        str: Путь к созданному файлу документации
    """
    if output_file is None:
        output_file = f"table_documentation_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.md"
    
    doc_content = generate_documentation(tables_structure)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(doc_content)
    
    logger.info(f"Документация сохранена в файл: {output_file}")
    return output_file

def analyze_empty_cells_files():
    """
    Анализирует файлы с пустыми ячейками для получения статистики
    
    Returns:
        dict: Статистика по пустым ячейкам
    """
    empty_cells_files = glob.glob("empty_cells_*.json")
    if not empty_cells_files:
        logger.warning("Не найдено файлов с данными о пустых ячейках")
        return {}
    
    stats = {
        "total_files": len(empty_cells_files),
        "total_empty_cells": 0,
        "tables": defaultdict(int),
        "columns": defaultdict(int),
        "table_column_pairs": defaultdict(int),
        "recent_date": None,
        "oldest_date": None
    }
    
    for file_path in sorted(empty_cells_files):
        try:
            # Извлекаем дату из имени файла
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', file_path)
            if date_match:
                date_str = date_match.group(1)
                if stats["recent_date"] is None or date_str > stats["recent_date"]:
                    stats["recent_date"] = date_str
                if stats["oldest_date"] is None or date_str < stats["oldest_date"]:
                    stats["oldest_date"] = date_str
            
            # Читаем содержимое файла
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if "empty_cells" not in data:
                continue
                
            stats["total_empty_cells"] += len(data["empty_cells"])
            
            # Анализируем каждую пустую ячейку
            for cell_desc in data["empty_cells"]:
                parts = cell_desc.split(',', 1)
                if len(parts) < 2:
                    continue
                    
                table_name = parts[0].strip()
                rest_info = parts[1].strip()
                
                stats["tables"][table_name] += 1
                
                # Извлекаем название колонки, если есть
                column_match = re.search(r'Колонка:\s*([^)]+)', rest_info)
                if column_match:
                    column_name = column_match.group(1).strip()
                    stats["columns"][column_name] += 1
                    stats["table_column_pairs"][f"{table_name}:{column_name}"] += 1
        except Exception as e:
            logger.error(f"Ошибка при анализе файла {file_path}: {e}")
    
    return stats

def main():
    """
    Основная функция скрипта
    """
    parser = argparse.ArgumentParser(description='Создание документации о структуре таблиц')
    parser.add_argument('--input', '-i', help='Путь к существующему файлу с данными всех ячеек')
    parser.add_argument('--output', '-o', help='Путь для сохранения документации')
    parser.add_argument('--demo', '-d', action='store_true', help='Использовать демо-URL')
    parser.add_argument('--empty-cells', '-e', action='store_true', help='Включить анализ пустых ячеек из имеющихся файлов')
    parser.add_argument('--analyze-only', '-a', action='store_true', help='Только анализировать данные, не собирать новые')
    args = parser.parse_args()
    
    # Получаем данные
    if args.input:
        data_file = args.input
        logger.info(f"Используем данные из указанного файла: {data_file}")
    elif args.analyze_only:
        # Ищем самый свежий файл с данными
        all_cells_files = glob.glob("all_cells_*.json")
        if all_cells_files:
            data_file = max(all_cells_files)
            logger.info(f"Используем самый свежий файл с данными: {data_file}")
        else:
            logger.error("Не найдено файлов с данными. Укажите файл с помощью --input или запустите сбор данных без --analyze-only")
            return
    else:
        # Собираем данные заново
        url = DEMO_URL if args.demo else REAL_URL
        if not url:
            url = DEMO_URL
            logger.info("Реальный URL не настроен, используется демо-URL")
        
        logger.info(f"Получаем данные о ячейках с URL: {url}")
        data_file = dump_all_cells(url)
    
    # Анализируем данные
    tables_structure = analyze_all_cells(data_file)
    
    # Если структура получена успешно, создаем документацию
    if tables_structure:
        # Анализируем пустые ячейки, если нужно
        empty_cells_data = None
        if args.empty_cells:
            empty_cells_data = analyze_empty_cells_files()
            logger.info(f"Проанализировано {empty_cells_data.get('total_files', 0)} файлов с данными о пустых ячейках")
        
        # Создаем документацию
        doc_file = create_documentation_file(tables_structure, args.output, empty_cells_data)
        
        print("\n" + "=" * 70)
        print(f"Документация успешно создана и сохранена в файл:")
        print(f"\n{doc_file}\n")
        print("Теперь вы можете загрузить этот файл в ассистента OpenAI")
        print("для лучшего понимания структуры таблиц при анализе пустых ячеек.")
        print("=" * 70 + "\n")
        
    else:
        # В этом случае создадим хотя бы минимальную документацию
        logger.warning("Не удалось получить структуру таблиц из файла данных")
        
        # Если включен режим анализа пустых ячеек, хотя бы его используем
        if args.empty_cells:
            empty_cells_data = analyze_empty_cells_files()
            logger.info(f"Проанализировано {empty_cells_data.get('total_files', 0)} файлов с данными о пустых ячейках")
            
            # Создаем минимальную документацию только с анализом пустых ячеек
            doc_file = create_documentation_file({}, args.output, empty_cells_data)
            
            print("\n" + "=" * 70)
            print(f"Создана частичная документация (только анализ пустых ячеек):")
            print(f"\n{doc_file}\n")
            print("=" * 70 + "\n")
        else:
            print("\n" + "=" * 70)
            print("Не удалось создать документацию из-за ошибок при анализе данных")
            print("Попробуйте использовать параметр --empty-cells для создания")
            print("документации на основе анализа имеющихся файлов с пустыми ячейками")
            print("=" * 70 + "\n")

if __name__ == "__main__":
    main()
