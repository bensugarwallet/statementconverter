import re
from typing import List, Dict, Any, Optional, ClassVar, Pattern
from datetime import datetime
import logging

from .base_parser import BaseStatementParser
from utils.pdf_utils import find_date_in_text, parse_money_amount, identify_transaction_type, clean_description

logger = logging.getLogger(__name__)

class Bank3StatementParser(BaseStatementParser):
    """
    Parser for Bank3 statements (e.g., Wells Fargo)
    
    Sample format:
    TRANSACTION HISTORY
    MM/DD/YYYY | CHECK # | DESCRIPTION | DEPOSITS | WITHDRAWALS | ENDING DAILY BALANCE
    01/15/2023 | | Deposit | 500.00 | | 1,500.00
    01/17/2023 | 1234 | Check | | 100.00 | 1,400.00
    """
    
    BANK_NAME: ClassVar[str] = "Wells Fargo"
    
    # Patterns to identify Bank3 statements
    IDENTIFICATION_PATTERNS: ClassVar[List[Pattern]] = [
        re.compile(r'wells\s*fargo', re.IGNORECASE),
        re.compile(r'wf\s*bank', re.IGNORECASE),
    ]
    
    # Patterns to identify transaction tables in Bank3 statements
    TRANSACTION_TABLE_HEADERS = [
        re.compile(r'date\s+(?:check\s+)?(?:\w+\s+)*description\s+(?:\w+\s+)*deposits(?:/credits)?\s+(?:\w+\s+)*withdrawals(?:/debits)?\s+(?:\w+\s+)*(?:ending\s+daily\s+)?balance', re.IGNORECASE),
        re.compile(r'transaction\s+history', re.IGNORECASE),
    ]
    
    # Pattern to match date in Bank3 format (MM/DD/YYYY)
    DATE_PATTERN = re.compile(r'\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b')
    
    def extract_account_info(self) -> Dict[str, Any]:
        """
        Extract account information from Bank3 statement
        
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
        Extract statement period from Bank3 statement
        
        Returns:
            Dictionary with 'start_date' and 'end_date' keys, or None if not found
        """
        if not self.pages_text:
            return None
            
        # Look for statement period in first page text
        period_pattern = re.compile(r'(?:statement\s*period|for\s*period|activity\s*for)\s*(?:from|:)?\s*([\w\s,/]+)\s+(?:to|through|-)\s+([\w\s,/]+)', re.IGNORECASE)
        
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
        Extract transactions from Bank3 statement
        
        Returns:
            List of dictionaries, each representing a transaction
        """
        transactions = []
        
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
            
            for i, line in enumerate(lines):
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
            transaction = self._parse_transaction_line(line)
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
            check_idx = next((i for i, cell in enumerate(header_row) if 'check' in cell), None)
            desc_idx = next((i for i, cell in enumerate(header_row) if 'description' in cell), None)
            deposit_idx = next((i for i, cell in enumerate(header_row) if 'deposit' in cell or 'credit' in cell), None)
            withdraw_idx = next((i for i, cell in enumerate(header_row) if 'withdraw' in cell or 'debit' in cell), None)
            balance_idx = next((i for i, cell in enumerate(header_row) if 'balance' in cell), None)
            
            # Need at least date, description, and either deposit or withdrawal columns
            if date_idx is None or desc_idx is None or (deposit_idx is None and withdraw_idx is None):
                continue
                
            # Process data rows
            for row in table[1:]:  # Skip header row
                if len(row) <= max([i for i in [date_idx, desc_idx, deposit_idx, withdraw_idx, balance_idx] if i is not None]):
                    continue  # Row too short
                    
                # Extract cell values
                date_cell = row[date_idx] if row[date_idx] else ''
                desc_cell = row[desc_idx] if row[desc_idx] else ''
                
                # Add check number to description if available
                if check_idx is not None and check_idx < len(row) and row[check_idx]:
                    check_num = row[check_idx]
                    if check_num and str(check_num).strip() and str(check_num).strip() != '0':
                        desc_cell = f"Check #{check_num} - {desc_cell}"
                
                # Parse deposits and withdrawals
                deposit_amount = None
                withdraw_amount = None
                
                if deposit_idx is not None and deposit_idx < len(row):
                    deposit_cell = row[deposit_idx]
                    if deposit_cell:
                        deposit_amount = parse_money_amount(str(deposit_cell))
                        
                if withdraw_idx is not None and withdraw_idx < len(row):
                    withdraw_cell = row[withdraw_idx]
                    if withdraw_cell:
                        withdraw_amount = parse_money_amount(str(withdraw_cell))
                
                # Determine the transaction amount (deposit or withdrawal)
                amount = None
                if deposit_amount is not None and deposit_amount != 0:
                    amount = deposit_amount  # Deposit (positive)
                elif withdraw_amount is not None and withdraw_amount != 0:
                    amount = -abs(withdraw_amount)  # Withdrawal (negative)
                
                # Skip rows without a valid amount
                if amount is None:
                    continue
                
                # Parse date (MM/DD/YYYY format for Bank3)
                date_match = self.DATE_PATTERN.search(str(date_cell))
                if not date_match:
                    continue
                    
                month, day, year = date_match.groups()
                if len(year) == 2:
                    year = f"20{year}" if int(year) < 50 else f"19{year}"
                    
                date_obj = datetime(int(year), int(month), int(day))
                
                # Parse balance if available
                balance = None
                if balance_idx is not None and balance_idx < len(row) and row[balance_idx]:
                    balance = parse_money_amount(str(row[balance_idx]))
                
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
        # Check if the line starts with a date in MM/DD/YYYY format
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
            re.compile(r'ending\s+balance', re.IGNORECASE),
            re.compile(r'totals?\s+for\s+this\s+(?:period|statement)', re.IGNORECASE),
            re.compile(r'summary\s+of\s+(?:fees|charges)', re.IGNORECASE),
            re.compile(r'interest\s+summary', re.IGNORECASE),
        ]
        
        return any(pattern.search(line) for pattern in end_patterns)
    
    def _parse_transaction_line(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Parse a transaction line from text
        
        Args:
            line: Line of text containing a transaction
            
        Returns:
            Dictionary with transaction details, or None if parsing failed
        """
        # Expected format: MM/DD/YYYY [Check #] Description Deposit Withdrawal Balance
        date_match = self.DATE_PATTERN.search(line)
        if not date_match:
            return None
            
        # Extract date
        month, day, year = date_match.groups()
        if len(year) == 2:
            year = f"20{year}" if int(year) < 50 else f"19{year}"
            
        date_obj = datetime(int(year), int(month), int(day))
        
        # Find all dollar amounts in the line
        amount_pattern = re.compile(r'(\$[\d,]+\.\d{2})')
        amounts = amount_pattern.findall(line)
        
        if len(amounts) < 1:
            return None
            
        # Extract check number if present
        check_pattern = re.compile(r'\b(?:check|chk)\s*(?:#|no)?\s*(\d+)\b', re.IGNORECASE)
        check_match = check_pattern.search(line)
        check_number = check_match.group(1) if check_match else None
        
        # Determine which amount is deposit, withdrawal, and balance
        # For Wells Fargo, typically if there's one amount, it's the transaction amount
        # If there are two, first is transaction, second is balance
        # If there are three, they are deposit, withdrawal, balance
        
        deposit_amount = None
        withdraw_amount = None
        balance = None
        
        if len(amounts) == 1:
            # Single amount - determine if it's a deposit or withdrawal
            amount_str = amounts[0]
            if 'deposit' in line.lower() or 'credit' in line.lower():
                deposit_amount = parse_money_amount(amount_str)
            else:
                withdraw_amount = parse_money_amount(amount_str)
        elif len(amounts) == 2:
            # First amount is transaction, second is balance
            amount_str = amounts[0]
            balance_str = amounts[1]
            
            if 'deposit' in line.lower() or 'credit' in line.lower():
                deposit_amount = parse_money_amount(amount_str)
            else:
                withdraw_amount = parse_money_amount(amount_str)
                
            balance = parse_money_amount(balance_str)
        elif len(amounts) >= 3:
            # Try to determine which is which based on position
            # For Wells Fargo: first deposit, then withdrawal, then balance
            deposit_str = amounts[0]
            withdraw_str = amounts[1]
            balance_str = amounts[2]
            
            deposit_amount = parse_money_amount(deposit_str)
            withdraw_amount = parse_money_amount(withdraw_str)
            balance = parse_money_amount(balance_str)
            
        # Determine the transaction amount
        amount = None
        if deposit_amount is not None and deposit_amount != 0:
            amount = deposit_amount
        elif withdraw_amount is not None and withdraw_amount != 0:
            amount = -abs(withdraw_amount)
            
        if amount is None:
            return None
            
        # Extract description
        date_end = date_match.end()
        desc_end = line.find('$', date_end) if '$' in line[date_end:] else len(line)
        description = line[date_end:desc_end].strip()
        
        # Add check number to description if found
        if check_number and 'check' not in description.lower():
            description = f"Check #{check_number} - {description}"
            
        # Determine transaction type
        transaction_type = identify_transaction_type(amount)
        
        return {
            'Date': date_obj.strftime('%Y-%m-%d'),
            'Description': clean_description(description),
            'Type': transaction_type,
            'Amount': amount,
            'Balance': balance
        }
