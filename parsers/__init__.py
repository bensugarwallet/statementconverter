from typing import Optional, List, Type
from pathlib import Path
import logging
import re
import pdfplumber

from .base_parser import BaseStatementParser
from .bank1_parser import Bank1StatementParser
from .bank2_parser import Bank2StatementParser
from .bank3_parser import Bank3StatementParser
from .nz_bank_parser import NZBankStatementParser

logger = logging.getLogger(__name__)

# List of available parsers
AVAILABLE_PARSERS = [
    NZBankStatementParser,  # Try NZ banks first
    Bank1StatementParser,
    Bank2StatementParser,
    Bank3StatementParser,
]


def get_parser_for_statement(pdf_path: Path) -> Optional[BaseStatementParser]:
    """
    Identify the appropriate parser for a given bank statement PDF
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        An instance of the appropriate parser, or None if no suitable parser is found
    """
    logger.info(f"Determining parser for {pdf_path}")
    
    # First, extract some text from the first page to use for identification
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if len(pdf.pages) == 0:
                logger.error(f"PDF has no pages: {pdf_path}")
                return None
                
            first_page = pdf.pages[0]
            header_text = first_page.extract_text(x_tolerance=3)
            if not header_text:
                logger.warning(f"No text could be extracted from the first page of {pdf_path}")
                return None
                
            # Try each parser's can_parse method
            for parser_class in AVAILABLE_PARSERS:
                try:
                    if parser_class.can_parse(header_text):
                        logger.info(f"Using {parser_class.__name__} for {pdf_path}")
                        return parser_class(pdf_path)
                except Exception as e:
                    logger.warning(f"Error checking {parser_class.__name__}: {str(e)}")
                    continue
                    
            # If no parser was found, try to identify the bank based on the header text
            bank_name = identify_bank_from_header(header_text)
            if bank_name:
                logger.info(f"Identified as {bank_name} statement, but no specific parser available")
                
            logger.warning(f"No suitable parser found for {pdf_path}")
            return None
                
    except Exception as e:
        logger.error(f"Error opening PDF to determine parser: {str(e)}")
        return None


def identify_bank_from_header(header_text: str) -> Optional[str]:
    """
    Try to identify the bank from the header text of a statement
    
    Args:
        header_text: Text from the header of the statement
        
    Returns:
        Name of the bank if identified, None otherwise
    """
    # Common bank name patterns
    bank_patterns = [
        # New Zealand banks
        (re.compile(r'anz\s*bank', re.IGNORECASE), "ANZ Bank"),
        (re.compile(r'asb\s*bank', re.IGNORECASE), "ASB Bank"),
        (re.compile(r'kiwibank', re.IGNORECASE), "Kiwibank"),
        (re.compile(r'bnz|bank\s*of\s*new\s*zealand', re.IGNORECASE), "Bank of New Zealand"),
        (re.compile(r'westpac', re.IGNORECASE), "Westpac NZ"),
        
        # US banks
        (re.compile(r'bank\s*of\s*america', re.IGNORECASE), "Bank of America"),
        (re.compile(r'chase', re.IGNORECASE), "Chase"),
        (re.compile(r'wells\s*fargo', re.IGNORECASE), "Wells Fargo"),
        (re.compile(r'citi(?:bank)?', re.IGNORECASE), "Citibank"),
        (re.compile(r'capital\s*one', re.IGNORECASE), "Capital One"),
        (re.compile(r'td\s*bank', re.IGNORECASE), "TD Bank"),
        (re.compile(r'pnc\s*bank', re.IGNORECASE), "PNC Bank"),
        (re.compile(r'u\.?s\.?\s*bank', re.IGNORECASE), "US Bank"),
    ]
    
    for pattern, bank_name in bank_patterns:
        if pattern.search(header_text):
            return bank_name
            
    return None
