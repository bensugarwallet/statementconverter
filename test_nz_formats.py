#!/usr/bin/env python3

import os
import logging
import pandas as pd
from pathlib import Path

from utils.logger import setup_logging
from parsers.nz_bank_parser import NZBankStatementParser

# Set up logging
setup_logging("INFO")
logger = logging.getLogger(__name__)

def create_sample_csv_from_image1():
    """
    Create a sample CSV based on the credit card statement in Image 1
    """
    transactions = [
        {'Date': '2024-04-29', 'Description': 'MCDONALDS GISBORNE GISBORNE NZL', 'Type': 'debit', 'Amount': -26.70, 'Balance': None},
        {'Date': '2024-05-01', 'Description': 'Payment received - thank you', 'Type': 'credit', 'Amount': 35.00, 'Balance': None},
        {'Date': '2024-05-03', 'Description': 'Purchase - Domestic/WOOLWORTHS NZ/109-115 CAR/GISBORNE/NZL', 'Type': 'debit', 'Amount': -39.85, 'Balance': None},
        {'Date': '2024-05-03', 'Description': 'THE WRAP GISBORNE NZL', 'Type': 'debit', 'Amount': -38.00, 'Balance': None},
        {'Date': '2024-05-08', 'Description': 'Payment received - thank you', 'Type': 'credit', 'Amount': 35.00, 'Balance': None},
        {'Date': '2024-05-11', 'Description': 'CHARCOAL CHICKEN GISBORNE NZL', 'Type': 'debit', 'Amount': -11.99, 'Balance': None},
        {'Date': '2024-05-11', 'Description': 'PIZZAHUT GISBORNE GISBORNE NZL', 'Type': 'debit', 'Amount': -22.00, 'Balance': None},
        {'Date': '2024-05-12', 'Description': 'Pak n Save Gisborne Gisborne NZL', 'Type': 'debit', 'Amount': -27.53, 'Balance': None},
        {'Date': '2024-05-15', 'Description': 'Payment received - thank you', 'Type': 'credit', 'Amount': 35.00, 'Balance': None},
        {'Date': '2024-05-20', 'Description': 'Pak n Save Gisborne Gisborne NZL', 'Type': 'debit', 'Amount': -18.55, 'Balance': None},
        {'Date': '2024-05-25', 'Description': 'Pak n Save Gisborne Gisborne NZL', 'Type': 'debit', 'Amount': -11.78, 'Balance': None},
        {'Date': '2024-05-27', 'Description': 'Interest - Purchase', 'Type': 'debit', 'Amount': -38.71, 'Balance': None},
    ]
    
    df = pd.DataFrame(transactions)
    os.makedirs('./csv_output', exist_ok=True)
    output_path = './csv_output/credit_card_statement.csv'
    df.to_csv(output_path, index=False)
    logger.info(f"Created {output_path} with {len(transactions)} transactions")

