import re
from typing import List, Dict, Any, Optional, Tuple, Pattern
from datetime import datetime
import pdfplumber
import logging

logger = logging.getLogger(__name__)

def extract_text_from_pdf(pdf_path: str) -> List[str]:
    """
    Extract text from each page of a PDF file
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        List of strings, one for each page in the PDF
    """
    pages_text = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text)
                else:
                    logger.warning(f"Empty text extracted from page {page.page_number}")
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        
    return pages_text


def extract_tables_from_pdf(pdf_path: str) -> List[List[List[str]]]:
    """
    Extract tables from each page of a PDF file
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        List of tables, where each table is a list of rows, and each row is a list of cells
    """
    all_tables = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                if tables:
                    all_tables.extend(tables)
    except Exception as e:
        logger.error(f"Error extracting tables from PDF: {str(e)}")
        
    return all_tables


def find_date_in_text(text: str, date_patterns: List[Pattern] = None) -> Optional[datetime]:
    """
    Find and parse a date in the given text using a list of regex patterns
    
    Args:
        text: Text to search for a date
        date_patterns: List of compiled regex patterns to use for searching
                      If None, uses some common date formats
                      
    Returns:
        datetime object if a date is found, None otherwise
    """
    if date_patterns is None:
        # Common date formats: MM/DD/YYYY, MM-DD-YYYY, YYYY-MM-DD, DD/MM/YYYY, etc.
        date_patterns = [
            re.compile(r'\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})\b'),  # MM/DD/YYYY or DD/MM/YYYY
            re.compile(r'\b(\d{4})[/.-](\d{1,2})[/.-](\d{1,2})\b'),  # YYYY-MM-DD
            re.compile(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* (\d{1,2}),? (\d{2,4})\b', re.IGNORECASE)  # Month DD, YYYY
        ]
    
    for pattern in date_patterns:
        match = pattern.search(text)
        if match:
            try:
                # Handle different formats based on the pattern matched
                groups = match.groups()
                if len(groups) == 3:
                    if pattern == date_patterns[0]:  # MM/DD/YYYY or DD/MM/YYYY - assuming MM/DD/YYYY here
                        month, day, year = groups
                    elif pattern == date_patterns[1]:  # YYYY-MM-DD
                        year, month, day = groups
                    else:  # Month DD, YYYY
                        month_str, day, year = groups
                        month_map = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6, 
                                    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
                        month = month_map.get(month_str.lower()[:3], 1)
                        
                    # Ensure year is 4 digits
                    if len(str(year)) == 2:
                        year = f"20{year}" if int(year) < 50 else f"19{year}"
                        
                    return datetime(int(year), int(month), int(day))
            except ValueError as e:
                # Invalid date, continue to the next match
                logger.debug(f"Error parsing date: {str(e)}")
                continue
                
    return None


def parse_money_amount(amount_str: str) -> Optional[float]:
    """
    Parse a string as a monetary amount
    
    Args:
        amount_str: String representing a monetary amount
        
    Returns:
        Float value of the amount, or None if parsing fails
    """
    if not amount_str or not isinstance(amount_str, str):
        return None
        
    # Remove currency symbols, commas, and whitespace
    cleaned = re.sub(r'[\$,\s]', '', amount_str)
    
    # Check for parentheses indicating negative number (e.g., ($100.00))
    is_negative = '(' in cleaned and ')' in cleaned
    cleaned = cleaned.replace('(', '').replace(')', '')
    
    # Handle credit/debit indicators
    if cleaned.lower().endswith('cr'):
        cleaned = cleaned[:-2].strip()
        is_negative = False
    elif cleaned.lower().endswith('dr'):
        cleaned = cleaned[:-2].strip()
        is_negative = True
        
    try:
        amount = float(cleaned)
        if is_negative:
            amount = -amount
        return amount
    except ValueError:
        return None


def identify_transaction_type(amount: float) -> str:
    """
    Identify whether a transaction is a credit or debit based on the amount
    
    Args:
        amount: Transaction amount
        
    Returns:
        'credit' for positive amounts, 'debit' for negative amounts
    """
    return 'credit' if amount >= 0 else 'debit'


def clean_description(description: str) -> str:
    """
    Clean a transaction description by removing unnecessary whitespace, newlines, etc.
    
    Args:
        description: Raw transaction description
        
    Returns:
        Cleaned description
    """
    if not description:
        return ""
        
    # Replace multiple spaces, tabs, and newlines with a single space
    cleaned = re.sub(r'\s+', ' ', description)
    
    # Remove any leading/trailing whitespace
    cleaned = cleaned.strip()
    
    return cleaned
