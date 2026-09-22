# Gemini Book Translator

Desktop application in Python (Tkinter GUI) for translating books and long documents using Google Gemini API.

## Supported Formats
* EPUB (`.epub`)
* PDF (`.pdf`)
* Word (`.docx`)
* RTF (`.rtf`)
* PalmDOC (`.pdb`)
* Text (`.txt`)

## Translation Directions
* Czech -> Slovak
* English -> Slovak
* English -> Czech

## Features
* Automatic text chunking (3,500 characters)
* API rate-limit handling
* PalmDOC (PDB) decompression support

## How to Run

1. Install required libraries:
   pip install -r requirements.txt

2. Open app.py and insert your Gemini API key:
   API_KLUC = "YOUR_API_KEY_HERE"

3. Run the application:
   python3 app.py
