"""
Handles saving and loading of data, including progress state.
"""
import json
import logging
from pathlib import Path
from typing import Dict, List
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)

def save_incremental_data(celebrities_data: List[Dict], celebrity_categories_data: List[Dict], config: Dict, batch_num: int, output_dir: Path):
    """Save data incrementally after each batch."""
    logger.info(f"💾 Saving incremental data for batch {batch_num}")
    
    if not celebrities_data:
        logger.warning("⚠️ No data to save for this batch")
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_filename = f"{config['project_name']}_batch_{batch_num:03d}_{timestamp}"
    
    # Save celebrities
    celebrities_df = prepare_celebrities_csv(celebrities_data)
    celebrities_file = output_dir / f"{batch_filename}_celebrities.csv"
    celebrities_df.to_csv(celebrities_file, index=False, encoding='utf-8')
    logger.info(f"✅ Celebrities saved: {celebrities_file}")
    
    # Save categories (deduplicated)
    categories_df = prepare_categories_csv(celebrities_data)
    categories_file = output_dir / f"{batch_filename}_categories.csv"
    categories_df.to_csv(categories_file, index=False, encoding='utf-8')
    logger.info(f"✅ Categories saved: {categories_file}")
    
    # Save celebrity-categories relationships
    celebrity_categories_df = prepare_celebrity_categories_csv(celebrity_categories_data)
    relationships_file = output_dir / f"{batch_filename}_celebrity_categories.csv"
    celebrity_categories_df.to_csv(relationships_file, index=False, encoding='utf-8')
    logger.info(f"✅ Relationships saved: {relationships_file}")

def save_progress_state(batch_num: int, processed_urls: set, total_processed: int, config: Dict, output_dir: Path):
    """Save current progress state for resume capability."""
    progress_state = {
        'last_batch': batch_num,
        'processed_urls': list(processed_urls),
        'total_processed': total_processed,
        'timestamp': datetime.now().isoformat(),
        'config': config
    }
    
    progress_file = output_dir / 'progress_state.json'
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump(progress_state, f, indent=2, ensure_ascii=False)
    
    logger.info(f"📊 Progress state saved: {progress_file}")

def load_progress_state(output_dir: Path) -> Dict:
    """Load previous progress state for resume."""
    progress_file = output_dir / 'progress_state.json'
    
    if not progress_file.exists():
        return {}
    
    try:
        with open(progress_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"❌ Error loading progress state: {e}")
        return {}

def prepare_celebrities_csv(celebrities_data: List[Dict]) -> pd.DataFrame:
    """Prepare celebrities data for CSV export."""
    return pd.DataFrame(celebrities_data)

def prepare_categories_csv(celebrities_data: List[Dict]) -> pd.DataFrame:
    """Prepare categories data for CSV export."""
    categories = {}
    for celebrity in celebrities_data:
        cat_name = celebrity['source_category']
        if cat_name not in categories:
            categories[cat_name] = {
                'category_name': cat_name,
                'category_group': celebrity['source_group'],
                'region': celebrity['region'],
                'language': celebrity['language']
            }
    return pd.DataFrame(categories.values())

def prepare_celebrity_categories_csv(celebrity_categories_data: List[Dict]) -> pd.DataFrame:
    """Prepare celebrity-category relationship data for CSV export."""
    return pd.DataFrame(celebrity_categories_data)
