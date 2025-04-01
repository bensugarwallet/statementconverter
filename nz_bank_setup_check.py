#!/usr/bin/env python3

import os
import logging
from pathlib import Path
from typing import List, Dict
import importlib.util

from utils.logger import setup_logging

# Set up logging
setup_logging("INFO")
logger = logging.getLogger(__name__)


def check_required_modules() -> bool:
    """
    Check if all required modules are installed
    """
    required_modules = ["pdfplumber", "pandas", "pytesseract"]
    missing_modules = []
    
    for module in required_modules:
        if importlib.util.find_spec(module) is None:
            missing_modules.append(module)
    
    if missing_modules:
        logger.error(f"Missing required modules: {', '.join(missing_modules)}")
        logger.error("Install using: pip install -r requirements.txt")
        return False
    
    logger.info("All required modules are installed.")
    return True


def check_parser_classes() -> bool:
    """
    Check if all parser classes exist
    """
    required_parsers = [
        "parsers.base_parser",
        "parsers.bank1_parser", 
        "parsers.bank2_parser", 
        "parsers.bank3_parser",
        "parsers.nz_bank_parser"
    ]
    
    missing_parsers = []
    
    for parser in required_parsers:
        try:
            importlib.import_module(parser)
        except ImportError as e:
            missing_parsers.append(parser)
            logger.error(f"Failed to import {parser}: {str(e)}")
    
    if missing_parsers:
        logger.error(f"Missing required parser modules: {', '.join(missing_parsers)}")
        return False
    
    logger.info("All required parser classes exist.")
    return True


def check_directory_structure() -> bool:
    """
    Check if all required directories exist
    """
    required_dirs = [
        "./parsers",
        "./utils",
        "./csv_output"
    ]
    
    missing_dirs = []
    
    for directory in required_dirs:
        if not os.path.isdir(directory):
            missing_dirs.append(directory)
    
    if missing_dirs:
        logger.error(f"Missing required directories: {', '.join(missing_dirs)}")
        for directory in missing_dirs:
            logger.info(f"Creating {directory}")
            os.makedirs(directory, exist_ok=True)
    else:
        logger.info("All required directories exist.")
    
    return True


def check_config_files() -> bool:
    """
    Check if all required configuration files exist
    """
    required_files = [
        "./requirements.txt",
        "./README.md"
    ]
    
    missing_files = []
    
    for file in required_files:
        if not os.path.isfile(file):
            missing_files.append(file)
    
    if missing_files:
        logger.error(f"Missing required files: {', '.join(missing_files)}")
        return False
    
    logger.info("All required configuration files exist.")
    return True


def run_setup_checks() -> None:
    """
    Run all setup checks and print a summary
    """
    logger.info("Starting NZ Bank Statement Parser setup check...")
    
    checks = {
        "Module Check": check_required_modules(),
        "Parser Classes Check": check_parser_classes(),
        "Directory Structure Check": check_directory_structure(),
        "Configuration Files Check": check_config_files()
    }
    
    # Print summary
    logger.info("\nSetup Check Summary:")
    all_passed = True
    
    for check_name, result in checks.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        logger.info(f"{check_name}: {status}")
        if not result:
            all_passed = False
    
    if all_passed:
        logger.info("\nAll checks passed! The NZ Bank Statement Parser is correctly set up.")
        logger.info("To convert a PDF statement, run:")
        logger.info("python pdf_to_csv.py --pdf PATH_TO_NZ_PDF --output-dir ./csv_output")
    else:
        logger.error("\nSome checks failed. Please fix the issues above before continuing.")


if __name__ == "__main__":
    run_setup_checks()
