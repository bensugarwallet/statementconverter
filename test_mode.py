#!/usr/bin/env python3

import os
import logging
import argparse
from pathlib import Path
import pandas as pd
from tqdm import tqdm

from utils.logger import setup_logging

# Set up logging
setup_logging("INFO")
logger = logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(description='Test the bank statement parser with sample data')
    parser.add_argument('--bank', choices=['anz', 'asb', 'credit'], default='all', help='Bank type to process')
    parser.add_argument('--output-dir', default='./output', help='Directory to save processed files')
    return parser.parse_args()

def process_sample_csv(bank_type, output_dir):
    """
    Process a sample CSV file and copy it to the output directory
    """
    sample_file_map = {
        'anz': './csv_output/anz_bank_statement.csv',
        'asb': './csv_output/asb_bank_statement.csv',
        'credit': './csv_output/credit_card_statement.csv'
    }
    
    if bank_type not in sample_file_map:
        logger.error(f"Unknown bank type: {bank_type}")
        return False
    
    source_file = sample_file_map[bank_type]
    if not os.path.exists(source_file):
        logger.error(f"Sample file does not exist: {source_file}")
        return False
    
    try:
        # Read the sample CSV file
        df = pd.read_csv(source_file)
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Save to the output directory
        output_path = Path(output_dir) / f"{bank_type}_bank_statement_processed.csv"
        df.to_csv(output_path, index=False)
        
        logger.info(f"Successfully processed {bank_type} sample to {output_path}")
        logger.info(f"Processed {len(df)} transactions")
        
        return True
    
    except Exception as e:
        logger.error(f"Error processing {bank_type} sample: {str(e)}")
        return False

def main():
    args = parse_args()
    
    # Process all banks or just the specified one
    banks_to_process = ['anz', 'asb', 'credit'] if args.bank == 'all' else [args.bank]
    
    logger.info(f"Starting test mode for {len(banks_to_process)} bank type(s)")
    
    success_count = 0
    for bank in tqdm(banks_to_process):
        if process_sample_csv(bank, args.output_dir):
            success_count += 1
    
    logger.info(f"Processed {len(banks_to_process)} bank types. Success: {success_count}, Failed: {len(banks_to_process) - success_count}")
    
    if success_count > 0:
        logger.info(f"\nSuccessfully processed sample files. You can find the results in: {args.output_dir}")
        logger.info("This simulates what would happen with actual PDF bank statements.")
        logger.info("\nTo process real PDF files when you have them, use:")
        logger.info("python pdf_to_csv.py --pdf ./statements/your_statement.pdf --output-dir ./csv_output")

if __name__ == "__main__":
    main()
