# LearnixAI - Developer Documentation

## Project Overview

**LearnixAI** is an AI-powered E-Learning Platform with two main components:

| Component | Technology | Port | Purpose |
|-----------|------------|------|---------|
| Main App | Node.js + Express | 16000 | Web interface, user management, dashboards |
| Chatbot Service | Python + FastAPI | 8000 | AI-powered Q&A and answer evaluation |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        LearnixAI                            │
├─────────────────────────────┬───────────────────────────────┤
│     Main Application        │      Chatbot Service          │
│   (Node.js + Express)     │    (Python + FastAPI)         │
│         :16000              │         :8000                 │
│                             │                               │
│  ┌───────────────┐         │  ┌─────────────────┐          │
│  │   MongoDB     │         │  │   FAISS Index   │          │
│  │  (Mongoose)   │         │  │  (Vector Store) │          │
│  └───────────────┘         │  └─────────────────┘          │
│                             │                               │
│  ┌───────────────┐         │  ┌─────────────────┐          │
│  │   EJS Views   │         │  │  Embeddings     │          │
│  │  (Frontend)   │         │  │  (processed/)   │          │
│  └───────────────┘         │  └─────────────────┘          │
└─────────────────────────────┴───────────────────────────────┘
```

---

## 1. Main Application (`/LearnixAI`)

### Tech Stack
- **Runtime:** Node.js
- **Framework:** Express.js 4.21.2
- **Database:** MongoDB (Mongoose 8.9.5)
- **Template Engine:** EJS 3.1.10
- **Authentication:** bcrypt 5.1.1
- **File Uploads:** Multer 1.4.5-lts.1

### Directory Structure

```
LearnixAI/
├── src/
│   ├── index.js              # Application entry point
│   ├── config/               # Database configuration
│   │   └── db.js
│   ├── controllers/          # Business logic
│   │   ├── auth/             # Authentication controllers
│   │   ├── school/           # School management
│   │   ├── student/          # Student controllers
│   │   ├── teach/            # Teacher controllers
│   │   └── teacherDashboard/   # Dashboard features
│   ├── models/               # Mongoose schemas
│   │   ├── User.js
│   │   ├── school/
│   │   ├── student/
│   │   ├── superAdmin/
│   │   ├── teacher/
│   │   └── teacherDashboard/
│   ├── routes/               # Route definitions
│   │   ├── School/
│   │   ├── Student/
│   │   ├── Teacher/
│   │   ├── TeacherDashboard/
│   │   ├── chatbotRoutes.js
│   │   ├── home/
│   │   ├── studentDashboardRoutes.js
│   │   └── teacherDashboardRoutes.js
│   ├── views/                # EJS templates
│   └── utils/                # Utility functions
├── public/                   # Static assets
├── package.json
└── node_modules/
```

### Core Routes

| Route | Description |
|-------|-------------|
| `/` | Home page |
| `/school` | School management endpoints |
| `/teacher` | Teacher authentication & management |
| `/student` | Student authentication & management |
| `/teacher/dashboard` | Teacher dashboard interface |
| `/student/dashboard` | Student dashboard interface |
| `/teacher/announcement` | Announcement management |
| `/teacher/assignment` | Assignment CRUD |
| `/teacher/studyMaterial` | Study material uploads |
| `/teacher/events` | Event management |
| `/chatbot` | Chatbot integration proxy |

### Running the Application

```bash
cd LearnixAI
npm install
npm start    # Uses nodemon for auto-restart
# or
node src/index.js
```

---

## 2. Chatbot Service (`/Learnixchatbot`)

### Tech Stack
- **Framework:** FastAPI (Python)
- **Vector DB:** FAISS (Facebook AI Similarity Search)
- **Embeddings:** Sentence-transformers / OpenAI
- **NLP:** Custom hybrid search algorithm

### Directory Structure

```
Learnixchatbot/
├── scripts/
│   ├── server.py           # FastAPI entry point
│   ├── search_faiss.py     # Core search logic
│   ├── chunk_text.py       # Text chunking utilities
│   ├── extract_text.py     # Text extraction from documents
│   └── debug_faiss.py      # Debugging utilities
├── data/
│   ├── raw/                # Original documents (PDFs, etc.)
│   ├── processed/          # Extracted text chunks
│   └── embeddings/         # FAISS index files
├── frontend/
│   └── (chat interface files)
└── embeddings/             # Pre-computed embeddings
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Process user query and return AI answer |
| `/api/evaluate` | POST | Evaluate student answer against question |

