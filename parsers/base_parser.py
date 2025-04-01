from typing import List, Dict, Any, Optional, ClassVar, Pattern
import re
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
import logging

from utils.pdf_utils import extract_text_from_pdf, extract_tables_from_pdf

logger = logging.getLogger(__name__)

class BaseStatementParser(ABC):
    """
    Base class for all bank statement parsers.
    Each bank's specific parser should inherit from this class and implement
    the required methods.
    """
    
    # Class variable to identify the bank (to be overridden by subclasses)
    BANK_NAME: ClassVar[str] = ""
    
    # Regex patterns to identify this bank's statements (to be overridden by subclasses)
    IDENTIFICATION_PATTERNS: ClassVar[List[Pattern]] = []
    
    def __init__(self, pdf_path: Path):
        """
        Initialize the parser with a path to the PDF file
        
        Args:
            pdf_path: Path to the PDF bank statement
        """
        self.pdf_path = Path(pdf_path)
        self.pages_text = []
        self.tables = []
        self.account_info = {}
        self.transactions = []
        
        # Load PDF content
        self._load_pdf_content()
        
    def _load_pdf_content(self):
        """
        Load text and tables from the PDF file
        """
        logger.info(f"Loading content from {self.pdf_path}")
        try:
            self.pages_text = extract_text_from_pdf(str(self.pdf_path))
            self.tables = extract_tables_from_pdf(str(self.pdf_path))
            
            logger.info(f"Loaded {len(self.pages_text)} pages and {len(self.tables)} tables from {self.pdf_path}")
        except Exception as e:
            logger.error(f"Error loading PDF content: {str(e)}")
            raise
            
    @classmethod
    def can_parse(cls, header_text: str) -> bool:
        """
        Determine if this parser can handle the given bank statement
        based on the header text from the first page
        
        Args:
            header_text: Text from the header of the statement
            
        Returns:
            True if this parser can handle the statement, False otherwise
        """
        if not cls.IDENTIFICATION_PATTERNS:
            return False
            
        return any(pattern.search(header_text) for pattern in cls.IDENTIFICATION_PATTERNS)
        
    @abstractmethod
    def extract_account_info(self) -> Dict[str, Any]:
        """
        Extract account information from the statement
        
        Returns:
            Dictionary containing account information
        """
        pass
        
    @abstractmethod
    def extract_transactions(self) -> List[Dict[str, Any]]:
        """
        Extract transactions from the statement
        
        Returns:
            List of dictionaries, each representing a transaction
        """
        pass
        
    def get_statement_period(self) -> Optional[Dict[str, datetime]]:
        """
        Extract the statement period (start and end dates)
        
        Returns:
            Dictionary with 'start_date' and 'end_date' keys, or None if not found
        """
        # Default implementation - to be overridden by subclasses if needed
        return None
        
    def _normalize_transactions(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize transaction data to a standard format
        
        Args:
            transactions: List of raw transaction dictionaries
            
        Returns:
            List of normalized transaction dictionaries
        """
        normalized = []
        
        for transaction in transactions:
            # Ensure all required fields are present
            if 'Date' not in transaction or not transaction['Date']:
                logger.warning(f"Skipping transaction without date: {transaction}")
                continue
                
            if 'Amount' not in transaction or transaction['Amount'] is None:
                logger.warning(f"Skipping transaction without amount: {transaction}")
                continue
                
            # Create normalized transaction
            normalized_transaction = {
                'Date': transaction['Date'],
                'Description': transaction.get('Description', ''),
                'Type': transaction.get('Type', 'unknown'),
                'Amount': transaction['Amount'],
                'Balance': transaction.get('Balance', None)
            }
            
            normalized.append(normalized_transaction)
            
        return normalized
