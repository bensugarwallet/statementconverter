import os
import logging
import tempfile
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
from werkzeug.utils import secure_filename
import pandas as pd

from utils.logger import setup_logging
from parsers import get_parser_for_statement
from test_nz_formats import create_sample_csv_from_image1, create_sample_csv_from_image2, create_sample_csv_from_image3

# Set up logging
setup_logging("INFO")
logger = logging.getLogger(__name__)

# Configure Flask app
app = Flask(__name__)
app.secret_key = 'pdf_to_csv_converter_secret_key'
app.config['UPLOAD_FOLDER'] = './uploads'
app.config['OUTPUT_FOLDER'] = './webapp_output'
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)


def allowed_file(filename):
    """
    Check if a file has an allowed extension
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def process_pdf(pdf_path, output_folder):
    """
    Process a PDF file and convert it to CSV
    """
    pdf_path = Path(pdf_path)
    output_folder = Path(output_folder)
    
    try:
        # Get the appropriate parser for this statement
        parser = get_parser_for_statement(pdf_path)
        if not parser:
            logger.error(f"No suitable parser found for {pdf_path}")
            return None
            
        # Extract transactions from the PDF
        transactions = parser.extract_transactions()
        
        if not transactions:
            logger.warning(f"No transactions found in {pdf_path}")
            return None
            
        # Convert to DataFrame and save as CSV
        df = pd.DataFrame(transactions)
        
        # Ensure output directory exists
        os.makedirs(output_folder, exist_ok=True)
        
        # Save to CSV
        output_path = output_folder / f"{pdf_path.stem}.csv"
        df.to_csv(output_path, index=False)
        
        logger.info(f"Successfully converted {pdf_path} to {output_path}")
        logger.info(f"Extracted {len(transactions)} transactions")
        
        return output_path
        
    except Exception as e:
        logger.error(f"Error processing {pdf_path}: {str(e)}")
        return None


def process_test_file(bank_type, output_folder):
    """
    Process a test file and save it to the output folder
    """
    try:
        # Create sample csv based on bank type
        if bank_type == 'credit_card':
            create_sample_csv_from_image1()
            source_file = './csv_output/credit_card_statement.csv'
        elif bank_type == 'asb':
            create_sample_csv_from_image2()
            source_file = './csv_output/asb_bank_statement.csv'
        elif bank_type == 'anz':
            create_sample_csv_from_image3()
            source_file = './csv_output/anz_bank_statement.csv'
        else:
            logger.error(f"Unknown bank type: {bank_type}")
            return None
            
        if not os.path.exists(source_file):
            logger.error(f"Sample file does not exist: {source_file}")
            return None
            
        # Read the sample CSV file
        df = pd.read_csv(source_file)
        
        # Ensure output directory exists
        os.makedirs(output_folder, exist_ok=True)
        
        # Save to the output directory
        output_filename = f"{bank_type}_bank_statement.csv"
        output_path = Path(output_folder) / output_filename
        df.to_csv(output_path, index=False)
        
        logger.info(f"Successfully processed {bank_type} sample to {output_path}")
        
        return output_path
        
    except Exception as e:
        logger.error(f"Error processing test file: {str(e)}")
        return None


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    # Check if a file was uploaded
    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('index'))
        
    file = request.files['file']
    
    # If the user doesn't select a file, the browser may
    # submit an empty part without a filename
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('index'))
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Process the PDF file
        output_file = process_pdf(filepath, app.config['OUTPUT_FOLDER'])
        
        if output_file:
            # Store the output file path in the session
            session['output_file'] = str(output_file)
            flash(f'Successfully converted {filename} to CSV')
            return redirect(url_for('result'))
        else:
            flash(f'Failed to process {filename}. Using test mode instead.')
            return redirect(url_for('test_mode'))
    else:
        flash('Only PDF files are allowed')
        return redirect(url_for('index'))


@app.route('/test', methods=['GET', 'POST'])
def test_mode():
    if request.method == 'POST':
        bank_type = request.form.get('bank_type')
        if not bank_type:
            flash('Please select a bank type')
            return redirect(url_for('test_mode'))
            
        # Process the test file
        output_file = process_test_file(bank_type, app.config['OUTPUT_FOLDER'])
        
        if output_file:
            # Store the output file path in the session
            session['output_file'] = str(output_file)
            flash(f'Successfully generated sample CSV for {bank_type}')
            return redirect(url_for('result'))
        else:
            flash(f'Failed to generate sample CSV for {bank_type}')
            return redirect(url_for('test_mode'))
    
    return render_template('test_mode.html')


@app.route('/result')
def result():
    output_file = session.get('output_file')
    if not output_file or not os.path.exists(output_file):
        flash('No output file found')
        return redirect(url_for('index'))
        
    # Read the CSV file and prepare data for display
    df = pd.read_csv(output_file)
    headers = df.columns.tolist()
    rows = df.values.tolist()
    
    return render_template('result.html', headers=headers, rows=rows, filename=os.path.basename(output_file))


@app.route('/download')
def download():
    output_file = session.get('output_file')
    if not output_file or not os.path.exists(output_file):
        flash('No output file found')
        return redirect(url_for('index'))
        
    return send_file(output_file, as_attachment=True)


if __name__ == '__main__':
    # Create templates and static directories if they don't exist
    os.makedirs('./templates', exist_ok=True)
    os.makedirs('./static', exist_ok=True)
    
    app.run(debug=True)
