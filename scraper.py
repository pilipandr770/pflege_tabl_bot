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
        # Setup headless browser
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
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
            
            for row_idx, row in enumerate(rows):
                cells = row.find_elements(By.TAG_NAME, "td")
                
                for cell_idx, cell in enumerate(cells):
                    if not cell.text.strip():
                        # Empty cell found
                        # Get header info if possible
                        header_info = get_header_info(table, row_idx, cell_idx)
                        empty_cells.append(f"{table_id}, Row {row_idx+1}, Column {cell_idx+1} {header_info}")
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
            
            # ExtJS often uses div.x-grid-cell for cells
            cells = element.find_elements(By.CSS_SELECTOR, "div.x-grid-cell")
            
            # Try to get table headers for more context
            header_texts = {}
            try:
                headers = element.find_elements(By.CSS_SELECTOR, "div.x-column-header")
                for i, header in enumerate(headers):
                    header_texts[i] = header.text.strip()
            except:
                # If we can't find headers, try an alternative
                try:
                    headers = element.find_elements(By.CSS_SELECTOR, "span.x-column-header-text")
                    for i, header in enumerate(headers):
                        header_texts[i] = header.text.strip()
                except:
                    pass
            
            if cells:
                for cell_idx, cell in enumerate(cells):
                    if not cell.text.strip():
                        # Try to get row and column information
                        row_info = "unknown"
                        col_info = "unknown"
                        
                        # ExtJS often has data-recordindex for rows
                        try:
                            row_parent = cell.find_element(By.XPATH, "./ancestor::div[contains(@class, 'x-grid-item')]")
                            if row_parent:
                                row_info = row_parent.get_attribute("data-recordindex") or "unknown"
                        except:
                            pass
                        
                        # And data-columnid for columns
                        try:
                            col_id = cell.get_attribute("data-columnid")
                            if col_id:
                                col_info = col_id
                            else:
                                # Try to find column index and use header text if available
                                col_info = f"Column {cell_idx % len(header_texts) + 1}"
                                if header_texts and (cell_idx % len(header_texts)) in header_texts:
                                    col_info += f" ({header_texts[cell_idx % len(header_texts)]})"
                        except:
                            col_info = f"Column {cell_idx+1}"
                        
                        empty_cells.append(f"{element_id}, Row {row_info}, {col_info} (Empty)")
            else:
                # No cells found, try looking for content containers
                content_divs = element.find_elements(By.CSS_SELECTOR, "div.x-grid-cell-inner")
                
                for div_idx, div in enumerate(content_divs):
                    if not div.text.strip():
                        column_info = ""
                        if header_texts and (div_idx % len(header_texts)) in header_texts:
                            column_info = f" ({header_texts[div_idx % len(header_texts)]})"
                        
                        empty_cells.append(f"{element_id}, Item {div_idx+1}{column_info} (Empty)")
                        
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