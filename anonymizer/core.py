# anonymizer/core.py

import logging
from typing import Dict, Optional
from utils.pdf_utils import PDFAnonymizer as PDFUtils

class PDFAnonymizer:
    def __init__(self, config: Optional[Dict] = None):
        """Initialize the PDF Anonymizer with optional configuration."""
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.pdf_utils = PDFUtils()

    def detect_pii(self, file_path: str) -> Dict:
        """
        Detect PII in the given PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dictionary of detected PII by category
        """
        try:
            return self.pdf_utils.detect_pii(file_path)
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
            return self.pdf_utils.anonymize_pdf(
                input_path,
                output_path,
                selected_categories
            )
        except Exception as e:
            self.logger.error(f"Error anonymizing PDF: {str(e)}")
            return False

    def get_supported_categories(self) -> list:
        """Get list of supported PII categories."""
        return list(self.pdf_utils.pattern_manager.patterns.keys())