### Request/Response Format

**Chat Endpoint:**
```json
// POST /api/chat
{
  "query": "What is photosynthesis?"
}

// Response
{
  "answer": "Photosynthesis is the process...",
  "source": "search"
}
```

**Evaluate Endpoint:**
```json
// POST /api/evaluate
{
  "question": "Explain photosynthesis",
  "user_answer": "It's how plants make food using sunlight"
}

// Response
{
  "evaluation": "Your answer correctly identifies..."
}
```

### Running the Chatbot Service

```bash
cd Learnixchatbot/scripts
pip install fastapi uvicorn faiss-cpu sentence-transformers
python server.py

# Or with auto-reload
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

---

## 3. Database Schema Overview

### Key Models

**User** (`src/models/User.js`)
```javascript
{
  email: String,
  password: String,  // Hashed with bcrypt
  role: String,      // 'school', 'teacher', 'student', 'superAdmin'
  createdAt: Date
}
```

**School** (`src/models/school/`)
- School profile and settings
- Admin management

**Teacher** (`src/models/teacher/`)
- Profile information
- Subject assignments
- Class management

**Student** (`src/models/student/`)
- Profile data
- Enrollments
- Progress tracking

**TeacherDashboard** (`src/models/teacherDashboard/`)
- Announcements
- Assignments
- Study materials
- Events calendar

---

## 4. Development Workflow

### Prerequisites
- Node.js 18+
- Python 3.9+
- MongoDB (local or Atlas)
- pip (Python package manager)

### Setup Steps

1. **Clone and setup main app:**
```bash
git clone <repo-url>
cd LearnixAI
npm install
cp .env.example .env  # Configure your environment variables
```

2. **Setup chatbot service:**
```bash
cd Learnixchatbot
pip install -r requirements.txt  # If available, or install individually
```

3. **Start services (run in separate terminals):**
```bash
# Terminal 1: Main app
cd LearnixAI
npm start

# Terminal 2: Chatbot service
cd Learnixchatbot/scripts
python server.py
```

### Environment Variables

Create `.env` in `LearnixAI/`:
```env
PORT=16000
MONGODB_URI=mongodb://localhost:27017/learnixai
JWT_SECRET=your_secret_key
CHATBOT_URL=http://localhost:8000
```

---

## 5. Key Features

### For Schools
- Multi-tenant school management
- Teacher/student enrollment
- Administrative controls

### For Teachers
- **Dashboard:** Overview of classes and activities
- **Announcements:** Post class-wide notifications
- **Assignments:** Create, distribute, and grade assignments
- **Study Materials:** Upload and organize learning resources
- **Events:** Schedule and manage class events

### For Students
- Personal dashboard
- Assignment submissions
- Access to study materials
- Chatbot for Q&A
- Answer evaluation feedback

### AI Features
- **Hybrid Search:** Combines keyword + semantic search
- **Contextual Answers:** Generates responses from indexed content
- **Answer Evaluation:** Provides feedback on student responses

---

## 6. Common Commands

| Command | Purpose |
|---------|---------|
| `npm start` | Start main app with nodemon |
| `python scripts/server.py` | Start chatbot service |
| `python scripts/chunk_text.py` | Process new documents |
| `python scripts/debug_faiss.py` | Debug vector store |

---

## 7. Troubleshooting

**Port 16000 in use:**
```bash
# Find and kill process
lsof -i :16000
kill -9 <PID>
```

**Port 8000 in use (chatbot):**
```bash
lsof -i :8000
kill -9 <PID>
# Or use different port
uvicorn server:app --port 8001
```

**FAISS index missing:**
- Ensure `data/embeddings/` contains the index files
- Run document processing pipeline if needed

---

## 8. Contributing

1. Create feature branches from `main`
2. Follow existing code style
3. Test both services before submitting
4. Update this documentation for significant changes

---

## License

[Specify your license here]

---

**Maintained by:** LearnixAI Team  
**Last Updated:** March 2026
