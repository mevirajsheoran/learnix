import os
import json
import fitz  
from typing import List, Dict, Tuple
import tiktoken


INPUT_PDF = "/Users/ayushsiddhant/Desktop/Learnix Chatbot/Learnixchatbot/data/raw/Science_Chapter1.pdf"
OUTPUT_FILE = "/Users/ayushsiddhant/Desktop/Learnix Chatbot/Learnixchatbot/data/processed/pagewise_chunks.json"


MAX_PAGE_TOKENS = 500 
MIN_CHUNK_TOKENS = 50

def num_tokens_from_string(text: str, encoding_name: str = "cl100k_base") -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    return len(encoding.encode(text))

def extract_text_by_page(pdf_path: str) -> List[Tuple[int, str]]:
    """Extract text from PDF with page numbers."""
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found at {pdf_path}")
        return []
    
    try:
        doc = fitz.open(pdf_path)
        return [(page.number + 1, page.get_text()) for page in doc]
    except Exception as e:
        print(f"Error extracting text: {str(e)}")
        return []

def split_page_content(page_num: int, text: str) -> List[Dict]:
    """Split page content into manageable chunks with metadata."""
    if not text.strip():
        return []
    
    chunks = []
    current_chunk = []
    current_tokens = 0
    
    
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    
    for para in paragraphs:
        para_tokens = num_tokens_from_string(para)
        
        
        if para_tokens > MAX_PAGE_TOKENS:
            words = para.split()
            sub_chunk = []
            sub_tokens = 0
            
            for word in words:
                word_tokens = num_tokens_from_string(word) + 1
                if sub_tokens + word_tokens > MAX_PAGE_TOKENS:
                    chunks.append({
                        "text": " ".join(sub_chunk),
                        "page": page_num,
                        "tokens": sub_tokens,
                        "is_complete": False
                    })
                    sub_chunk = [word]
                    sub_tokens = word_tokens
                else:
                    sub_chunk.append(word)
                    sub_tokens += word_tokens
            
            if sub_tokens >= MIN_CHUNK_TOKENS:
                chunks.append({
                    "text": " ".join(sub_chunk),
                    "page": page_num,
                    "tokens": sub_tokens,
                    "is_complete": True
                })
        else:
            if current_tokens + para_tokens > MAX_PAGE_TOKENS:
                chunks.append({
                    "text": " ".join(current_chunk),
                    "page": page_num,
                    "tokens": current_tokens,
                    "is_complete": True
                })
                current_chunk = [para]
                current_tokens = para_tokens
            else:
                current_chunk.append(para)
                current_tokens += para_tokens
    
    if current_tokens >= MIN_CHUNK_TOKENS:
        chunks.append({
            "text": " ".join(current_chunk),
            "page": page_num,
            "tokens": current_tokens,
            "is_complete": True
        })
    
    return chunks

def process_pdf_to_chunks(pdf_path: str) -> List[Dict]:
    """Process PDF into page-wise chunks with metadata."""
    page_contents = extract_text_by_page(pdf_path)
    if not page_contents:
        return []
    
    all_chunks = []
    
    for page_num, text in page_contents:
        page_chunks = split_page_content(page_num, text)
        for chunk in page_chunks:
            all_chunks.append({
                "id": f"page-{chunk['page']}-chunk-{len(all_chunks) + 1}",
                "text": chunk["text"],
                "metadata": {
                    "page_number": chunk["page"],
                    "source": os.path.basename(pdf_path),
                    "chapter": "Chapter 1",
                    "class": "Class 7",
                    "subject": "Science",
                    "tokens": chunk["tokens"],
                    "is_complete_context": chunk["is_complete"]
                }
            })
    
    return all_chunks

def save_chunks_to_json(chunks: List[Dict], output_path: str):
    """Save chunks to JSON file."""
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, indent=2, ensure_ascii=False)
        print(f"Successfully saved {len(chunks)} chunks to {output_path}")
    except Exception as e:
        print(f"Error saving chunks: {str(e)}")

if __name__ == "__main__":
    # Install required packages if missing
    try:
        import tiktoken
    except ImportError:
        print("Installing tiktoken...")
        import subprocess
        subprocess.run(["pip", "install", "tiktoken"], check=True)
        import tiktoken
    
    try:
        import fitz
    except ImportError:
        print("Installing PyMuPDF...")
        import subprocess
        subprocess.run(["pip", "install", "pymupdf"], check=True)
        import fitz
    
    print("Processing PDF...")
    chunks = process_pdf_to_chunks(INPUT_PDF)
    
    if chunks:
        save_chunks_to_json(chunks, OUTPUT_FILE)
        print("\nSample chunk:")
        print(json.dumps(chunks[0], indent=2))
    else:
        print("No chunks were created. Please check the input PDF.")