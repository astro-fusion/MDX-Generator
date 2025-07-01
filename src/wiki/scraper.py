import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import time
import re
from urllib.parse import urljoin
import logging
from requests.adapters import HTTPAdapter, Retry
from datetime import datetime
import secrets
import string
from pathlib import Path
from typing import Dict, List, Optional

from .scraper_config import load_config, get_default_config
from .category_mapping import load_category_mapping
from .celebrity_parser import extract_comprehensive_info

logger = logging.getLogger(__name__)

class RobustWikiScraper:
    def __init__(self, config_file: str = 'scraping_config.json'):
        self.config = load_config(config_file)
        self.setup_session()
        self.celebrities_data = []
        self.categories_data = []
        self.celebrity_categories_data = []
        self.processed_urls = set()
        self.current_batch = 0
        self.total_processed = 0
        self.category_mapping = load_category_mapping(self.config['categories']['mapping_file'])
        self.output_dir = Path(self.config.get('output_directory', 'scraped_data'))
        self.output_dir.mkdir(exist_ok=True)
        logger.info(f"🚀 Initialized {self.__class__.__name__} v3.0")
        logger.info(f"📁 Output directory: {self.output_dir}")

    def setup_session(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.config['scraping']['user_agent'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        retry_strategy = Retry(
            total=self.config['scraping']['max_retries'],
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def generate_public_id(self, length: int = 8) -> str:
        chars = string.ascii_lowercase + string.digits
        return ''.join(secrets.choice(chars) for _ in range(length))

    def ensure_unique_public_id(self, public_id: str) -> str:
        existing_ids = {item.get('public_id') for item in self.celebrities_data}
        while public_id in existing_ids:
            public_id = self.generate_public_id()
        return public_id

    def rate_limit_delay(self, request_type: str = 'request'):
        if request_type == 'request':
            delay = self.config['rate_limit']['delay_between_requests']
        elif request_type == 'batch':
            delay = self.config['rate_limit']['delay_between_batches']
        else:
            delay = 1.0
        if delay > 0:
            logger.debug(f"⏱️ Rate limiting: waiting {delay}s")
            time.sleep(delay)

    def get_wikipedia_page_id(self, url: str) -> Optional[str]:
        try:
            page_title = url.split('/wiki/')[-1]
            api_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{page_title}"
            self.rate_limit_delay('request')
            response = self.session.get(api_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return str(data.get('pageid', ''))
        except Exception as e:
            logger.error(f"Error getting Wikipedia page ID: {e}")
        return None

    def get_celebrity_names_from_list_page(self, url: str) -> List[Dict]:
        try:
            logger.info(f"📥 Fetching celebrity list from: {url}")
            self.rate_limit_delay('request')
            response = self.session.get(url, timeout=self.config['scraping']['timeout'])
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'lxml')
            celebrities = []
            category_info = self.category_mapping.get(url, {
                'category_name': 'Unknown Category',
                'category_group': 'Entertainment & Media',
                'category_description': 'Automatically detected category',
                'is_primary': True,
                'region': 'Unknown',
                'language': 'English'
            })
            links = soup.find_all('a', href=True)
            logger.info(f"🔍 Processing {len(links)} links...")
            for link in links:
                href = link['href']
                if self.is_valid_celebrity_link(href, link.text):
                    celebrity_url = urljoin('https://en.wikipedia.org', href)
                    celebrity_slug = href.split('/wiki/')[-1]
                    celebrities.append({
                        'name': link.text.strip(),
                        'url': celebrity_url,
                        'slug': celebrity_slug,
                        'source_category': category_info['category_name'],
                        'source_group': category_info['category_group'],
                        'region': category_info['region'],
                        'language': category_info['language'],
                        'source_url': url,
                        'is_primary_category': category_info['is_primary']
                    })
            logger.info(f"✅ Found {len(celebrities)} potential celebrities from {url}")
            return celebrities
        except Exception as e:
            logger.error(f"❌ Error fetching celebrity list from {url}: {e}")
            return []

    def is_valid_celebrity_link(self, href: str, text: str) -> bool:
        if not href.startswith('/wiki/') or not text:
            return False
        skip_patterns = [
            'category:', 'file:', 'template:', 'help:', 'talk:', 'user:',
            'list_of_', 'portal:', 'wikipedia:', 'special:', 'disambiguation'
        ]
        return not any(pattern in href.lower() for pattern in skip_patterns)

    def scrape_from_urls(self, urls: List[str], limit: Optional[int] = None):
        logger.info(f"🚀 Starting scraping from {len(urls)} URLs")
        for i, url in enumerate(urls, 1):
            logger.info(f"\n{'='*80}")
            logger.info(f"🌐 Processing URL {i}/{len(urls)}: {url}")
            logger.info(f"{'='*80}")
            celebrities = self.get_celebrity_names_from_list_page(url)
            if not celebrities:
                logger.warning(f"⚠️ No celebrities found from {url}")
                continue
            if limit:
                celebrities = celebrities[:limit]
                logger.info(f"✂️ Limited to {limit} celebrities for testing")
            unique_celebrities = {c['slug']: c for c in celebrities}.values()
            celebrity_list = list(unique_celebrities)
            logger.info(f"📋 Processing {len(celebrity_list)} unique celebrities")
            for j, celebrity in enumerate(celebrity_list, 1):
                logger.info(f"📝 [{j}/{len(celebrity_list)}] Processing: {celebrity['name']}")
                profile = self.get_enhanced_celebrity_profile(celebrity)
                if profile:
                    self.celebrities_data.append(profile)
                    logger.info(f"✅ Success: {celebrity['name']}")
                else:
                    logger.warning(f"❌ Failed: {celebrity['name']}")
                if j < len(celebrity_list):
                    self.rate_limit_delay('request')
            self.rate_limit_delay('batch')
        logger.info(f"\n🎉 Scraping completed!")
        logger.info(f"📊 Total processed: {len(self.celebrities_data)} celebrities")
        logger.info(f"📁 Files saved to: {self.output_dir}")

    def get_enhanced_celebrity_profile(self, celebrity_data: Dict) -> Optional[Dict]:
        try:
            logger.info(f"🔍 Scraping: {celebrity_data['name']} ({celebrity_data['url']})")
            self.rate_limit_delay('request')
            response = self.session.get(
                celebrity_data['url'],
                timeout=self.config['scraping']['timeout']
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'lxml')
            profile = extract_comprehensive_info(soup)
            public_id = self.generate_public_id()
            public_id = self.ensure_unique_public_id(public_id)
            profile.update({
                'public_id': public_id,
                'name': celebrity_data['name'],
                'wikipedia_url': celebrity_data['url'],
                'wikipedia_slug': celebrity_data['slug'],
                'wikipedia_id': self.get_wikipedia_page_id(celebrity_data['url']),
                'source_category': celebrity_data['source_category'],
                'source_group': celebrity_data['source_group'],
                'region': celebrity_data['region'],
                'language': celebrity_data['language'],
                'source_url': celebrity_data['source_url'],
                'is_verified': False,
                'verification_source': None,
                'time_verified': None,
                'data_quality_score': 0,
                'last_updated': datetime.now().isoformat(),
                'created_at': datetime.now().isoformat()
            })
            return profile
        except Exception as e:
            logger.error(f"❌ Error scraping {celebrity_data['url']}: {e}")
            return None