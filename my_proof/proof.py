import json
import logging
import os
from typing import Dict, Any
import requests
from jwt import encode as jwt_encode

from my_proof.models.proof_response import ProofResponse

# Task data type mapping with configurable points
TASK_DATA_TYPE_MAPPING = {
    "NETFLIX": {
        "NETFLIX_HISTORY": 50,
        "NETFLIX_FAVORITE": 50,
    },
    "SPOTIFY": {
        "SPOTIFY_PLAYLIST": 50,
        "SPOTIFY_HISTORY": 50,
    },
    "AMAZON": {
        "AMAZON_PRIME_VIDEO": 50,
        "AMAZON_ORDER_HISTORY": 50,
    },
    "TWITTER": {
        "TWITTER_USERINFO": 50,
    },
    "YOUTUBE": {
        "YOUTUBE_HISTORY": 50,
        "YOUTUBE_PLAYLIST": 50,
        "YOUTUBE_SUBSCRIBERS": 50,
    },
    "FARCASTER": {
        "FARCASTER_USERINFO": 50,
    },
}

# Contribution subtype weights
CONTRIBUTION_SUBTYPE_WEIGHTS = {
    "YOUTUBE_HISTORY": 1.5,
    "YOUTUBE_PLAYLIST": 1.2,
    "YOUTUBE_SUBSCRIBERS": 1.3,
    "NETFLIX_HISTORY": 1.4,
    "NETFLIX_FAVORITE": 1.1,
    "SPOTIFY_PLAYLIST": 1.2,
    "SPOTIFY_HISTORY": 1.3,
    "AMAZON_PRIME_VIDEO": 1.4,
    "AMAZON_ORDER_HISTORY": 1.1,
    "TWITTER_USERINFO": 1.0,
    "FARCASTER_USERINFO": 1.1,
}

CONTRIBUTION_THRESHOLD = 4
EXTRA_POINTS = 5

class Proof:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.proof_response = ProofResponse(dlp_id=config['dlp_id'])

    def generate(self) -> ProofResponse:
        """Generate proofs for all input files."""
        logging.info("Starting proof generation")

        proof_response_object = {
            'dlp_id': self.config.get('dlp_id', '24'),
            'valid': True,
        }

        for input_filename in os.listdir(self.config['input_dir']):
            input_file = os.path.join(self.config['input_dir'], input_filename)
            if os.path.splitext(input_file)[1].lower() == '.json':
                with open(input_file, 'r', encoding='utf-8') as f:
                    input_data = json.load(f)

                logging.info(f"Processing file: {input_filename}")

                jwt_token = self.generate_jwt_token()
                contribution_score_result = self.calculate_contribution_score(input_data)

                proof_response_object['authenticity'] = self.calculate_authenticity(input_data)
                proof_response_object['uniqueness'] = 1.0  # uniqueness is validated at the time of submission
                proof_response_object['quality'] = 1.0
                # Add other scores (e.g., ownership)
                proof_response_object['ownership'] = self.calculate_ownership_score(jwt_token, input_data)

                # Calculate the final score
                proof_response_object['score'] = self.calculate_score(proof_response_object)

                proof_response_object['attributes'] = {
                    'normalizedContributionScore': contribution_score_result['normalized_dynamic_score'],
                    'totalContributionScore': contribution_score_result['total_dynamic_score'],
                    'jwtToken': self.config.get('jwt_secret_key'),
                }

        logging.info(f"Proof response: {proof_response_object}")
        return proof_response_object

    def generate_jwt_token(self):
        secret_key = self.config.get('jwt_secret_key', 'default_secret')
        expiration_time = self.config.get('jwt_expiration_time', 180)
        return jwt_encode({}, secret_key, algorithm='HS256')

    def calculate_contribution_score(self, data_list: Dict[str, Any]) -> Dict[str, float]:
        contributions = data_list.get('contribution', [])

        total_dynamic_score = 0
        for item in contributions:
            type_ = item.get('type')
            task_subtype = item.get('taskSubType')

            if type_ and task_subtype:
                base_score = TASK_DATA_TYPE_MAPPING.get(type_, {}).get(task_subtype, 0)
                weight = CONTRIBUTION_SUBTYPE_WEIGHTS.get(task_subtype, 1)
                total_dynamic_score += base_score * weight

        if len(contributions) > CONTRIBUTION_THRESHOLD:
            total_dynamic_score += EXTRA_POINTS

        max_possible_score = sum(
            base * CONTRIBUTION_SUBTYPE_WEIGHTS.get(subtype, 1)
            for type_, subtypes in TASK_DATA_TYPE_MAPPING.items()
            for subtype, base in subtypes.items()
        )

        normalized_dynamic_score = min(total_dynamic_score / max_possible_score, 1)

        return {
            'total_dynamic_score': total_dynamic_score,
            'normalized_dynamic_score': normalized_dynamic_score,
        }

    def calculate_authenticity(self, data_list: Dict[str, Any]) -> float:
        contributions = data_list.get('contribution', [])
        valid_domains = ["wss://witness.reclaimprotocol.org/ws", "reclaimprotocol.org"]

        valid_count = sum(
            1 for contribution in contributions
            if contribution.get('witnesses', '').endswith(tuple(valid_domains))
        )

        return round(valid_count / len(contributions), 5) if contributions else 0

    def calculate_ownership_score(self, jwt_token: str, data: Dict[str, Any]) -> float:
        # if not jwt_token or not isinstance(jwt_token, str):
        #     raise ValueError('JWT token is required and must be a string')
        # if not data or not isinstance(data, dict) or 'walletAddress' not in data or not isinstance(data.get('subType'), list):
        #     raise ValueError('Invalid data format. Ensure walletAddress is a string and subType is an array.')

        # try:
        #     headers = {
        #         'Authorization': f'Bearer {jwt_token}',  # Attach JWT token in the Authorization header
        #     }
        #     response = requests.post(api_url, json=data, headers=headers)

        #     response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)

        #     # return response.json().get('success', False) and 1.0 or 0.0
            return 1.0
        # except requests.exceptions.RequestException as e:
        #     logging.error(f"Error during API request: {e}")
        #     return 0.0

        # except requests.exceptions.HTTPError as error:
        #     print({'error': error})
        #     if error.response.status_code == 400:
        #         return 0.0
        #     raise ValueError(f'API call failed: {error.response.json().get("error", str(error))}')


    def calculate_score(self, proof_response_object: Dict[str, Any]) -> float:
        attributes = ['authenticity', 'uniqueness', 'contribution', 'ownership']

        valid_attributes = [
            proof_response_object.get(attr, 0) for attr in attributes
            if proof_response_object.get(attr) is not None
        ]

        if not valid_attributes:
            return 0

        return round(sum(valid_attributes) / len(valid_attributes), 5)