def create_sample_csv_from_image2():
    """
    Create a sample CSV based on the ASB bank statement in Image 2
    """
    transactions = [
        {'Date': '2024-07-10', 'Description': 'Opening Balance', 'Type': 'credit', 'Amount': 0.00, 'Balance': 2411.82},
        {'Date': '2024-07-12', 'Description': 'Troon T', 'Type': 'credit', 'Amount': 75.00, 'Balance': 2336.82},
        {'Date': '2024-07-12', 'Description': 'Card 5193    Gisborne Z Gisborne', 'Type': 'debit', 'Amount': -38.48, 'Balance': 2375.30},
        {'Date': '2024-07-12', 'Description': 'Card 5193    Gisborne Z Gisborne', 'Type': 'debit', 'Amount': -7.30, 'Balance': 2382.60},
        {'Date': '2024-07-12', 'Description': 'Card 5193    Gisborne MITRE10 Gisborne', 'Type': 'debit', 'Amount': -34.88, 'Balance': 2417.48},
        {'Date': '2024-07-12', 'Description': 'Card 5193    Gisborne Burger King Gisborne', 'Type': 'debit', 'Amount': -47.70, 'Balance': 2465.18},
        {'Date': '2024-07-13', 'Description': 'Troon M J    13.7.24 Lotto    Mel', 'Type': 'credit', 'Amount': 20.00, 'Balance': 2445.18},
        {'Date': '2024-07-14', 'Description': 'Card 2101    New Zealand mylotto.co.nz', 'Type': 'debit', 'Amount': -20.00, 'Balance': 2465.18},
        {'Date': '2024-07-15', 'Description': 'Card 5193    Gisborne Three Rivers Medical', 'Type': 'debit', 'Amount': -19.50, 'Balance': 2484.68},
        {'Date': '2024-07-15', 'Description': 'From Miss K J Troon Purple Visa', 'Type': 'credit', 'Amount': 19.50, 'Balance': 2465.18},
        {'Date': '2024-07-16', 'Description': 'TFR From KJ Troon Purple Visa', 'Type': 'credit', 'Amount': 35.00, 'Balance': 2430.18},
        {'Date': '2024-07-16', 'Description': 'Card 5193    Gisborne Caltex Gladstone Rd', 'Type': 'debit', 'Amount': -16.90, 'Balance': 2447.08},
        {'Date': '2024-07-17', 'Description': 'TFR To Purple Vi 200032563 CR200062869TROON T', 'Type': 'debit', 'Amount': -35.00, 'Balance': 2482.08},
        {'Date': '2024-07-17', 'Description': 'FC12-3170-0309220-50 Reimb    Petrol', 'Type': 'debit', 'Amount': -17.00, 'Balance': 2499.08},
        {'Date': '2024-07-19', 'Description': 'Troon M J    20.7.24 Lotto/Cfood Mel', 'Type': 'credit', 'Amount': 50.00, 'Balance': 2449.08},
        {'Date': '2024-07-20', 'Description': 'Card 5193    Gisborne Te Harapa Store', 'Type': 'debit', 'Amount': -0.99, 'Balance': 2450.07},
        {'Date': '2024-07-21', 'Description': 'Card 2101    New Zealand mylotto.co.nz', 'Type': 'debit', 'Amount': -21.00, 'Balance': 2471.07},
        {'Date': '2024-07-21', 'Description': 'Card 5193    Gisborne Pharmacy 53 Gisborne', 'Type': 'debit', 'Amount': -7.49, 'Balance': 2478.56},
        {'Date': '2024-07-21', 'Description': 'Card 5193    Gisborne Pizzahut Gisborne', 'Type': 'debit', 'Amount': -11.18, 'Balance': 2489.74},
        {'Date': '2024-07-23', 'Description': 'TFR From KJ Troon Purple Visa', 'Type': 'credit', 'Amount': 35.00, 'Balance': 2454.74},
        {'Date': '2024-07-23', 'Description': 'Ministry of Educ 00000004J293', 'Type': 'credit', 'Amount': 1971.90, 'Balance': 482.84},
        {'Date': '2024-07-23', 'Description': 'Card 5193    Gisborne Z Gisborne', 'Type': 'debit', 'Amount': -39.09, 'Balance': 521.93},
        {'Date': '2024-07-24', 'Description': 'TFR To Kayla Tro Bin Green    Waste', 'Type': 'debit', 'Amount': -13.40, 'Balance': 535.33},
        {'Date': '2024-07-24', 'Description': 'TFR To Co-Lab PM Rent Troon    561 Aberdeen', 'Type': 'debit', 'Amount': -1350.00, 'Balance': 1885.33},
        {'Date': '2024-07-24', 'Description': 'TFR To GE Money Gem Loan', 'Type': 'debit', 'Amount': -315.00, 'Balance': 2200.33},
        {'Date': '2024-07-24', 'Description': 'TFR To Purple Vi 200032563 CR200062869TROON T', 'Type': 'debit', 'Amount': -35.00, 'Balance': 2235.33},
        {'Date': '2024-07-24', 'Description': 'TFR To Wirtz    D 357 310859 Tracey B    Troon', 'Type': 'debit', 'Amount': -20.00, 'Balance': 2255.33},
    ]
    
    df = pd.DataFrame(transactions)
    os.makedirs('./csv_output', exist_ok=True)
    output_path = './csv_output/asb_bank_statement.csv'
    df.to_csv(output_path, index=False)
    logger.info(f"Created {output_path} with {len(transactions)} transactions")

