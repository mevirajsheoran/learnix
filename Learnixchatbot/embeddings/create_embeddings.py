import os
import json
import faiss
import numpy as np
import openai
from dotenv import load_dotenv
from tqdm import tqdm
import time
from typing import List, Dict, Optional

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY is missing. Please add it to your .env file.")

openai.api_key = OPENAI_API_KEY

# Configuration
CHUNK_SIZE = 300  # Optimal for text-embedding-ada-002
BATCH_SIZE = 16   # Conservative batch size
MAX_RETRIES = 3
RETRY_DELAY = 5
EMBEDDING_MODEL = "text-embedding-ada-002"

# Directories
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROCESSED_DIR = os.path.join(BASE_DIR, "data/processed")
EMBEDDINGS_DIR = os.path.join(BASE_DIR, "data/embeddings")
os.makedirs(EMBEDDINGS_DIR, exist_ok=True)

VECTOR_STORE_PATH = os.path.join(EMBEDDINGS_DIR, "faiss_index")
METADATA_PATH = os.path.join(EMBEDDINGS_DIR, "metadata.json")

def load_chunks() -> tuple[List[str], List[Dict]]:
    """Load and validate text chunks from JSON file with page metadata."""
    chunks_path = os.path.join(PROCESSED_DIR, "pagewise_chunks.json")
    
    if not os.path.exists(chunks_path):
        raise FileNotFoundError(f"❌ Missing {chunks_path}. Run chunking script first.")

    with open(chunks_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            raise ValueError("❌ Invalid JSON format in input file.")

    chunks = []
    metadata_records = []
    
    for entry in data:
        if not isinstance(entry, dict):
            continue
            
        text = entry.get("text", "")
        if not text or not isinstance(text, str):
            continue
            
        # Log each text chunk and metadata for verification
        print(f"Loaded text for chunk {entry.get('chunk_id')}: {text[:100]}...")  # Log first 100 characters of the text
        print(f"Metadata for chunk {entry.get('chunk_id')}: {entry.get('metadata')}")
        
        chunks.append(text)
        metadata_records.append({
        "page_number": entry.get("metadata", {}).get("page_number"),
        "source": entry.get("metadata", {}).get("source", ""),
        "chunk_id": entry.get("id", ""),
        "chapter": entry.get("metadata", {}).get("chapter", ""),
        "class": entry.get("metadata", {}).get("class", ""),
        "subject": entry.get("metadata", {}).get("subject", ""),
        "is_complete_context": entry.get("metadata", {}).get("is_complete_context", False),
        "text": entry.get("text", "No text available")  # Include the text itself
})


    if not chunks:
        raise ValueError("❌ No valid text chunks found in input file.")

    return chunks, metadata_records


    


def get_embeddings(texts: List[str]) -> Optional[np.ndarray]:
    """Get embeddings with robust error handling and retries."""
    client = openai.OpenAI()
    
    for attempt in range(MAX_RETRIES):
        try:
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=texts
            )
            return np.array([e.embedding for e in response.data], dtype="float32")
            
        except Exception as e:
            print(f"⚠️ Attempt {attempt + 1} failed: {str(e)}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
    
    print(f"❌ Failed after {MAX_RETRIES} attempts for batch")
    return None

def create_faiss_index():
    """Create and save FAISS index with page metadata tracking."""
    try:
        texts, metadata = load_chunks()
        print(f"✅ Loaded {len(texts)} text chunks with page metadata")
    except Exception as e:
        print(str(e))
        return

    # Save metadata for later retrieval
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "records": metadata,
            "embedding_model": EMBEDDING_MODEL,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }, f, indent=2, ensure_ascii=False)

    # Initialize empty array for embeddings
    all_embeddings = []
    failed_batches = 0

    # Process in batches with progress bar
    progress = tqdm(range(0, len(texts), BATCH_SIZE), desc="Generating embeddings")
    
    for i in progress:
        batch = texts[i:i + BATCH_SIZE]
        embeddings = get_embeddings(batch)
        
        if embeddings is not None:
            all_embeddings.append(embeddings)
        else:
            failed_batches += 1
            progress.set_postfix({"failed": failed_batches})

    if not all_embeddings:
        print("❌ No embeddings generated. Check API connectivity.")
        return

    # Combine all embeddings
    embeddings_matrix = np.vstack(all_embeddings)
    
    # Create and save FAISS index
    dimension = embeddings_matrix.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings_matrix)
    
    faiss.write_index(index, VECTOR_STORE_PATH)
    print(f"\n✅ Saved FAISS index with {embeddings_matrix.shape[0]} vectors")
    print(f"   - Dimension: {dimension}")
    print(f"   - Failed batches: {failed_batches}/{len(texts)//BATCH_SIZE}")
    print(f"✅ Metadata saved to {METADATA_PATH}")

def search_with_page_reference(query: str, top_k: int = 3) -> List[Dict]:
    """Search FAISS index and return results with page references."""
    # Load index and metadata
    try:
        index = faiss.read_index(VECTOR_STORE_PATH)
    except Exception as e:
        print(f"❌ Error reading FAISS index: {e}")
        return []
    
    try:
        with open(METADATA_PATH, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    except Exception as e:
        print(f"❌ Error reading metadata: {e}")
        return []
    
    # Get query embedding
    try:
        client = openai.OpenAI()
        response = client.embeddings.create(input=[query], model=EMBEDDING_MODEL)
        query_embedding = np.array([response.data[0].embedding], dtype="float32")
    except Exception as e:
        print(f"❌ Error getting query embedding: {e}")
        return []
    
    # Search FAISS index
    try:
        distances, indices = index.search(query_embedding, top_k)
    except Exception as e:
        print(f"❌ Error during FAISS search: {e}")
        return []
    
    # Ensure that indices are within bounds
    results = []
    for i, idx in enumerate(indices[0]):
        if 0 <= idx < len(metadata["records"]):
            record = metadata["records"][idx]
            text = record.get('text', 'No text available')
            results.append({
                "text": f"From page {record['page_number']}: {text}",
                "page_number": record["page_number"],
                "source": record["source"],
                "chapter": record["chapter"],
                "score": float(distances[0][i])  # Convert numpy float to Python float
            })
        else:
            print(f"⚠️ Index {idx} out of bounds in metadata. Skipping this result.")
    
    # If fewer results are found than requested, log the difference
    if len(results) < top_k:
        print(f"⚠️ Only {len(results)} results returned, fewer than requested {top_k}.")
    
    return results


if __name__ == "__main__":
    create_faiss_index()
    
    # Example usage of search with page reference
    test_query = "What is photosynthesis?"
    print(f"\nTesting search for: '{test_query}'")
    results = search_with_page_reference(test_query)
    for i, result in enumerate(results, 1):
        print(f"\nResult {i}:")
        print(f"Page: {result['page_number']}")
        print(f"Text: {result['text']}")
        print(f"Source: {result['source']}")
        print(f"Chapter: {result['chapter']}")
        print(f"Similarity Score: {result['score']:.4f}")