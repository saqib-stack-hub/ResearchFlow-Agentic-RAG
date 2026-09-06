# ResearchFlow AI

> **Production-Ready Agentic RAG Document Question Answering System**

ResearchFlow AI is an intelligent document question-answering system that allows users to upload documents and ask questions about their content.

Unlike a basic `Question → Retriever → LLM → Answer` pipeline, ResearchFlow AI uses an **agentic LangGraph workflow** that analyzes queries, retrieves relevant information, evaluates retrieval quality, rewrites queries when necessary, generates grounded answers, and verifies citations before returning the final response.

---

## 📌 Project Overview

ResearchFlow AI is designed as a production-oriented **Retrieval-Augmented Generation (RAG)** application.

Users can:

* Upload PDF, TXT, and DOCX documents
* Automatically process and index documents
* Ask natural-language questions about uploaded documents
* Retrieve relevant document chunks using semantic search
* Re-rank retrieved results
* Automatically rewrite queries when retrieval quality is poor
* Generate answers grounded in retrieved context
* View document and page-level citations
* Maintain chat history
* Manage uploaded documents

The system is built using:

* Python
* LangChain
* LangGraph
* FastAPI
* Pydantic
* PostgreSQL
* Redis
* Qdrant
* Embeddings
* LLM
* React / Next.js
* Docker

---

# 🏗️ Architecture

The high-level architecture of ResearchFlow AI is:

```text
                    ┌─────────────────────┐
                    │       User          │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ React / Next.js     │
                    │     Frontend        │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    FastAPI API      │
                    └──────────┬──────────┘
                               │
                 ┌─────────────┴─────────────┐
                 │                           │
                 ▼                           ▼
        ┌─────────────────┐        ┌─────────────────┐
        │ Document        │        │ LangGraph       │
        │ Ingestion       │        │ Agentic RAG     │
        └────────┬────────┘        └────────┬────────┘
                 │                          │
                 ▼                          ▼
        ┌─────────────────┐        ┌─────────────────┐
        │ LangChain       │        │ Query Analyzer  │
        │ Loaders         │        └────────┬────────┘
        └────────┬────────┘                 │
                 ▼                          ▼
        ┌─────────────────┐        ┌─────────────────┐
        │ Cleaning &      │        │ Retriever       │
        │ Chunking        │        └────────┬────────┘
        └────────┬────────┘                 │
                 ▼                          ▼
        ┌─────────────────┐        ┌─────────────────┐
        │ Embeddings      │        │ Relevance       │
        └────────┬────────┘        │ Grader          │
                 │                 └───────┬─────────┘
                 ▼                         │
        ┌─────────────────┐        ┌───────┴────────┐
        │ Qdrant          │        │                │
        │ Vector Database │        ▼                ▼
        └─────────────────┘   Relevant         Not Relevant
                                   │                │
                                   ▼                ▼
                              Generate Answer   Query Rewriter
                                   │                │
                                   │                └──► Retriever
                                   ▼
                            Citation Checker
                                   │
                                   ▼
                             Final Response
```

---

# 🔄 LangGraph Agentic Workflow

The core of the application is an agentic LangGraph workflow.

```text
START
  │
  ▼
Query Analyzer
  │
  ▼
Retriever
  │
  ▼
Relevance Grader
  │
  ├─────────────── Relevant ───────────────► Generate Answer
  │                                             │
  │                                             ▼
  │                                      Citation Checker
  │                                             │
  │                                             ▼
  │                                      Final Response
  │                                             │
  │                                             ▼
  │                                            END
  │
  └────────────── Not Relevant ───────────► Query Rewriter
                                                │
                                                ▼
                                             Retriever
```

### Query Analyzer

Determines:

* Whether the question is document-related
* What type of information is requested
* Whether retrieval should be performed

### Retriever

Searches the vector database for semantically relevant document chunks.

### Relevance Grader

Evaluates whether retrieved documents actually answer the user's question.

The grader produces a relevance decision and score.

### Query Rewriter

If retrieval quality is insufficient, the original question is rewritten into a better search query and retrieval is performed again.

### Answer Generator

Generates an answer using only the optimized retrieved context.

### Citation Checker