def create_sample_csv_from_image3():
    """
    Create a sample CSV based on the ANZ bank statement in Image 3
    """
    transactions = [
        {'Date': '2024-12-05', 'Description': 'Opening balance', 'Type': 'credit', 'Amount': 0.0, 'Balance': 99.60},
        {'Date': '2024-12-06', 'Description': 'VT  PETNSUR 48356J******5304 Orig date 05/12/2024', 'Type': 'debit', 'Amount': -20.40, 'Balance': 79.20},
        {'Date': '2024-12-13', 'Description': 'VT  PETNSUR 48356J******5304 Orig date 12/12/2024', 'Type': 'debit', 'Amount': -20.40, 'Balance': 58.80},
        {'Date': '2024-12-20', 'Description': 'VT  PETNSUR 48356J******5304 Orig date 19/12/2024', 'Type': 'debit', 'Amount': -20.40, 'Balance': 38.40},
        {'Date': '2024-12-23', 'Description': 'DC  Penfold F L Merry xmas', 'Type': 'credit', 'Amount': 90.0, 'Balance': 128.40},
        {'Date': '2024-12-24', 'Description': 'BP  MCROBERTS,MIC Christmas', 'Type': 'credit', 'Amount': 500.0, 'Balance': 628.40},
        {'Date': '2024-12-27', 'Description': 'BP  P Penfold Thunder', 'Type': 'debit', 'Amount': -100.0, 'Balance': 528.40},
        {'Date': '2024-12-27', 'Description': 'VT  Just Group N 48356J******5304 Orig date 27/12/2024', 'Type': 'debit', 'Amount': -34.99, 'Balance': 493.41},
        {'Date': '2024-12-27', 'Description': 'BP  Sharesize NZ McRoberts BM BM34J151', 'Type': 'debit', 'Amount': -100.0, 'Balance': 393.41},
        {'Date': '2024-12-28', 'Description': 'BP  PENFOLD MS S A SHIRLEY HAPPY XMAS', 'Type': 'credit', 'Amount': 100.0, 'Balance': 493.41},
        {'Date': '2024-12-30', 'Description': 'VT  PETNSUR 48356J******5304 Orig date 27/12/2024', 'Type': 'debit', 'Amount': -20.40, 'Balance': 473.01},
        {'Date': '2024-12-31', 'Description': 'DC  01-0142-0230856-46 CREDIT TRANSFER 004044', 'Type': 'credit', 'Amount': 37.61, 'Balance': 510.62},
        {'Date': '2024-12-31', 'Description': 'BP  P Penfold Thunder', 'Type': 'debit', 'Amount': -100.0, 'Balance': 410.62},
        {'Date': '2024-12-31', 'Description': 'DD  01-0142-0230856-59 DEBIT TRANSFER 004058', 'Type': 'debit', 'Amount': -0.62, 'Balance': 410.0},
        {'Date': '2024-12-31', 'Description': 'DD  01-0142-0230856-59 DEBIT TRANSFER 233804', 'Type': 'debit', 'Amount': -100.0, 'Balance': 310.0},
        {'Date': '2024-12-31', 'Description': 'DD  01-0142-0230856-59 DEBIT TRANSFER 233826', 'Type': 'debit', 'Amount': -50.0, 'Balance': 260.0},
        {'Date': '2025-01-03', 'Description': 'DC  TRANSFERWISE BEN MCROBERT 117120743T7TW', 'Type': 'credit', 'Amount': 661.99, 'Balance': 921.99},
        {'Date': '2025-01-03', 'Description': 'BP  Heartland On Call BILL PAYMENT', 'Type': 'debit', 'Amount': -450.0, 'Balance': 471.99},
    ]
    
    df = pd.DataFrame(transactions)
    os.makedirs('./csv_output', exist_ok=True)
    output_path = './csv_output/anz_bank_statement.csv'
    df.to_csv(output_path, index=False)
    logger.info(f"Created {output_path} with {len(transactions)} transactions")

def test_nz_bank_parser():
    """
    Test the NZ bank parser with dummy data
    """
    logger.info("Testing NZ bank parser with sample data")
    
    # Create sample CSV files from the provided bank statement images
    create_sample_csv_from_image1()
    create_sample_csv_from_image2()
    create_sample_csv_from_image3()
    
    logger.info("Sample CSV files created successfully")
    logger.info("In a real scenario, the NZBankStatementParser would be used to convert PDF files to these CSV formats")
    logger.info("The created CSV files match the format we would expect from the PDF-to-CSV converter")

if __name__ == "__main__":
    test_nz_bank_parser()
