<div align="center">

<img src="https://img.icons8.com/color/96/000000/container-truck.png" alt="Logo" height="96">

<h1 align="center">LadingLens</h1>
<h3 align="center">The "I-Don't-Want-To-Read-PDFs" Automation Agent 🚛</h3>

<p align="center">
  A full-stack agent that reads logistics emails so you don't have to.
  <br />
  <br />
  <a href="#setup--installation"><strong>Get Started »</strong></a>
  ·
  <a href="project_writeup.md"><strong>Read the Tech Docs »</strong></a>
  ·
  <a href="#demo"><strong>View Demo</strong></a>
</p>

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![GCP](https://img.shields.io/badge/Google_Cloud-Firestore-4285F4?style=for-the-badge&logo=google-cloud&logoColor=white)
![Agent](https://img.shields.io/badge/Agent-Pydantic_AI-E91E63?style=for-the-badge)

</div>

<br />

> [!NOTE]
> **Why does this exist?** Because manually copying container numbers from PDFs is a violation of human rights. This tool automates the extraction of Bill of Lading (HBL/MBL) data from Gmail to Firestore.

---

## 🧐 What does this thing do?

LadingLens is an intelligent ingestion pipeline that:
1.  **Ingests Emails**: Retrieves the last 10 emails from a specific Gmail account.
2.  **Classifies Status**: Determines if an email is a "Pre-alert" or "Draft" using heuristic analysis.
3.  **Processes PDFs**: Extracts structured data (Shipper, Consignee, Containers) from Bill of Lading attachments.
4.  **Deduplicates**: Prevents redundant processing using unique hash keys for every document.
5.  **Visualizes**: Presents extracted data in a clean, paginated React dashboard.

## 🚀 Setup & Installation

### Prerequisites
*   **Python 3.11+** (Managed via `pyenv` recommended)
*   **Bun** or Node.js
*   **Google Cloud Project** (The cloud ☁️)
    *   Enabled APIs: Gmail API, Firestore.
    *   `credentials.json` for an OAuth Desktop Client.

### 0. Google Cloud Setup
Since this is a public repo, you need your own credentials:
1.  Go to [Google Cloud Console](https://console.cloud.google.com/).
2.  Create a project and enable **Gmail API** and **Cloud Firestore API**.
3.  Go to **APIs & Services > Credentials**.
4.  Create **OAuth 2.0 Client ID** (Application type: Desktop app).
5.  Download the JSON, rename it to `credentials.json`, and place it in the `secrets` folder.
6.  Create a Service Account for Firestore, generate a key (JSON), and save the path for the `.env`.

### 1. Backend Setup

```bash
# Navigate to the backend directory
cd backend

# Create and activate virtual environment using pyenv
pyenv install 3.11.5
pyenv virtualenv 3.11.5 ladinglens
pyenv local ladinglens

# Install dependencies
pip install -r requirements.txt
```

#### Configuration (`.env`)
Create a `.env` file in `root folder` based on `.env.example`:

```ini
# .env
GOOGLE_APPLICATION_CREDENTIALS="path/to/your/firebase-service-account.json"
GMAIL_CREDENTIALS_FILE="path/to/your/credentials.json"
LLM_PROVIDER="ollama" # or "anthropic"
```

> [!IMPORTANT]
> If using **Anthropic** (Claude), set `ANTHROPIC_API_KEY=sk-...` in your `.env`.
> If using **Ollama**, make sure it's running (`ollama serve`).

### 2. Frontend Setup

```bash
# Navigate to frontend
cd ../frontend

# Install dependencies
bun install

# Start the development server
bun run dev
```

Visit `http://localhost:5173` to view the application.

---

## 🎮 Usage

1.  **Authenticate**: On first run (`python app/main.py`), a browser window will open to authorize access to your Gmail. Click "Allow".
    > **Note**: This creates a `token.json` file for future runs.
2.  **Process**: In the UI, click the **"Process Gmail Inbox"** button.
3.  **Wait**: The system will fetch emails and extract data in the background.
4.  **Review**: View the extracted HBL and MBL records in the respective tabs.

---

## 🏗️ Architecture & Details

For a detailed breakdown of the extraction algorithm, benchmarks, and architectural decisions:

👉 **[Read the Full Project Write-up](project_writeup.md)**

---

## 🛠️ Tech Stack

*   **Backend**: Python, FastAPI, Pydantic, PydanticAI
*   **Frontend**: React, TypeScript, TailwindCSS, Bun
*   **Database**: Google Firestore (NoSQL)
*   **LLM**: Ollama (Llama 3) or Anthropic (Claude 4 Sonnet)

---

## Contact Information 📧

- **Main Dev**: Yasser Nabouzi - [@NBGamer99](https://github.com/NBGamer99)
