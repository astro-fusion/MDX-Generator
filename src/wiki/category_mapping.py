import pandas as pd
import logging

logger = logging.getLogger(__name__)

def load_category_mapping(mapping_file: str) -> dict:
    """Load category mapping from external CSV file."""
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