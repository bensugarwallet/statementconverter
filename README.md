# PDF Bank Statement Converter

This tool converts PDF bank statements into structured CSV files. It can handle multiple bank statement layouts and formats, extracting transaction data with high accuracy. It now includes support for New Zealand bank statements!

## Features

- Converts PDF bank statements to CSV files
- Supports multiple bank statement formats including US banks and New Zealand banks
- Extracts transaction date, description, amount, and balance
- Handles multi-page statements and various formatting styles
- Provides extensibility for adding new bank statement formats

## Installation

1. Clone this repository
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

3. If using OCR capabilities (for scanned statements), make sure to install Tesseract OCR:
   - On macOS: `brew install tesseract`
   - On Ubuntu: `sudo apt-get install tesseract-ocr`
   - On Windows: [Download and install Tesseract](https://github.com/UB-Mannheim/tesseract/wiki)

## Usage

```bash
python pdf_to_csv.py --pdf PATH_TO_PDF1 [PATH_TO_PDF2 ...] --output-dir OUTPUT_DIRECTORY
```

Example:
```bash
python pdf_to_csv.py --pdf ./sample_pdfs/BankStatement1.pdf ./sample_pdfs/BankStatement2.pdf --output-dir ./csv_output
```

## Adding New Bank Statement Formats

To add support for a new bank statement format:

1. Create a new parser class in `parsers/` that inherits from the `BaseStatementParser`
2. Implement the required methods for parsing the new format
3. Add the new parser to the `AVAILABLE_PARSERS` list in `parsers/__init__.py`

## CSV Output Format

The generated CSV files follow this schema:

```
Date,Description,Type,Amount,Balance
YYYY-MM-DD,"Transaction description",credit,100.00,1000.00
YYYY-MM-DD,"Another transaction",debit,-50.00,950.00
...
```

## Supported Banks

- Bank of America (US)
- Chase Bank (US)
- Wells Fargo (US)
- ANZ Bank (New Zealand)
- ASB Bank (New Zealand)
- Credit card statements (various issuers)

## Limitations

- PDF statements must be text-based (not scanned images) for optimal results
- Complex multi-column layouts may require custom parsers
- Transaction descriptions that span multiple lines might be concatenated

## License

MIT
