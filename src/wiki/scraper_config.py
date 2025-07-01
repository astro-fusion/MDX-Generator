import json
import logging

logger = logging.getLogger(__name__)

def load_config(config_file: str) -> dict:
    """Load scraping configuration from JSON file."""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        logger.info(f"✅ Configuration loaded from {config_file}")
        return config
    except FileNotFoundError:
        logger.warning(f"⚠️ Config file {config_file} not found, using defaults")
        return get_default_config()
    except Exception as e:
        logger.error(f"❌ Error loading config: {e}")
        return get_default_config()

def get_default_config() -> dict:
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