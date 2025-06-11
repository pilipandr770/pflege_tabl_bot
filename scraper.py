import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging
import os
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logger = logging.getLogger(__name__)

def get_empty_cells(url="https://app.meinpflegedienst.com/mp/?demo=X#uebersicht"):
    """
    Scrape the table from the website and return a list of empty cells
    
    Args:
        url (str): URL of the page to analyze, defaults to the demo URL
        
    Returns:
        list: List of strings describing empty cells found on the page
    """
    try:
        # Setup browser options
        chrome_options = Options()
        
        # Check if running in Docker or if SELENIUM_HEADLESS is set
        if os.environ.get('SELENIUM_HEADLESS', '').lower() == 'true':
            chrome_options.add_argument("--headless=new")
            logger.info("Running Chrome in headless mode")
            
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-gpu")
        
        # Create driver with appropriate service
        driver = webdriver.Chrome(options=chrome_options)
        
        # Load the page
        logger.info(f"Loading URL: {url}")
        driver.get(url)
        
        # ExtJS takes longer to load - wait more time
        logger.info("Waiting for the page to load...")
        
        try:
            # First wait for basic page structure
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # ExtJS often uses divs with specific classes for tables
            # Need to wait longer for dynamic content
            time.sleep(10)
            
            # Take screenshot for debugging
            driver.save_screenshot("page_loaded.png")
            
            # Log page title for verification
            logger.info(f"Page Title: {driver.title}")
            
            # Try different selectors that might contain table data in ExtJS
            selectors = [
                "table", 
                "div.x-grid-item-container", 
                "div.x-grid", 
                "div.x-panel-body",
                "div.x-grid-view"
            ]
            
            empty_cells = []
            
            for selector in selectors:
                try:
                    logger.info(f"Trying selector: {selector}")
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    if elements:
                        logger.info(f"Found {len(elements)} elements with selector {selector}")
                        
                        # Process tables
                        if selector == "table":
                            empty_cells.extend(process_standard_tables(driver, elements))
                        # Process ExtJS grid structures
                        else:
                            empty_cells.extend(process_extjs_grids(driver, elements, selector))
                
                except Exception as e:
                    logger.error(f"Error processing selector {selector}: {str(e)}")
            
            # If no empty cells found, try to get all page content for analysis
            if not empty_cells:
                logger.info("No empty cells found through selectors, getting page content")
                body_text = driver.find_element(By.TAG_NAME, "body").text
                empty_cells.append(f"No empty cells identified. Page uses ExtJS framework which requires custom selectors. Page content length: {len(body_text)} characters")
                
                # Add information about the structure
                html_structure = driver.page_source
                logger.info(f"HTML structure length: {len(html_structure)}")
            
            driver.quit()
            return empty_cells
        
        except TimeoutException:
            logger.error("Timeout waiting for page elements to load")
            driver.save_screenshot("timeout_error.png")
            driver.quit()
            return ["Error: Page took too long to load. The site might be using complex JavaScript that requires authentication."]
    
    except Exception as e:
        logger.error(f"Error in get_empty_cells: {str(e)}")
        if 'driver' in locals():
            driver.quit()
        raise e

def process_standard_tables(driver, tables):
    """Process standard HTML tables"""
    empty_cells = []
    
    for table_idx, table in enumerate(tables):
        try:
            rows = table.find_elements(By.TAG_NAME, "tr")
            
            # Get table identifier if possible
            table_id = table.get_attribute("id") or f"Table {table_idx+1}"
            
            # Extract all headers for better context
            all_headers = []
            try:
                headers_row = table.find_elements(By.TAG_NAME, "th")
                if headers_row:
                    for header in headers_row:
                        all_headers.append(header.text.strip())
                elif len(rows) > 0:
                    # Try to use first row as header if no TH elements
                    first_row = rows[0]
                    header_cells = first_row.find_elements(By.TAG_NAME, "td")
                    for header_cell in header_cells:
                        all_headers.append(header_cell.text.strip())
                        
                logger.info(f"Found headers for table {table_id}: {all_headers}")
            except Exception as e:
                logger.error(f"Error extracting headers for table {table_id}: {str(e)}")
            
            # Process each row, starting with the second row if the first was used for headers
            start_row = 1 if len(all_headers) > 0 and len(rows) > 0 else 0
            
            for row_idx, row in enumerate(rows[start_row:], start=start_row):
                # Try to find a row identifier (usually first cell or cells with specific classes)
                row_identifier = None
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if cells and len(cells) > 0:
                        row_identifier = cells[0].text.strip()
                except:
                    pass
                
                row_id_text = f" (ID: {row_identifier})" if row_identifier else ""
                
                for cell_idx, cell in enumerate(cells):
                    if not cell.text.strip():
                        # Empty cell found
                        # Get header info if possible
                        header_info = ""
                        if all_headers and cell_idx < len(all_headers) and all_headers[cell_idx]:
                            header_info = f" (Колонка: {all_headers[cell_idx]})"
                        else:
                            header_info = get_header_info(table, row_idx, cell_idx)
                            
                        empty_cells.append(f"{table_id}, Строка {row_idx+1}{row_id_text}, Колонка {cell_idx+1}{header_info}")
        except Exception as e:
            logger.error(f"Error processing table {table_idx+1}: {str(e)}")
    
    return empty_cells

