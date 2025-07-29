#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify if the PDF scanner app can run
"""

import sys
import os

def test_imports():
    """Test if all required imports work"""
    try:
        print("Testing imports...")
        
        # Test PyQt5
        from PyQt5.QtWidgets import QApplication
        print("✅ PyQt5 import successful")
        
        # Test PyMuPDF
        import fitz
        print("✅ PyMuPDF (fitz) import successful")
        
        # Test OpenAI
        import openai
        print("✅ OpenAI import successful")
        
        # Test dotenv
        from dotenv import load_dotenv
        print("✅ python-dotenv import successful")
        
        # Test Camelot
        import camelot
        print("✅ Camelot import successful")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_app_creation():
    """Test if the main app can be created"""
    try:
        print("\nTesting app creation...")
        
        # Import the main app
        from pdf_scanner_progressivo import PDFTableExtractor
        
        # Import QApplication
        from PyQt5.QtWidgets import QApplication
        
        # Create QApplication
        app = QApplication(sys.argv)
        
        # Create main window
        window = PDFTableExtractor()
        print("✅ App creation successful")
        
        # Don't show window, just test creation
        app.quit()
        return True
        
    except Exception as e:
        print(f"❌ App creation error: {e}")
        return False

if __name__ == "__main__":
    print("PDF Scanner App Test")
    print("=" * 30)
    
    # Test imports
    imports_ok = test_imports()
    
    if imports_ok:
        # Test app creation
        app_ok = test_app_creation()
        
        if app_ok:
            print("\n🎉 All tests passed! The app should work correctly.")
            print("\nTo run the app, use:")
            print("python pdf_scanner_progressivo.py")
        else:
            print("\n❌ App creation failed. Check the code for syntax errors.")
    else:
        print("\n❌ Some imports failed. Install missing packages with:")
        print("pip install -r requirements.txt")
