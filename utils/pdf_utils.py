import fitz  # PyMuPDF
import logging
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import os
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pdf_anonymizer.log'),
        logging.StreamHandler()
    ]
)

# Import from detector using absolute import
from anonymizer.detector import PatternManager, PIIContext, PIIMatch

@dataclass
class PDFContext:
    """Stores context information for PDF analysis"""
    page_number: int
    bbox: tuple
    preceding_text: str
    following_text: str
    line_text: str
    is_table_cell: bool = False

class PDFAnalyzer:
    """Analyzes PDF structure and content"""
    
    def __init__(self, doc: fitz.Document):
        self.doc = doc
        self.logger = logging.getLogger(__name__)

    def _merge_nearby_blocks(self, blocks, threshold=5):
        """Merge text blocks that are likely part of the same logical unit"""
        if not blocks:
            return blocks
            
        try:
            merged = []
            current = list(blocks[0])  # Convert tuple to list for modification
            
            for block in blocks[1:]:
                try:
                    # Unpack coordinates and text
                    x0, y0, x1, y1, text = block[:5]
                    curr_x0, curr_y0, curr_x1, curr_y1, curr_text = current[:5]
                    
                    # Check if blocks are on the same line (similar y-coordinate)
                    if abs(y0 - curr_y0) < threshold:
                        # Merge blocks if they're close horizontally
                        if abs(x0 - curr_x1) < threshold * 3:  # Allow larger horizontal gap
                            current[2] = x1  # Extend right boundary
                            current[4] = curr_text + ' ' + text  # Merge text
                            continue
                    
                    # If not merged, add current block to results and start new one
                    merged.append(tuple(current))
                    current = list(block)
                except Exception as e:
                    self.logger.error(f"Error processing block in merge: {str(e)}")
                    continue
            
            merged.append(tuple(current))
            return merged
        except Exception as e:
            self.logger.error(f"Error in _merge_nearby_blocks: {str(e)}")
            return blocks

    def is_table_cell(self, bbox: tuple, page_num: int) -> bool:
        """Detect if a text block is likely part of a table"""
        try:
            page = self.doc[page_num]
            blocks = page.get_text("blocks")
            
            x0, y0, x1, y1 = bbox
            aligned_blocks = []
            
            # Look for aligned blocks
            for block in blocks:
                try:
                    block_x0, block_y0, block_x1, block_y1 = block[:4]
                    
                    # Skip the current block
                    if block[:4] == bbox:
                        continue
                    
                    # Check for horizontal alignment (same row)
                    if abs(block_y0 - y0) < 10:
                        aligned_blocks.append(block)
                    # Check for vertical alignment (same column)
                    elif abs(block_x0 - x0) < 10:
                        aligned_blocks.append(block)
                except Exception as e:
                    self.logger.error(f"Error processing block in table detection: {str(e)}")
                    continue
            
            # Consider it a table cell if there are aligned blocks
            is_table = len(aligned_blocks) >= 2
            if is_table:
                self.logger.debug(f"Detected table cell at {bbox}")
            return is_table
        except Exception as e:
            self.logger.error(f"Error in is_table_cell: {str(e)}")
            return False

    def get_nearby_text(self, bbox: tuple, page_num: int, direction: str = "left") -> str:
        """Get text near the given bbox in specified direction"""
        try:
            page = self.doc[page_num]
            x0, y0, x1, y1 = bbox
            
            # Increase the search area for OCR text
            margin = 10  # Vertical margin
            search_width = 150  # Horizontal search width
            
            if direction == "left":
                search_rect = fitz.Rect(max(0, x0 - search_width), y0 - margin, x0, y1 + margin)
            elif direction == "right":
                search_rect = fitz.Rect(x1, y0 - margin, x1 + search_width, y1 + margin)
            else:
                self.logger.warning(f"Invalid direction specified: {direction}")
                return ""
            
            # Get text blocks in the search area
            blocks = page.get_text("blocks", clip=search_rect)
            
            if not blocks:
                return ""
                
            # Merge nearby blocks for better context
            merged_blocks = self._merge_nearby_blocks(blocks)
            
            # Combine text from all blocks
            text = " ".join(block[4].strip() for block in merged_blocks if len(block) > 4)
            
            # Clean up OCR artifacts and normalize whitespace
            text = " ".join(text.split())
            
            self.logger.debug(f"Found nearby text ({direction}): {text}")
            return text
            
        except Exception as e:
            self.logger.error(f"Error getting nearby text: {str(e)}")
            return ""

    def get_text_blocks(self, page_num: int) -> List[tuple]:
        """Get merged and cleaned text blocks from a page"""
        try:
            page = self.doc[page_num]
            blocks = page.get_text("blocks")
            return self._merge_nearby_blocks(blocks)
        except Exception as e:
            self.logger.error(f"Error in get_text_blocks: {str(e)}")
            return []