def process_extjs_grids(driver, elements, selector):
    """Process ExtJS grid structures which are more complex"""
    empty_cells = []
    
    for idx, element in enumerate(elements):
        try:
            # Try to get a meaningful identifier
            element_id = element.get_attribute("id") or f"{selector.replace('div.', '')} {idx+1}"
            
            # Log the identified element
            logger.info(f"Processing ExtJS grid: {element_id}")
            
            # ExtJS often uses div.x-grid-cell for cells
            cells = element.find_elements(By.CSS_SELECTOR, "div.x-grid-cell")
            
            # Try to get table headers for more context using multiple methods
            header_texts = {}
            all_headers = []
            
            # Method 1: Standard ExtJS header cells
            try:
                headers = element.find_elements(By.CSS_SELECTOR, "div.x-column-header")
                for i, header in enumerate(headers):
                    header_text = header.text.strip()
                    header_texts[i] = header_text
                    all_headers.append(header_text)
                logger.info(f"Found {len(headers)} headers using method 1")
            except Exception as e:
                logger.warning(f"Error finding headers with method 1: {str(e)}")
            
            # Method 2: Header text spans
            if not header_texts:
                try:
                    headers = element.find_elements(By.CSS_SELECTOR, "span.x-column-header-text")
                    for i, header in enumerate(headers):
                        header_text = header.text.strip()
                        header_texts[i] = header_text
                        all_headers.append(header_text)
                    logger.info(f"Found {len(headers)} headers using method 2")
                except Exception as e:
                    logger.warning(f"Error finding headers with method 2: {str(e)}")
            
            # Method 3: Try to get header from the first row's cell contents
            if not header_texts:
                try:
                    # Get all rows
                    rows = element.find_elements(By.CSS_SELECTOR, "div.x-grid-item")
                    if rows:
                        # Get cells in first row
                        first_row_cells = rows[0].find_elements(By.CSS_SELECTOR, "div.x-grid-cell")
                        for i, cell in enumerate(first_row_cells):
                            header_text = cell.text.strip()
                            if header_text:  # Only add non-empty cells
                                header_texts[i] = header_text
                                all_headers.append(header_text)
                        logger.info(f"Found {len(header_texts)} potential headers from first row")
                except Exception as e:
                    logger.warning(f"Error finding headers from first row: {str(e)}")
            
            # Log found headers
            if header_texts:
                logger.info(f"Headers for {element_id}: {header_texts}")
            
            if cells:
                # Create a structure to track row identifiers
                row_identifiers = {}
                
                # Try to extract row IDs from all rows first (usually in first column)
                try:
                    rows = element.find_elements(By.CSS_SELECTOR, "div.x-grid-item")
                    for i, row in enumerate(rows):
                        # Try to find a patient ID or name in the row
                        patient_cells = row.find_elements(By.CSS_SELECTOR, "div.x-grid-cell")
                        if patient_cells:
                            # Assume first cell might contain patient ID/name
                            row_identifiers[i] = patient_cells[0].text.strip()
                except Exception as e:
                    logger.warning(f"Error extracting row identifiers: {str(e)}")
                
                # Process each cell
                for cell_idx, cell in enumerate(cells):
                    if not cell.text.strip():
                        # Try to get row and column information
                        row_info = "unknown"
                        col_info = "unknown"
                        row_number = 0
                        
                        # ExtJS often has data-recordindex for rows
                        try:
                            row_parent = cell.find_element(By.XPATH, "./ancestor::div[contains(@class, 'x-grid-item')]")
                            if row_parent:
                                row_record_index = row_parent.get_attribute("data-recordindex")
                                if row_record_index:
                                    row_number = int(row_record_index)
                                    row_info = row_record_index
                                    
                                    # Add row identifier if available
                                    if row_number in row_identifiers and row_identifiers[row_number]:
                                        row_info += f" (Пациент: {row_identifiers[row_number]})"
                        except Exception as e:
                            logger.warning(f"Error getting row info: {str(e)}")
                        
                        # Get column information
                        try:
                            col_id = cell.get_attribute("data-columnid")
                            if col_id:
                                col_info = col_id
                            else:
                                # Calculate column index within its row
                                try:
                                    row_cells_count = len(header_texts) if header_texts else 1
                                    col_index = cell_idx % row_cells_count
                                    col_info = f"Колонка {col_index + 1}"
                                    
                                    # Add header text if available
                                    if header_texts and col_index in header_texts:
                                        col_info += f" ({header_texts[col_index]})"
                                except:
                                    col_info = f"Колонка {cell_idx + 1}"
                        except Exception as e:
                            logger.warning(f"Error getting column info: {str(e)}")
                            col_info = f"Колонка {cell_idx + 1}"
                        
                        empty_cells.append(f"{element_id}, Строка {row_info}, {col_info} (Пустая ячейка)")
            else:
                # No cells found, try looking for content containers
                content_divs = element.find_elements(By.CSS_SELECTOR, "div.x-grid-cell-inner")
                
                for div_idx, div in enumerate(content_divs):
                    if not div.text.strip():
                        column_info = ""
                        if header_texts:
                            col_index = div_idx % len(header_texts) if len(header_texts) > 0 else 0
                            if col_index in header_texts:
                                column_info = f" (Колонка: {header_texts[col_index]})"
                        
                        empty_cells.append(f"{element_id}, Запись {div_idx+1}{column_info} (Пустая ячейка)")
                        
        except Exception as e:
            logger.error(f"Error processing ExtJS element {idx+1}: {str(e)}")
    
    return empty_cells