Verifies:

* The answer is supported by retrieved documents
* Citations are present
* Citations correspond to actual documents
* Unsupported claims are removed or flagged

---

# 📚 Document Ingestion Pipeline

ResearchFlow AI supports:

* PDF
* TXT
* DOCX

The ingestion pipeline automatically detects the document type and uses the appropriate LangChain loader.

```text
Upload Document
       │
       ▼
File Type Detection
       │
       ▼
LangChain Document Loader
       │
       ▼
Document Cleaning
       │
       ├── Empty Page Removal
       ├── Whitespace Cleaning
       ├── Duplicate Removal
       ├── Broken Text Handling
       └── Metadata Normalization
       │
       ▼
Text Chunking
       │
       ▼
Embeddings
       │
       ▼
Qdrant Vector Database
```

### Chunking

The chunking strategy supports configurable:

```text
chunk_size
chunk_overlap
```

These values can be adjusted through configuration/environment variables.

---

# 🧠 Advanced RAG Pipeline

ResearchFlow AI implements an advanced retrieval pipeline rather than basic similarity search.

```text
User Query
    │
    ▼
Query Processing
    │
    ▼
Semantic Retrieval
    │
    ▼
Top-K Results
    │
    ▼
Advanced Retrieval / MMR
    │
    ▼
Re-ranking
    │
    ▼
Relevance Filtering
    │
    ▼
Duplicate Removal
    │
    ▼
Context Length Optimization
    │
    ▼
LLM
    │
    ▼
Answer + Citations
```

### Retrieval Configuration

The system supports configurable:

* `top_k`
* similarity threshold
* chunk size
* chunk overlap

### Advanced Retrieval

The implementation can use techniques such as:

* MMR
* Hybrid retrieval
* Multi-query retrieval
* Parent-document retrieval

### Re-ranking

Retrieved documents are re-ranked before being passed to the LLM.

This improves the quality of the final context and reduces irrelevant information.

### Context Optimization

Before generation, the system performs:

* Duplicate removal
* Relevance filtering
* Context length control

This helps prevent unnecessary document content from being sent to the LLM.

---

# 📎 Citation System

Every document-grounded answer should include citations.

Example:

```text
Answer:

The company's refund period is 30 days.

Sources:

[1] company_policy.pdf — Page 4
[2] refund_policy.pdf — Page 7
```

Citations are generated from the **actual retrieved documents** rather than manually hardcoded sources.

---

# ⚙️ Backend

The backend is implemented using **FastAPI**.

## API Endpoints

### Upload Document

```http
POST /documents/upload
```

Uploads and processes a document.

Supported formats:

* PDF
* TXT
* DOCX

---

### List Documents

```http
GET /documents
```

Returns indexed documents.

---

### Delete Document

```http
DELETE /documents/{id}
```

Deletes a document and its associated indexed data.

---

### Chat

```http
POST /chat
```

Example request:

```json
{
  "question": "What is the company's refund policy?",
  "session_id": "abc123"
}
```

Example response:

```json
{
  "answer": "The refund period is 30 days.",
  "citations": [
    {
      "document": "policy.pdf",
      "page": 4
    }
  ],
  "retrieval_score": 0.91
}
```

---

### Chat History

```http
GET /chat/history/{session_id}
```

Returns previous conversations for a session.

---

### Health Check

```http
GET /health/chat
```

Used to verify backend and AI/RAG service health.

---

# 🖥️ Frontend

The frontend is built with React / Next.js.

Main interface sections include:

### Document Management

```text
Upload Document
       ↓
Processing
       ↓
Indexed ✓
```

Users can upload documents and monitor their processing status.

### Chat Interface

The chat interface allows users to:

* Ask questions
* Receive AI-generated answers
* View citations
* Continue conversations
* Access previous chat history

---

# 🗄️ Data & Infrastructure

ResearchFlow AI uses:

### PostgreSQL

Used for persistent application data such as:

* Documents
* Sessions
* Chat history
* Metadata

### Redis

Used for:

* Caching
* Temporary state
* Application performance

### Qdrant

Used as the persistent vector database for semantic retrieval.

### LLM

Used for:

