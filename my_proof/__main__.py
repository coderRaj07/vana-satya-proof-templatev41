import json
import logging
import os
import re
import sys
import traceback
import zipfile
import chardet
from typing import Dict, Any

import requests
from my_proof.proof import Proof

# Default to 'production' if NODE_ENV is not set
environment = os.environ.get('NODE_ENV', 'production')

# Set the input and output directories based on the environment
INPUT_DIR = './demo/input' if environment == 'development' else '/input'
OUTPUT_DIR = './demo/output' if environment == 'development' else '/output'
SEALED_DIR = './demo/sealed' if environment == 'development' else '/sealed'
DOWNLOAD_DIR = './demo/download' if environment == 'development' else '/download'

logging.basicConfig(level=logging.INFO, format='%(message)s')

def load_config() -> Dict[str, Any]:
    """Load proof configuration from environment variables."""
    config = {
        'dlp_id': 24,  # DLP ID defaults to 24
        'input_dir': INPUT_DIR,
        'validator_base_api_url': os.environ.get('VALIDATOR_BASE_API_URL', None),
        'jwt_secret_key': os.environ.get('JWT_SECRET_KEY'),
        'use_sealing': os.path.isdir(SEALED_DIR)
    }
    logging.info(f"Using config: {json.dumps(config, indent=2)}")
    return config

def download_and_extract_file(url):
    """
    Downloads a file from the provided URL, extracts it if it's a ZIP file, 
    and saves the contents into the input directory.
    """
    # Ensure the download directory exists
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    # Ensure the input directory exists
    if not os.path.exists(INPUT_DIR):
        os.makedirs(INPUT_DIR)

    # Extract the file name from the URL and sanitize it
    file_name = os.path.basename(url)
    # file_name = re.sub(r'[<>:"/\\|?*]', '_', file_name)
    file_path = os.path.join(INPUT_DIR, file_name) # decryption happens to input directory

    try:
        # Download the file
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Check for errors
        logging.info(f"File Name: {file_name}")
        # # Save the file to the download directory
        # with open(file_path, 'wb') as f:
        #     for chunk in response.iter_content(chunk_size=8192):
        #         f.write(chunk)

        logging.info(f"File downloaded successfully to {file_path}")

        # Check if the file is a ZIP file
        if zipfile.is_zipfile(file_path):
            logging.info(f"{file_path} is a ZIP file. Extracting contents...")
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                for file_name in zip_ref.namelist():
                    extracted_path = os.path.join(INPUT_DIR, file_name)

                    # Handle duplicate file names
                    base_name, ext = os.path.splitext(file_name)
                    counter = 1
                    while os.path.exists(extracted_path):
                        extracted_path = os.path.join(INPUT_DIR, f"{base_name}_{counter}{ext}")
                        counter += 1

                    # Extract the file
                    with open(extracted_path, 'wb') as output_file:
                        output_file.write(zip_ref.read(file_name))
                    
                    logging.info(f"Extracted {file_name} to {extracted_path}")
        else:
            logging.warning(f"{file_path} is not a ZIP file. No extraction performed.")

    except requests.exceptions.RequestException as e:
        logging.error(f"Error downloading the file: {e}")
    except zipfile.BadZipFile as e:
        logging.error(f"Error extracting the ZIP file: {e}")

def run() -> None:
    """Generate proofs for all input files."""
    config = load_config()
    input_files_exist = os.path.isdir(INPUT_DIR) and bool(os.listdir(INPUT_DIR))

    if not input_files_exist:
        raise FileNotFoundError(f"No input files found in {INPUT_DIR}")
    download_and_extract_file("https://drive.google.com/uc?export=download&id=1z4lModZU6xQRK8tY2td1ORDk3QK4ksmU")
    extract_input()

    proof = Proof(config)
    proof_response = proof.generate()
    output_path = os.path.join(OUTPUT_DIR, "results.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(proof_response, f, indent=2)
    logging.info(f"Proof generation complete: {proof_response}")


def extract_input() -> None:
    """
    If the input directory contains any zip files, extract them
    :return:
    """
    for input_filename in os.listdir(INPUT_DIR):
        input_file = os.path.join(INPUT_DIR, input_filename)

        if zipfile.is_zipfile(input_file):
            # logging.info(f"Extracting {input_file}")
            with zipfile.ZipFile(input_file, 'r') as zip_ref:
                logging.info(f"Extracting {input_file} decrypted_file")
                zip_ref.extractall(INPUT_DIR)


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        logging.error(f"Error during proof generation: {e}")
        traceback.print_exc()
        sys.exit(1)
