import re
from typing import List, Dict, Any, Optional, ClassVar, Pattern
from datetime import datetime
import logging

from .base_parser import BaseStatementParser
from utils.pdf_utils import find_date_in_text, parse_money_amount, identify_transaction_type, clean_description

logger = logging.getLogger(__name__)

class Bank2StatementParser(BaseStatementParser):
    """
    Parser for Bank2 statements (e.g., Chase Bank)
    
    Sample format:
    TRANSACTION DETAIL
    DATE | DESCRIPTION | WITHDRAWALS | DEPOSITS | BALANCE
    MM/DD | Transaction description | $XX.XX | | $X,XXX.XX
    MM/DD | Deposit description | | $XX.XX | $X,XXX.XX
    """
    
    BANK_NAME: ClassVar[str] = "Chase Bank"
    
    # Patterns to identify Bank2 statements
    IDENTIFICATION_PATTERNS: ClassVar[List[Pattern]] = [
        re.compile(r'chase', re.IGNORECASE),
        re.compile(r'jpmorgan', re.IGNORECASE),
    ]
    
    # Patterns to identify transaction tables in Bank2 statements
    TRANSACTION_TABLE_HEADERS = [
        re.compile(r'date\s+(?:\w+\s+)*description\s+(?:\w+\s+)*withdrawals(?:\([-\$]\))?\s+(?:\w+\s+)*deposits(?:\([+\$]\))?\s+(?:\w+\s+)*balance', re.IGNORECASE),
        re.compile(r'date\s+details\s+amount\s+balance', re.IGNORECASE),
    ]
    
    # Pattern to match date in Bank2 format
    DATE_PATTERN = re.compile(r'\b(\d{2})/(\d{2})\b')
    
    def extract_account_info(self) -> Dict[str, Any]:
        """
        Extract account information from Bank2 statement
        
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
        Extract statement period from Bank2 statement
        
        Returns:
            Dictionary with 'start_date' and 'end_date' keys, or None if not found
        """
        if not self.pages_text:
            return None
            
        # Look for statement period in first page text
        period_pattern = re.compile(r'(?:statement\s*period|for\s*the\s*period|from)\s*:?\s*([\w\s,]+)\s+(?:to|through|-)\s+([\w\s,]+)', re.IGNORECASE)
        
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
        Extract transactions from Bank2 statement
        
        Returns:
            List of dictionaries, each representing a transaction
        """
        transactions = []
        statement_year = datetime.now().year
        
        # Check for statement period to get the year
        period = self.get_statement_period()
        if period and 'end_date' in period:
            statement_year = period['end_date'].year
            
        # First try to extract from tables
        table_transactions = self._extract_from_tables(statement_year)
        if table_transactions:
            return self._normalize_transactions(table_transactions)
            
        # If no tables found, try to extract from text
        if not self.pages_text:
            logger.warning("No text content found in PDF")
            return []
            
        # Find transaction sections in the text
        for page_idx, page_text in enumerate(self.pages_text):
            # Find where the transaction section starts
            transaction_section_match = None
            for pattern in self.TRANSACTION_TABLE_HEADERS:
                transaction_section_match = pattern.search(page_text)
                if transaction_section_match:
                    break
                    
            if not transaction_section_match:
                continue
                
            # Get the text starting from the transaction header
            start_pos = transaction_section_match.start()
            transaction_text = page_text[start_pos:]
            
            # Process the transaction section line by line
            lines = transaction_text.split('\n')
            header_idx = 0  # First line is the header we matched
            
            for i in range(1, len(lines)):  # Start after the header
                line = lines[i].strip()
                
                # Check if this is a transaction line
                if self._is_transaction_line(line):
                    transaction = self._parse_transaction_line(line, statement_year)
                    if transaction:
                        transactions.append(transaction)
                        
                # Check if we've reached the end of the transaction section
                if self._is_end_of_transactions(line):
                    break
                    
        return self._normalize_transactions(transactions)
    
    def _extract_from_tables(self, statement_year: int) -> List[Dict[str, Any]]:
        """
        Extract transactions from tables in the PDF
        
        Args:
            statement_year: Year of the statement
            
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
            desc_idx = next((i for i, cell in enumerate(header_row) if 'description' in cell or 'details' in cell), None)
            withdraw_idx = next((i for i, cell in enumerate(header_row) if 'withdraw' in cell or 'debit' in cell), None)
            deposit_idx = next((i for i, cell in enumerate(header_row) if 'deposit' in cell or 'credit' in cell), None)
            amount_idx = next((i for i, cell in enumerate(header_row) if 'amount' in cell), None)
            balance_idx = next((i for i, cell in enumerate(header_row) if 'balance' in cell), None)
            
            # Need at least date, description, and some form of amount column
            if date_idx is None or desc_idx is None or (withdraw_idx is None and deposit_idx is None and amount_idx is None):
                continue
                
            # Process data rows
            for row in table[1:]:  # Skip header row
                if len(row) <= max([i for i in [date_idx, desc_idx, withdraw_idx, deposit_idx, amount_idx, balance_idx] if i is not None]):
                    continue  # Row too short
                    
                # Extract cell values
                date_cell = row[date_idx] if row[date_idx] else ''
                desc_cell = row[desc_idx] if row[desc_idx] else ''
                
                # Get amount (either from amount column or from withdraw/deposit columns)
                amount = None
                if amount_idx is not None:
                    amount_cell = row[amount_idx] if row[amount_idx] else ''
                    amount = parse_money_amount(str(amount_cell))
                else:
                    # Try withdraw and deposit columns
                    withdraw_cell = row[withdraw_idx] if withdraw_idx is not None and withdraw_idx < len(row) and row[withdraw_idx] else ''
                    deposit_cell = row[deposit_idx] if deposit_idx is not None and deposit_idx < len(row) and row[deposit_idx] else ''
                    
                    withdraw_amount = parse_money_amount(str(withdraw_cell))
                    deposit_amount = parse_money_amount(str(deposit_cell))
                    
                    if withdraw_amount is not None and withdraw_amount != 0:
                        amount = -abs(withdraw_amount)  # Ensure withdrawals are negative
                    elif deposit_amount is not None and deposit_amount != 0:
                        amount = abs(deposit_amount)  # Ensure deposits are positive
                
                # Skip rows without a valid amount
                if amount is None:
                    continue
                
                # Parse date (MM/DD format typically in Bank2)
                date_match = self.DATE_PATTERN.search(str(date_cell))
                if not date_match:
                    continue
                    
                month, day = map(int, date_match.groups())
                date_obj = datetime(statement_year, month, day)
                
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
            re.compile(r'ending\s+balance', re.IGNORECASE),
            re.compile(r'daily\s+ending\s+balance', re.IGNORECASE),
            re.compile(r'service\s+fees?\s+summary', re.IGNORECASE),
            re.compile(r'service\s+charge\s+summary', re.IGNORECASE),
            re.compile(r'total(?:s)?\b', re.IGNORECASE),
        ]
        
        return any(pattern.search(line) for pattern in end_patterns)
    
    def _parse_transaction_line(self, line: str, statement_year: int) -> Optional[Dict[str, Any]]:
        """
        Parse a transaction line from text
        
        Args:
            line: Line of text containing a transaction
            statement_year: Year of the statement
            
        Returns:
            Dictionary with transaction details, or None if parsing failed
        """
        # Expected formats:
        # MM/DD Description $XX.XX (withdrawal) $X,XXX.XX (balance)
        # MM/DD Description $XX.XX (deposit) $X,XXX.XX (balance)
        
        date_match = self.DATE_PATTERN.search(line)
        if not date_match:
            return None
            
        # Extract date
        month, day = map(int, date_match.groups())
        date_obj = datetime(statement_year, month, day)
        
        # Find all dollar amounts in the line
        amount_pattern = re.compile(r'(\(?\$[\d,]+\.\d{2}\)?)')
        amounts = amount_pattern.findall(line)
        
        if len(amounts) < 1:
            return None
            
        # For Chase format, we need to determine if this is a withdrawal or deposit
        # Look for keywords that indicate the transaction type
        is_withdrawal = any(kw in line.lower() for kw in ['withdrawal', 'debit', 'purchase', 'payment', 'fee', 'check #'])
        is_deposit = any(kw in line.lower() for kw in ['deposit', 'credit', 'interest', 'refund'])
        
        # If we have multiple dollar amounts and can't determine from keywords,
        # make an educated guess based on position
        amount_str = None
        balance_str = None
        
        if len(amounts) == 1:
            amount_str = amounts[0]
            # Can't determine balance with just one amount
        elif len(amounts) >= 2:
            # For Chase, typically the first amount is the transaction and the last is the balance
            if is_withdrawal:
                amount_str = amounts[0]  # First amount is withdrawal
            elif is_deposit:
                amount_str = amounts[0]  # First amount is deposit
            else:
                # If we can't determine type, assume first amount is transaction
                amount_str = amounts[0]
                
            # Last amount is typically the balance
            balance_str = amounts[-1]
            
        # Parse amount
        amount = parse_money_amount(amount_str)
        if amount is None:
            return None
            
        # If we determined it's a withdrawal but the amount is positive, make it negative
        if is_withdrawal and amount > 0:
            amount = -amount
        # If we determined it's a deposit but the amount is negative, make it positive
        elif is_deposit and amount < 0:
            amount = abs(amount)
            
        # Parse balance if available
        balance = parse_money_amount(balance_str) if balance_str else None
        
        # Extract description (everything between the date and the amount)
        date_end = date_match.end()
        amount_start = line.find(amount_str, date_end) if amount_str else -1
        
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
