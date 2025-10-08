import json
import logging
from pathlib import Path

def load_configuration(config_path: Path):
    """Load configuration from config.json file."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            logging.info("✓ Configuration successfully loaded from %s", config_path)
            return config.get('file_categories', {})
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error("❌ Error loading %s: %s. Using default configuration.", config_path, e)
        # Fallback to default configuration if file is missing or corrupt
        return {
            'Images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico', '.tiff'],
            'Documents': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.xls', '.xlsx', '.ppt', '.pptx'],
            'Videos': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp'],
            'Audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'],
            'Archives': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'],
            'Programs': ['.exe', '.msi', '.dmg', '.pkg', '.deb', '.rpm', '.appx'],
            'Code': ['.py', '.js', '.html', '.css', '.java', '.cpp', '.c', '.php', '.rb', '.go'],
            'Others': []
        }
