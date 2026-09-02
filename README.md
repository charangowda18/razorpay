# 🚀 AI Revenue Recovery System

> **Razorpay Buildathon 2025** — AI Revenue Recovery Track

An AI-powered payment recovery system that detects failed payments, intelligently predicts retry success using Machine Learning, and generates recovery strategies using LLM (Google Gemini) — all through a premium real-time dashboard.

---

## 🎯 Problem Statement

Merchants lose **3-7% of revenue** due to payment failures. Most failures are recoverable — insufficient funds clear up after salary credits, bank servers come back online, network timeouts resolve. But without intelligent retry logic, this revenue is permanently lost.

**Our solution**: Detect → Predict → Recover — using AI at every step.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│              Frontend (HTML/CSS/JS)              │
│  Dashboard │ Analytics │ Recovery │ AI Insights  │
└──────────────────────┬──────────────────────────┘
                       │ REST API
┌──────────────────────▼──────────────────────────┐
│              FastAPI Backend (Python)            │
│                                                  │
│  ┌──────────┐  ┌───────────┐  ┌──────────────┐  │
│  │ Payment  │  │  Retry    │  │  AI Analysis │  │
│  │ Manager  │  │  Engine   │  │  Engine      │  │
│  └──────────┘  └───────────┘  └──────────────┘  │
│                                                  │
│  ┌──────────┐  ┌───────────┐  ┌──────────────┐  │
│  │ Recovery │  │  ML Model │  │  Analytics   │  │
│  │ Agent    │  │  (sklearn)│  │  Module      │  │
│  └──────────┘  └───────────┘  └──────────────┘  │
└──────────────────────┬──────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │  SQLite  │ │  Gemini  │ │  Random  │
    │  Database│ │  LLM API │ │  Forest  │
    └──────────┘ └──────────┘ └──────────┘
```

---

## 🤖 AI Components

### 1. Retry Scoring Model (Machine Learning)
- **Model**: Random Forest Classifier (scikit-learn)
- **Purpose**: Predicts probability of a failed payment retry succeeding
- **Features**: failure_reason, payment_method, bank_name, hour_of_day, day_of_week, amount_bucket, retry_count
- **Why Random Forest?**: Interpretable feature importances — we can explain *why* the model predicts a retry will succeed

### 2. LLM Recovery Agent (Google Gemini)
- **Model**: Gemini 2.0 Flash (free tier)
- **Purpose**: Analyzes payment failure patterns and generates:
  - Root cause analysis
  - Recovery strategy recommendations
  - Personalized customer notification messages
  - Trend alerts and anomaly detection

### 3. Hybrid Recovery Engine (Rules + ML + LLM)
- Combines ML prediction scores with business rules
- Non-retryable failures (expired card, fraud) are caught by rules
- ML handles probabilistic decisions (when to retry)
- LLM provides human-readable insights and strategies

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Revenue Dashboard** | Real-time overview of failed, recovered, and potential recovery amounts |
| **Smart Retry Engine** | AI-powered retry scheduling with optimal timing |
| **Failure Analytics** | Charts showing failure trends, bank performance, hourly patterns |
| **AI Insights** | LLM-generated analysis of payment failure patterns |
| **Recovery Opportunities** | Ranked list of transactions most likely to be recovered |
| **Merchant Performance** | Per-merchant payment health monitoring |
| **Feature Importances** | Visual explanation of what the ML model considers important |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | **FastAPI** (Python) |
| Database | **SQLite** |
| ML Model | **scikit-learn** (Random Forest) |
| LLM | **Google Gemini 2.0 Flash** |
| Frontend | **HTML/CSS/JavaScript** |
| Charts | **Chart.js** |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Google Gemini API key ([free at aistudio.google.com](https://aistudio.google.com/apikey))

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/charangowda18/razorpay.git
cd razorpay

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 4. Generate synthetic data
python backend/data/generate_data.py

# 5. Train the ML model
python backend/ml/train_model.py

# 6. Start the server
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# 7. Open the dashboard
# Visit http://localhost:8000
```

---

## 📁 Project Structure

```
ai-revenue-recovery/
├── backend/
│   ├── main.py                 # FastAPI entry point
│   ├── config.py               # Configuration
│   ├── database.py             # SQLite setup
│   ├── routers/
│   │   ├── transactions.py     # Transaction CRUD endpoints
│   │   ├── recovery.py         # Recovery action endpoints
│   │   └── analytics.py        # Dashboard data endpoints
│   ├── services/
│   │   ├── retry_engine.py     # Smart retry scoring logic
│   │   ├── ai_agent.py         # Gemini LLM integration
│   │   └── recovery_engine.py  # Recovery orchestrator
│   ├── ml/
│   │   ├── train_model.py      # Train retry prediction model
│   │   └── predict.py          # Inference helpers
│   └── data/
│       └── generate_data.py    # Synthetic data generator
├── frontend/
│   ├── index.html              # Main dashboard
│   ├── css/styles.css          # Premium dark theme
│   └── js/
│       ├── app.js              # Main app logic
│       ├── charts.js           # Chart rendering
│       └── api.js              # API client
├── requirements.txt
├── .env.example
└── README.md
```

---

## 📊 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/analytics/dashboard` | Dashboard statistics |
| GET | `/api/analytics/merchants` | Merchant list with stats |
| GET | `/api/analytics/model-info` | ML model metadata |
| GET | `/api/transactions/failed` | Failed transactions (filterable) |
| GET | `/api/transactions/{id}` | Single transaction details |
| GET | `/api/recovery/evaluate/{id}` | AI retry evaluation |
| POST | `/api/recovery/trigger/{id}` | Trigger recovery flow |
| GET | `/api/recovery/opportunities` | Top recovery opportunities |
| GET | `/api/recovery/insights` | AI-generated insights |
| GET | `/health` | System health check |
| GET | `/docs` | Interactive API documentation |

---

## 🧠 Design Decisions

### Why Random Forest over Deep Learning?
- **Interpretability**: Feature importances show exactly what drives predictions
- **Small dataset**: Works well with hundreds of samples, unlike neural nets
- **No GPU needed**: Trains in seconds on CPU
- **Easy to explain**: "It builds 100 decision trees and takes a vote"

### Why Hybrid (ML + Rules + LLM)?
- Pure ML can be unpredictable for edge cases
- Pure rules don't adapt to new patterns
- LLMs excel at natural language insights but shouldn't make binary decisions alone
- The hybrid gives us: ML adaptability + Rule safety + LLM intelligence

### Why SQLite?
- Zero configuration (ships with Python)
- Perfect for demo/prototype scale
- Easy to swap with PostgreSQL for production

### Why FastAPI?
- Auto-generates API documentation (Swagger UI at /docs)
- Built-in data validation via Pydantic
- Async support for non-blocking I/O
- Easy to explain architecture in interviews

---

## 🎥 Demo

[Link to demo video will be added here]

---

## 📝 License

MIT License
