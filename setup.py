from setuptools import setup, find_packages
import os
import spacy
import shutil
from pathlib import Path

def download_spacy_model():
    """Download spacy model during setup"""
    spacy.cli.download("en_core_web_sm")