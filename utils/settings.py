"""
Settings management for MDX Generator.

This module handles saving and loading user preferences.
"""
import os
import json
from pathlib import Path

# Path to settings file
SETTINGS_FILE = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "settings.json"

# Default settings
DEFAULT_SETTINGS = {
    "last_directory": None,
}

def load_settings():
    """
    Load settings from settings.json file.
    
    Returns:
        dict: Settings dictionary
    """
    try:
        if not SETTINGS_FILE.exists():
            return DEFAULT_SETTINGS.copy()
            
        with open(SETTINGS_FILE, 'r') as f:
            settings = json.load(f)
            
        # Merge with defaults to ensure all keys exist
        result = DEFAULT_SETTINGS.copy()
        result.update(settings)
        return result
    except Exception as e:
        print(f"Error loading settings: {str(e)}")
        return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    """
    Save settings to settings.json file.
    
    Args:
        settings (dict): Settings to save
    """
    try:
        # Create parent directories if they don't exist
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
            
    except Exception as e:
        print(f"Error saving settings: {str(e)}")

def update_last_directory(directory):
    """
    Update the last used directory in settings.
    
    Args:
        directory (str): Path to directory
    """
    if not directory:
        return
        
    settings = load_settings()
    settings["last_directory"] = directory
    save_settings(settings)

def get_last_directory():
    """
    Get the last used directory from settings.
    
    Returns:
        str: Path to last used directory or None if not set
    """
    settings = load_settings()
    directory = settings.get("last_directory")
    
    # Validate directory still exists
    if directory and not os.path.isdir(directory):
        return None
        
    return directory