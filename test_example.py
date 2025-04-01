#!/usr/bin/env python3

import os
import logging
from parsers import get_parser_for_statement, Bank1StatementParser, Bank2StatementParser, Bank3StatementParser
from utils.logger import setup_logging
from utils.pdf_utils import extract_text_from_pdf
import pandas as pd
from pathlib import Path


def create_dummy_transactions() -> dict:
    """
    Create sample transaction data for testing when no PDF files are available
    
    Returns:
        Dictionary with transaction data for each bank
    """
    dummy_data = {
        'bank1': [
            {'Date': '2023-01-15', 'Description': 'GROCERY STORE PURCHASE', 'Type': 'debit', 'Amount': -45.67, 'Balance': 1234.56},
            {'Date': '2023-01-18', 'Description': 'ONLINE TRANSFER FROM SAVINGS', 'Type': 'credit', 'Amount': 500.00, 'Balance': 1734.56},
            {'Date': '2023-01-20', 'Description': 'SALARY DEPOSIT', 'Type': 'credit', 'Amount': 2500.00, 'Balance': 4234.56},
            {'Date': '2023-01-22', 'Description': 'ATM WITHDRAWAL', 'Type': 'debit', 'Amount': -200.00, 'Balance': 4034.56},
            {'Date': '2023-01-25', 'Description': 'MONTHLY SERVICE FEE', 'Type': 'debit', 'Amount': -12.95, 'Balance': 4021.61},
        ],
        'bank2': [
            {'Date': '2023-02-01', 'Description': 'AMAZON PURCHASE', 'Type': 'debit', 'Amount': -29.99, 'Balance': 2500.25},
            {'Date': '2023-02-03', 'Description': 'RESTAURANT PAYMENT', 'Type': 'debit', 'Amount': -75.45, 'Balance': 2424.80},
            {'Date': '2023-02-05', 'Description': 'INTEREST PAYMENT', 'Type': 'credit', 'Amount': 0.15, 'Balance': 2424.95},
            {'Date': '2023-02-08', 'Description': 'DIRECT DEPOSIT - PAYROLL', 'Type': 'credit', 'Amount': 1500.00, 'Balance': 3924.95},
            {'Date': '2023-02-12', 'Description': 'CHECK #1234', 'Type': 'debit', 'Amount': -350.00, 'Balance': 3574.95},
        ],
        'bank3': [
            {'Date': '2023-03-01', 'Description': 'Check #5678 - RENT PAYMENT', 'Type': 'debit', 'Amount': -1200.00, 'Balance': 5250.75},
            {'Date': '2023-03-05', 'Description': 'ELECTRIC BILL AUTOPAY', 'Type': 'debit', 'Amount': -124.56, 'Balance': 5126.19},
            {'Date': '2023-03-10', 'Description': 'MOBILE DEPOSIT', 'Type': 'credit', 'Amount': 350.00, 'Balance': 5476.19},
            {'Date': '2023-03-15', 'Description': 'SUBSCRIPTION PAYMENT', 'Type': 'debit', 'Amount': -14.99, 'Balance': 5461.20},
            {'Date': '2023-03-20', 'Description': 'ATM WITHDRAWAL', 'Type': 'debit', 'Amount': -60.00, 'Balance': 5401.20},
        ]
    }
    
    return dummy_data


def write_dummy_csv_files(output_dir: str):
    """
    Create sample CSV files with dummy transaction data
    
    Args:
        output_dir: Directory to save the CSV files
    """
    os.makedirs(output_dir, exist_ok=True)
    
    dummy_data = create_dummy_transactions()
    
    for bank, transactions in dummy_data.items():
        df = pd.DataFrame(transactions)
        output_path = os.path.join(output_dir, f"{bank}_statement.csv")
        df.to_csv(output_path, index=False)
        print(f"Created {output_path}")


def main():
    setup_logging("INFO")
    logger = logging.getLogger(__name__)
    
    # Define the output directory for CSV files
    output_dir = "./csv_output"
    
    # Look for PDF files in the sample_pdfs directory
    pdf_dir = "./sample_pdfs"
    pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]
    
    if pdf_files:
        logger.info(f"Found {len(pdf_files)} PDF files in {pdf_dir}")
        for pdf_file in pdf_files:
            pdf_path = Path(os.path.join(pdf_dir, pdf_file))
            logger.info(f"Processing {pdf_path}")
            
            # Get the appropriate parser for this statement
            parser = get_parser_for_statement(pdf_path)
            if not parser:
                logger.error(f"No suitable parser found for {pdf_path}")
                continue
                
            # Extract transactions from the PDF
            transactions = parser.extract_transactions()
            
            if not transactions:
                logger.warning(f"No transactions found in {pdf_path}")
                continue
                
            # Convert to DataFrame and save as CSV
            df = pd.DataFrame(transactions)
            
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            # Save to CSV
            output_path = os.path.join(output_dir, f"{pdf_path.stem}.csv")
            df.to_csv(output_path, index=False)
            
            logger.info(f"Successfully converted {pdf_path} to {output_path}")
            logger.info(f"Extracted {len(transactions)} transactions")
    else:
        logger.warning(f"No PDF files found in {pdf_dir}. Creating dummy CSV files instead.")
        write_dummy_csv_files(output_dir)


if __name__ == "__main__":
    main()
