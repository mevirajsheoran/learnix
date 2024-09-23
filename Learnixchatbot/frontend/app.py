import streamlit as st
import os
import sys
from io import BytesIO
import time

# Add the path to the scripts directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

# Import search functions from search_faiss
from search_faiss import (
    search_hybrid,
    generate_cohesive_answer,
    FALLBACK_ANSWERS
)

# Configuration
TEACHER_NAME = "Professor Minakshi"
CONCEPTS_BEFORE_MCQ = 3

# Initialize session state variables
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": f"Hi there! I'm {TEACHER_NAME}, your science tutor. What would you like to learn about today?"}
    ]
    st.session_state.concept_count = 0
    st.session_state.recent_concepts = []
    st.session_state.waiting_for_answer = False
    st.session_state.current_question = None

# Streamlit CSS for chat bubbles and layout
st.markdown("""
<style>
    .chat-container {
        max-height: 70vh;
        overflow-y: auto;
        padding: 20px;
        display: flex;
        flex-direction: column;
    }
    .user-message {
        background-color: #FFFACD;
        color: black;
        border-radius: 18px 18px 0 18px;
        padding: 14px 18px;
        margin-left: auto;
        max-width: 75%;
        font-size: 16px;
        box-shadow: 2px 2px 8px rgba(0, 0, 0, 0.1);
        margin-bottom: 12px;
    }
    .assistant-message {
        background-color: #D8BFD8;
        color: black;
        border-radius: 18px 18px 18px 0;
        padding: 14px 18px;
        margin-right: auto;
        max-width: 75%;
        font-size: 16px;
        box-shadow: 2px 2px 8px rgba(0, 0, 0, 0.1);
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

def generate_response(query: str) -> str:
    """Generate response strictly based on search_faiss results without showing search metadata"""
    # First check if we have a fallback answer
    query_lower = query.lower().strip()
    for key, answer in FALLBACK_ANSWERS.items():
        if key.lower() in query_lower:
            return answer
    
    # Perform hybrid search (still used internally)
    results = search_hybrid(query)
    
    # Generate answer from the search results
    answer = generate_cohesive_answer(query, results)
    
    return answer

def evaluate_answer(question: str, user_answer: str) -> str:
    """Evaluate student's answer using search_faiss knowledge"""
    # Search for both question and answer to find relevant context
    question_results = search_hybrid(question)
    answer_results = search_hybrid(user_answer)
    
    if not question_results and not answer_results:
        return "That's an interesting perspective! Let's explore another topic."
    
    # Generate evaluation using the same search_faiss system
    context = []
    if question_results:
        context.append(question_results[0]['text'])
    if answer_results:
        context.append(answer_results[0]['text'])
    
    prompt = f"""
    Based on this context:
    {" ".join(context)}
    
    The student was asked: {question}
    They answered: {user_answer}
    
    Provide brief feedback and correction if needed.
    """
    
    return generate_cohesive_answer(prompt, question_results or answer_results)

st.title(f"{TEACHER_NAME}'s Science Tutor 🧪")

# Chat display
chat_container = st.container()
with chat_container:
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    for msg in st.session_state.messages:
        role_class = "user-message" if msg["role"] == "user" else "assistant-message"
        st.markdown(f'<div class="{role_class}">{msg["content"]}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Input
user_input = st.chat_input("Ask me anything about science...")

if user_input:
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # If waiting for an answer to a follow-up question
    if st.session_state.waiting_for_answer:
        evaluation = evaluate_answer(st.session_state.current_question, user_input)
        st.session_state.messages.append({"role": "assistant", "content": evaluation})
        st.session_state.waiting_for_answer = False
    else:
        # Generate clean response without search metadata
        response = generate_response(user_input)
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.session_state.recent_concepts.append(user_input)
        st.session_state.concept_count += 1
        
        # Check if response contains a question to wait for answer
        if "?" in response.split("\n")[-1]:
            st.session_state.waiting_for_answer = True
            st.session_state.current_question = response.split("\n")[-1]

    # Refresh UI
    st.rerun()