# Automated Invoice Intake

AI-assisted intake for Japanese invoices. Gemini and Groq alternate invoice calls, while deterministic Python validation checks the extracted supplier, dates, tax codes, and totals before the accounting API receives anything.

## Setup

Use Python 3.9+ and install dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Set `.env` file:
```text
# Gemini API Setup
GEMINI_API_KEY=your_gemini_api_key_here

# Groq API Setup
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
GROQ_API_URL=https://api.groq.com/openai/v1/chat/completions

# Accounting System API Configuration
ACCOUNTING_API_URL=http://localhost:8080
ACCOUNTING_API_KEY=your_accounting_api_key_here
```
When both are configured, invoices alternate Gemini then Groq. If the selected provider fails, the other configured provider is tried immediately. Groq handles image invoices; PDF invoices fall back to Gemini because the Groq chat endpoint accepts image inputs, not PDF files. The accounting API defaults to `http://localhost:8080` and `demo-key-1234`.

Start the mock accounting API in one terminal:

```powershell
.\.venv\Scripts\python.exe sample\accounting_api.py
```

Start invoice intake in another terminal:

```powershell
.\.venv\Scripts\python.exe main.py
```

The runner processes every PDF and image in `invoices/`. Valid results are submitted. Invalid or rejected results are written to `review_queue.json`. To extract and validate without changing the accounting system, use:

```powershell
.\.venv\Scripts\python.exe main.py --dry-run
```

The AI's role is limited to visual extraction and supplier matching. Code owns provider rotation, business-rule validation, API integration, fallback/review routing, and the final audit output.
