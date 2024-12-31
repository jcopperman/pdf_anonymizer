import re
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class PIIContext:
	"""Context information for a PII match"""
	preceding_text: str = ""
	following_text: str = ""
	line_text: str = ""
	is_labeled: bool = False
	page_number: Optional[int] = None
	bbox: Optional[tuple] = None
	is_table_cell: bool = False

@dataclass
class PIIMatch:
	"""Represents a PII match with its context and confidence"""
	text: str
	start: int
	end: int
	category: str
	confidence: float
	context: PIIContext
	replacement: str

class PatternManager:
	"""Manages PII detection patterns and performs context-aware matching"""
	
	DEFAULT_PATTERNS = {
		"Names": {
			"patterns": [
				r'\b[A-Z][a-zçéèêëíìîïñóòôöúùûü]+[.\s-]*(?:[A-Z][a-zçéèêëíìîïñóòôöúùûü]+[.\s-]*){1,2}\b',
				r'\b[A-Za-z][a-zçéèêëíìîïñóòôöúùûü]+[.\s-]*(?:[A-Za-z][a-zçéèêëíìîïñóòôöúùûü]+[.\s-]*){1,2}\b',
				r'\b[A-Za-z][a-zçéèêëíìîïñóòôöúùûü]+[.\s-]*(?:[A-Za-z][a-zçéèêëíìîïñóòôöúùûü]+[.\s-]*){1,2}\b',
				r'\b[A-Z][a-z]+(?:[A-Z][a-z]+){1,2}\b',
				r'\b[A-Z0O][a-zçéèêëíìîïñóòôöúùûü]+[.\s-]*(?:[A-Z0O][a-zçéèêëíìîïñóòôöúùûü]+[.\s-]*){1,2}\b',
				r'\b(?:[A-Z]\.?\s*){1,2}[A-Z][a-zçéèêëíìîïñóòôöúùûü]+(?:\s+[A-Z][a-zçéèêëíìîïñóòôöúùûü]+)*\b'
			],
			"labels": [
				r'\b(?:name|full[\s-]*name|customer|client|account[\s-]*holder|prepared[\s-]*by|signed[\s-]*by)\b[:\s]*$',
				r'^[:\s]*name[:\s]*',
				r'\b(?:mr|mrs|ms|dr|prof)[.\s]+',
				r'\b(?:signature|signed|approved)\s+(?:by|of)[:\s]*',
				r'\b(?:authorized|certified|verified)\s+(?:by|for)[:\s]*',
				r'\b(?:employee|manager|supervisor|agent)[:\s]*'
			],
			"replacement": "[REDACTED NAME]",
			"confidence_threshold": 0.55
		},
		"Account Numbers": {
			"patterns": [
				r'\b[0-9O]{1,4}[\s-]*[0-9O]{1,4}[\s-]*[0-9O]{1,4}[\s-]*[0-9O]{1,4}\b',
				r'\b[A-Z]{2}[\s-]*[0-9O]{2}(?:[\s-]*[0-9O]{4}){2,4}\b',
				r'\b[0-9O]{10,16}\b',
				r'\b[O0-9lI]{10,16}\b',
				r'\b(?:[0-9O]{4}[\s-]*){4}\b',
				r'\b[0-9O]{1,5}(?:[- /.\\][0-9O]{1,5}){2,5}\b'
			],
			"labels": [
				r'\b(?:account|acc|account[\s-]*no|reference|ref|number)\b[:\s]*$',
				r'^[:\s]*account[:\s]*',
				r'\b(?:acc|acct|account)[\s-]*(?:number|#|no)[:\s]*',
				r'\b(?:iban|swift|routing|card|credit|debit)[:\s]*',
				r'\b(?:ref|reference|transaction)[\s-]*(?:number|#|no)[:\s]*'
			],
			"replacement": "[REDACTED ACCOUNT]",
			"confidence_threshold": 0.6
		},
		"Addresses": {
			"patterns": [
				r'\b\d+[\s-]+[A-Za-z\s-]+(?:Road|Street|Ave|Avenue|Boulevard|Blvd|Lane|Drive|Dr|Circle|Cir|Court|Ct|Place|Pl|Square|Sq|Way|Parkway|Pkwy)[.,\s]*\b',
				r'\b(?:P\.?[\s-]*O\.?[\s-]*Box|Post[\s-]*Office[\s-]*Box|PO[\s-]*Box|P0[\s-]*Box)[\s-]*[0-9O]+\b',
				r'\b(?:Apt|Suite|Unit|Building|Bldg|Room|Rm)\.?[\s-]*[A-Za-z0-9-]+\b',
				r'\b\d+[\s-]+[A-Za-z\s-]+(?:Rd|St|Av|Ave|Blvd|Ln|Dr|Cir|Ct|Pl|Sq)[.,\s]*\b',
				r'\b[A-Z][0-9O][A-Z][\s-]*[0-9O][A-Z][0-9O]\b',
				r'\b[0-9O]{5}(?:[-\s][0-9O]{4})?\b'
			],
			"labels": [
				r'\b(?:address|location|residence|mailing|shipping|billing)\b[:\s]*$',
				r'^[:\s]*address[:\s]*',
				r'\b(?:street|avenue|road|boulevard|lane|drive)[:\s]*',
                # Address with unit numbers
                r'\b#\s*\d+[\s-]+[A-Za-z\s-]+(?:Road|Street|Ave|Avenue|Boulevard|Blvd|Lane|Drive|Dr)[.,\s]*\b'
            ],
            "labels": [
                r'\b(?:address|location|residence|mailing|shipping|billing)\b[:\s]*$',
                r'^[:\s]*address[:\s]*',
                r'\b(?:street|avenue|road|boulevard|lane|drive)[:\s]*',
                r'\b(?:city|state|zip|postal|province|country)[:\s]*',
                r'\b(?:deliver|ship|send)[\s-]*to[:\s]*'
            ],
            "replacement": "[REDACTED ADDRESS]",
            "confidence_threshold": 0.55
        },
        "Phone Numbers": {
            "patterns": [
                # International format with flexible spacing
                r'\+\s*\d[\s-]*(?:\d[\s-]*){6,14}\b',
                # North American format
                r'\b(?:\+\s*1[-\s]*)?(?:\d{3}|\(\d{3}\))[-\s]*\d{3}[-\s]*\d{4}\b',
                # Extension variations
                r'\b(?:ext|x|ex)\.?\s*\d{2,5}\b',
                # Common OCR mistakes in phone numbers
                r'\b[O0-9lI]{3}[\s-]*[O0-9lI]{3}[\s-]*[O0-9lI]{4}\b',
                # Numbers with dots
                r'\b\d{3}[.]\d{3}[.]\d{4}\b'
            ],
            "labels": [
                r'\b(?:phone|tel|telephone|mobile|cell|fax|contact)[\s-]*(?:number|no|#)?[:\s]*$',
                r'^[:\s]*(?:phone|tel|telephone|mobile|cell|fax)[:\s]*',
                r'\b(?:call|dial|contact)[:\s]*',
                r'\b(?:phone|tel|telephone|mobile|cell|fax)[:\s]*'
            ],
            "replacement": "[REDACTED PHONE]",
            "confidence_threshold": 0.55
        },
		"Email Addresses": {
			"patterns": [
				# Standard email with flexible spacing
				r'\b[A-Za-z0-9._%+-]+[\s]*@[\s]*[A-Za-z0-9.-]+[\s]*\.[\s]*[A-Za-z]{2,}\b',
				# Common OCR mistakes in emails
				r'\b[A-Za-z0-9._%+-]+(?:@|＠|[\s]*@[\s]*|[\s]*\(?at\)?[\s]*)[A-Za-z0-9.-]+(?:\.|\(?dot\)?)[A-Za-z]{2,}\b',
				# Emails with domain variations
				r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.(?:com|org|net|edu|gov|mil|biz|info|mobi|name|aero|asia|jobs|museum)\b',
				# Handle OCR spacing in email addresses
				r'\b[A-Za-z0-9._%+-]+\s*[@＠]\s*[A-Za-z0-9.-]+\s*\.\s*[A-Za-z]{2,}\b'
			],
			"labels": [
				r'\b(?:email|e-mail|mail|contact)[\s-]*(?:address)?[:\s]*$',
				r'^[:\s]*(?:email|e-mail|mail)[:\s]*',
				r'\b(?:send|contact|reach)[\s-]*(?:at|via|by)[:\s]*',
				r'\b(?:email|e-mail|mail)[:\s]*'
			],
			"replacement": "[REDACTED EMAIL]",
			"confidence_threshold": 0.55
		}}

	def __init__(self):
		"""Initialize the PatternManager"""
		self.patterns = self.DEFAULT_PATTERNS.copy()
		self.logger = logging.getLogger(__name__)
		self.logger.setLevel(logging.DEBUG)
		self._compile_patterns()

	def _compile_patterns(self):
		"""Compile regex patterns for efficient matching"""
		for category, config in self.patterns.items():
			self.logger.debug(f"Compiling patterns for {category}")
			config['compiled_patterns'] = [re.compile(p, re.IGNORECASE) for p in config['patterns']]
			config['compiled_labels'] = [re.compile(l, re.IGNORECASE) for l in config['labels']]

	def detect_pii(self, text: str, context: Optional[PIIContext] = None) -> Dict[str, List[PIIMatch]]:
		"""
		Detect PII in text with context awareness
		
		Args:
			text: Text to analyze
			context: Optional context information
			
		Returns:
			Dictionary mapping categories to lists of PIIMatch objects
		"""
		if context is None:
			context = PIIContext()

		matches = {}
		self.logger.debug(f"Analyzing text block: {text[:100]}...")
		
		for category, config in self.patterns.items():
			category_matches = []
			self.logger.debug(f"Checking {category} patterns")
			
			# Check for label matches in context
			label_confidence = 0.0
			if context.preceding_text or context.following_text:
				for label_pattern in config['compiled_labels']:
					if (label_pattern.search(context.preceding_text) or 
						label_pattern.search(context.following_text)):
						label_confidence = 0.3
						self.logger.debug(f"Found label match for {category}, confidence boost: 0.3")
						break

			# Find pattern matches
			for pattern in config['compiled_patterns']:
				for match in pattern.finditer(text):
					base_confidence = 0.5
					
					# Adjust confidence based on context
					confidence = base_confidence + label_confidence
					
					if context.is_table_cell:
						confidence += 0.1
						self.logger.debug("Table cell context detected, confidence boost: 0.1")
						
					# Create match object if confidence meets threshold
					if confidence >= config.get('confidence_threshold', 0.7):
						pii_match = PIIMatch(
							text=match.group(),
							start=match.start(),
							end=match.end(),
							category=category,
							confidence=confidence,
							context=context,
							replacement=config.get('replacement', f'[REDACTED {category}]')
						)
						self.logger.debug(f"Found {category} match: {match.group()} (confidence: {confidence})")
						category_matches.append(pii_match)
			
			if category_matches:
				matches[category] = category_matches
				
		return matches

	def add_pattern(self, category: str, pattern: str, labels: List[str], 
				   replacement: str, confidence_threshold: float = 0.7):
		"""Add a new pattern configuration"""
		if category not in self.patterns:
			self.patterns[category] = {
				'patterns': [],
				'labels': [],
				'replacement': replacement,
				'confidence_threshold': confidence_threshold
			}
			
		self.patterns[category]['patterns'].append(pattern)
		self.patterns[category]['labels'].extend(labels)
		self._compile_patterns()

	def get_supported_categories(self) -> List[str]:
		"""Get list of supported PII categories"""
		return list(self.patterns.keys())

	def update_patterns(self, patterns: Dict):
		"""Update pattern configurations"""
		self.patterns = patterns
		self._compile_patterns()