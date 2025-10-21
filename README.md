# Redoku

Redoku converts input text into dyslexia-friendly PDF files and stores optional email addresses (no passwords).

## Features
- Input text -> download dyslexia-friendly PDF
- PDF characteristics: large font, extra spacing, first letter of each word highlighted, soft background
- Collect and store email addresses only (SQLite)
- No ads, no newsletter sending by default

## Local setup

1. Clone repo
2. Create and activate a virtualenv:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # or .\.venv\Scripts\Activate.ps1 on Windows PowerShell
