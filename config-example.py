# Пример файла конфигурации для бота проверки таблиц

# Базовый URL для демо-версии
DEMO_URL = "https://app.meinpflegedienst.com/mp/?demo=X#uebersicht"

# URL для реальной таблицы (заменить на действительный URL, когда будет доступен)
REAL_URL = ""

# Количество ячеек для отображения в каждой категории
MAX_CELLS_PER_CATEGORY = 5

# Время ожидания для загрузки страницы (в секундах)
PAGE_LOAD_TIMEOUT = 20

# Дополнительное время ожидания для ExtJS (в секундах)
EXTJS_ADDITIONAL_WAIT = 10

# CSS-селекторы для поиска таблиц
TABLE_SELECTORS = [
    "table", 
    "div.x-grid-item-container", 
    "div.x-grid", 
    "div.x-panel-body",
    "div.x-grid-view"
]

# Соответствие идентификаторов таблиц и их описаний
TABLE_DESCRIPTIONS = {
    "termine": "ℹ️ Таблица содержит информацию о назначениях и встречах",
    "geburtstage": "🎂 Таблица содержит информацию о днях рождения"
}
