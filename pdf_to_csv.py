#!/usr/bin/env python3

import argparse
import os
import logging
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
from tqdm import tqdm

from parsers import get_parser_for_statement
from utils.logger import setup_logging


def parse_args():
    parser = argparse.ArgumentParser(description='Convert PDF bank statements to CSV')
    parser.add_argument('--pdf', nargs='+', required=True, help='Path to PDF bank statement(s)')
    parser.add_argument('--output-dir', default='./csv_output', help='Directory to save CSV files')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO',
                        help='Set the logging level')
    return parser.parse_args()


def process_pdf(pdf_path: str, output_dir: str) -> bool:
    """
    Process a single PDF bank statement and convert it to CSV
    
    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save the CSV output
        
    Returns:
        bool: True if processing was successful, False otherwise
    """
    logger = logging.getLogger(__name__)
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        logger.error(f"PDF file does not exist: {pdf_path}")
        return False
    
    logger.info(f"Processing {pdf_path}")
    
    try:
        # Get the appropriate parser for this statement
        parser = get_parser_for_statement(pdf_path)
        if not parser:
            logger.error(f"No suitable parser found for {pdf_path}")
            return False
            
        # Extract transactions from the PDF
        transactions = parser.extract_transactions()
        
        if not transactions:
            logger.warning(f"No transactions found in {pdf_path}")
            return False
            
        # Convert to DataFrame and save as CSV
        df = pd.DataFrame(transactions)
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Save to CSV
        output_path = Path(output_dir) / f"{pdf_path.stem}.csv"
        df.to_csv(output_path, index=False)
        
        logger.info(f"Successfully converted {pdf_path} to {output_path}")
        logger.info(f"Extracted {len(transactions)} transactions")
        
        return True
        
    except Exception as e:
        logger.error(f"Error processing {pdf_path}: {str(e)}")
        return False


def main():
    args = parse_args()
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    logger.info(f"Starting PDF to CSV conversion for {len(args.pdf)} file(s)")
    
    success_count = 0
    for pdf_path in tqdm(args.pdf):
        if process_pdf(pdf_path, args.output_dir):
            success_count += 1
    
    logger.info(f"Processed {len(args.pdf)} PDF files. Success: {success_count}, Failed: {len(args.pdf) - success_count}")


if __name__ == "__main__":
    main()
