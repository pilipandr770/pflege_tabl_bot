# Telegram-бот для поиска незаполненных ячеек в таблицах

Этот Telegram-бот предназначен для анализа веб-страницы с таблицами и обнаружения незаполненных ячеек. Бот работает с веб-сайтом, использующим ExtJS фреймворк, и умеет анализировать динамически загружаемые таблицы.

## Функциональность

- Анализ страницы `https://app.meinpflegedienst.com/mp/?demo=X#uebersicht` на наличие пустых ячеек
- Структурированное представление результатов по категориям
- Сохранение полного списка пустых ячеек в JSON-файл
- Отправка файла с результатами через Telegram
- Статистика по найденным пустым ячейкам
- ИИ-анализ пустых ячеек с помощью OpenAI для понимания важности отсутствующих данных
- Возможность добавления комментариев к найденным пустым ячейкам
- Отображение названий всех колонок в таблицах
- Автоматическая очистка данных в соответствии с GDPR (EU) требованиями
- Отправка уведомлений через Signal Messenger
- Генерация документации о структуре таблиц для OpenAI ассистента

## Команды бота

- `/start` - Начать работу с ботом
- `/check` - Проверить наличие пустых ячеек в таблицах
- `/stats` - Показать статистику по последней проверке
- `/columns` - Показать список всех колонок в таблицах
- `/comments` - Показать все комментарии к находкам
- `/cleanup` - Запустить ручную очистку старых файлов
- `/dumpall` - Экспортировать все данные таблиц в JSON
- `/help` - Показать справочную информацию

## Требования

- Python 3.6+
- Chrome браузер (для Selenium)
- Пакеты Python из файла `requirements.txt`

## Установка

1. Создайте виртуальное окружение:
```
python -m venv venv
```

2. Активируйте виртуальное окружение:
```
# В Windows PowerShell:
.\venv\Scripts\Activate.ps1

# В Windows Command Prompt:
venv\Scripts\activate.bat
```

3. Установите зависимости:
```
pip install -r requirements.txt
```

4. Установите токен бота Telegram в файл `.env`:
```
BOT_TOKEN=ваш_токен_бота
```

## Запуск

### Прямой запуск

```
python bot.py
```

### Запуск с использованием Docker

1. Соберите Docker-образ:
```
docker build -t tablica_bot_pflege .
```

2. Запустите контейнер:
```
docker run -d --name tablica_bot -v $(pwd)/.env:/app/.env -v $(pwd)/config.py:/app/config.py tablica_bot_pflege
```

### Запуск с использованием Docker Compose

```
docker-compose up -d
```

## Структура проекта

- `bot.py` - Основной файл с логикой Telegram-бота
- `scraper.py` - Модуль для анализа веб-страницы и поиска пустых ячеек
- `.env` - Файл с переменными окружения (токен бота)
- `requirements.txt` - Список зависимостей
- `empty_cells_*.json` - Сохраненные результаты проверок
- `findings_*.json` - Структурированные данные о найденных пустых ячейках
- `cleanup.py` - Модуль для автоматической очистки старых файлов
- `generate_tables_docs.py` - Скрипт для генерации документации о структуре таблиц
- `upload_to_assistant.py` - Скрипт для загрузки документации в OpenAI Assistant
- `create_and_upload_docs.ps1` - Скрипт для автоматической генерации и загрузки документации
- `register-signal-cli*.ps1` - Скрипты для настройки Signal Messenger
- `test-signal-message.ps1` - Скрипт для тестирования отправки сообщений через Signal
- `change-signal-recipient.ps1` - Скрипт для изменения получателя сообщений Signal
- `Dockerfile` - Инструкции для сборки Docker-образа
- `docker-compose.yml` - Конфигурация для Docker Compose

## Дополнительные инструменты

### Генерация документации о структуре таблиц

Для лучшего понимания OpenAI ассистентом структуры таблиц при анализе пустых ячеек можно создать подробную документацию:

```
python generate_tables_docs.py --empty-cells
```

Скрипт проанализирует структуру таблиц и историю пустых ячеек, создав Markdown-файл с подробным описанием.

### Загрузка документации в OpenAI Assistant

После создания документации её можно загрузить в OpenAI Assistant:

```
python upload_to_assistant.py
```

Для автоматической генерации и загрузки в один шаг:

```
.\create_and_upload_docs.ps1
```

> **Примечание:** Для работы с OpenAI API необходимо указать OPENAI_API_KEY и OPENAI_ASSISTANT_ID в файле .env

## Примечания

- Для доступа к реальным данным может потребоваться авторизация
- Структура ExtJS-таблиц может отличаться, поэтому скрипт использует различные селекторы для поиска
- Для отладки в директории создаются скриншоты страницы
