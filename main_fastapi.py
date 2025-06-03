# FastAPI entrypoint for multi-agent system
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi import status
from agents.classifier_agent import ClassifierAgent
from agents.email_agent import EmailAgent
from agents.json_agent import JSONAgent
from agents.pdf_agent import PDFAgent
from action_router import ActionRouter
from memory_store import MemoryStore
import shutil
import os
import time
import uuid
import json
import traceback
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
load_dotenv()

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Invoice Processing API", description="API for processing invoices using AI agents")

# Add CORS middleware to allow all origins (for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def root():
    html_content = """
    <!DOCTYPE html>
    <html>
        <head>
            <title>Invoice Processing Dashboard</title>
            <meta name='viewport' content='width=device-width, initial-scale=1.0'>
            <style>
                body {
                    background: #f4f7fa;
                    font-family: 'Segoe UI', Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                }
                .dashboard-container {
                    max-width: 1100px;
                    margin: 0 auto;
                    padding: 32px 8px 40px 8px;
                }
                h1 {
                    color: #2d3748;
                    text-align: center;
                    font-size: 2.5rem;
                    margin-bottom: 10px;
                    letter-spacing: -1px;
                }
                .subtitle {
                    text-align: center;
                    color: #4a5568;
                    margin-bottom: 34px;
                    font-size: 1.1rem;
                }
                .card-top {
                    margin-bottom: 32px;
                    box-shadow: 0 4px 18px rgba(49,130,206,0.09);
                    border: 1.5px solid #e2e8f0;
                }
                .card-grid.card-grid-bottom {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
                    gap: 24px;
                }
                .card {
                    background: #fff;
                    border-radius: 12px;
                    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
                    padding: 28px 20px 22px 20px;
                    display: flex;
                    flex-direction: column;
                    align-items: stretch;
                    border: 1.5px solid #e2e8f0;
                    transition: box-shadow 0.2s;
                }
                .card:hover {
                    box-shadow: 0 8px 24px rgba(49,130,206,0.13);
                }

                .card h2 {
                    font-size: 1.3rem;
                    color: #2b6cb0;
                    margin-bottom: 10px;
                }
                .card form, .card .form {
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                }
                label {
                    font-size: 0.98rem;
                    color: #4a5568;
                }
                input[type="text"], input[type="number"], textarea, select {
                    border: 1px solid #cbd5e0;
                    border-radius: 6px;
                    padding: 8px 10px;
                    font-size: 1rem;
                    background: #f7fafc;
                    color: #2d3748;
                }
                input[type="file"] {
                    font-size: 1rem;
                }
                button {
                    background: linear-gradient(90deg, #3182ce 0%, #63b3ed 100%);
                    color: #fff;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 0;
                    font-size: 1rem;
                    font-weight: bold;
                    cursor: pointer;
                    margin-top: 10px;
                    transition: background 0.2s;
                }
                button:hover {
                    background: linear-gradient(90deg, #2563eb 0%, #4299e1 100%);
                }
                .result-area {
                    background: #f7fafc;
                    border-radius: 8px;
                    padding: 12px;
                    margin-top: 10px;
                    font-size: 0.98rem;
                    color: #2d3748;
                    min-height: 24px;
                    word-break: break-all;
                }
                .loading {
                    color: #4299e1;
                    font-weight: bold;
                }
                @media (max-width: 700px) {
                    .dashboard-container {
                        padding: 10px 2px;
                    }
                }
            </style>
        </head>
        <body>
            <div class="dashboard-container">
                <h1>Invoice Processing Dashboard</h1>
                <div class="subtitle">Process invoices and trigger business actions using AI agents</div>
                <!-- Process Invoice/Email at the top -->
                <div class="card card-top">
                    <h2>Process Invoice / Email</h2>
                    <form id="processForm" enctype="multipart/form-data" onsubmit="processInput(event)">
                        <label for="fileInput">Upload PDF, Image, Email (.eml/.txt/.pdf):</label>
                        <input type="file" id="fileInput" name="file" accept=".pdf,.jpg,.jpeg,.png,.eml,.txt,.json" required>
                        <button type="submit">Process</button>
                    </form>
                    <div id="processResult" class="result-area"></div>
                </div>
                <!-- Action cards below -->
                <div class="card-grid card-grid-bottom">
                    <div class="card">
                        <h2>Escalate to CRM</h2>
                        <form id="crmForm" onsubmit="submitCrm(event)">
                            <label>Invoice ID</label>
                            <input type="text" name="invoice_id" required>
                            <label>Customer Name</label>
                            <input type="text" name="customer_name" required>
                            <label>Amount</label>
                            <input type="number" name="amount" step="0.01">
                            <label>Reason</label>
                            <input type="text" name="reason" required>
                            <label>Priority</label>
                            <select name="priority">
                                <option value="medium">Medium</option>
                                <option value="high">High</option>
                                <option value="low">Low</option>
                            </select>
                            <button type="submit">Escalate</button>
                        </form>
                        <div id="crmResult" class="result-area"></div>
                    </div>
                    <div class="card">
                        <h2>Trigger Risk Alert</h2>
                        <form id="riskForm" onsubmit="submitRisk(event)">
                            <label>Alert Type</label>
                            <input type="text" name="alert_type" required>
                            <label>Severity</label>
                            <select name="severity">
                                <option value="medium">Medium</option>
                                <option value="high">High</option>
                                <option value="low">Low</option>
                                <option value="critical">Critical</option>
                            </select>
                            <label>Description</label>
                            <input type="text" name="description" required>
                            <label>Source</label>
                            <input type="text" name="source">
                            <button type="submit">Trigger Alert</button>
                        </form>
                        <div id="riskResult" class="result-area"></div>
                    </div>
                    <div class="card">
                        <h2>Send Alert</h2>
                        <form id="alertForm" onsubmit="submitAlert(event)">
                            <label>Type</label>
                            <input type="text" name="type" required>
                            <label>Message</label>
                            <input type="text" name="message" required>
                            <label>Recipients (comma separated)</label>
                            <input type="text" name="recipients" required>
                            <label>Priority</label>
                            <select name="priority">
                                <option value="medium">Medium</option>
                                <option value="high">High</option>
                                <option value="low">Low</option>
                            </select>
                            <button type="submit">Send Alert</button>
                        </form>
                        <div id="alertResult" class="result-area"></div>
                    </div>
                    <div class="card">
                        <h2>Log Data</h2>
                        <form id="logForm" onsubmit="submitLog(event)">
                            <label>Level</label>
                            <select name="level">
                                <option value="info">Info</option>
                                <option value="warning">Warning</option>
                                <option value="error">Error</option>
                                <option value="critical">Critical</option>
                            </select>
                            <label>Message</label>
                            <input type="text" name="message" required>
                            <label>Source</label>
                            <input type="text" name="source">
                            <button type="submit">Log</button>
                        </form>
                        <div id="logResult" class="result-area"></div>
                    </div>
                    <div class="card">
                        <h2>Store Data</h2>
                        <form id="storeForm" onsubmit="submitStore(event)">
                            <label>Collection</label>
                            <input type="text" name="collection" required>
                            <label>Data (JSON)</label>
                            <textarea name="data" rows="3" required></textarea>
                            <button type="submit">Store</button>
                        </form>
                        <div id="storeResult" class="result-area"></div>
                    </div>
                </div>
            </div>
            <script>
                // Helper for showing loading
                function showLoading(el) {
                    el.innerHTML = '<span class="loading">Loading...</span>';
                }
                // Helper for showing results and auto-filling forms
                function showResult(el, data) {
                    el.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
                    // --- Auto-fill logic ---
                    if (data && data.result && data.result.fields) {
                        const fields = data.result.fields;
                        // Auto-fill CRM form
                        if (fields.invoice_id || fields.invoice_number) {
                            document.querySelector('#crmForm input[name="invoice_id"]').value = fields.invoice_id || fields.invoice_number || '';
                        }
                        if (fields.customer_name) {
                            document.querySelector('#crmForm input[name="customer_name"]').value = fields.customer_name;
                        }
                        if (fields.amount || fields.total || fields.invoice_total) {
                            document.querySelector('#crmForm input[name="amount"]').value = fields.amount || fields.total || fields.invoice_total || '';
                        }
                        if (data.result.flags && data.result.flags.length > 0) {
                            document.querySelector('#crmForm input[name="reason"]').value = data.result.flags.join(', ');
                        } else if (fields.description) {
                            document.querySelector('#crmForm input[name="reason"]').value = fields.description;
                        }
                        // Auto-fill Risk Alert form
                        if (data.result.flags && data.result.flags.length > 0) {
                            document.querySelector('#riskForm input[name="alert_type"]').value = data.result.flags[0];
                            document.querySelector('#riskForm input[name="description"]').value = data.result.flags.join(', ');
                        }
                        if (fields.customer_name) {
                            document.querySelector('#riskForm input[name="source"]').value = fields.customer_name;
                        }
                        // Auto-fill Alert form
                        if (fields.customer_name) {
                            document.querySelector('#alertForm input[name="message"]').value = `Invoice for ${fields.customer_name}`;
                        }
                        if (fields.invoice_id || fields.invoice_number) {
                            document.querySelector('#alertForm input[name="type"]').value = 'Invoice';
                        }
                    }
                }
                // Helper for showing errors
                function showError(el, error) {
                    el.innerHTML = `<span style='color:#e53e3e;'>${error}</span>`;
                }
                // Process Input
                function processInput(e) {
                    e.preventDefault();
                    const form = document.getElementById('processForm');
                    const fileInput = document.getElementById('fileInput');
                    const resultEl = document.getElementById('processResult');
                    if (!fileInput.files.length) {
                        showError(resultEl, 'Please select a file.');
                        return;
                    }
                    showLoading(resultEl);
                    const formData = new FormData(form);
                    fetch('/process_input/', {
                        method: 'POST',
                        body: formData
                    })
                    .then(r=>r.json())
                    .then(data=>showResult(resultEl, data))
                    .catch(err=>showError(resultEl, err));
                }
                // CRM Escalate
                function submitCrm(e) {
                    e.preventDefault();
                    const form = document.getElementById('crmForm');
                    const resultEl = document.getElementById('crmResult');
                    showLoading(resultEl);
                    const payload = Object.fromEntries(new FormData(form));
                    payload.amount = payload.amount ? parseFloat(payload.amount) : undefined;
                    fetch('/crm_escalate/', {
                        method: 'POST',
                        headers: {'Content-Type':'application/json'},
                        body: JSON.stringify(payload)
                    })
                    .then(r=>r.json())
                    .then(data=>showResult(resultEl, data))
                    .catch(err=>showError(resultEl, err));
                }
                // Risk Alert
                function submitRisk(e) {
                    e.preventDefault();
                    const form = document.getElementById('riskForm');
                    const resultEl = document.getElementById('riskResult');
                    showLoading(resultEl);
                    const payload = Object.fromEntries(new FormData(form));
                    fetch('/risk_alert/', {
                        method: 'POST',
                        headers: {'Content-Type':'application/json'},
                        body: JSON.stringify(payload)
                    })
                    .then(r=>r.json())
                    .then(data=>showResult(resultEl, data))
                    .catch(err=>showError(resultEl, err));
                }
                // Alerts
                function submitAlert(e) {
                    e.preventDefault();
                    const form = document.getElementById('alertForm');
                    const resultEl = document.getElementById('alertResult');
                    showLoading(resultEl);
                    const payload = Object.fromEntries(new FormData(form));
                    payload.recipients = payload.recipients.split(',').map(x=>x.trim()).filter(Boolean);
                    fetch('/alerts/', {
                        method: 'POST',
                        headers: {'Content-Type':'application/json'},
                        body: JSON.stringify(payload)
                    })
                    .then(r=>r.json())
                    .then(data=>showResult(resultEl, data))
                    .catch(err=>showError(resultEl, err));
                }
                // Log
                function submitLog(e) {
                    e.preventDefault();
                    const form = document.getElementById('logForm');
                    const resultEl = document.getElementById('logResult');
                    showLoading(resultEl);
                    const payload = Object.fromEntries(new FormData(form));
                    fetch('/log/', {
                        method: 'POST',
                        headers: {'Content-Type':'application/json'},
                        body: JSON.stringify(payload)
                    })
                    .then(r=>r.json())
                    .then(data=>showResult(resultEl, data))
                    .catch(err=>showError(resultEl, err));
                }
                // Store
                function submitStore(e) {
                    e.preventDefault();
                    const form = document.getElementById('storeForm');
                    const resultEl = document.getElementById('storeResult');
                    showLoading(resultEl);
                    const payload = Object.fromEntries(new FormData(form));
                    try {
                        payload.data = JSON.parse(payload.data);
                    } catch {
                        showError(resultEl, 'Data must be valid JSON.');
                        return;
                    }
                    fetch('/store/', {
                        method: 'POST',
                        headers: {'Content-Type':'application/json'},
                        body: JSON.stringify(payload)
                    })
                    .then(r=>r.json())
                    .then(data=>showResult(resultEl, data))
                    .catch(err=>showError(resultEl, err));
                }
            </script>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)


# Initialize shared components
memory_store = MemoryStore(db_path="./memory.db")
classifier = ClassifierAgent(memory=memory_store)
email_agent = EmailAgent(memory=memory_store)
json_agent = JSONAgent(memory=memory_store)
pdf_agent = PDFAgent(memory=memory_store)
action_router = ActionRouter(memory=memory_store, simulate=True)

# Simulated REST endpoints for ActionRouter
from fastapi import status
from fastapi.responses import JSONResponse

from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import HTTPException
import json
import os

# In-memory storage for demo purposes
class Storage:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Storage, cls).__new__(cls)
            cls._instance.risk_alerts = []
            cls._instance.crm_escalations = []
            cls._instance.alerts = []
            cls._instance.logs = []
            cls._instance.storage = {}
            
            # Create logs directory if it doesn't exist
            os.makedirs('logs', exist_ok=True)
        return cls._instance

storage = Storage()

@app.post("/crm_escalate/")
async def crm_escalate(payload: Dict[str, Any]):
    """
    Escalate an issue to CRM system.
    Expected payload format:
    {
        "invoice_id": str,
        "customer_name": str,
        "amount": float,
        "reason": str,
        "priority": "low"|"medium"|"high",
        "additional_data": dict
    }
    """
    try:
        # Validate required fields
        required_fields = ["invoice_id", "customer_name", "reason"]
        for field in required_fields:
            if field not in payload:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Create escalation record
        escalation = {
            "id": f"crm_{len(storage.crm_escalations) + 1}",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "pending",
            **payload
        }
        
        # Store in memory
        storage.crm_escalations.append(escalation)
        
        # Log the escalation
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": "crm_escalation_created",
            "escalation_id": escalation["id"],
            "details": f"Escalated to CRM: {payload['reason']}"
        }
        storage.logs.append(log_entry)
        
        # In a real app, you would integrate with your CRM system here
        # e.g., crm_client.create_ticket(escalation)
        
        return {
            "status": "success", 
            "message": "Issue escalated to CRM",
            "escalation_id": escalation["id"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/risk_alert/")
async def risk_alert(payload: Dict[str, Any]):
    """
    Create a risk alert.
    Expected payload format:
    {
        "alert_type": str,
        "severity": "low"|"medium"|"high"|"critical",
        "description": str,
        "source": str,
        "related_entities": list[dict],
        "metadata": dict
    }
    """
    try:
        required_fields = ["alert_type", "severity", "description"]
        for field in required_fields:
            if field not in payload:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Create alert record
        alert = {
            "id": f"risk_{len(storage.risk_alerts) + 1}",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "open",
            **payload
        }
        
        storage.risk_alerts.append(alert)
        
        # Log the alert
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": "risk_alert_created",
            "alert_id": alert["id"],
            "severity": alert["severity"],
            "description": alert["description"]
        }
        storage.logs.append(log_entry)
        
        # In a real app, you might want to trigger notifications here
        # e.g., notify_security_team(alert)
        
        return {
            "status": "success", 
            "message": "Risk alert created",
            "alert_id": alert["id"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/alerts/")
async def alerts(payload: Dict[str, Any]):
    """
    Send an alert/notification.
    Expected payload format:
    {
        "type": str,
        "message": str,
        "recipients": list[str],
        "priority": "low"|"medium"|"high",
        "metadata": dict
    }
    """
    try:
        required_fields = ["type", "message", "recipients"]
        for field in required_fields:
            if field not in payload:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Create alert record
        alert = {
            "id": f"alert_{len(storage.alerts) + 1}",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "sent",
            **payload
        }
        
        storage.alerts.append(alert)
        
        # Log the alert
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": "alert_sent",
            "alert_id": alert["id"],
            "type": alert["type"],
            "recipients": alert["recipients"]
        }
        storage.logs.append(log_entry)
        
        # In a real app, you would send the actual notification here
        # e.g., send_email(alert['recipients'], alert['message'])
        
        return {
            "status": "success", 
            "message": "Alert sent successfully",
            "alert_id": alert["id"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/log/")
async def log(payload: Dict[str, Any]):
    """
    Log an event or message.
    Expected payload format:
    {
        "level": "info"|"warning"|"error"|"critical",
        "message": str,
        "source": str,
        "context": dict
    }
    """
    try:
        required_fields = ["level", "message"]
        for field in required_fields:
            if field not in payload:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Create log entry
        log_entry = {
            "id": f"log_{len(storage.logs) + 1}",
            "timestamp": datetime.utcnow().isoformat(),
            **payload
        }
        
        # Store in memory
        storage.logs.append(log_entry)
        
        # Also write to file for persistence
        with open(f"logs/app_{datetime.utcnow().strftime('%Y%m%d')}.log", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        
        return {
            "status": "success", 
            "message": "Log entry created",
            "log_id": log_entry["id"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/store/")
async def store(payload: Dict[str, Any]):
    """
    Store data in the system.
    Expected payload format:
    {
        "collection": str,
        "data": dict,
        "metadata": dict
    }
    """
    try:
        required_fields = ["collection", "data"]
        for field in required_fields:
            if field not in payload:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        collection = payload["collection"]
        data = payload["data"]
        
        # Initialize collection if it doesn't exist
        if collection not in storage.storage:
            storage.storage[collection] = []
        
        # Add metadata and timestamps
        record = {
            "id": f"{collection}_{len(storage.storage[collection]) + 1}",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "data": data,
            "metadata": payload.get("metadata", {})
        }
        
        # Store the record
        storage.storage[collection].append(record)
        
        # Log the storage action
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": "data_stored",
            "collection": collection,
            "record_id": record["id"]
        }
        storage.logs.append(log_entry)
        
        return {
            "status": "success", 
            "message": "Data stored successfully",
            "collection": collection,
            "id": record["id"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
async def store(payload: dict):
    return JSONResponse(content={"status": "Stored OK", "payload": payload}, status_code=status.HTTP_200_OK)

@app.post("/process_input/")
async def process_input(request: Request, file: UploadFile = File(None)):
    # Accepts file upload or JSON body
    source = None
    input_data = None
    debug_info = {"time": time.strftime('%Y-%m-%d %H:%M:%S')}
    
    try:
        if file:
            filename = file.filename
            debug_info["filename"] = filename
            debug_info["content_type"] = file.content_type
            
            ext = filename.split('.')[-1].lower()
            debug_info["extension"] = ext
            
            temp_path = f"temp_{filename}"
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
                
            debug_info["temp_path"] = temp_path
            debug_info["file_size"] = os.path.getsize(temp_path)
            
            if ext == 'pdf':
                source = 'PDF'
                input_data = temp_path
            else:
                # Determine if image or email based on mime type or extension
                if file.content_type and file.content_type.startswith('image/'):
                    source = 'Image'
                else:
                    source = 'Email'  # Default for non-PDF, non-image
                input_data = temp_path
        else:
            try:
                body = await request.json()
                source = 'JSON'
                input_data = body
                debug_info["body_keys"] = list(body.keys()) if isinstance(body, dict) else "not_dict"
            except Exception as e:
                debug_info["body_parse_error"] = str(e)
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid JSON body", "detail": str(e), "debug": debug_info}
                )

        debug_info["source"] = source
        
        # 1. Classify
        try:
            classification_result = classifier.classify(input_data, source)
            debug_info["classification_success"] = True
        except Exception as e:
            debug_info["classification_error"] = str(e)
            classification_result = {"format": source, "intent": "Unknown", "error": str(e)}
        
        agent_trace = {"classification": classification_result}
        debug_info["classification"] = classification_result
        
        # 2. Route to agent based on format
        format_type = classification_result.get("format", "Unknown")
        classification_result["routed_agent"] = format_type  # Add routed agent info
        
        try:
            if format_type == "Email":
                result = email_agent.process(input_data)
            elif format_type == "PDF":
                result = pdf_agent.process(input_data)
            elif format_type == "JSON":
                result = json_agent.process(input_data)
            elif format_type == "Image":
                # For images, we've already extracted text in the classifier
                result = {
                    "status": "processed",
                    "format": "Image",
                    "fields": {
                        "text_excerpt": classification_result.get("metadata", {}).get("extracted_text", ""),
                        "intent": classification_result.get("intent", "Unknown")
                    }
                }
            else:
                result = {
                    "error": f"Unsupported format: {format_type}",
                    "available_formats": ["Email", "PDF", "JSON", "Image"],
                    "fields": {"text_excerpt": "Unsupported format"}
                }
            
            debug_info["agent_process_success"] = True
        except Exception as e:
            debug_info["agent_process_error"] = str(e)
            result = {
                "error": f"Agent processing error: {str(e)}",
                "fields": {"text_excerpt": f"Error processing {format_type}: {str(e)}"}
            }
            
        # Ensure 'fields' exists in result for UI consistency
        if "fields" not in result:
            result["fields"] = {"text_excerpt": "No structured fields extracted"}
            
        agent_trace["agent_result"] = result
        debug_info["result"] = result

        # 3. Action Router
        try:
            actions = action_router.route(result)
            debug_info["action_router_success"] = True
        except Exception as e:
            debug_info["action_router_error"] = str(e)
            actions = [f"Error determining actions: {str(e)}"]
            
        agent_trace["actions"] = actions
        debug_info["actions"] = actions

        # 4. Log to memory store
        try:
            # Generate a process ID for this request
            process_id = str(uuid.uuid4())
            
            # Log classification
            classification_id = memory_store.log_classification(
                format_type=format_type,
                intent=classification_result.get("intent", "Unknown"),
                confidence=classification_result.get("confidence", 0.0),
                metadata=classification_result.get("metadata", {}),
                summary=classification_result.get("summary", None)
            )
            
            # Log extraction result
            extraction_id = memory_store.log_extraction(
                format_type=format_type,
                agent=format_type,
                fields=result.get("fields", {}),
                valid=result.get("valid", True),
                anomalies=result.get("anomalies", []),
                summary=result.get("fields", {}).get("text_excerpt", ""),
                classification_id=classification_id
            )
            
            # Log trace
            memory_store.log_trace(
                process_id=process_id,
                stage="classify",
                details={"classification_id": classification_id}
            )
            
            memory_store.log_trace(
                process_id=process_id,
                stage="extract",
                details={"extraction_id": extraction_id}
            )
            
            # Store process ID for response
            debug_info["process_id"] = process_id
            debug_info["classification_id"] = classification_id
            debug_info["extraction_id"] = extraction_id
            debug_info["memory_log_success"] = True
        except Exception as e:
            debug_info["memory_log_error"] = str(e)

        # Cleanup temp file if needed
        if source in ["PDF", "Email", "Image"] and input_data and os.path.exists(input_data):
            os.remove(input_data)
            debug_info["temp_file_cleanup"] = "success"

        # Return comprehensive response with debug info
        return {
            "classification": classification_result, 
            "result": result, 
            "actions": actions,
            "agent_trace": agent_trace,
            "debug": debug_info
        }
        
    except Exception as e:
        debug_info["unhandled_error"] = str(e)
        debug_info["traceback"] = traceback.format_exc()
        
        if source in ["PDF", "Email", "Image"] and input_data and os.path.exists(input_data):
            try:
                os.remove(input_data)
                debug_info["emergency_cleanup"] = "success"
            except:
                debug_info["emergency_cleanup"] = "failed"
                
        return JSONResponse(
            status_code=500,
            content={
                "error": "Processing failed", 
                "detail": str(e),
                "debug": debug_info,
                "result": {"fields": {"text_excerpt": f"Error: {str(e)}"}},
                "classification": {"format": source or "Unknown", "intent": "Error"},
                "actions": ["Contact support"]
            }
        )

if __name__ == "__main__":
    import uvicorn
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    port = int(os.getenv("BACKEND_PORT", "8000"))
    uvicorn.run("main_fastapi:app", host="0.0.0.0", port=port, reload=True)
