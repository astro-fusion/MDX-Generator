"""
Miscellaneous utility functions.
"""
import logging
import secrets
import string
import time
from typing import Dict, List, Optional
import pandas as pd
import re

logger = logging.getLogger(__name__)

def rate_limit_delay(config: Dict, request_type: str = 'request'):
    """Apply rate limiting delays."""
    if request_type == 'request':
        delay = config['rate_limit']['delay_between_requests']
    elif request_type == 'batch':
        delay = config['rate_limit']['delay_between_batches']
    else:
        delay = 1.0
    
    if delay > 0:
        logger.debug(f"⏱️ Rate limiting: waiting {delay}s")
        time.sleep(delay)

def generate_public_id(length: int = 8) -> str:
    """Generate Base36 public ID."""
    chars = string.ascii_lowercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))

def ensure_unique_public_id(public_id: str, celebrities_data: List[Dict]) -> str:
    """Ensure public_id is unique across existing data."""
    existing_ids = {item.get('public_id') for item in celebrities_data}
    
    while public_id in existing_ids:
        public_id = generate_public_id()
    
    return public_id

def get_wikipedia_page_id(session, url: str) -> Optional[str]:
    """Extract Wikipedia page ID from URL or API."""
    try:
        page_title = url.split('/wiki/')[-1]
        api_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{page_title}"
        
        response = session.get(api_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return str(data.get('pageid', ''))
    except Exception as e:
        logger.error(f"Error getting Wikipedia page ID: {e}")
    
    return None

def load_category_mapping(config: Dict) -> Dict:
    """Load category mapping from external CSV file."""
    mapping_file = config['categories']['mapping_file']
    try:
        df = pd.read_csv(mapping_file)
        mapping = {}
        
        for _, row in df.iterrows():
            url = row['url'].strip()
            mapping[url] = {
                'category_name': row['category_name'],
                'category_group': row.get('category_group', 'Entertainment & Media'),
                'category_description': row.get('category_description', ''),
                'is_primary': row.get('is_primary', True),
                'region': row.get('region', 'Global'),
                'language': row.get('language', 'English')
            }
        
        logger.info(f"✅ Loaded {len(mapping)} URL-category mappings from {mapping_file}")
        return mapping
        
    except FileNotFoundError:
        logger.error(f"❌ Category mapping file {mapping_file} not found!")
        return {}
    except Exception as e:
        logger.error(f"❌ Error loading category mapping: {e}")
        return {}

def calculate_quality_score(profile: Dict) -> int:
    """Calculate data quality score based on completeness."""
    score = 0
    important_fields = [
        'date_of_birth', 'place_of_birth', 'occupation',
        'profile_summary', 'nationality'
    ]
    
    for field in important_fields:
        if profile.get(field):
            score += 20
    
    # Bonus points
    if profile.get('profile_image_url'):
        score += 10
    if profile.get('external_urls'):
        score += 5
    if profile.get('spouse'):
        score += 5
    
    return min(score, 100)
