import os
import json
import fitz  
from tqdm import tqdm


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_DIR = os.path.join(BASE_DIR, "data/raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data/processed")
OUTPUT_FILE = os.path.join(PROCESSED_DIR, "raw_extracted_text.json")

def extract_all_text(pdf_path: str) -> str:
    """Extracts all text from a PDF as one continuous string"""
    try:
        doc = fitz.open(pdf_path)
        full_text = []
        for page in doc:
            full_text.append(page.get_text("text"))
        return "\n".join(full_text)
    except Exception as e:
        print(f" Failed to extract {pdf_path}: {str(e)}")
        return ""

def clean_text(text: str) -> str:
    """Basic text cleaning"""
    return " ".join(text.replace("\n", " ").split())

def process_pdfs():
    """Process all PDFs and dump raw text"""
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    
    results = {}
    
    for filename in tqdm([f for f in os.listdir(RAW_DIR) if f.endswith(".pdf")], 
                        desc="Extracting PDFs"):
        pdf_path = os.path.join(RAW_DIR, filename)
        raw_text = extract_all_text(pdf_path)
        results[filename] = clean_text(raw_text) if raw_text else None
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Done! Extracted text from {len(results)} PDFs")

if __name__ == "__main__":
    process_pdfs()