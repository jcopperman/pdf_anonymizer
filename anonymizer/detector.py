# anonymizer/detector.py

import re
import logging
from typing import Dict, List, Pattern, Any
from dataclasses import dataclass
from utils.validation import validate_pattern

@dataclass
class PIIMatch:
    """Class for storing PII match information"""
    text: str
    category: str
    confidence: float
    start: int
    end: int
    replacement: str = ""

class PatternManager:
    def __init__(self):
        """Initialize the Pattern Manager with predefined PII patterns"""
        self.logger = logging.getLogger(__name__)
        self.patterns: Dict[str, Dict[str, Any]] = {
            "Email": {
                "pattern": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                "validator": lambda x: '@' in x and '.' in x,
                "confidence": 0.9
            },
            "Phone": {
                "pattern": r'\b(\+\d{1,2}\s?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b',
                "validator": lambda x: len(re.sub(r'[\s()-.]', '', x)) >= 10,
                "confidence": 0.85
            },
            "SSN": {
                "pattern": r'\b\d{3}[-]?\d{2}[-]?\d{4}\b',
                "validator": lambda x: len(re.sub(r'[-]', '', x)) == 9,
                "confidence": 0.95
            },
            "CreditCard": {
                "pattern": r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
                "validator": lambda x: validate_pattern("credit_card", x),
                "confidence": 0.9
            },
            "Date": {
                "pattern": r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b',
                "validator": lambda x: True,  # Add date validation if needed
                "confidence": 0.8
            }
        }
        
        # Compile patterns for better performance
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for better performance"""
        for category in self.patterns:
            pattern = self.patterns[category]["pattern"]
            self.patterns[category]["compiled"] = re.compile(pattern)

    def detect_pii(self, text: str) -> Dict[str, List[PIIMatch]]:
        """
        Detect PII in the given text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary of PII matches by category
        """
        matches: Dict[str, List[PIIMatch]] = {category: [] for category in self.patterns}
        
        try:
            for category, pattern_info in self.patterns.items():
                compiled_pattern: Pattern = pattern_info["compiled"]
                validator = pattern_info["validator"]
                base_confidence = pattern_info["confidence"]
                
                for match in compiled_pattern.finditer(text):
                    match_text = match.group()
                    
                    # Skip if the match doesn't pass validation
                    if not validator(match_text):
                        continue
                    
                    # Create PIIMatch object
                    pii_match = PIIMatch(
                        text=match_text,
                        category=category,
                        confidence=base_confidence,
                        start=match.start(),
                        end=match.end()
                    )
                    
                    matches[category].append(pii_match)
                    
            return matches
            
        except Exception as e:
            self.logger.error(f"Error detecting PII: {str(e)}")
            raise

    def get_supported_categories(self) -> List[str]:
        """Get list of supported PII categories"""
        return list(self.patterns.keys())

    def add_pattern(self, category: str, pattern: str, validator: callable, confidence: float = 0.8):
        """
        Add a new PII pattern.
        
        Args:
            category: Name of the PII category
            pattern: Regex pattern string
            validator: Validation function
            confidence: Base confidence score (0.0 to 1.0)
        """
        try:
            self.patterns[category] = {
                "pattern": pattern,
                "compiled": re.compile(pattern),
                "validator": validator,
                "confidence": confidence
            }
        except Exception as e:
            self.logger.error(f"Error adding pattern: {str(e)}")
            raise

    def remove_pattern(self, category: str):
        """Remove a PII pattern category"""
        try:
            if category in self.patterns:
                del self.patterns[category]
        except Exception as e:
            self.logger.error(f"Error removing pattern: {str(e)}")
            raise
