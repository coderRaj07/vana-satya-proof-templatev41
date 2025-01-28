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

def download_file(url):
        # Get the input directory from the config
        input_dir = INPUT_DIR
        sealed_dir = SEALED_DIR
        # Ensure the directory exists
        if not os.path.exists(input_dir):
            os.makedirs(input_dir)

        # Extract the file name from the URL
        file_name = os.path.basename(url)

        # Sanitize the file name (remove invalid characters for Windows)
        file_name = re.sub(r'[<>:"/\\|?*]', '_', file_name)

        # Create the full path where the file will be saved
        destination = os.path.join(input_dir, file_name)

        try:
            # Send GET request to the URL
            response = requests.get(url)
            response.raise_for_status()  # Check for any errors during request

            # Write the content to the input directory
            with open(input_dir, 'wb') as file:
                file.write(response.content)

            logging.info(f"File downloaded successfully to {input_dir}")

            # Detect encoding and read the file content
            with open(input_dir, 'rb') as file:
                raw_data = file.read()
                detected = chardet.detect(raw_data)
                encoding = detected.get('encoding', 'utf-8')

                try:
                    file_content = raw_data.decode(encoding)
                    logging.info(f"File contents successfully stored in ProofResponse.attributes {file_content}")
                except Exception as e:
                    logging.error(f"Error decoding file contents with encoding {encoding}: {e}")

            # Check if the file also exists in the sealed directory
            if os.path.exists(sealed_dir):
                logging.info(f"File also exists in sealed folder: {sealed_dir}")
                with open(sealed_dir, 'rb') as sealed_file:
                    sealed_raw_data = sealed_file.read()
                    sealed_detected = chardet.detect(sealed_raw_data)
                    sealed_encoding = sealed_detected.get('encoding', 'utf-8')

                    try:
                        sealed_file_content = sealed_raw_data.decode(sealed_encoding)
                        logging.info("Successfully read file contents from sealed folder")
                        # Optional: Do something with `sealed_file_content`
                    except Exception as e:
                        logging.error(f"Error decoding file contents from sealed folder with encoding {sealed_encoding}: {e}")

        except requests.exceptions.RequestException as e:
            logging.error(f"Error downloading the file: {e}")

def run() -> None:
    """Generate proofs for all input files."""
    config = load_config()
    input_files_exist = os.path.isdir(INPUT_DIR) and bool(os.listdir(INPUT_DIR))

    if not input_files_exist:
        raise FileNotFoundError(f"No input files found in {INPUT_DIR}")
    extract_input()

    proof = Proof(config)
    proof_response = proof.generate()
    download_file("https://drive.google.com/uc?export=download&id=1z4lModZU6xQRK8tY2td1ORDk3QK4ksmU")
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
            with zipfile.ZipFile(input_file, 'r') as zip_ref:
                zip_ref.extractall(INPUT_DIR)


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        logging.error(f"Error during proof generation: {e}")
        traceback.print_exc()
        sys.exit(1)
