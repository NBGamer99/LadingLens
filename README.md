# LadingLens

A full-stack automation agent for ingesting, classifying, and extracting data from logistics emails (Bill of Lading).

## Features
- **Email Ingestion**: Fetches recent emails from Gmail via API.
- **Auto-Classification**: Determines "Pre-alert" vs "Draft" status using specific heuristics.
- **Document Processing**: Extracts text from PDF attachments (HBL/MBL).
- **AI Extraction**: Uses LLMs (Ollama/Anthropic) via `pydantic-ai` agents to extract structured data (Parties, Containers, Dates).
- **Deduplication**: Prevents processing the same document twice using unique hashes.
- **UI**: Modern React Dashboard (Bun + Vite) for reviewing extracted data.

## Architecture
- **Frontend**: React, TailwindCSS, Lucide Icons, Axios.
- **Backend**: FastAPI (Async), Pydantic, Firestore, Gmail API.
- **AI**: `pydantic-ai` (agent framework), `pdfplumber` (text extraction).

## Setup & Running

### Prerequisites
1.  **Python 3.11+**
2.  **Bun** (or Node.js)
3.  **Google Cloud Project** with Gmail API and Firestore enabled. (Credentials required)
4.  **Ollama** running locally (optional, for free inference).

### 1. Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Configuration**:
1.  Copy `.env.example` to `.env` (already created).
2.  Place your `credentials.json` (Gmail OAuth Desktop Client) in `backend/`.
3.  Ensure Firestore is enabled in your GCP project.

**Running**:
```bash
python app/main.py
```
*On first run, a browser window will open to authenticate with Gmail.*

### 2. Frontend Setup
```bash
cd frontend
bun install
bun run dev
```

### 3. Usage
1.  Open `http://localhost:5173`.
2.  Click "Process Gmail Inbox".
3.  View extracted HBL/MBL records in the tabs.

## AI Configuration
By default, the system uses **Ollama** (`llama3`).
To use **Anthropic**:
1.  Set `LLM_PROVIDER=anthropic` in `backend/.env`.
2.  Set `ANTHROPIC_API_KEY=sk-...` in `backend/.env`.
