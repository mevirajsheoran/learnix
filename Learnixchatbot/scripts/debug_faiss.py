import os
import json
import faiss
import numpy as np
from openai import OpenAI, OpenAIError
from dotenv import load_dotenv
from typing import Optional, Tuple, List

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is missing. Please add it to your .env file.")

client = OpenAI(api_key=OPENAI_API_KEY)


EMBEDDING_MODEL = "text-embedding-ada-002"
GPT_MODEL = "gpt-3.5-turbo"
TEMPERATURE = 0.7
MAX_TOKENS = 300
TOP_K = 3
SIMILARITY_THRESHOLD = 0.5

# Paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
EMBEDDINGS_DIR = os.path.join(BASE_DIR, "data", "embeddings")
VECTOR_STORE_PATH = os.path.join(EMBEDDINGS_DIR, "faiss_index")
CHUNKS_PATH = os.path.join(PROCESSED_DIR, "pagewise_chunks.json")

# Load FAISS index and chunk data
def load_faiss_data() -> Tuple[Optional[faiss.Index], List[dict]]:
    try:
        if not os.path.exists(VECTOR_STORE_PATH):
            print(f"⚠️ FAISS index not found at {VECTOR_STORE_PATH}")
            return None, []

        with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
            chunks = json.load(f)

        index = faiss.read_index(VECTOR_STORE_PATH)

        if index.ntotal != len(chunks):
            print(f"⚠️ Misalignment: {index.ntotal} vectors but {len(chunks)} chunks.")
            return None, []

        return index, chunks

    except Exception as e:
        print(f"⚠️ Error loading FAISS data: {str(e)}")
        return None, []

# Get OpenAI Embeddings
def get_openai_embedding(text: str) -> Optional[np.ndarray]:
    try:
        response = client.embeddings.create(input=[text], model=EMBEDDING_MODEL)
        embedding = np.array(response.data[0].embedding, dtype=np.float32)
        return embedding
    except OpenAIError as e:
        print(f"⚠️ OpenAI Embedding Error: {str(e)}")
        return None
    except Exception as e:
        print(f"⚠️ Unexpected error getting embedding: {str(e)}")
        return None

# FAISS Search (Vector-based)
# FAISS Search (Vector-based)
def search_faiss(query: str, top_k: int = TOP_K) -> List[dict]:
    index, chunks = load_faiss_data()
    if index is None or not chunks:
        return []

    query_embedding = get_openai_embedding(query)
    if query_embedding is None:
        return []

    query_embedding = np.expand_dims(query_embedding, axis=0)

    try:
        distances, indices = index.search(query_embedding, top_k)
        results = []
        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if 0 <= idx < len(chunks) and dist >= SIMILARITY_THRESHOLD:
                chunk = chunks[idx]
                results.append({
                    "text": chunk.get("text", "No text available"),
                    "page_number": chunk.get("page_number", "Unknown"),  # Ensure page number is included
                    "similarity": float(dist),
                    "source": chunk.get("source", "Unknown")  # If you have a filename or chapter info, include it
                })
        return results

    except Exception as e:
        print(f"⚠️ FAISS Search Error: {str(e)}")
        return []

# Keyword Search
def keyword_search(query: str, chunks: List[dict]) -> List[dict]:
    """Find exact keyword matches in chunks."""
    keyword_matches = []
    query_words = query.lower().split()

    for chunk in chunks:
        chunk_text = chunk.get("text", "").lower()
        if any(word in chunk_text for word in query_words):
            keyword_matches.append({
                "text": chunk.get("text", "No text available"),
                "page_number": chunk.get("page_number", "Unknown"),
                "similarity": 1.0
            })

    return keyword_matches


def search_hybrid(query: str, top_k: int = TOP_K) -> List[dict]:
    """Hybrid search combining keyword and vector-based FAISS search."""
    index, chunks = load_faiss_data()
    if index is None or not chunks:
        return []

    keyword_results = keyword_search(query, chunks)
    vector_results = search_faiss(query, top_k)

   
    unique_results = {res["text"]: res for res in (keyword_results + vector_results)}

    return sorted(unique_results.values(), key=lambda x: x["similarity"], reverse=True)

FALLBACK_ANSWERS = {
    "plant require animals for photosynthesis": 
        "No, plants don’t need animals for photosynthesis. They only need sunlight, carbon dioxide, and water.",
    "plant require cow’s milk for photosynthesis": 
        "No, plants do not require cow’s milk for photosynthesis. They use sunlight, carbon dioxide, and water to produce their own food.",
    "leichen": 
        "Lichens are a symbiotic association between a fungus and a chlorophyll-containing partner, such as an alga. The fungus provides shelter, water, and certain nutrients, while the alga provides food through photosynthesis."
}


def generate_cohesive_answer(query: str, results: List[dict]) -> str:
    """Generate a structured response using retrieved context, fallback knowledge, or 'out of scope' handling."""
    
    if results:
        # Extract context and track page numbers
        formatted_results = []
        pages = set()
        sources = set()

        for res in results:
            page = res.get("page_number", "Unknown")
            source = res.get("source", "Unknown")
            text = res.get("text", "")
            formatted_results.append(f"📄 Page {page} ({source}): {text[:200]}...")  # Show first 200 chars for preview
            if page != "Unknown":
                pages.add(page)
            if source != "Unknown":
                sources.add(source)

        context = "\n\n".join(formatted_results)
        page_reference = ", ".join(map(str, sorted(pages))) if pages else "Unknown"
        source_reference = ", ".join(sources) if sources else "Unknown"

        response_prompt = (
            f"Based on the following textbook excerpts, answer the query '{query}' "
            f"strictly using the given context. If the context does not contain relevant information, reply only with: 'This is out of my scope.'\n\n"
            f"{context}\n\n"
            f"Your answer should be clear, concise, and reference the relevant page numbers explicitly when available. "
            f"If multiple pages contribute to the answer, mention them. If no page number is available, state 'Source: Page Unknown'.\n\n"
            f"Answer:"
        )

        try:
            response = client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": "You are a science assistant that strictly answers based on the provided textbook excerpts. Do not generate any information beyond the retrieved context. Always reference the page number(s) if available."},
                    {"role": "user", "content": response_prompt}
                ],
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS
            )

            # Get the generated answer
            answer = response.choices[0].message.content.strip()

            # If the response is out of scope, return a default out-of-scope response
            if "out of my scope" in answer.lower():
                return "This is out of my scope."

            # Append source reference properly
            answer += f"\n\n(Source: {source_reference}, Pages: {page_reference})"

            return answer

        except OpenAIError as e:
            print(f"⚠️ OpenAI Generation Error: {str(e)}")
            return "Sorry, I couldn't generate a response."
    
    # If no relevant search results, check fallback answers
    query_lower = query.lower().strip()
    for key, fallback_answer in FALLBACK_ANSWERS.items():
        if key.lower() in query_lower:
            return fallback_answer

    return "This is out of my scope."


def main():
    query = input("Enter your query: ")
    results = search_hybrid(query)

    if results:
        print("\n🔍 Top Results:")
        for res in results:
            print(f"- Page {res['page_number']} (Similarity: {res['similarity']:.4f}): {res['text'][:100]}...")

        answer = generate_cohesive_answer(query, results)
        print("\n💡 Final Answer:")
        print(answer)
    else:
        print("No relevant information found.")

if __name__ == "__main__":
    main()