* Query analysis
* Query rewriting
* Relevance grading
* Answer generation
* Citation verification

---

# 🔐 Environment Variables

Create a `.env` file based on `.env.example`.

Example:

```env
OPENAI_API_KEY=

HUGGINGFACE_API_KEY=

DATABASE_URL=

REDIS_URL=

QDRANT_URL=
QDRANT_API_KEY=

LLM_MODEL=

EMBEDDING_MODEL=

FRONTEND_URL=

BACKEND_URL=

CORS_ORIGINS=
```

> **Never commit real API keys, passwords, database credentials, or private service URLs to GitHub.**

The repository should contain `.env.example`, not the real `.env` file.

---

# 🚀 Installation

## 1. Clone Repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd researchflow-ai
```

## 2. Configure Environment

Copy:

```text
.env.example
```

to:

```text
.env
```

Then configure the required credentials and service URLs.

---

# ▶️ Running Locally

## Backend

Navigate to the backend:

```bash
cd backend
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start FastAPI:

```bash
uvicorn app.main:app --reload
```

Backend:

```text
http://localhost:8000
```

Swagger documentation:

```text
http://localhost:8000/docs
```

---

## Frontend

Navigate to the frontend:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start development server:

```bash
npm run dev
```

Frontend:

```text
http://localhost:3000
```

---

# 🐳 Docker Setup

The complete system is containerized using Docker.

Required files:

```text
docker-compose.yml
Dockerfile.backend
Dockerfile.frontend
.env.example
```

Start the complete application:

```bash
docker compose up --build
```

This starts the required application services and infrastructure.

---

# 🧪 Evaluation

ResearchFlow AI includes an evaluation dataset containing at least **30 questions** covering different RAG scenarios.

The evaluation categories include:

* Easy questions
* Multi-hop questions
* Citation-specific questions
* No-answer questions
* Ambiguous questions
* Hallucination-focused questions

Example:

```json
{
  "question": "What database does the system use?",
  "expected_answer": "PostgreSQL",
  "expected_source": "architecture.pdf"
}
```

## Retrieval Metrics

The system evaluates:

* Recall@K
* Precision@K

## Generation Metrics

The system evaluates:

* Faithfulness
* Answer Relevance
* Citation Correctness

Evaluation can be implemented using:

* Ragas
* DeepEval
* Custom evaluation code

Evaluation results are stored in:

```text
evaluation/results/
```

---

# 📁 Project Structure

```text
researchflow-ai/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── agents/
│   │   ├── rag/
│   │   ├── graph/
│   │   ├── models/
│   │   └── services/
│   │
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── services/
│   └── Dockerfile
│
├── data/
│
├── evaluation/
│   ├── questions.json
│   ├── evaluate.py
│   └── results/
│
├── docker-compose.yml
├── .env.example
├── README.md
└── architecture.png
```

---

# 📖 API Documentation

When running locally, FastAPI automatically provides interactive Swagger documentation:

```text
http://localhost:8000/docs
```

The deployed application should expose the corresponding public Swagger URL.

---

# ☁️ Deployment

The application is designed for cloud deployment.

Possible deployment architecture:

```text
                 Internet
                    │
                    ▼
          ┌──────────────────┐
          │ Next.js Frontend │
          │     Hosting      │
          └────────┬─────────┘
                   │
                   ▼
          ┌──────────────────┐
          │ FastAPI Backend  │
          │      Cloud       │
          └────────┬─────────┘
                   │
       ┌───────────┼───────────┐
       ▼           ▼           ▼
 PostgreSQL      Redis       Qdrant
       │           │           │
       └───────────┼───────────┘
                   ▼
                  LLM
```

Possible hosting platforms include:

* Vercel
* Render
* Railway
* AWS
* Azure
* Google Cloud
* Hugging Face Spaces

### Deployment URLs

After deployment, update this section with the **actual working URLs**:

```text
Frontend:
<ACTUAL_FRONTEND_URL>

Backend:
<ACTUAL_BACKEND_URL>

Swagger:
<ACTUAL_SWAGGER_URL>
```

> Do not submit placeholder URLs. These must be replaced with real deployed URLs before final submission.

---

# 🔒 Security

