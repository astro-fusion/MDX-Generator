"""This module contains the main scraper class."""
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from bs4 import BeautifulSoup

from . import config as cfg
from . import session as sess
from . import parser
from . import storage
from . import utils

logger = logging.getLogger(__name__)

class WikiScraper:
    """A modular Wikipedia scraper."""

    def __init__(self, config_file: str = 'scraping_config.json'):
        self.config = cfg.load_config(config_file)
        self.session = sess.create_session(self.config)

        self.celebrities_data = []
        self.celebrity_categories_data = []

        self.processed_urls = set()
        self.current_batch = 0
        self.total_processed = 0

        self.category_mapping = utils.load_category_mapping(self.config)

        self.output_dir = Path(self.config.get('output_directory', 'scraped_data'))
        self.output_dir.mkdir(exist_ok=True)

        logger.info(f"🚀 Initialized {self.__class__.__name__}")
        logger.info(f"📁 Output directory: {self.output_dir}")

    def get_enhanced_celebrity_profile(self, celebrity_data: Dict) -> Optional[Dict]:
        """Get comprehensive celebrity profile."""
        try:
            logger.info(f"🔍 Scraping: {celebrity_data['name']} ({celebrity_data['url']})")

            utils.rate_limit_delay(self.config, 'request')
            response = self.session.get(
                celebrity_data['url'],
                timeout=self.config['scraping']['timeout']
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'lxml')

            profile = parser.extract_comprehensive_info(soup)

            public_id = utils.generate_public_id()
            public_id = utils.ensure_unique_public_id(public_id, self.celebrities_data)

            profile.update({
                'public_id': public_id,
                'name': celebrity_data['name'],
                'wikipedia_url': celebrity_data['url'],
                'wikipedia_slug': celebrity_data['slug'],
                'wikipedia_id': utils.get_wikipedia_page_id(self.session, celebrity_data['url']),

                'source_category': celebrity_data['source_category'],
                'source_group': celebrity_data['source_group'],
                'region': celebrity_data['region'],
                'language': celebrity_data['language'],
                'source_url': celebrity_data['source_url'],

                'is_verified': False,
                'verification_source': None,
                'time_verified': None,
                'data_quality_score': utils.calculate_quality_score(profile),
                'last_updated': datetime.now().isoformat(),
                'created_at': datetime.now().isoformat()
            })

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

    def scrape_from_urls(self, urls: List[str], limit: Optional[int] = None):
        """Main scraping method with incremental saving."""
        logger.info(f"🚀 Starting scraping from {len(urls)} URLs")

        progress_state = storage.load_progress_state(self.output_dir)
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

            utils.rate_limit_delay(self.config, 'request')
            response = self.session.get(url, timeout=self.config['scraping']['timeout'])
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'lxml')

            celebrities = parser.get_celebrity_names_from_list_page(soup, url, self.category_mapping)

            if not celebrities:
                logger.warning(f"⚠️ No celebrities found from {url}")
                self.processed_urls.add(url)
                continue

            if limit:
                celebrities = celebrities[:limit]
                logger.info(f"✂️ Limited to {limit} celebrities for testing")

            unique_celebrities = {c['slug']: c for c in celebrities}.values()
            celebrity_list = list(unique_celebrities)

            logger.info(f"📋 Processing {len(celebrity_list)} unique celebrities")

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

                if j < len(celebrity_list):
                    utils.rate_limit_delay(self.config, 'request')

            self.processed_urls.add(url)
            self.total_processed += successful
            self.current_batch += 1

            logger.info(f"📊 URL {i} completed: {successful} successful, {failed} failed")

            if self.config['incremental']['save_after_each_url']:
                storage.save_incremental_data(self.celebrities_data, self.celebrity_categories_data, self.config, self.current_batch, self.output_dir)
                storage.save_progress_state(self.current_batch, self.processed_urls, self.total_processed, self.config, self.output_dir)
                self.celebrities_data.clear()
                self.celebrity_categories_data.clear()

            if i < len(urls):
                utils.rate_limit_delay(self.config, 'batch')

        logger.info(f"\n🎉 Scraping completed!")
        logger.info(f"📊 Total processed: {self.total_processed} celebrities")
        logger.info(f"📁 Files saved to: {self.output_dir}")