class PDFAnonymizer:
    """Enhanced PDF anonymization with context awareness"""
    
    def __init__(self):
        self.pattern_manager = PatternManager()
        self.analyzer = None  # Will be initialized per document
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

    def _clean_ocr_text(self, text: str) -> str:
        """Clean up common OCR artifacts from text"""
        try:
            # Replace common OCR artifacts
            replacements = {
                '|': 'I',    # Vertical bar to I
                'l': 'l',    # lowercase L to I if it's part of a number
                'O': '0',    # Letter O to zero in number contexts
                '¡': 'i',    # Inverted exclamation to i
                '¦': 'I',    # Broken bar to I
                "'": "'",    # Smart quote to simple quote
                '"': '"',    # Smart quote to simple quote
                '—': '-',    # Em dash to hyphen
                '–': '-',    # En dash to hyphen
                '\xad': '-', # Soft hyphen to regular hyphen
            }
            
            # Apply replacements
            for old, new in replacements.items():
                text = text.replace(old, new)
            
            # Remove zero-width spaces and other invisible characters
            text = ''.join(c for c in text if c.isprintable())
            
            # Normalize whitespace
            text = ' '.join(text.split())
            
            return text
        except Exception as e:
            self.logger.error(f"Error in _clean_ocr_text: {str(e)}")
            return text

    def detect_pii(self, pdf_path: str) -> Dict[str, List[PIIMatch]]:
        """Detect PII with context awareness"""
        matches = defaultdict(list)
        doc = None
        try:
            doc = fitz.open(pdf_path)
            self.analyzer = PDFAnalyzer(doc)
            
            self.logger.debug(f"Processing PDF: {pdf_path}")
            for page_num in range(len(doc)):
                page = doc[page_num]
                self.logger.debug(f"Processing page {page_num + 1}")
                
                blocks = self.analyzer.get_text_blocks(page_num)
                self.logger.debug(f"Found {len(blocks)} merged text blocks on page {page_num + 1}")
                
                for block_num, block in enumerate(blocks):
                    try:
                        text = self._clean_ocr_text(block[4])
                        bbox = block[:4]
                        
                        if len(text.strip()) < 2:
                            continue
                        
                        context = PIIContext(
                            preceding_text=self._clean_ocr_text(self.analyzer.get_nearby_text(bbox, page_num, "left")),
                            following_text=self._clean_ocr_text(self.analyzer.get_nearby_text(bbox, page_num, "right")),
                            line_text=text,
                            is_labeled=False,
                            page_number=page_num,
                            bbox=bbox,
                            is_table_cell=self.analyzer.is_table_cell(bbox, page_num)
                        )
                        
                        block_matches = self.pattern_manager.detect_pii(text, context)
                        for category, category_matches in block_matches.items():
                            matches[category].extend(category_matches)
                    except Exception as e:
                        self.logger.error(f"Error processing block {block_num}: {str(e)}")
                        continue
            
            return matches
        except Exception as e:
            self.logger.error(f"Error in detect_pii: {str(e)}")
            return matches
        finally:
            if doc:
                doc.close()
            self.analyzer = None

    def anonymize_pdf(self, input_path: str, output_path: str, 
                     selected_categories: Optional[Dict[str, bool]] = None,
                     min_confidence: float = 0.7) -> bool:
        """Anonymize PDF with selected categories and confidence threshold.
        
        Args:
            input_path: Path to input PDF file
            output_path: Path to save anonymized PDF
            selected_categories: Dict of category names and their selection status
            min_confidence: Minimum confidence threshold for matches
            
        Returns:
            bool: True if successful, False otherwise
        """
        doc = None
        try:
            doc = fitz.open(input_path)
            matches = self.detect_pii(input_path)
            
            # Process matches for selected categories
            for category, match_list in matches.items():
                if selected_categories is None or selected_categories.get(category, True):
                    for match in match_list:
                        if match.confidence >= min_confidence:
                            # Get page and create rectangle for redaction
                            page = doc[match.context.page_number]
                            rect = fitz.Rect(match.context.bbox)
                            
                            # Draw white rectangle and insert replacement text
                            page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
                            page.insert_text(rect.tl, match.replacement, color=(0, 0, 0))
            
            doc.save(output_path)
            return True
            
        except Exception as e:
            self.logger.error(f"Error in anonymize_pdf: {str(e)}")
            return False
        finally:
            if doc:
                doc.close()

    def get_supported_categories(self) -> List[str]:
        """Get list of supported PII categories.
        
        Returns:
            List[str]: List of supported category names
        """
        return self.pattern_manager.get_supported_categories()
