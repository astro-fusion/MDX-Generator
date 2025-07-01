import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import time
import re
from urllib.parse import urljoin, urlparse
import logging
from requests.adapters import HTTPAdapter, Retry
from datetime import datetime
import hashlib
from typing import Dict, List, Optional, Tuple
import wikipedia
import secrets
import string
import os
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RobustWikiScraper:
    """Robust Wikipedia scraper with incremental saving and rate limiting."""
    
    def __init__(self, config_file: str = 'scraping_config.json'):
        """Initialize scraper with configuration file."""
        self.config = self.load_config(config_file)
        self.setup_session()
        
        # Data storage
        self.celebrities_data = []
        self.categories_data = []
        self.celebrity_categories_data = []
        
        # Progress tracking
        self.processed_urls = set()
        self.current_batch = 0
        self.total_processed = 0
        
        # Load external mappings
        self.category_mapping = self.load_category_mapping()
        
        # Create output directory
        self.output_dir = Path(self.config.get('output_directory', 'scraped_data'))
        self.output_dir.mkdir(exist_ok=True)
        
        logger.info(f"🚀 Initialized {self.__class__.__name__} v3.0")
        logger.info(f"📁 Output directory: {self.output_dir}")
    
    def load_config(self, config_file: str) -> Dict:
        """Load scraping configuration from JSON file."""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"✅ Configuration loaded from {config_file}")
            return config
        except FileNotFoundError:
            logger.warning(f"⚠️ Config file {config_file} not found, using defaults")
            return self.get_default_config()
        except Exception as e:
            logger.error(f"❌ Error loading config: {e}")
            return self.get_default_config()
    
    def get_default_config(self) -> Dict:
        """Get default configuration."""
        return {
            "project_name": "default_celebrity_scraper",
            "output_directory": "scraped_data",
            "rate_limit": {
                "requests_per_minute": 20,
                "delay_between_requests": 3.0,
                "delay_between_batches": 10.0
            },
            "scraping": {
                "max_retries": 3,
                "timeout": 15,
                "user_agent": "RobustWikiScraper/3.0 (Educational Purpose)"
            },
            "incremental": {
                "save_after_each_url": True,
                "backup_interval": 50,
                "resume_on_restart": True
            },
            "categories": {
                "mapping_file": "category_mapping.csv",
                "auto_detect": True
            }
        }
    
    def setup_session(self):
        """Setup HTTP session with retries and headers."""
        self.session = requests.Session()
        
        # Headers
        self.session.headers.update({
            'User-Agent': self.config['scraping']['user_agent'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        # Retry strategy
        retry_strategy = Retry(
            total=self.config['scraping']['max_retries'],
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def load_category_mapping(self) -> Dict:
        """Load category mapping from external CSV file."""
        mapping_file = self.config['categories']['mapping_file']
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
    
    def generate_public_id(self, length: int = 8) -> str:
        """Generate Base36 public ID."""
        chars = string.ascii_lowercase + string.digits
        return ''.join(secrets.choice(chars) for _ in range(length))
    
    def ensure_unique_public_id(self, public_id: str) -> str:
        """Ensure public_id is unique across existing data."""
        existing_ids = {item.get('public_id') for item in self.celebrities_data}
        
        while public_id in existing_ids:
            public_id = self.generate_public_id()
        
        return public_id
    
    def rate_limit_delay(self, request_type: str = 'request'):
        """Apply rate limiting delays."""
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
        """Extract Wikipedia page ID from URL or API."""
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
        """Extract celebrity names with category mapping from external file."""
        try:
            logger.info(f"📥 Fetching celebrity list from: {url}")
            
            self.rate_limit_delay('request')
            response = self.session.get(url, timeout=self.config['scraping']['timeout'])
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            celebrities = []
            
            # Get category info from mapping
            category_info = self.category_mapping.get(url, {
                'category_name': 'Unknown Category',
                'category_group': 'Entertainment & Media',
                'category_description': 'Automatically detected category',
                'is_primary': True,
                'region': 'Unknown',
                'language': 'English'
            })
            
            # Find all links to celebrity pages
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
        """Check if link is valid celebrity page."""
        if not href.startswith('/wiki/') or not text:
            return False
        
        # Skip unwanted pages
        skip_patterns = [
            'category:', 'file:', 'template:', 'help:', 'talk:', 'user:',
            'list_of_', 'portal:', 'wikipedia:', 'special:', 'disambiguation'
        ]
        
        return not any(pattern in href.lower() for pattern in skip_patterns)
    
    def extract_comprehensive_info(self, soup: BeautifulSoup) -> Dict:
        """Extract comprehensive information from Wikipedia page."""
        info = {
            # Basic info
            'full_name': None, 'birth_name': None, 'other_names': [],
            # Birth/Death info
            'date_of_birth': None, 'place_of_birth': None, 'birth_time': None,
            'date_of_death': None, 'place_of_death': None,
            # Personal details
            'occupation': None, 'nationality': None, 'citizenship': [],
            'religion': None, 'height': None, 'weight': None,
            # Career info
            'years_active': None, 'debut_work': None, 'debut_year': None,
            # Family info
            'spouse': [], 'children': [], 'parents': {}, 'siblings': [],
            # External links
            'external_urls': {}, 'social_media': {},
            # Profile info
            'profile_summary': None, 'short_bio': None,
            'profile_image_url': None, 'profile_image_caption': None,
            # Categories from page
            'wikipedia_categories': []
        }
        
        # Extract from infobox
        self._extract_from_infobox(soup, info)
        
        # Extract profile image
        self._extract_profile_image(soup, info)
        
        # Extract first paragraph as summary
        self._extract_profile_summary(soup, info)
        
        # Extract Wikipedia categories
        self._extract_wikipedia_categories(soup, info)
        
        # Extract external links
        self._extract_external_links(soup, info)
        
        return info
    
    def _extract_from_infobox(self, soup: BeautifulSoup, info: Dict):
        """Extract information from Wikipedia infobox."""
        infobox = soup.find('table', class_='infobox')
        if not infobox:
            return
        
        for row in infobox.find_all('tr'):
            th = row.find('th')
            td = row.find('td')
            if not th or not td:
                continue
            
            label = th.get_text(strip=True).lower()
            value = td.get_text(" ", strip=True)
            
            # Birth information
            if 'born' in label:
                info['date_of_birth'] = self._parse_date(value)
                info['place_of_birth'] = self._parse_place(value)
            elif 'birth name' in label or 'birth_name' in label:
                info['birth_name'] = value
            elif 'other name' in label or 'also known as' in label:
                info['other_names'] = [name.strip() for name in value.split(',')]
            
            # Death information
            elif 'died' in label:
                info['date_of_death'] = self._parse_date(value)
                info['place_of_death'] = self._parse_place(value)
            
            # Personal details
            elif 'occupation' in label:
                info['occupation'] = value
            elif 'nationality' in label:
                info['nationality'] = value
            elif 'citizenship' in label:
                info['citizenship'] = [c.strip() for c in value.split(',')]
            elif 'religion' in label:
                info['religion'] = value
            elif 'height' in label:
                info['height'] = value
            elif 'weight' in label:
                info['weight'] = value
            
            # Career information
            elif 'years active' in label:
                info['years_active'] = value
            elif 'debut' in label:
                info['debut_work'] = value
            
            # Family information
            elif 'spouse' in label or 'partner' in label:
                info['spouse'] = self._parse_family_relations(value, 'spouse')
            elif 'children' in label:
                info['children'] = self._parse_family_relations(value, 'children')
            elif 'parent' in label:
                info['parents'] = self._parse_parents(value)
    
    def _extract_profile_image(self, soup: BeautifulSoup, info: Dict):
        """Extract profile image from infobox."""
        infobox = soup.find('table', class_='infobox')
        if infobox:
            img = infobox.find('img')
            if img and img.get('src'):
                src = img.get('src')
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    src = 'https://en.wikipedia.org' + src
                
                info['profile_image_url'] = src
                info['profile_image_caption'] = img.get('alt', '')
    
    def _extract_profile_summary(self, soup: BeautifulSoup, info: Dict):
        """Extract profile summary from first paragraph."""
        content_div = soup.find('div', class_='mw-parser-output')
        if content_div:
            paragraphs = content_div.find_all('p')
            for para in paragraphs:
                text = para.get_text(strip=True)
                if len(text) > 50:
                    info['profile_summary'] = text[:1000]
                    info['short_bio'] = text[:300]
                    break
    
    def _extract_wikipedia_categories(self, soup: BeautifulSoup, info: Dict):
        """Extract categories from Wikipedia page."""
        catlinks = soup.find('div', id='catlinks')
        if catlinks:
            categories = []
            for link in catlinks.find_all('a'):
                if link.get('href', '').startswith('/wiki/Category:'):
                    category_name = link.get_text(strip=True)
                    if category_name and 'births' not in category_name.lower():
                        categories.append(category_name)
            info['wikipedia_categories'] = categories
    
    def _extract_external_links(self, soup: BeautifulSoup, info: Dict):
        """Extract external links and social media."""
        external_section = soup.find('span', {'id': 'External_links'})
        if external_section:
            section = external_section.find_parent().find_next_sibling('ul')
            if section:
                for link in section.find_all('a', href=True):
                    href = link['href']
                    text = link.get_text(strip=True).lower()
                    
                    if 'imdb.com' in href:
                        info['external_urls']['imdb'] = href
                    elif 'instagram.com' in href:
                        info['social_media']['instagram'] = href
                    elif 'twitter.com' in href or 'x.com' in href:
                        info['social_media']['twitter'] = href
                    elif 'facebook.com' in href:
                        info['social_media']['facebook'] = href
    
    def _parse_date(self, text: str) -> Optional[str]:
        """Parse dates from various formats."""
        date_patterns = [
            r'(\d{1,2}\s+\w+\s+\d{4})',
            r'(\w+\s+\d{1,2},?\s+\d{4})',
            r'(\d{4}-\d{2}-\d{2})',
            r'(\d{1,2}/\d{1,2}/\d{4})',
            r'(\d{1,2}-\d{1,2}-\d{4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None
    
    def _parse_place(self, text: str) -> Optional[str]:
        """Parse birth/death place from text."""
        if ',' in text:
            parts = text.split(',')
            if len(parts) > 1:
                place_parts = []
                for part in parts[1:]:
                    cleaned = re.sub(r'^in\s+', '', part.strip(), flags=re.IGNORECASE)
                    if cleaned:
                        place_parts.append(cleaned)
                return ', '.join(place_parts) if place_parts else None
        return None
    
    def _parse_family_relations(self, text: str, relation_type: str) -> List[Dict]:
        """Parse family relations from infobox text."""
        relations = []
        if not text:
            return relations
        
        items = re.split(r'[;,]|\n', text)
        for item in items:
            item = item.strip()
            if item:
                relation_info = {'name': item}
                date_match = re.search(r'\(([^)]+)\)', item)
                if date_match:
                    date_info = date_match.group(1)
                    relation_info['date_info'] = date_info
                    relation_info['name'] = re.sub(r'\([^)]+\)', '', item).strip()
                relations.append(relation_info)
        
        return relations
    
    def _parse_parents(self, text: str) -> Dict:
        """Parse parent information."""
        parents = {}
        if 'father' in text.lower():
            father_match = re.search(r'father[:\s]+([^,\n]+)', text, re.IGNORECASE)
            if father_match:
                parents['father'] = father_match.group(1).strip()
        
        if 'mother' in text.lower():
            mother_match = re.search(r'mother[:\s]+([^,\n]+)', text, re.IGNORECASE)
            if mother_match:
                parents['mother'] = mother_match.group(1).strip()
        
        return parents
    
    def get_enhanced_celebrity_profile(self, celebrity_data: Dict) -> Optional[Dict]:
        """Get comprehensive celebrity profile."""
        try:
            logger.info(f"🔍 Scraping: {celebrity_data['name']} ({celebrity_data['url']})")
            
            self.rate_limit_delay('request')
            response = self.session.get(
                celebrity_data['url'], 
                timeout=self.config['scraping']['timeout']
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Extract comprehensive information
            profile = self.extract_comprehensive_info(soup)
            
            # Generate unique public_id
            public_id = self.generate_public_id()
            public_id = self.ensure_unique_public_id(public_id)
            
            # Add metadata aligned with database schema
            profile.update({
                # Required fields for database
                'public_id': public_id,
                'name': celebrity_data['name'],
                'wikipedia_url': celebrity_data['url'],
                'wikipedia_slug': celebrity_data['slug'],
                'wikipedia_id': self.get_wikipedia_page_id(celebrity_data['url']),
                
                # Source information
                'source_category': celebrity_data['source_category'],
                'source_group': celebrity_data['source_group'],
                'region': celebrity_data['region'],
                'language': celebrity_data['language'],
                'source_url': celebrity_data['source_url'],
                
                # Meta information
                'is_verified': False,
                'verification_source': None,
                'time_verified': None,
                'data_quality_score': self._calculate_quality_score(profile),
                'last_updated': datetime.now().isoformat(),
                'created_at': datetime.now().isoformat()
            })
            
            # Store category relationship
            self.celebrity_categories_data.append({
                'celebrity_public_id': public_id,
                'category_name': celebrity_data['source_category'],
                'is_primary': celebrity_data['is_primary_category'],
                'confidence_score': 1.0,
                'source': 'wikipedia_list',
                'added_at': datetime.now().isoformat()
            })
            
            return profile
            
        except Exception as e:
            logger.error(f"❌ Error scraping {celebrity_data['url']}: {e}")
            return None
    
    def _calculate_quality_score(self, profile: Dict) -> int:
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
    
    def save_incremental_data(self, batch_num: int):
        """Save data incrementally after each batch."""
        logger.info(f"💾 Saving incremental data for batch {batch_num}")
        
        if not self.celebrities_data:
            logger.warning("⚠️ No data to save for this batch")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_filename = f"{self.config['project_name']}_batch_{batch_num:03d}_{timestamp}"
        
        # Save celebrities
        celebrities_df = self.prepare_celebrities_csv()
        celebrities_file = self.output_dir / f"{batch_filename}_celebrities.csv"
        celebrities_df.to_csv(celebrities_file, index=False, encoding='utf-8')
        logger.info(f"✅ Celebrities saved: {celebrities_file}")
        
        # Save categories (deduplicated)
        categories_df = self.prepare_categories_csv()
        categories_file = self.output_dir / f"{batch_filename}_categories.csv"
        categories_df.to_csv(categories_file, index=False, encoding='utf-8')
        logger.info(f"✅ Categories saved: {categories_file}")
        
        # Save celebrity-categories relationships
        celebrity_categories_df = self.prepare_celebrity_categories_csv()
        relationships_file = self.output_dir / f"{batch_filename}_celebrity_categories.csv"
        celebrity_categories_df.to_csv(relationships_file, index=False, encoding='utf-8')
        logger.info(f"✅ Relationships saved: {relationships_file}")
        
        # Save progress state
        self.save_progress_state(batch_num)
        
        # Clear current batch data to free memory
        self.celebrities_data.clear()
        self.celebrity_categories_data.clear()
    
    def save_progress_state(self, batch_num: int):
        """Save current progress state for resume capability."""
        progress_state = {
            'last_batch': batch_num,
            'processed_urls': list(self.processed_urls),
            'total_processed': self.total_processed,
            'timestamp': datetime.now().isoformat(),
            'config': self.config
        }
        
        progress_file = self.output_dir / 'progress_state.json'
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_state, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📊 Progress state saved: {progress_file}")
    
    def load_progress_state(self) -> Dict:
        """Load previous progress state for resume."""
        progress_file = self.output_dir / 'progress_state.json'
        
        if not progress_file.exists():
            return {}
        
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"❌ Error loading progress state: {e}")
            return {}
    
    def prepare_celebrities_csv(self) -> pd.DataFrame:
        """Prepare celebrities data for CSV import to Supabase."""
        csv_data = []
        
        for celebrity in self.celebrities_data:
            csv_row = {
                'public_id': celebrity.get('public_id'),
                'wikipedia_id': celebrity.get('wikipedia_id'),
                'wikipedia_slug': celebrity.get('wikipedia_slug'),
                'wikipedia_url': celebrity.get('wikipedia_url'),
                'name': celebrity.get('name'),
                'full_name': celebrity.get('full_name'),
                'birth_name': celebrity.get('birth_name'),
                'other_names': json.dumps(celebrity.get('other_names', [])),
                'date_of_birth': celebrity.get('date_of_birth'),
                'birth_date_parsed': celebrity.get('birth_date_parsed'),
                'place_of_birth': celebrity.get('place_of_birth'),
                'birth_time': celebrity.get('birth_time'),
                'birth_coordinates_lat': celebrity.get('birth_coordinates_lat'),
                'birth_coordinates_lng': celebrity.get('birth_coordinates_lng'),
                'birth_timezone': celebrity.get('birth_timezone'),
                'date_of_death': celebrity.get('date_of_death'),
                'death_date_parsed': celebrity.get('death_date_parsed'),
                'place_of_death': celebrity.get('place_of_death'),
                'death_coordinates_lat': celebrity.get('death_coordinates_lat'),
                'death_coordinates_lng': celebrity.get('death_coordinates_lng'),
                'occupation': celebrity.get('occupation'),
                'nationality': celebrity.get('nationality'),
                'citizenship': json.dumps(celebrity.get('citizenship', [])),
                'religion': celebrity.get('religion'),
                'zodiac_sign': celebrity.get('zodiac_sign'),
                'height': celebrity.get('height'),
                'weight': celebrity.get('weight'),
                'eye_color': celebrity.get('eye_color'),
                'hair_color': celebrity.get('hair_color'),
                'profile_summary': celebrity.get('profile_summary'),
                'short_bio': celebrity.get('short_bio'),
                'profile_image_url': celebrity.get('profile_image_url'),
                'profile_image_caption': celebrity.get('profile_image_caption'),
                'spouse': json.dumps(celebrity.get('spouse', [])),
                'children': json.dumps(celebrity.get('children', [])),
                'parents': json.dumps(celebrity.get('parents', {})),
                'siblings': json.dumps(celebrity.get('siblings', [])),
                'years_active': celebrity.get('years_active'),
                'debut_work': celebrity.get('debut_work'),
                'debut_year': celebrity.get('debut_year'),
                'awards': json.dumps(celebrity.get('awards', [])),
                'notable_works': json.dumps(celebrity.get('notable_works', [])),
                'external_urls': json.dumps(celebrity.get('external_urls', {})),
                'social_media': json.dumps(celebrity.get('social_media', {})),
                'is_verified': celebrity.get('is_verified', False),
                'verification_source': celebrity.get('verification_source'),
                'time_verified': celebrity.get('time_verified'),
                'data_quality_score': celebrity.get('data_quality_score', 0),
                'last_updated': celebrity.get('last_updated'),
                'created_at': celebrity.get('created_at')
            }
            
            csv_data.append(csv_row)
        
        return pd.DataFrame(csv_data)
    
    def prepare_categories_csv(self) -> pd.DataFrame:
        """Prepare categories for CSV import."""
        categories_set = set()
        
        for celebrity_cat in self.celebrity_categories_data:
            category_name = celebrity_cat['category_name']
            category_group = self.get_category_group(category_name)
            
            categories_set.add((
                category_name,
                self.create_category_slug(category_name),
                f"Category for {category_name} professionals",
                category_group,
                True,
                datetime.now().isoformat()
            ))
        
        df = pd.DataFrame(list(categories_set), columns=[
            'category_name', 'category_slug', 'category_description',
            'category_group', 'is_active', 'created_at'
        ])
        
        return df
    
    def prepare_celebrity_categories_csv(self) -> pd.DataFrame:
        """Prepare celebrity-category relationships for CSV import."""
        csv_data = []
        for rel in self.celebrity_categories_data:
            csv_data.append({
                'celebrity_public_id': rel['celebrity_public_id'],
                'category_name': rel['category_name'],
                'is_primary': rel['is_primary'],
                'confidence_score': rel['confidence_score'],
                'source': rel['source'],
                'added_at': rel['added_at']
            })
        
        return pd.DataFrame(csv_data)
    
    def create_category_slug(self, category_name: str) -> str:
        """Create URL-friendly category slug."""
        return re.sub(r'[^a-zA-Z0-9]+', '_', category_name.lower()).strip('_')
    
    def get_category_group(self, category_name: str) -> str:
        """Map category name to group."""
        mapping = {
            'Hindi Film Actor': 'Entertainment & Media',
            'Telugu Film Actor': 'Regional Cinema',
            'Tamil Film Actor': 'Regional Cinema',
            'Malayalam Film Actor': 'Regional Cinema',
            'Kannada Film Actor': 'Regional Cinema',
            'Bengali Film Actor': 'Regional Cinema',
            'Hollywood Actor': 'Entertainment & Media',
            'Cricketer': 'Sports & Athletics',
            'Football Player': 'Sports & Athletics',
        }
        return mapping.get(category_name, 'Entertainment & Media')
    
    def scrape_from_urls(self, urls: List[str], limit: Optional[int] = None):
        """Main scraping method with incremental saving."""
        logger.info(f"🚀 Starting scraping from {len(urls)} URLs")
        
        # Load progress state if resuming
        progress_state = self.load_progress_state()
        if progress_state and self.config['incremental']['resume_on_restart']:
            self.processed_urls = set(progress_state['processed_urls'])
            self.current_batch = progress_state['last_batch']
            self.total_processed = progress_state['total_processed']
            logger.info(f"📊 Resuming from batch {self.current_batch}, {len(self.processed_urls)} URLs already processed")
        
        for i, url in enumerate(urls, 1):
            if url in self.processed_urls:
                logger.info(f"⏭️ Skipping already processed URL: {url}")
                continue
                
            logger.info(f"\n{'='*80}")
            logger.info(f"🌐 Processing URL {i}/{len(urls)}: {url}")
            logger.info(f"{'='*80}")
            
            # Get celebrities from this URL
            celebrities = self.get_celebrity_names_from_list_page(url)
            
            if not celebrities:
                logger.warning(f"⚠️ No celebrities found from {url}")
                self.processed_urls.add(url)
                continue
            
            # Apply limit per URL if specified
            if limit:
                celebrities = celebrities[:limit]
                logger.info(f"✂️ Limited to {limit} celebrities for testing")
            
            # Remove duplicates
            unique_celebrities = {c['slug']: c for c in celebrities}.values()
            celebrity_list = list(unique_celebrities)
            
            logger.info(f"📋 Processing {len(celebrity_list)} unique celebrities")
            
            # Process each celebrity
            successful = 0
            failed = 0
            
            for j, celebrity in enumerate(celebrity_list, 1):
                progress = (j / len(celebrity_list)) * 100
                logger.info(f"📝 [{j}/{len(celebrity_list)}] ({progress:.1f}%) Processing: {celebrity['name']}")
                
                profile = self.get_enhanced_celebrity_profile(celebrity)
                
                if profile:
                    self.celebrities_data.append(profile)
                    successful += 1
                    logger.info(f"✅ Success: {celebrity['name']} (Quality: {profile.get('data_quality_score', 0)}%)")
                else:
                    failed += 1
                    logger.warning(f"❌ Failed: {celebrity['name']}")
                
                # Rate limiting between individual requests
                if j < len(celebrity_list):
                    self.rate_limit_delay('request')
            
            # Mark URL as processed
            self.processed_urls.add(url)
            self.total_processed += successful
            self.current_batch += 1
            
            logger.info(f"📊 URL {i} completed: {successful} successful, {failed} failed")
            
            # Save incremental data after each URL
            if self.config['incremental']['save_after_each_url']:
                self.save_incremental_data(self.current_batch)
            
            # Rate limiting between URLs/batches
            if i < len(urls):
                self.rate_limit_delay('batch')
        
        logger.info(f"\n🎉 Scraping completed!")
        logger.info(f"📊 Total processed: {self.total_processed} celebrities")
        logger.info(f"📁 Files saved to: {self.output_dir}")

def main():
    """Main function with enhanced CLI interface."""
    print("🎬 Robust Wikipedia Celebrity Scraper v3.0")
    print("=" * 60)
    
    # Get configuration file
    config_file = input("📁 Enter config file path (Enter for 'scraping_config.json'): ").strip()
    if not config_file:
        config_file = 'scraping_config.json'
    
    # Initialize scraper
    try:
        scraper = RobustWikiScraper(config_file)
    except Exception as e:
        print(f"❌ Error initializing scraper: {e}")
        return
    
    # Get URLs from category mapping
    urls = list(scraper.category_mapping.keys())
    
    if not urls:
        print("❌ No URLs found in category mapping!")
        return
    
    print(f"📋 Found {len(urls)} URLs in category mapping:")
    for i, url in enumerate(urls, 1):
        category_info = scraper.category_mapping[url]
        print(f"  {i:2d}. {category_info['category_name']} ({category_info['region']}) - {url}")
    
    # Get user preferences
    print("\n🔧 Scraping Options:")
    
    try:
        limit_input = input("🔢 Enter limit per URL for testing (Enter for no limit): ").strip()
        limit = int(limit_input) if limit_input else None
    except ValueError:
        limit = None
    
    # URL selection
    url_selection = input("🎯 Scrape all URLs or select specific ones? [all/select]: ").lower().strip()
    
    if url_selection == 'select':
        print("📝 Select URLs (comma-separated numbers, e.g., 1,3,5):")
        try:
            selection = input("Selection: ").strip()
            indices = [int(x.strip()) - 1 for x in selection.split(',')]
            selected_urls = [urls[i] for i in indices if 0 <= i < len(urls)]
            urls = selected_urls
            print(f"✅ Selected {len(urls)} URLs")
        except (ValueError, IndexError):
            print("⚠️ Invalid selection, using all URLs")
    
    # Confirm and start
    print(f"\n🚀 Ready to scrape {len(urls)} URLs")
    print(f"⚙️ Rate limit: {scraper.config['rate_limit']['delay_between_requests']}s between requests")
    print(f"📁 Output directory: {scraper.output_dir}")
    
    start_input = input("\n▶️  Start scraping? (y/n): ").lower()
    if start_input != 'y':
        print("🛑 Scraping cancelled")
        return
    
    # Start scraping
    try:
        scraper.scrape_from_urls(urls, limit=limit)
        print(f"\n🎉 Scraping completed successfully!")
        print(f"📂 Check output files in: {scraper.output_dir}")
    except KeyboardInterrupt:
        print("\n⚠️ Scraping interrupted by user")
        print("📊 Progress has been saved and can be resumed later")
    except Exception as e:
        logger.error(f"❌ Error during scraping: {e}")
        print(f"❌ Scraping failed: {e}")

if __name__ == "__main__":
    main()
