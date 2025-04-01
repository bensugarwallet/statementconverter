import re
from typing import List, Dict, Any, Optional, ClassVar, Pattern
from datetime import datetime
import logging

from .base_parser import BaseStatementParser
from utils.pdf_utils import find_date_in_text, parse_money_amount, identify_transaction_type, clean_description

logger = logging.getLogger(__name__)

class Bank1StatementParser(BaseStatementParser):
    """
    Parser for Bank1 statements (e.g., Bank of America)
    
    Sample format:
    DATE | DESCRIPTION | AMOUNT | BALANCE
    MM/DD | Transaction description | -$XX.XX | $X,XXX.XX
    """
    
    BANK_NAME: ClassVar[str] = "Bank of America"
    
    # Patterns to identify Bank1 statements
    IDENTIFICATION_PATTERNS: ClassVar[List[Pattern]] = [
        re.compile(r'bank\s*of\s*america', re.IGNORECASE),
        re.compile(r'bofa', re.IGNORECASE),
    ]
    
    # Patterns to identify transaction tables in Bank1 statements
    TRANSACTION_TABLE_HEADERS = [
        re.compile(r'date\s+description\s+amount\s+balance', re.IGNORECASE),
        re.compile(r'posting\s+date\s+description\s+amount\s+balance', re.IGNORECASE),
    ]
    
    # Pattern to match date in Bank1 format
    DATE_PATTERN = re.compile(r'\b(\d{1,2})/(\d{1,2})\b')
    
    def extract_account_info(self) -> Dict[str, Any]:
        """
        Extract account information from Bank1 statement
        
        Returns:
            Dictionary containing account information
        """
        account_info = {}
        
        if not self.pages_text:
            return account_info
            
        # Extract account number from first page
        account_pattern = re.compile(r'account\s*(?:number|#)\s*(?::)?\s*([\d*]+)', re.IGNORECASE)
        
        for line in self.pages_text[0].split('\n'):
            match = account_pattern.search(line)
            if match:
                account_info['account_number'] = match.group(1)
                break
                
        # Extract statement period
        period = self.get_statement_period()
        if period:
            account_info['statement_period'] = period
            
        return account_info
    
    def get_statement_period(self) -> Optional[Dict[str, datetime]]:
        """
        Extract statement period from Bank1 statement
        
        Returns:
            Dictionary with 'start_date' and 'end_date' keys, or None if not found
        """
        if not self.pages_text:
            return None
            
        # Look for statement period in first page text
        period_pattern = re.compile(r'(?:statement\s*period|for\s*period)\s*(?:from|:)?\s*([\w\s,]+)\s+(?:to|through|-)\s+([\w\s,]+)', re.IGNORECASE)
        
        for line in self.pages_text[0].split('\n'):
            match = period_pattern.search(line)
            if match:
                start_str, end_str = match.groups()
                start_date = find_date_in_text(start_str)
                end_date = find_date_in_text(end_str)
                
                if start_date and end_date:
                    return {
                        'start_date': start_date,
                        'end_date': end_date
                    }
                    
        return None
    
    def extract_transactions(self) -> List[Dict[str, Any]]:
        """
        Extract transactions from Bank1 statement
        
        Returns:
            List of dictionaries, each representing a transaction
        """
        transactions = []
        current_year = datetime.now().year
        
        # First try to extract from tables
        table_transactions = self._extract_from_tables()
        if table_transactions:
            return self._normalize_transactions(table_transactions)
            
        # If no tables found, try to extract from text
        if not self.pages_text:
            logger.warning("No text content found in PDF")
            return []
            
        # Find transaction sections in the text
        in_transaction_section = False
        transaction_lines = []
        
        for page_text in self.pages_text:
            lines = page_text.split('\n')
            
            for line in lines:
                # Check if this line is a transaction section header
                if any(pattern.search(line) for pattern in self.TRANSACTION_TABLE_HEADERS):
                    in_transaction_section = True
                    continue
                    
                # If we're in a transaction section, process the line
                if in_transaction_section:
                    # Check if the line matches the transaction pattern
                    if self._is_transaction_line(line):
                        transaction_lines.append(line)
                    # Check if we've reached the end of the transaction section
                    elif self._is_end_of_transactions(line):
                        in_transaction_section = False
                        
        # Process transaction lines
        for line in transaction_lines:
            transaction = self._parse_transaction_line(line, current_year)
            if transaction:
                transactions.append(transaction)
                
        return self._normalize_transactions(transactions)
    
    def _extract_from_tables(self) -> List[Dict[str, Any]]:
        """
        Extract transactions from tables in the PDF
        
        Returns:
            List of dictionaries, each representing a transaction
        """
        transactions = []
        current_year = datetime.now().year
        
        if not self.tables:
            return transactions
            
        for table in self.tables:
            # Check if this table is a transaction table by examining the header row
            if not table or len(table) < 2:  # Need at least header + one row
                continue
                
            header_row = [str(cell).lower() if cell else '' for cell in table[0]]
            header_str = ' '.join(header_row)
            
            is_transaction_table = any(pattern.search(header_str) for pattern in self.TRANSACTION_TABLE_HEADERS)
            if not is_transaction_table:
                continue
                
            # Find column indexes
            date_idx = next((i for i, cell in enumerate(header_row) if 'date' in cell and 'due' not in cell), None)
            desc_idx = next((i for i, cell in enumerate(header_row) if 'description' in cell or 'transaction' in cell), None)
            amount_idx = next((i for i, cell in enumerate(header_row) if 'amount' in cell), None)
            balance_idx = next((i for i, cell in enumerate(header_row) if 'balance' in cell), None)
            
            if date_idx is None or desc_idx is None or amount_idx is None:
                continue  # Missing required columns
                
            # Process data rows
            for row in table[1:]:  # Skip header row
                if len(row) <= max(date_idx, desc_idx, amount_idx):
                    continue  # Row too short
                    
                # Extract cell values
                date_cell = row[date_idx] if row[date_idx] else ''
                desc_cell = row[desc_idx] if row[desc_idx] else ''
                amount_cell = row[amount_idx] if row[amount_idx] else ''
                balance_cell = row[balance_idx] if balance_idx is not None and balance_idx < len(row) and row[balance_idx] else ''
                
                # Skip rows without a date or amount
                if not date_cell or not amount_cell:
                    continue
                    
                # Parse date (MM/DD format typically in Bank1)
                date_match = self.DATE_PATTERN.search(str(date_cell))
                if not date_match:
                    continue
                    
                month, day = map(int, date_match.groups())
                date_obj = datetime(current_year, month, day)
                
                # Parse amount
                amount = parse_money_amount(str(amount_cell))
                if amount is None:
                    continue
                    
                # Parse balance if available
                balance = parse_money_amount(str(balance_cell)) if balance_cell else None
                
                # Determine transaction type
                transaction_type = identify_transaction_type(amount)
                
                # Create transaction record
                transaction = {
                    'Date': date_obj.strftime('%Y-%m-%d'),
                    'Description': clean_description(str(desc_cell)),
                    'Type': transaction_type,
                    'Amount': amount,
                    'Balance': balance
                }
                
                transactions.append(transaction)
                
        return transactions
    
    def _is_transaction_line(self, line: str) -> bool:
        """
        Check if a line of text represents a transaction
        
        Args:
            line: Line of text to check
            
        Returns:
            True if the line appears to be a transaction, False otherwise
        """
        # Check if the line starts with a date in MM/DD format
        date_match = self.DATE_PATTERN.match(line.strip())
        if not date_match:
            return False
            
        # Check if the line contains a dollar amount
        amount_pattern = re.compile(r'\$[\d,]+\.\d{2}')
        return bool(amount_pattern.search(line))
    
    def _is_end_of_transactions(self, line: str) -> bool:
        """
        Check if a line indicates the end of the transaction section
        
        Args:
            line: Line of text to check
            
        Returns:
            True if the line appears to be the end of transactions, False otherwise
        """
        end_patterns = [
            re.compile(r'total(?:s)?\b', re.IGNORECASE),
            re.compile(r'beginning\s+balance', re.IGNORECASE),
            re.compile(r'ending\s+balance', re.IGNORECASE),
            re.compile(r'summary\b', re.IGNORECASE),
        ]
        
        return any(pattern.search(line) for pattern in end_patterns)
    
    def _parse_transaction_line(self, line: str, current_year: int) -> Optional[Dict[str, Any]]:
        """
        Parse a transaction line from text
        
        Args:
            line: Line of text containing a transaction
            current_year: Current year to use for the date
            
        Returns:
            Dictionary with transaction details, or None if parsing failed
        """
        # Expected format: MM/DD Description $Amount $Balance
        date_match = self.DATE_PATTERN.search(line)
        if not date_match:
            return None
            
        # Extract date
        month, day = map(int, date_match.groups())
        date_obj = datetime(current_year, month, day)
        
        # Find all dollar amounts in the line
        amount_pattern = re.compile(r'(\(?\$[\d,]+\.\d{2}\)?)')
        amounts = amount_pattern.findall(line)
        
        if len(amounts) < 1:
            return None
            
        # Assume the last amount is the balance (if there are multiple)
        amount_str = amounts[0] if len(amounts) == 1 else amounts[-2]
        balance_str = amounts[-1] if len(amounts) > 1 else None
        
        # Parse amount and balance
        amount = parse_money_amount(amount_str)
        balance = parse_money_amount(balance_str) if balance_str else None
        
        if amount is None:
            return None
            
        # Extract description (everything between the date and the amount)
        date_end = date_match.end()
        amount_start = line.find(amount_str, date_end)
        
        if amount_start > date_end:
            description = line[date_end:amount_start].strip()
        else:
            # If we can't find the amount after the date, use the rest of the line
            description = line[date_end:].strip()
            
        # Determine transaction type
        transaction_type = identify_transaction_type(amount)
        
        return {
            'Date': date_obj.strftime('%Y-%m-%d'),
            'Description': clean_description(description),
            'Type': transaction_type,
            'Amount': amount,
            'Balance': balance
        }
