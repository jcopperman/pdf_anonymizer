import PyInstaller.__main__
import sys
import os
import subprocess
from pathlib import Path
import spacy.util

def create_installer():
    # Directory for Tesseract files
    tesseract_dir = Path("bundled_tools/tesseract")
    tesseract_dir.mkdir(parents=True, exist_ok=True)
    
    # Download Tesseract installer
    tesseract_url = "https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.1/tesseract-ocr-w64-setup-5.3.1.exe"
    subprocess.run(["curl", "-L", tesseract_url, "-o", "tesseract_installer.exe"])
    
    # Extract necessary files (you'll need 7zip or similar)
    subprocess.run(["7z", "x", "tesseract_installer.exe", f"-o{tesseract_dir}"])
    
    # Define additional data files
    additional_files = [
        # Tesseract files
        (str(tesseract_dir / "tesseract.exe"), "bundled_tools/tesseract"),
        (str(tesseract_dir / "*.dll"), "bundled_tools/tesseract"),
        (str(tesseract_dir / "tessdata"), "bundled_tools/tesseract/tessdata"),
        
        # Spacy model
        (str(Path(spacy.util.get_package_path("en_core_web_sm"))), "en_core_web_sm"),
    ]
    
    PyInstaller.__main__.run([
        'main.py',
        '--name=PDFAnonymizer',
        '--onefile',
        '--windowed',
        '--add-data=' + ';'.join(additional_files),
        '--hidden-import=spacy.lang.en',
        '--hidden-import=spacy.lang.en.stop_words',
        '--hidden-import=queue'
    ])