def get_header_info(table, row_idx, cell_idx):
    """Attempt to get header information for context"""
    try:
        # Try to get column header
        headers = table.find_elements(By.TAG_NAME, "th")
        
        if headers and cell_idx < len(headers):
            header_text = headers[cell_idx].text.strip()
            if header_text:
                return f"(Header: {header_text})"
        
        # Alternative: try to find headers in first row
        first_row = table.find_elements(By.TAG_NAME, "tr")[0]
        if first_row:
            headers = first_row.find_elements(By.TAG_NAME, "td")
            if headers and cell_idx < len(headers):
                header_text = headers[cell_idx].text.strip()
                if header_text:
                    return f"(Header: {header_text})"
        
        return ""
    except Exception:
        return ""

def dump_all_cells(url="https://app.meinpflegedienst.com/mp/?demo=X#uebersicht", filename=None):
    """
    Сохраняет все ячейки всех таблиц с названиями колонок в JSON-файл.
    Формат:
    {
        "TableName1": [
            {"row": 1, "data": {"Column1": "value", "Column2": "value", ...}},
            ...
        ],
        ...
    }
    """
    from selenium.webdriver.common.by import By
    import json
    import time
    import os
    
    chrome_options = Options()
    if os.environ.get('SELENIUM_HEADLESS', '').lower() == 'true':
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)
    time.sleep(10)
    
    tables = driver.find_elements(By.TAG_NAME, "table")
    all_tables = {}
    for table_idx, table in enumerate(tables):
        table_id = table.get_attribute("id") or f"Table {table_idx+1}"
        rows = table.find_elements(By.TAG_NAME, "tr")
        # Получаем заголовки
        headers = []
        header_cells = []
        if rows:
            ths = rows[0].find_elements(By.TAG_NAME, "th")
            if ths:
                header_cells = ths
            else:
                header_cells = rows[0].find_elements(By.TAG_NAME, "td")
            headers = [cell.text.strip() for cell in header_cells]
        # Сохраняем строки
        table_data = []
        for row_idx, row in enumerate(rows[1:], start=1):
            cells = row.find_elements(By.TAG_NAME, "td")
            row_data = {}
            for col_idx, cell in enumerate(cells):
                col_name = headers[col_idx] if col_idx < len(headers) else f"Column {col_idx+1}"
                row_data[col_name] = cell.text.strip()
            table_data.append({"row": row_idx, "data": row_data})
        all_tables[table_id] = table_data
    driver.quit()
    # Сохраняем в файл
    if not filename:
        filename = f"all_cells_{int(time.time())}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(all_tables, f, ensure_ascii=False, indent=2)
    return filename