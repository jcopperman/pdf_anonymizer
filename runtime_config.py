import os
import sys
from pathlib import Path

def setup_runtime_environment():
    """Configure paths and environment for bundled tools"""
    if getattr(sys, 'frozen', False):
        # Running in PyInstaller bundle
        bundle_dir = Path(sys._MEIPASS)
    else:
        # Running in normal Python environment
        bundle_dir = Path(__file__).parent
    
    # Set up Tesseract paths
    tesseract_path = bundle_dir / "bundled_tools" / "tesseract"
    os.environ["TESSDATA_PREFIX"] = str(tesseract_path / "tessdata")
    os.environ["PATH"] = f"{str(tesseract_path)};{os.environ['PATH']}"
    
    # Set up Spacy
    os.environ["SPACY_WARNING_IGNORE"] = "W008"
    
    return bundle_dir