# pdf_anonymizer/config/settings.py
from typing import Dict, Any
import json
import logging

class ConfigManager:
    DEFAULT_CONFIG = {
        "replacement_patterns": {
            "Names": {
                "default": "[REDACTED]",
                "custom": "[NAME]",
                "format": "{category}-{index}"
            },
            "PhoneNumbers": {
                "default": "[PHONE]",
                "custom": "XXX-XXX-XXXX",
                "format": "{category}-{index}"
            }
        },
        "confidence_thresholds": {
            "ocr": 0.8,
            "pattern_matching": 0.9
        },
        "enabled_categories": ["Names", "PhoneNumbers", "SSN", "Email"]
    }
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path
        self.config = self.DEFAULT_CONFIG.copy()
        if config_path:
            self.load_config()
    
    def load_config(self) -> None:
        try:
            with open(self.config_path, 'r') as f:
                user_config = json.load(f)
                self.config.update(user_config)
        except Exception as e:
            logging.warning(f"Could not load config: {str(e)}")
    
    def save_config(self) -> None:
        if self.config_path:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
