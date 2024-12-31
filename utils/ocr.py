# utils/ocr.py

import pytesseract
import cv2
import numpy as np
from PIL import Image
import logging
from typing import Optional, Tuple, Dict, Any
from pathlib import Path
import tempfile
import os

class OCRProcessor:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize OCR Processor with configuration.
        
        Args:
            config: Dictionary containing OCR configuration
                   - lang: OCR language (default: 'eng')
                   - psm: Page segmentation mode (default: 3)
                   - oem: OCR Engine mode (default: 3)
                   - confidence_threshold: Minimum confidence score (default: 60)
        """
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # Set default configuration
        self.lang = self.config.get('lang', 'eng')
        self.psm = self.config.get('psm', 3)
        self.oem = self.config.get('oem', 3)
        self.confidence_threshold = self.config.get('confidence_threshold', 60)
        
        # Verify Tesseract installation
        self._verify_tesseract()

    def _verify_tesseract(self):
        """Verify Tesseract installation and language pack"""
        try:
            pytesseract.get_tesseract_version()
        except Exception as e:
            self.logger.error("Tesseract not properly installed")
            raise RuntimeError("Tesseract not properly installed") from e
        
        # Check if language pack is available
        try:
            langs = pytesseract.get_languages()
            if self.lang not in langs:
                self.logger.warning(f"Language pack '{self.lang}' not found. Using 'eng'")
                self.lang = 'eng'
        except Exception as e:
            self.logger.warning("Could not verify language pack availability")

    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for better OCR results.
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Preprocessed image as numpy array
        """
        try:
            # Convert to grayscale if image is color
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image

            # Apply noise reduction
            denoised = cv2.fastNlMeansDenoising(gray)
            
            # Apply thresholding
            _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Apply dilation to connect text components
            kernel = np.ones((1, 1), np.uint8)
            dilated = cv2.dilate(binary, kernel, iterations=1)
            
            return dilated
            
        except Exception as e:
            self.logger.error(f"Image preprocessing error: {str(e)}")
            raise

    def process_image(self, image_path: str) -> Tuple[str, float]:
        """
        Process image and extract text with confidence score.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Tuple of (extracted text, confidence score)
        """
        try:
            # Verify file exists
            if not Path(image_path).exists():
                raise FileNotFoundError(f"Image file not found: {image_path}")

            # Read image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not read image: {image_path}")
                
            return self._process_image_array(image)
            
        except Exception as e:
            self.logger.error(f"OCR processing error for {image_path}: {str(e)}")
            raise

    def _process_image_array(self, image: np.ndarray) -> Tuple[str, float]:
        """
        Process image array and extract text with confidence score.
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Tuple of (extracted text, confidence score)
        """
        try:
            # Preprocess image
            processed = self.preprocess_image(image)
            
            # Configure OCR
            config = f'--oem {self.oem} --psm {self.psm}'
            
            # Perform OCR with confidence
            data = pytesseract.image_to_data(processed, lang=self.lang, config=config, output_type=pytesseract.Output.DICT)
            
            # Extract text and calculate confidence
            text_parts = []
            conf_scores = []
            
            for i, conf in enumerate(data['conf']):
                if conf > self.confidence_threshold:
                    text = data['text'][i].strip()
                    if text:
                        text_parts.append(text)
                        conf_scores.append(conf)
            
            # Combine text and calculate average confidence
            full_text = ' '.join(text_parts)
            avg_confidence = sum(conf_scores) / len(conf_scores) if conf_scores else 0
            
            return full_text, avg_confidence
            
        except Exception as e:
            self.logger.error(f"Image array processing error: {str(e)}")
            raise

    def process_pdf_image(self, image: np.ndarray) -> Tuple[str, float]:
        """
        Process image extracted from PDF.
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Tuple of (extracted text, confidence score)
        """
        return self._process_image_array(image)

    def save_debug_image(self, image: np.ndarray, filename: str):
        """
        Save preprocessed image for debugging.
        
        Args:
            image: Input image as numpy array
            filename: Output filename
        """
        try:
            processed = self.preprocess_image(image)
            cv2.imwrite(filename, processed)
        except Exception as e:
            self.logger.error(f"Error saving debug image: {str(e)}")
