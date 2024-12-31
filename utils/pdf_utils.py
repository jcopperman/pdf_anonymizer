import fitz  # PyMuPDF
import re
import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import os

@dataclass
class PDFContext:
    """Stores context information for PII detection"""
    preceding_text: str
    following_text: str
    page_number: int
    bbox: tuple
    is_table_cell: bool
    nearby_labels: List[str]

@dataclass
class PIIMatch:
    """Represents a detected PII instance with context"""
    category: str
    text: str
    context: PDFContext
    replacement: str
    confidence: float

class PDFPatternManager:
    """Manages PII detection patterns with context awareness"""
    
    DEFAULT_PATTERNS = {
        "Names": {
            "patterns": [
                r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}\b'
            ],
            "labels": [
                r'\b(?:name|full name|customer|client|account holder)\s*:?\s*$',
                r'^name\s*:',
            ],
            "replacement": "[REDACTED NAME]",
            "confidence_threshold": 0.7
        },
        "Account Numbers": {
            "patterns": [
                r'\b\d{10,16}\b',
                r'\b[A-Z]{2}\d{2}(?:\s?\d{4}){2,4}\b'  # IBAN-like
            ],
            "labels": [
                r'\b(?:account|acc|account no|reference)\s*:?\s*$',
                r'^account\s*:',
            ],
            "replacement": "[REDACTED ACCOUNT]",
            "confidence_threshold": 0.8
        },
        "Addresses": {
            "patterns": [
                r'\b\d+\s+[A-Za-z\s]+(?:Road|Street|Ave|Boulevard|Lane|Drive)\b',
                r'\b(?:P\.?O\.?\s*Box|Post Office Box)\s+\d+\b'
            ],
            "labels": [
                r'\b(?:address|location|residence)\s*:?\s*$',
                r'^address\s*:',
            ],
            "replacement": "[REDACTED ADDRESS]",
            "confidence_threshold": 0.75
        }
    }

    def __init__(self):
        self.patterns = self.load_patterns()

    def load_patterns(self) -> Dict:
        """Load patterns from config file or use defaults"""
        config_path = "pii_patterns.json"
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return self.DEFAULT_PATTERNS
        return self.DEFAULT_PATTERNS

    def save_patterns(self):
        """Save current patterns to config file"""
        with open("pii_patterns.json", 'w') as f:
            json.dump(self.patterns, f, indent=2)

    def add_pattern(self, category: str, pattern: str, labels: List[str], replacement: str):
        """Add a new pattern to a category"""
        if category not in self.patterns:
            self.patterns[category] = {
                "patterns": [],
                "labels": [],
                "replacement": replacement,
                "confidence_threshold": 0.7
            }
        self.patterns[category]["patterns"].append(pattern)
        self.patterns[category]["labels"].extend(labels)
        self.save_patterns()

class PDFAnalyzer:
    """Analyzes PDF structure and content"""
    
    def __init__(self, doc: fitz.Document):
        self.doc = doc

    def is_table_cell(self, bbox: tuple, page_num: int) -> bool:
        """Detect if a text block is likely part of a table"""
        page = self.doc[page_num]
        # Look for aligned text blocks and regular spacing
        blocks = page.get_text("dict")["blocks"]
        
        # Check for regular vertical alignment
        x0, y0, x1, y1 = bbox
        aligned_blocks = [
            block for block in blocks
            if abs(block["bbox"][0] - x0) < 5  # Same x position
            or abs(block["bbox"][2] - x1) < 5   # Same width
        ]
        
        return len(aligned_blocks) >= 3

    def get_nearby_text(self, bbox: tuple, page_num: int, direction: str = "left") -> str:
        """Get text near the given bbox in specified direction"""
        page = self.doc[page_num]
        x0, y0, x1, y1 = bbox
        
        if direction == "left":
            search_rect = fitz.Rect(x0 - 100, y0, x0, y1)
        elif direction == "right":
            search_rect = fitz.Rect(x1, y0, x1 + 100, y1)
        else:
            return ""
            
        return page.get_text("text", clip=search_rect)

class PDFAnonymizer:
    """Enhanced PDF anonymization with context awareness"""
    
    def __init__(self):
        self.pattern_manager = PDFPatternManager()
    
    def calculate_confidence(self, match: str, context: PDFContext, category: str) -> float:
        """Calculate confidence score for a PII match based on context"""
        confidence = 0.5  # Base confidence
        
        # Check for known labels
        label_patterns = self.pattern_manager.patterns[category]["labels"]
        if any(re.search(label, context.preceding_text, re.IGNORECASE) for label in label_patterns):
            confidence += 0.3
            
        # Structured data boost
        if context.is_table_cell:
            confidence += 0.1
            
        # Length and format checks
        if len(match) > 3:  # Avoid very short matches
            confidence += 0.1
            
        return min(confidence, 1.0)

    def detect_pii(self, pdf_path: str) -> Dict[str, List[PIIMatch]]:
        """Detect PII with context awareness"""
        matches = defaultdict(list)
        doc = fitz.open(pdf_path)
        analyzer = PDFAnalyzer(doc)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text_page = page.get_text("dict")
            
            for block in text_page["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"]
                            bbox = span["bbox"]
                            
                            # Get context
                            context = PDFContext(
                                preceding_text=analyzer.get_nearby_text(bbox, page_num, "left"),
                                following_text=analyzer.get_nearby_text(bbox, page_num, "right"),
                                page_number=page_num,
                                bbox=bbox,
                                is_table_cell=analyzer.is_table_cell(bbox, page_num),
                                nearby_labels=[]
                            )
                            
                            # Check each category
                            for category, config in self.pattern_manager.patterns.items():
                                for pattern in config["patterns"]:
                                    for match in re.finditer(pattern, text):
                                        confidence = self.calculate_confidence(
                                            match.group(), context, category
                                        )
                                        
                                        if confidence >= config["confidence_threshold"]:
                                            matches[category].append(PIIMatch(
                                                category=category,
                                                text=match.group(),
                                                context=context,
                                                replacement=config["replacement"],
                                                confidence=confidence
                                            ))
        
        doc.close()
        return matches

    def anonymize_pdf(self, input_path: str, output_path: str, 
                     selected_categories: Optional[Dict[str, bool]] = None,
                     min_confidence: float = 0.7) -> bool:
        """Anonymize PDF with selected categories and confidence threshold"""
        try:
            doc = fitz.open(input_path)
            matches = self.detect_pii(input_path)
            
            for category, match_list in matches.items():
                if selected_categories is None or selected_categories.get(category, True):
                    for match in match_list:
                        if match.confidence >= min_confidence:
                            page = doc[match.context.page_number]
                            rect = fitz.Rect(match.context.bbox)
                            
                            # Use white rectangle for redaction
                            page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
                            
                            # Insert replacement text
                            page.insert_text(
                                rect.tl,
                                match.replacement,
                                color=(0, 0, 0)
                            )
            
            doc.save(output_path)
            doc.close()
            return True
            
        except Exception as e:
            print(f"Error in anonymize_pdf: {str(e)}")
            return False

# For backward compatibility
def anonymize_pdf(input_path: str, output_path: str) -> bool:
    """Wrapper function for backward compatibility"""
    anonymizer = PDFAnonymizer()
    return anonymizer.anonymize_pdf(input_path, output_path)