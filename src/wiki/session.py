"""
Manages HTTP sessions for the scraper.
"""
import requests
from requests.adapters import HTTPAdapter, Retry
from typing import Dict

def create_session(config: Dict) -> requests.Session:
    """Setup HTTP session with retries and headers."""
    session = requests.Session()
    
    # Headers
    session.headers.update({
        'User-Agent': config['scraping']['user_agent'],
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    })
    
    # Retry strategy
    retry_strategy = Retry(
        total=config['scraping']['max_retries'],
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session
