from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware 
from pydantic import BaseModel
from search_faiss import search_hybrid, generate_cohesive_answer, FALLBACK_ANSWERS
import os
import sys
import logging
from typing import Dict, Any
import pathlib
from contextlib import asynccontextmanager


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = pathlib.Path(__file__).parent.resolve()
os.chdir(SCRIPT_DIR) 

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Modern lifespan handler replacing startup/shutdown events"""
 
    logger.info("🔍 Verifying resources...")
    from search_faiss import VECTOR_STORE_PATH, CHUNKS_PATH
    
   
    if not os.path.exists(VECTOR_STORE_PATH):
        logger.error(f"❌ FAISS index missing at: {VECTOR_STORE_PATH}")
    else:
        logger.info(f"✅ FAISS index found ({os.path.getsize(VECTOR_STORE_PATH)} bytes)")
    
 
    if not os.path.exists(CHUNKS_PATH):
        logger.error(f"❌ Chunks file missing at: {CHUNKS_PATH}")
    else:
        logger.info(f"✅ Chunks file found ({os.path.getsize(CHUNKS_PATH)} bytes)")
    
   
    test_query = "photosynthesis"
    logger.info(f"🧪 Testing search with query: '{test_query}'")
    from search_faiss import search_hybrid
    test_results = search_hybrid(test_query)
    logger.info(f"🧪 Test results count: {len(test_results)}")
    
    yield  
    
   

app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:16000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    query: str

class EvaluateRequest(BaseModel):
    question: str
    user_answer: str

@app.post("/api/chat")
async def chat(request: ChatRequest):
    query = request.query.strip()
    logger.info(f"\n{'='*50}")
    logger.info(f"📩 Processing query: '{query}' (Length: {len(query)})")
    
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    

    logger.info("🔍 Executing hybrid search...")
    results = search_hybrid(query)
    
    if not results:
        logger.warning("⚠️ No results found in vector store")

    logger.info(f"🔍 FAISS returned {len(results)} results")


    if results:
        logger.info(f"📝 First result: {results[0]}")

   
    answer = generate_cohesive_answer(query, results)
    
    logger.info(f"💡 Generated answer: {answer[:200]}{'...' if len(answer) > 200 else ''}")

    return {"answer": answer, "source": "search" if answer != "This is out of my scope." else "out_of_scope"}

@app.post("/api/evaluate")
async def evaluate(request: EvaluateRequest):
    question = request.question.strip()
    user_answer = request.user_answer.strip()
    
    if not question or not user_answer:
        raise HTTPException(status_code=400, detail="Question and answer cannot be empty")
    
    logger.info(f"\n📝 Evaluation request - Q: '{question}' A: '{user_answer}'")
    
    question_results = search_hybrid(question)
    answer_results = search_hybrid(user_answer)

    if not question_results and not answer_results:
        logger.warning("⚠️ No context found for evaluation")
        return {"evaluation": "That's an interesting perspective! Let's explore another topic."}

    context = []
    if question_results:
        context.append(question_results[0]['text'])
    if answer_results:
        context.append(answer_results[0]['text'])

    evaluation = generate_cohesive_answer(
        f"Question: {question}\nAnswer: {user_answer}\nContext: {' '.join(context)}",
        question_results or answer_results
    )
    
    logger.info(f"📝 Evaluation result: {evaluation[:200]}{'...' if len(evaluation) > 200 else ''}")
    return {"evaluation": evaluation}

if __name__ == "__main__":
    import uvicorn
    try:
       
        logger.info("🔄 Registered routes:")
        for route in app.routes:
            logger.info(f"  {route.path} ({route.methods})")
        
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except OSError as e:
        if e.errno == 48: 
            logger.error("⚠️ Port 8000 is already in use. Try:")
            logger.error("   1. Kill the existing process: lsof -i :8000 && kill -9 <PID>")
            logger.error("   2. Use a different port: uvicorn server:app --port 8001")
            logger.error("   3. Wait a few minutes for the port to become available")
        else:
            logger.error(f"⚠️ Failed to start server: {str(e)}")