# anonymizer/replacer.py

import logging
from typing import Dict, Any, Optional
from .detector import PIIMatch

class ReplacementManager:
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the Replacement Manager.
        
        Args:
            config: Optional configuration dictionary
        """
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        self.replacement_patterns = self._init_replacement_patterns()
        self.category_counters = {}

    def _init_replacement_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize default replacement patterns for each PII category"""
        default_patterns = {
            "Email": {
                "format": "[EMAIL-{index}]",
                "preserve_domain": True,
                "default": "[REDACTED-EMAIL]"
            },
            "Phone": {
                "format": "[PHONE-{index}]",
                "preserve_area": False,
                "default": "[REDACTED-PHONE]"
            },
            "SSN": {
                "format": "[SSN-{index}]",
                "preserve_last": False,
                "default": "[REDACTED-SSN]"
            },
            "CreditCard": {
                "format": "[CC-{index}]",
                "preserve_last": True,
                "default": "[REDACTED-CC]"
            },
            "Date": {
                "format": "[DATE-{index}]",
                "preserve_year": True,
                "default": "[REDACTED-DATE]"
            }
        }

        # Override defaults with any config settings
        if self.config.get("replacement_patterns"):
            for category, settings in self.config["replacement_patterns"].items():
                if category in default_patterns:
                    default_patterns[category].update(settings)

        return default_patterns

    def get_replacement(self, match: PIIMatch) -> str:
        """
        Get replacement text for a PII match.
        
        Args:
            match: PIIMatch object containing the detected PII
            
        Returns:
            Replacement text string
        """
        try:
            category = match.category
            
            # Initialize counter for this category if not exists
            if category not in self.category_counters:
                self.category_counters[category] = 0
            
            # Increment counter
            self.category_counters[category] += 1
            
            # Get replacement pattern
            pattern = self.replacement_patterns.get(category, {})
            
            if not pattern:
                return "[REDACTED]"
            
            # Generate replacement text based on pattern
            replacement = self._generate_replacement(
                match.text,
                pattern,
                self.category_counters[category]
            )
            
            return replacement
            
        except Exception as e:
            self.logger.error(f"Error generating replacement: {str(e)}")
            return "[ERROR]"

    def _generate_replacement(self, original: str, pattern: Dict[str, Any], index: int) -> str:
        """
        Generate replacement text based on pattern and settings.
        
        Args:
            original: Original text
            pattern: Replacement pattern settings
            index: Counter index for this category
            
        Returns:
            Generated replacement text
        """
        try:
            # Use format string if available, otherwise use default
            if "format" in pattern:
                replacement = pattern["format"].format(index=index)
            else:
                replacement = pattern.get("default", "[REDACTED]")
            
            # Apply preservation rules if any
            if pattern.get("preserve_domain") and "@" in original:
                domain = original.split("@")[1]
                replacement = f"{replacement}@{domain}"
            
            if pattern.get("preserve_last"):
                last_four = original[-4:]
                replacement = f"{replacement}-{last_four}"
            
            if pattern.get("preserve_year") and len(original) >= 4:
                year = original[-4:]
                if year.isdigit():
                    replacement = f"{replacement} ({year})"
            
            return replacement
            
        except Exception as e:
            self.logger.error(f"Error in replacement generation: {str(e)}")
            return pattern.get("default", "[REDACTED]")

    def reset_counters(self):
        """Reset all category counters"""
        self.category_counters = {}

    def add_replacement_pattern(self, category: str, pattern: Dict[str, Any]):
        """
        Add a new replacement pattern.
        
        Args:
            category: PII category name
            pattern: Dictionary containing replacement pattern settings
        """
        try:
            self.replacement_patterns[category] = pattern
        except Exception as e:
            self.logger.error(f"Error adding replacement pattern: {str(e)}")
            raise

    def get_replacement_pattern(self, category: str) -> Dict[str, Any]:
        """
        Get replacement pattern for a category.
        
        Args:
            category: PII category name
            
        Returns:
            Dictionary containing replacement pattern settings
        """
        return self.replacement_patterns.get(category, {})
