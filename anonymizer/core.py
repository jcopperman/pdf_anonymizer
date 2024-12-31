# anonymizer/core.py

import logging
from typing import Dict, Optional
from utils.ocr import OCRProcessor
from utils.pdf_utils import PDFProcessor
from .detector import PatternManager
from .replacer import ReplacementManager

class PDFAnonymizer:
    def __init__(self, config: Optional[Dict] = None):
        """Initialize the PDF Anonymizer with optional configuration."""
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.ocr_processor = OCRProcessor()
        self.pdf_processor = PDFProcessor()
        self.pattern_manager = PatternManager()
        self.replacement_manager = ReplacementManager(self.config)

    def detect_pii(self, file_path: str) -> Dict:
        """
        Detect PII in the given PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dictionary of detected PII by category
        """
        try:
            # Extract text from PDF
            text = self.pdf_processor.extract_text(file_path)
            
            # Process any images in the PDF using OCR
            images_text = self.pdf_processor.process_images(file_path, self.ocr_processor)
            
            # Combine text from PDF and OCR
            full_text = f"{text}\n{images_text}"
            
            # Detect PII in the combined text
            pii_matches = self.pattern_manager.detect_pii(full_text)
            
            return pii_matches
            
        except Exception as e:
            self.logger.error(f"Error detecting PII: {str(e)}")
            raise

    def anonymize_pdf(self, input_path: str, output_path: str, selected_categories: Dict[str, bool]) -> bool:
        """
        Anonymize the PDF file based on selected PII categories.
        
        Args:
            input_path: Path to input PDF
            output_path: Path for output PDF
            selected_categories: Dictionary of category names and their selection status
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Detect PII
            pii_matches = self.detect_pii(input_path)
            
            # Filter selected categories
            selected_matches = {
                category: matches 
                for category, matches in pii_matches.items() 
                if selected_categories.get(category, False)
            }
            
            # Process the PDF with replacements
            success = self.pdf_processor.process_with_replacements(
                input_path,
                output_path,
                selected_matches,
                self.replacement_manager
            )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error anonymizing PDF: {str(e)}")
            return False

    def get_supported_categories(self) -> list:
        """Get list of supported PII categories."""
        return self.pattern_manager.get_supported_categories()