The project follows environment-based configuration.

Sensitive credentials must never be committed to GitHub.

Protected values include:

```text
OPENAI_API_KEY
HUGGINGFACE_API_KEY
DATABASE_URL
REDIS_URL
QDRANT_API_KEY
```

The repository should only contain:

```text
.env.example
```

with empty or example values.

---

# 📊 Observability & Logging

The backend includes structured logging and error handling to help monitor:

* API requests
* Retrieval failures
* RAG workflow errors
* Document processing errors
* LLM failures
* Application health

Additional observability tools such as LangSmith can be integrated for production monitoring.

---

# 🧩 Bonus Features

Potential bonus features supported by the architecture include:

### Streaming

Stream LLM responses using FastAPI SSE/WebSockets and LangGraph.

### Long-Term Memory

Persist conversation history and use previous interactions during future queries.

### Multi-User Authentication

Add:

* Registration
* Login
* JWT authentication
* Protected documents

### Hybrid Search

Combine:

```text
BM25
+
Vector Search
```

### Multi-Agent Architecture

Possible architecture:

```text
Research Agent
      ↓
Retriever Agent
      ↓
Verification Agent
      ↓
Citation Agent
```

### Observability

Possible integrations:

* LangSmith
* Structured logging
* Latency tracking
* Token usage monitoring
* Error monitoring

---

# ⚠️ Limitations

Potential limitations include:

* LLM output quality depends on the selected model.
* Very large documents may require additional processing optimization.
* OCR may be required for scanned/image-only PDFs.
* Retrieval quality depends on embedding and reranking models.
* Cloud deployment requires external infrastructure and API credentials.
* Evaluation metrics may vary depending on the evaluation model and dataset.

---

# 🔮 Future Improvements

Future improvements may include:

* Multi-user authentication
* Streaming responses
* Hybrid retrieval
* Better reranking models
* OCR support
* Advanced document parsing
* Multi-agent research workflows
* LangSmith observability
* Better long-term memory
* Automated evaluation pipelines
* Usage analytics
* Rate limiting
* Production-grade monitoring

---

# ✅ Assignment Requirements Checklist

| Requirement                | Status |
| -------------------------- | ------ |
| PDF upload                 | ✅      |
| TXT upload                 | ✅      |
| DOCX upload                | ✅      |
| Automatic file detection   | ✅      |
| Document cleaning          | ✅      |
| Configurable chunking      | ✅      |
| Embeddings                 | ✅      |
| Persistent vector database | ✅      |
| Semantic retrieval         | ✅      |
| Configurable Top-K         | ✅      |
| Similarity threshold       | ✅      |
| Advanced retrieval         | ✅      |
| Re-ranking                 | ✅      |
| Context optimization       | ✅      |
| Actual document citations  | ✅      |
| LangGraph workflow         | ✅      |
| Query Analyzer             | ✅      |
| Relevance Grader           | ✅      |
| Query Rewriter             | ✅      |
| Retrieval retry            | ✅      |
| Citation verification      | ✅      |
| Conditional routing        | ✅      |
| FastAPI backend            | ✅      |
| Required API endpoints     | ✅      |
| React / Next.js frontend   | ✅      |
| Docker                     | ✅      |
| PostgreSQL                 | ✅      |
| Redis                      | ✅      |
| Qdrant                     | ✅      |
| Evaluation dataset         | ✅      |
| Evaluation metrics         | ✅      |
| README                     | ✅      |
| Architecture diagram       | ✅      |
| Cloud deployment           | ⏳      |
| Live frontend URL          | ⏳      |
| Live backend URL           | ⏳      |
| Live Swagger URL           | ⏳      |
| Demo video                 | ⏳      |

---

# 📦 Final Submission

The final submission should contain:

1. GitHub Repository
2. Live Deployed Application URL
3. Backend API URL
4. Swagger Documentation URL
5. 30-question Evaluation Dataset
6. Evaluation Results
7. Docker Configuration
8. README.md
9. Architecture Diagram
10. Short Demo Video

---

# 👨‍💻 Author

**Saqib Ali**

AI Engineer / Computer Science Student

ResearchFlow AI — Advanced Agentic RAG System
