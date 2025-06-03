
# Invoice Processing Using AI Agents

A production-ready system for intelligently processing, classifying, and extracting data from invoices, emails, and business documents. Powered by a multi-agent AI framework with a dual interface—REST API (FastAPI) and a visual dashboard (Streamlit).

---

## Features

- **Multi-Format Document Support**  
  Process a wide range of input types including PDFs, Emails, JSON, and Images (with OCR capabilities).

- **Intelligent Data Extraction**  
  Automatically extracts key information such as invoice totals, line items, sender metadata, and more.

- **Context-Aware Processing**  
  Detects high-value transactions, urgent communications, and potential compliance issues.

- **Human-Readable Summaries**  
  Outputs clear, labeled summaries to facilitate rapid human review and validation.

- **Dual Interface Access**  
  Use the interactive Streamlit dashboard or programmatically interact via the FastAPI-based RESTful API.

---
---

## Project Structure

```

Lets-Build-Invoice-Processing-Using-AI-Agents/
├── agents/                 # AI agents for different input formats
│   ├── pdf\_agent.py        # Handles PDF invoices and documents
│   ├── email\_agent.py      # Parses and analyzes email content
│   ├── json\_agent.py       # Processes structured JSON input
│   └── classifier\_agent.py # Routes documents to the correct agent
├── components/             # Reusable Streamlit UI components
├── config/                 # Configuration files and environment variables
├── memory/                 # Session state and processing trace logic
├── static/                 # Static files (CSS, JS, images)
├── utils/                  # Helper functions and utilities
├── app.py                  # Streamlit app entry point
├── main\_fastapi.py         # FastAPI app entry point
└── requirements.txt        # Python dependencies

````

---

## Getting Started

### Prerequisites

- Python 3.8 or higher  
- `pip` (Python package manager)  
- (Optional) Virtual environment manager such as `venv` or `virtualenv`

### Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/rah-9/AgentAI.git
   cd AgentAI
   ```
````
````
2. **Set Up a Virtual Environment**

   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # Unix/macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**

   ```bash
   cp .env.example .env
   # Edit .env to suit your local or production environment
   ```

---

## Running the Application

### Launch Streamlit Dashboard

```bash
streamlit run app.py
```

Visit the dashboard at: [http://localhost:8501](http://localhost:8501)

### Start FastAPI Server

```bash
uvicorn main_fastapi:app --reload
```

API will be available at: [http://localhost:8000](http://localhost:8000)

---

## API Usage

### Endpoints

* `POST /process_input/`
  Accepts PDF, email, JSON, or image files and routes them to the appropriate processing agent.

* `GET /docs`
  OpenAPI interactive documentation (Swagger UI) for testing and exploring the API.

---

## Streamlit Dashboard

Access a user-friendly dashboard that allows document uploads, real-time processing, and visual summaries at:
[http://localhost:8501](http://localhost:8501)

---

## Contributing

We welcome contributions!

1. Fork this repository
2. Create a new branch:

   ```bash
   git checkout -b feature/YourFeatureName
   ```
3. Commit your changes:

   ```bash
   git commit -m "Add your feature"
   ```
4. Push to your fork:

   ```bash
   git push origin feature/YourFeatureName
   ```
5. Submit a Pull Request

---


## Acknowledgments

* [FastAPI](https://fastapi.tiangolo.com/) for the backend
* [Streamlit](https://streamlit.io/) for the frontend dashboard

---

For support, bug reports, or feature requests, please [open an issue](https://github.com/rah-9/AgentAI/issues) or contact the maintainers.
