import re
from typing import List, Dict, Any, Optional, ClassVar, Pattern
from datetime import datetime
import logging

from .base_parser import BaseStatementParser
from utils.pdf_utils import find_date_in_text, parse_money_amount, identify_transaction_type, clean_description

logger = logging.getLogger(__name__)

class NZBankStatementParser(BaseStatementParser):
    """
    Parser for New Zealand bank statements (e.g., ANZ, ASB, credit cards)
    
    Sample formats:
    1. Credit Card:
       Date | Card Number | Description | Debit (NZ$) | Credit (NZ$)
    
    2. ASB:
       Date | Transaction | Debit/Withdrawal $ | Deposit $ | Balance $
    
    3. ANZ:
       Date | Transaction type and details | Withdrawals | Deposits | Balance
    """
    
    BANK_NAME: ClassVar[str] = "NZ Bank"
    
    # Patterns to identify NZ bank statements
    IDENTIFICATION_PATTERNS: ClassVar[List[Pattern]] = [
        re.compile(r'ANZ', re.IGNORECASE),
        re.compile(r'ASB', re.IGNORECASE),
        re.compile(r'Westpac', re.IGNORECASE),
        re.compile(r'Kiwibank', re.IGNORECASE),
        re.compile(r'BNZ', re.IGNORECASE),
        re.compile(r'Debit\s*\(NZ\$\)|Credit\s*\(NZ\$\)', re.IGNORECASE),
        re.compile(r'New\s*Zealand', re.IGNORECASE),
    ]
    
    # Patterns to identify transaction tables in NZ bank statements
    TRANSACTION_TABLE_HEADERS = [
        # Credit card format
        re.compile(r'Date\s+Card\s*Number\s+Description\s+Debit\s*\(NZ\$\)\s+Credit\s*\(NZ\$\)', re.IGNORECASE),
        # ASB format
        re.compile(r'Date\s+Transaction\s+Debit/Withdrawal\s+\$\s+Deposit\s+\$\s+Balance\s+\$', re.IGNORECASE),
        # ANZ format
        re.compile(r'Date\s+Transaction\s+type\s+and\s+details\s+Withdrawals\s+Deposits\s+Balance', re.IGNORECASE),
        # ANZ format variations
        re.compile(r'Date\s+Details\s+Withdrawals\s+Deposits\s+Balance', re.IGNORECASE),
        re.compile(r'Date\s+Details\s+Money\s+Out\s+Money\s+In\s+Balance', re.IGNORECASE),
        re.compile(r'Date\s+Particulars\s+Code\s+Reference\s+Amount\s+Balance', re.IGNORECASE),
        re.compile(r'Date\s+(?:Transactions|Details|Particulars)\s+(?:Amount|\$)', re.IGNORECASE),
        # Westpac specific patterns
        re.compile(r'DATE\s+TYPE\s+NAME OF OTHER PARTY\s+TRANSACTION PARTICULARS\s+MONEY OUT\s+MONEY IN\s+BALANCE', re.IGNORECASE),
        re.compile(r'Your transactions', re.IGNORECASE),  # Westpac section header
        # Kiwibank specific patterns
        re.compile(r'Date\s+Transaction\s+Withdrawals\s+Deposits\s+Balance', re.IGNORECASE),
        re.compile(r'Account Name:', re.IGNORECASE),  # Kiwibank account section header
        re.compile(r'Statement Period:', re.IGNORECASE),  # Kiwibank statement period header
        # BNZ specific patterns
        re.compile(r'Date\s+Particulars\s+Type\s+Withdrawals\s+Deposits\s+Balance', re.IGNORECASE),
        re.compile(r'OPENING BALANCE', re.IGNORECASE),  # BNZ section header
        re.compile(r'STATEMENT NO', re.IGNORECASE),  # BNZ statement number header
        # Generic formats
        re.compile(r'Date\s+(?:\w+\s+)*Description\s+(?:\w+\s+)*Amount', re.IGNORECASE),
        re.compile(r'Transaction\s+details', re.IGNORECASE),
        re.compile(r'Opening\s+Balance', re.IGNORECASE),
    ]
    
    # Multiple date patterns to match various formats
    DATE_PATTERNS = [
        # DD/MM/YYYY
        re.compile(r'\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b'),
        # DD/MM/YY
        re.compile(r'\b(\d{1,2})/(\d{1,2})/(\d{2})\b'),
        # DD Month
        re.compile(r'\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\b', re.IGNORECASE),
    ]
    
    # Dictionary to convert month abbreviations to numbers
    MONTH_MAP = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6, 
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    
    def extract_account_info(self) -> Dict[str, Any]:
        """
        Extract account information from NZ bank statement
        
        Returns:
            Dictionary containing account information
        """
        account_info = {}
        
        if not self.pages_text:
            return account_info
            
        # Extract account number
        account_patterns = [
            re.compile(r'account\s*(?:no|number|#)\s*(?::)?\s*([\d\-]+)', re.IGNORECASE),
            re.compile(r'account\s*number\s*([\d\-]+)', re.IGNORECASE),
        ]
        
        for pattern in account_patterns:
            for page_text in self.pages_text:
                for line in page_text.split('\n'):
                    match = pattern.search(line)
                    if match:
                        account_info['account_number'] = match.group(1)
                        break
                if 'account_number' in account_info:
                    break
            if 'account_number' in account_info:
                break
                
        # Extract statement period
        period = self.get_statement_period()
        if period:
            account_info['statement_period'] = period
            
        return account_info
    
    def get_statement_period(self) -> Optional[Dict[str, datetime]]:
        """
        Extract statement period from NZ bank statement
        
        Returns:
            Dictionary with 'start_date' and 'end_date' keys, or None if not found
        """
        if not self.pages_text:
            return None
            
        # Look for statement period in text
        period_patterns = [
            re.compile(r'statement\s*period\s*:?\s*([\w\s,/]+)\s+(?:to|through|-)\s+([\w\s,/]+)', re.IGNORECASE),
            re.compile(r'period\s*:?\s*([\w\s,/]+)\s+(?:to|through|-)\s+([\w\s,/]+)', re.IGNORECASE),
            re.compile(r'statement\s*(?:period|from)\s*:?\s*([\w\s,/]+)\s+(?:to|through|-)\s+([\w\s,/]+)', re.IGNORECASE),
        ]
        
        for page_text in self.pages_text:
            for pattern in period_patterns:
                match = pattern.search(page_text)
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
        Extract transactions from NZ bank statement
        
        Returns:
            List of dictionaries, each representing a transaction
        """
        transactions = []
        statement_year = datetime.now().year
        
        # Check for statement period to get the year
        period = self.get_statement_period()
        if period and 'end_date' in period:
            statement_year = period['end_date'].year
            logger.info(f"Statement period detected: year {statement_year}")
        
        # Log some information about what we're processing
        logger.info(f"Processing statement with {len(self.pages_text)} pages of text and {len(self.tables)} tables")
        
        # Identify bank type - supports ANZ, Westpac, Kiwibank, BNZ
        is_anz = any('ANZ' in page for page in self.pages_text)
        is_westpac = any('Westpac' in page for page in self.pages_text)
        is_kiwibank = any('Kiwibank' in page or 'Kiwi bank' in page or 'Kiwi Bank' in page for page in self.pages_text)
        is_bnz = any('BNZ' in page or 'Bank of New Zealand' in page for page in self.pages_text)
        
        # Log bank identification
        detected_bank = None
        for page in self.pages_text:
            if 'ANZ' in page:
                is_anz = True
                detected_bank = "ANZ"
                # Log a snippet of the page to help with debugging
                snippet = page.split('\n')[0:5]  # First 5 lines
                logger.debug(f"ANZ text snippet: {' '.join(snippet)}")
                break
            elif 'Westpac' in page:
                is_westpac = True
                detected_bank = "Westpac"
                snippet = page.split('\n')[0:5]
                logger.debug(f"Westpac text snippet: {' '.join(snippet)}")
                break
            elif any(bank in page for bank in ['Kiwibank', 'Kiwi bank', 'Kiwi Bank']):
                is_kiwibank = True
                detected_bank = "Kiwibank"
                snippet = page.split('\n')[0:5]
                logger.debug(f"Kiwibank text snippet: {' '.join(snippet)}")
                break
            elif 'BNZ' in page or 'Bank of New Zealand' in page:
                is_bnz = True
                detected_bank = "BNZ"
                snippet = page.split('\n')[0:5]
                logger.debug(f"BNZ text snippet: {' '.join(snippet)}")
                break
                
        if detected_bank:
            logger.info(f"Detected {detected_bank} bank statement format")
            
        # For multi-page statements, make sure we have tables for all pages
        # Sometimes pdfplumber doesn't detect tables correctly on all pages
        if (is_anz or is_westpac or is_kiwibank or is_bnz) and len(self.pages_text) > 1 and len(self.tables) < len(self.pages_text):
            logger.warning(f"Bank statement has {len(self.pages_text)} pages but only {len(self.tables)} tables detected")
            logger.info(f"Attempting to extract all transactions from text for multi-page statement")
            text_transactions = self._extract_from_text(statement_year, force=True)
            if text_transactions:
                logger.info(f"Successfully extracted {len(text_transactions)} transactions from text for multi-page statement")
                return self._normalize_transactions(text_transactions)
            
        # For Westpac, Kiwibank, and BNZ, their table structures are specific
        # Try specific extraction first if we detected one of these banks
        if detected_bank and detected_bank != "ANZ":
            logger.info(f"Using {detected_bank}-specific extraction logic")
            text_transactions = self._extract_from_text(statement_year, force=True)
            if text_transactions:
                logger.info(f"Successfully extracted {len(text_transactions)} transactions using {detected_bank}-specific logic")
                return self._normalize_transactions(text_transactions)
            
        # First try to extract from tables
        table_transactions = self._extract_from_tables(statement_year)
        if table_transactions:
            logger.info(f"Successfully extracted {len(table_transactions)} transactions from tables")
            return self._normalize_transactions(table_transactions)
            
        # Try to extract from text using our dedicated method
        text_transactions = self._extract_from_text(statement_year)
        if text_transactions:
            return self._normalize_transactions(text_transactions)
            
        # If we get here, we couldn't extract transactions
        logger.warning("Could not extract any transactions from the statement")
        return []
        
    def _extract_from_text(self, statement_year: int, force: bool = False) -> List[Dict[str, Any]]:
        """
        Extract transactions from text content of the PDF
        
        Args:
            statement_year: Year of the statement
            force: If True, try harder to extract transactions even if format is unclear
            
        Returns:
            List of dictionaries, each representing a transaction
        """
        transactions = []
        
        if not self.pages_text:
            logger.warning("No text content found in PDF")
            return []
            
        # Check if this is an ANZ statement
        is_anz = any('ANZ' in page for page in self.pages_text)
            
        # Find transaction sections in the text
        in_transaction_section = False
        transaction_lines = []
        transaction_section_count = 0
        
        for page_idx, page_text in enumerate(self.pages_text):
            lines = page_text.split('\n')
            logger.debug(f"Processing page {page_idx+1} with {len(lines)} lines")
            
            # For ANZ statements, check for specific patterns
            if is_anz and not in_transaction_section:
                logger.debug("Looking for ANZ transaction section headers")
                # For ANZ, try to find date patterns followed by transaction codes
                date_followed_by_code = False
                for i in range(len(lines)-1):
                    if any(pattern.match(lines[i].strip()) for pattern in self.DATE_PATTERNS):
                        next_line = lines[i+1] if i+1 < len(lines) else ""
                        if re.search(r'\b(BP|TFR|DD|DC|AP|ATM|POS|VT|EFTPOS)\b', next_line):
                            date_followed_by_code = True
                            logger.info(f"Found ANZ transaction section on page {page_idx+1}")
                            in_transaction_section = True
                            break
                            
            # Enhanced ANZ detection for multi-page statements
            if is_anz and force and not in_transaction_section:
                # For ANZ multi-page statements, also check for date patterns that might indicate transactions
                # even if they don't have the standard header
                for i, line in enumerate(lines):
                    if self._is_transaction_line(line):
                        logger.info(f"Force mode: Found potential ANZ transaction on page {page_idx+1} without header")
                        in_transaction_section = True
                        transaction_lines.append(line)
                        # Check the next few lines too, they might be transactions without headers
                        for j in range(i+1, min(i+20, len(lines))):
                            if self._is_transaction_line(lines[j]):
                                transaction_lines.append(lines[j])
                            
            # Normal transaction section detection
            for line in lines:
                # Skip empty lines
                if not line.strip():
                    continue
                    
                # Check if this line is a transaction section header
                if any(pattern.search(line) for pattern in self.TRANSACTION_TABLE_HEADERS):
                    logger.debug(f"Found transaction section header: {line[:40]}...")
                    in_transaction_section = True
                    transaction_section_count += 1
                    continue
                    
                # If we're in a transaction section, process the line
                if in_transaction_section:
                    # Check if the line matches a transaction pattern
                    if self._is_transaction_line(line):
                        transaction_lines.append(line)
                        logger.debug(f"Found transaction line: {line[:40]}...")
                    # Check if we've reached the end of the transaction section
                    elif self._is_end_of_transactions(line):
                        logger.debug(f"End of transaction section: {line[:40]}...")
                        in_transaction_section = False
                        
            # For NZ banks, each page can have its own transaction section
            # Reset the flag at the end of each page for multi-page statements
            if is_anz or is_westpac or is_kiwibank or is_bnz:
                in_transaction_section = False
        
        logger.info(f"Found {transaction_section_count} transaction sections with {len(transaction_lines)} potential transaction lines")
                         
        # Process transaction lines
        for line in transaction_lines:
            transaction = self._parse_transaction_line(line, statement_year)
            if transaction:
                transactions.append(transaction)
                
        return transactions
    
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
            logger.warning("No tables found in PDF")
            return transactions
            
        # Log table information for debugging
        for i, table in enumerate(self.tables):
            if table and len(table) > 0:
                header_row = ' '.join(str(cell) for cell in table[0]) if table[0] else "Empty"
                logger.debug(f"Table {i+1} has {len(table)} rows. Header: {header_row[:60]}...")
            else:
                logger.debug(f"Table {i+1} is empty or has no rows")
        
        # Check if this is an ANZ statement
        is_anz = any('ANZ' in ' '.join(str(cell) for cell in table[0]) for table in self.tables 
                    if table and len(table) > 0)
        
        if is_anz:
            logger.info("Detected ANZ statement tables")
        
        # Process each table
        for table_idx, table in enumerate(self.tables):
            # Check if this table is a transaction table by examining the header row
            if not table or len(table) < 2:  # Need at least header + one row
                continue
                
            header_row = [str(cell).lower() if cell else '' for cell in table[0]]
            header_str = ' '.join(header_row)
            
            is_transaction_table = any(pattern.search(header_str) for pattern in self.TRANSACTION_TABLE_HEADERS)
            if not is_transaction_table:
                continue
                
            # Determine the format type based on header
            is_credit_card = 'card number' in header_str and ('debit (nz$)' in header_str or 'credit (nz$)' in header_str)
            is_asb = 'debit/withdrawal' in header_str and 'deposit' in header_str
            
            # ANZ has several formats
            is_anz_standard = 'transaction type and details' in header_str and 'withdrawals' in header_str and 'deposits' in header_str
            is_anz_simplified = 'details' in header_str and 'withdrawals' in header_str and 'deposits' in header_str
            is_anz_newer = 'details' in header_str and 'money out' in header_str and 'money in' in header_str
            is_anz_alternate = 'particulars' in header_str and 'code' in header_str and 'reference' in header_str
            
            is_anz = is_anz_standard or is_anz_simplified or is_anz_newer or is_anz_alternate or is_anz
            
            if is_anz:
                logger.info(f"Processing ANZ statement table {table_idx+1} with format: {header_str[:60]}...")
            
            # Find column indexes based on format
            date_idx = next((i for i, cell in enumerate(header_row) if 'date' in cell), None)
            desc_idx = None
            debit_idx = None
            credit_idx = None
            withdraw_idx = None
            deposit_idx = None
            balance_idx = None
            
            if is_credit_card:
                # Credit card format
                desc_idx = next((i for i, cell in enumerate(header_row) if 'description' in cell), None)
                debit_idx = next((i for i, cell in enumerate(header_row) if 'debit' in cell), None)
                credit_idx = next((i for i, cell in enumerate(header_row) if 'credit' in cell), None)
            elif is_asb:
                # ASB format
                desc_idx = next((i for i, cell in enumerate(header_row) if 'transaction' in cell), None)
                withdraw_idx = next((i for i, cell in enumerate(header_row) if 'debit/withdrawal' in cell), None)
                deposit_idx = next((i for i, cell in enumerate(header_row) if 'deposit' in cell), None)
                balance_idx = next((i for i, cell in enumerate(header_row) if 'balance' in cell), None)
            elif is_anz:
                # ANZ format - supports multiple variations
                # Description column
                if is_anz_standard:
                    desc_idx = next((i for i, cell in enumerate(header_row) if 'transaction type and details' in cell), None)
                else:
                    desc_idx = next((i for i, cell in enumerate(header_row) 
                                    if any(term in cell for term in ['details', 'particulars', 'reference', 'description'])), None)
                
                # Withdraw column
                if is_anz_newer:
                    withdraw_idx = next((i for i, cell in enumerate(header_row) if 'money out' in cell), None)
                else:
                    withdraw_idx = next((i for i, cell in enumerate(header_row) 
                                       if any(term in cell for term in ['withdrawal', 'withdrawals', 'money out', 'amount'])), None)
                
                # Deposit column
                if is_anz_newer:
                    deposit_idx = next((i for i, cell in enumerate(header_row) if 'money in' in cell), None)
                else:
                    deposit_idx = next((i for i, cell in enumerate(header_row) 
                                       if any(term in cell for term in ['deposit', 'deposits', 'money in'])), None)
                
                # Balance column is usually the last column
                balance_idx = next((i for i, cell in enumerate(header_row) if 'balance' in cell), None)
                
                # If we couldn't find specific columns, try to make a best guess for ANZ
                if not desc_idx:
                    # For ANZ, if all else fails, try to find the description column
                    for i, cell in enumerate(header_row):
                        if ('particulars' in cell or 'reference' in cell or 'details' in cell or 'code' in cell):
                            desc_idx = i
                            break
                
                # Handle the specialized ANZ particulars format
                if is_anz_alternate:
                    # This has a specialized format with separate columns for particulars, code, reference
                    particulars_idx = next((i for i, cell in enumerate(header_row) if 'particulars' in cell), None)
                    code_idx = next((i for i, cell in enumerate(header_row) if 'code' in cell), None)
                    reference_idx = next((i for i, cell in enumerate(header_row) if 'reference' in cell), None)
                    
                    # Use custom function to handle this case
                    logger.info("Detected ANZ specialized format with particulars/code/reference")
            else:
                # Generic format - try to identify columns by common names
                desc_idx = next((i for i, cell in enumerate(header_row) 
                               if any(term in cell for term in ['description', 'details', 'transaction', 'particulars', 'reference'])), None)
                
                debit_idx = next((i for i, cell in enumerate(header_row) 
                               if any(term in cell for term in ['debit', 'withdrawal', 'withdrawals', 'money out', 'payment', 'payments'])), None)
                
                credit_idx = next((i for i, cell in enumerate(header_row) 
                                if any(term in cell for term in ['credit', 'deposit', 'deposits', 'money in'])), None)
                
                balance_idx = next((i for i, cell in enumerate(header_row) if 'balance' in cell), None)
                
            # Log the detected columns
            logger.debug(f"Detected columns: date_idx={date_idx}, desc_idx={desc_idx}, debit_idx={debit_idx}, "
                        f"credit_idx={credit_idx}, withdraw_idx={withdraw_idx}, deposit_idx={deposit_idx}, balance_idx={balance_idx}")
            
            # If we couldn't find required columns, skip this table
            if date_idx is None or (
                (desc_idx is None) and 
                (debit_idx is None and credit_idx is None and withdraw_idx is None and deposit_idx is None)
            ):
                continue
                
            # Process data rows
            for row in table[1:]:  # Skip header row
                if len(row) <= max([i for i in [date_idx, desc_idx, debit_idx, credit_idx, withdraw_idx, deposit_idx, balance_idx] if i is not None]):
                    continue  # Row too short
                    
                # Extract cell values
                date_cell = row[date_idx] if row[date_idx] else ''
                desc_cell = row[desc_idx] if desc_idx is not None and desc_idx < len(row) and row[desc_idx] else ''
                
                # Parse amounts based on format
                amount = None
                debit_amount = None
                credit_amount = None
                balance = None
                
                if is_credit_card:
                    # Credit card format: separate debit and credit columns
                    if debit_idx is not None and debit_idx < len(row) and row[debit_idx]:
                        debit_amount = parse_money_amount(str(row[debit_idx]))
                        if debit_amount is not None and debit_amount > 0:
                            amount = -debit_amount  # Make debits negative
                    
                    if credit_idx is not None and credit_idx < len(row) and row[credit_idx]:
                        credit_amount = parse_money_amount(str(row[credit_idx]))
                        if credit_amount is not None and credit_amount > 0:
                            amount = credit_amount  # Credits are positive
                            
                elif is_asb or is_anz:
                    # ASB/ANZ format: withdrawal and deposit columns
                    if withdraw_idx is not None and withdraw_idx < len(row) and row[withdraw_idx]:
                        withdraw_amount = parse_money_amount(str(row[withdraw_idx]))
                        if withdraw_amount is not None and withdraw_amount > 0:
                            amount = -withdraw_amount  # Make withdrawals negative
                    
                    if deposit_idx is not None and deposit_idx < len(row) and row[deposit_idx]:
                        deposit_amount = parse_money_amount(str(row[deposit_idx]))
                        if deposit_amount is not None and deposit_amount > 0:
                            amount = deposit_amount  # Deposits are positive
                            
                    if balance_idx is not None and balance_idx < len(row) and row[balance_idx]:
                        balance = parse_money_amount(str(row[balance_idx]))
                else:
                    # Generic format: try both approaches
                    if debit_idx is not None and debit_idx < len(row) and row[debit_idx]:
                        debit_amount = parse_money_amount(str(row[debit_idx]))
                        if debit_amount is not None and debit_amount > 0:
                            amount = -debit_amount  # Make debits negative
                    
                    if credit_idx is not None and credit_idx < len(row) and row[credit_idx]:
                        credit_amount = parse_money_amount(str(row[credit_idx]))
                        if credit_amount is not None and credit_amount > 0:
                            amount = credit_amount  # Credits are positive
                            
                    if balance_idx is not None and balance_idx < len(row) and row[balance_idx]:
                        balance = parse_money_amount(str(row[balance_idx]))
                
                # Skip rows without a valid amount
                if amount is None:
                    continue
                
                # Parse date based on format
                date_obj = self._parse_date(str(date_cell), statement_year)
                if not date_obj:
                    continue
                
                # Create transaction record
                transaction = {
                    'Date': date_obj.strftime('%Y-%m-%d'),
                    'Description': clean_description(str(desc_cell)),
                    'Type': identify_transaction_type(amount),
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
        # Skip empty lines
        if not line.strip():
            return False
            
        # Skip lines that are clearly headers or footers
        if any(header in line.lower() for header in ['page', 'statement', 'balance brought forward', 'closing balance']):
            return False
            
        # Check if the line contains a recognizable date format
        has_date = False
        for pattern in self.DATE_PATTERNS:
            if pattern.search(line.strip()):
                has_date = True
                break
                
        # If no date is found, it's not a transaction line
        if not has_date:
            return False
            
        # Check if the line contains a dollar amount
        amount_pattern = re.compile(r'\$?[\d,]+\.\d{2}')
        has_amount = bool(amount_pattern.search(line))
        
        # Check for bank-specific transaction indicators
        
        # ANZ-specific transaction indicators
        anz_indicators = ['BP', 'TFR', 'DD', 'DC', 'AP', 'ATM', 'POS', 'VT', 'EFTPOS', 'DEPOSIT', 'CREDIT', 'DEBIT']
        has_anz_indicator = any(f' {indicator} ' in f' {line} ' for indicator in anz_indicators)
        
        # ASB-specific transaction indicators
        asb_indicators = ['W&I Benefit', 'MB Transfer', 'Card', 'Unarranged Overdraft', 'Opening Balance', 'Banzpay', 'FC', 'DR.Int', 'Transfer To', 'Transfer From', 'TFR', 'Savings', 'Interest', 'Withdrawal', 'Deposit', 'ATM', 'EFTPOS', 'Payment', 'BANK CHARGES', 'Account fee', 'Automatic Payment', 'From', 'Ministry of']
        has_asb_indicator = any(indicator.lower() in line.lower() for indicator in asb_indicators)
        
        # Westpac-specific transaction indicators
        westpac_indicators = ['DE', 'DC', 'BP', 'PS', 'CR', 'TFR', 'WBC']
        has_westpac_indicator = any(f' {indicator} ' in f' {line} ' for indicator in westpac_indicators)
        
        # Kiwibank-specific transaction indicators
        kiwibank_indicators = ['TRANSFER', 'PAY', 'BILL PAYMENT', 'DIRECT CREDIT', 'REF:']
        has_kiwibank_indicator = any(indicator.lower() in line.lower() for indicator in kiwibank_indicators)
        
        # BNZ-specific transaction indicators
        bnz_indicators = ['AP', 'IB', 'PS', 'DD', 'DC', 'LR', 'EFTPOS']
        has_bnz_indicator = any(f' {indicator} ' in f' {line} ' for indicator in bnz_indicators)
        
        # Return true if the line has a date and either an amount or a bank-specific indicator
        return has_amount or has_anz_indicator or has_asb_indicator or has_westpac_indicator or has_kiwibank_indicator or has_bnz_indicator
    
    def _is_end_of_transactions(self, line: str) -> bool:
        """
        Check if a line indicates the end of the transaction section
        
        Args:
            line: Line of text to check
            
        Returns:
            True if the line appears to be the end of transactions, False otherwise
        """
        # Common patterns across all banks
        end_patterns = [
            re.compile(r'total\s+(?:debit|credit)s?', re.IGNORECASE),
            re.compile(r'ending\s+balance', re.IGNORECASE),
            re.compile(r'closing\s+balance', re.IGNORECASE),
            re.compile(r'balance\s+(?:brought|carried)\s+forward', re.IGNORECASE),
            re.compile(r'totals?\s+(?:for|at)\s+(?:the|this)\s+(?:period|statement)', re.IGNORECASE),
            re.compile(r'carried\s+forward', re.IGNORECASE),
        ]
        
        # ANZ-specific patterns
        anz_patterns = [
            re.compile(r'opening\s+balance', re.IGNORECASE),
            re.compile(r'transaction\s+totals', re.IGNORECASE)
        ]
        
        # Westpac-specific patterns
        westpac_patterns = [
            re.compile(r'summary\s+of\s+account', re.IGNORECASE),
            re.compile(r'transaction\s+history', re.IGNORECASE),
            re.compile(r'contact\s+information', re.IGNORECASE)
        ]
        
        # Kiwibank-specific patterns
        kiwibank_patterns = [
            re.compile(r'account\s+summary', re.IGNORECASE),
            re.compile(r'daily\s+balance', re.IGNORECASE),
            re.compile(r'change\s+in\s+account\s+balance', re.IGNORECASE)
        ]
        
        # BNZ-specific patterns
        bnz_patterns = [
            re.compile(r'closing\s+balance', re.IGNORECASE),
            re.compile(r'please\s+keep\s+this\s+statement', re.IGNORECASE),
            re.compile(r'fees\s+summary', re.IGNORECASE)
        ]
        
        # ASB-specific patterns
        asb_patterns = [
            re.compile(r'balance\s+summary', re.IGNORECASE),
            re.compile(r'total\s+withdrawals', re.IGNORECASE),
            re.compile(r'total\s+deposits', re.IGNORECASE),
            re.compile(r'closing\s+balance', re.IGNORECASE)
        ]
        
        # Combine all patterns
        all_patterns = end_patterns + anz_patterns + asb_patterns + westpac_patterns + kiwibank_patterns + bnz_patterns
        
        return any(pattern.search(line) for pattern in all_patterns)
    
    def _parse_transaction_line(self, line: str, statement_year: int) -> Optional[Dict[str, Any]]:
        """
        Parse a transaction line from text
        
        Args:
            line: Line of text containing a transaction
            statement_year: Year of the statement
            
        Returns:
            Dictionary with transaction details, or None if parsing failed
        """
        # Extract date using our defined patterns
        date_obj = self._parse_date(line, statement_year)
        if not date_obj:
            return None
            
        # Find all dollar amounts in the line
        amount_pattern = re.compile(r'(\$?[\d,]+\.\d{2})')
        amounts = amount_pattern.findall(line)
        
        # ANZ-specific parsing for transaction codes
        anz_transaction_match = re.search(r'\b(BP|TFR|DD|DC|AP|ATM|POS|VT|EFTPOS)\s+([^\d]+)(?:\s+([\d\.,]+))?', line)
        
        # Also look for common ANZ formats like 'Opening balance' or specific merchant transactions
        anz_opening_match = re.search(r'Opening balance', line, re.IGNORECASE)
        anz_merchant_match = re.search(r'(\d{2}/\d{2})\s+([^\d]+)\s+(\d{2}/\d{2})?', line)
        
        # ASB-specific parsing
        asb_transaction_match = re.search(r'(W&I Benefit|MB Transfer|Card|FC\d+|DR\.Int|Transfer (?:To|From)|TFR|Automatic Payment|Account fee|BANK CHARGES|Ministry of)\s+([^\d]+)(?:\s+([\d\.,]+))?', line, re.IGNORECASE)
        asb_card_match = re.search(r'Card\s+(\d+)\s+([^\d]+)', line)
        asb_tfr_match = re.search(r'TFR\s+(From|To)\s+([^\d]+)', line, re.IGNORECASE)
        asb_date_transaction_match = re.search(r'(\d{1,2}/\d{1,2}(?:/\d{2,4})?)\s+([^\d$]+)\s+(?:([\d,]+\.\d{2}))?', line)
        asb_person_match = re.search(r'([A-Za-z]+\s+[A-Za-z]\s+[A-Za-z])\s+(\d{1,2}\.\d{1,2}\.\d{2,4})\s+([^\d]+)', line)
        
        # Westpac-specific parsing
        westpac_transaction_match = re.search(r'\b(DE|DC|BP|PS|CR)\s+([^\d]+)(?:\s+([\d\.,]+))?', line)
        westpac_name_match = re.search(r'\b(WBC|Transfer|Internet|Bill|Payment)\s+([^\d]+)(?:\s+([\d\.,]+))?', line)
        
        # Kiwibank-specific parsing
        kiwibank_transaction_match = re.search(r'\b(TRANSFER|PAY|BILL PAYMENT|DIRECT CREDIT)\s+([^\d]+)(?:\s+([\d\.,]+))?', line, re.IGNORECASE)
        kiwibank_ref_match = re.search(r'Ref:\s+([^\d]+)(?:\s+([\d\.,]+))?', line)
        
        # BNZ-specific parsing
        bnz_transaction_match = re.search(r'\b(AP|IB|PS|DD|DC|LR|EFTPOS)\s+([^\d]+)(?:\s+([\d\.,]+))?', line)
        
        # Determine transaction type and amount from context
        is_credit = any(kw in line.lower() for kw in ['payment received', 'deposit', 'credit', 'refund', 'opening balance', 'money in', 'direct credit', 'w&i benefit', 'transfer from', 'tfr from', 'from', 'interest paid', 'ministry of'])
        
        # Also check if the word 'deposit' is in the line
        if 'deposit' in line.lower():
            is_credit = True
        
        # Check bank-specific credit indicators
        # ANZ-specific
        if not is_credit and anz_transaction_match:
            tx_code = anz_transaction_match.group(1)
            # DC (Direct Credit) is usually a credit/deposit
            if tx_code == 'DC':
                is_credit = True
        
        # Westpac-specific
        if not is_credit and westpac_transaction_match:
            tx_code = westpac_transaction_match.group(1)
            # CR (Credit) is a credit, PS (Payment Service) could be either
            if tx_code == 'CR':
                is_credit = True
            # Check if it's in 'Money In' column for Westpac
            elif 'money in' in line.lower():
                is_credit = True
        
        # Kiwibank-specific
        if not is_credit and kiwibank_transaction_match:
            tx_type = kiwibank_transaction_match.group(1).upper()
            # DIRECT CREDIT is a credit, TRANSFER could be either
            if 'DIRECT CREDIT' in tx_type:
                is_credit = True
        
        # ASB-specific
        if not is_credit:
            # Check for deposit column in ASB statements
            deposit_column_match = re.search(r'\b(?:Deposit|Deposits)\s+\$', line, re.IGNORECASE)
            if deposit_column_match:
                is_credit = True
            # Check for specific ASB credit indicators
            elif any(kw in line.lower() for kw in ['transfer from', 'tfr from', 'from', 'interest paid', 'ministry of']):
                is_credit = True
            
        # BNZ-specific
        if not is_credit and bnz_transaction_match:
            tx_code = bnz_transaction_match.group(1)
            # DC (Direct Credit) is usually a credit/deposit
            if tx_code == 'DC':
                is_credit = True
        
        # Determine which amount is the transaction amount and which is the balance
        amount = None
        balance = None
        
        if len(amounts) == 1:
            amount_str = amounts[0]
            amount = parse_money_amount(amount_str)
            if not is_credit:
                # If not explicitly a credit, assume it's a debit
                amount = -abs(amount) if amount else None
        elif len(amounts) >= 2:
            # If we have multiple amounts, try to determine which is which
            # Typically, the first amount is the transaction and the last is the balance
            if is_credit:
                # For credits, find the positive amount
                for amt_str in amounts:
                    amt = parse_money_amount(amt_str)
                    if amt is not None and amt > 0:
                        amount = amt
                        break
            # Special handling for Westpac
            elif westpac_transaction_match or westpac_name_match:
                # Check which amount is positive and which is negative
                # For Westpac, sometimes Money Out is first, sometimes Money In is first
                if "money out" in line.lower() and "money in" in line.lower():
                    # If both columns present, determine which is which
                    money_out_idx = line.lower().find("money out")
                    money_in_idx = line.lower().find("money in")
                    
                    if len(amounts) >= 2:
                        amount_1 = parse_money_amount(amounts[0])
                        amount_2 = parse_money_amount(amounts[1])
                    
                        if money_out_idx < money_in_idx:
                            # Money Out is first, then Money In
                            amount = -abs(amount_1) if amount_1 else None  # Money Out is negative
                        else:
                            # Money In is first, then Money Out
                            amount = -abs(amount_2) if amount_2 else None  # Money Out is negative
                else:
                    # Just use the first amount and make it negative since it's a debit
                    amount_str = amounts[0]
                    amount = parse_money_amount(amount_str)
                    if amount is not None and amount > 0:
                        amount = -amount  # Make debits negative
            else:
                # For debits, find the negative amount or make the first amount negative
                amount_str = amounts[0]
                amount = parse_money_amount(amount_str)
                if amount is not None and amount > 0:
                    amount = -amount  # Make debits negative
            
            # Last amount is typically the balance
            balance_str = amounts[-1]
            balance = parse_money_amount(balance_str)
            
        if amount is None:
            return None
            
        # Extract description (everything between the date and the amount)
        description = ''
        
        # Try bank-specific patterns first for more accurate descriptions
        # ASB transaction patterns
        if asb_transaction_match:
            tx_type = asb_transaction_match.group(1)
            tx_description = asb_transaction_match.group(2)
            if tx_description:
                description = f"{tx_type} {tx_description.strip()}"
        # ASB card transaction
        elif asb_card_match:
            card_num = asb_card_match.group(1)
            merchant = asb_card_match.group(2)
            if merchant:
                description = f"Card {card_num} {merchant.strip()}"
        # ASB TFR transaction
        elif asb_tfr_match:
            direction = asb_tfr_match.group(1)
            recipient = asb_tfr_match.group(2)
            if recipient:
                description = f"TFR {direction} {recipient.strip()}"
        # ASB person transaction (e.g., 'Troon M J 13.7.24 Lotto Mel')
        elif asb_person_match:
            person = asb_person_match.group(1)
            date = asb_person_match.group(2)
            details = asb_person_match.group(3)
            if details:
                description = f"{person} {date} {details.strip()}"
        # ASB date-transaction pattern (common format in ASB statements)
        elif asb_date_transaction_match:
            tx_description = asb_date_transaction_match.group(2)
            if tx_description:
                description = tx_description.strip()
        # ANZ transaction patterns
        elif anz_transaction_match:
            tx_code = anz_transaction_match.group(1)
            tx_description = anz_transaction_match.group(2)
            if tx_description:
                description = f"{tx_code} {tx_description.strip()}"
        # ANZ merchant pattern
        elif anz_merchant_match:
            merchant_name = anz_merchant_match.group(2)
            if merchant_name:
                description = merchant_name.strip()
        # ANZ opening balance
        elif anz_opening_match:
            description = 'Opening balance'
        # Westpac transaction patterns
        elif westpac_transaction_match:
            tx_code = westpac_transaction_match.group(1)
            tx_description = westpac_transaction_match.group(2)
            if tx_description:
                description = f"{tx_code} {tx_description.strip()}"
        # Westpac name pattern
        elif westpac_name_match:
            tx_type = westpac_name_match.group(1)
            tx_description = westpac_name_match.group(2)
            if tx_description:
                description = f"{tx_type} {tx_description.strip()}"
        # Kiwibank transaction patterns
        elif kiwibank_transaction_match:
            tx_type = kiwibank_transaction_match.group(1)
            tx_description = kiwibank_transaction_match.group(2)
            if tx_description:
                description = f"{tx_type} {tx_description.strip()}"
        # Kiwibank reference pattern
        elif kiwibank_ref_match:
            ref_description = kiwibank_ref_match.group(1)
            if ref_description:
                description = f"Ref: {ref_description.strip()}"
        # BNZ transaction patterns
        elif bnz_transaction_match:
            tx_code = bnz_transaction_match.group(1)
            tx_description = bnz_transaction_match.group(2)
            if tx_description:
                description = f"{tx_code} {tx_description.strip()}"
        # Otherwise, fall back to extracting between date and amount
        else:
            date_match = None
            for pattern in self.DATE_PATTERNS:
                match = pattern.search(line)
                if match:
                    date_match = match
                    break
                    
            if date_match:
                date_end = date_match.end()
                # Find the first dollar amount after the date
                amount_match = amount_pattern.search(line, date_end)
                if amount_match:
                    amount_start = amount_match.start()
                    description = line[date_end:amount_start].strip()
                else:
                    # If we can't find the amount after the date, use the rest of the line
                    description = line[date_end:].strip()
            else:
                # Fallback - just use the whole line as description
                description = line.strip()
            
        # Remove any leading/trailing spaces and dollar signs from description
        description = clean_description(description)
        
        # Determine transaction type
        transaction_type = identify_transaction_type(amount)
        
        return {
            'Date': date_obj.strftime('%Y-%m-%d'),
            'Description': description,
            'Type': transaction_type,
            'Amount': amount,
            'Balance': balance
        }
        
    def _parse_date(self, text: str, statement_year: int) -> Optional[datetime]:
        """
        Parse a date from text using multiple formats
        
        Args:
            text: Text containing a date
            statement_year: Default year to use if not specified in the date
            
        Returns:
            datetime object if a date is found, None otherwise
        """
        # Try each date pattern
        for pattern in self.DATE_PATTERNS:
            match = pattern.search(text)
            if match:
                groups = match.groups()
                
                if len(groups) == 3 and groups[1].isdigit():
                    # DD/MM/YYYY or DD/MM/YY format
                    day, month, year = groups
                    # Handle 2-digit years
                    if len(year) == 2:
                        year = f"20{year}" if int(year) < 50 else f"19{year}"
                    return datetime(int(year), int(month), int(day))
                    
                elif len(groups) == 2 and not groups[1].isdigit():
                    # DD Month format
                    day, month_str = groups
                    month_num = self.MONTH_MAP.get(month_str.lower()[:3])
                    if month_num:
                        return datetime(statement_year, month_num, int(day))
                        
        return None
