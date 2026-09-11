<div align="center">

# 🚗 FleetTrack: Next-Gen AI Vehicle Telematics & Analytics Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.2-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React_18-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

**An enterprise-grade fleet telematics, predictive vehicle health, driver behavior classification, and eco-routing intelligence platform.**

[Features](#-key-features) • [Architecture](#-system-architecture) • [Getting Started](#-getting-started) • [API Documentation](#-api-documentation) • [Testing & CI/CD](#-testing--cicd-pipeline) • [License](#-license)

</div>

---

## 📌 Executive Overview

**FleetTrack** is a decoupled full-stack telematics intelligence platform engineered to analyze vehicular CAN bus and OBD-II sensor feeds in real time. It combines asynchronous Python microservices with an interactive React 18 Single-Page Application (SPA) to deliver driving risk profiling, telemetry visualization, predictive maintenance alerts, NLP assistant chat, and eco-optimized GPS routing.

### 🌟 What Makes FleetTrack Unique
- **High-Performance Asynchronous Backend**: Built with **FastAPI**, **SQLAlchemy 2.0 (AsyncIO)**, and **Pydantic v2** validation.
- **Enterprise Security**: Strict JWT Bearer token authentication, **bcrypt** password encryption, and zero IDOR vulnerability leakage.
- **Rich Aesthetic Dark UI**: State-of-the-art glassmorphism design system powered by Tailwind CSS and Google Fonts (`Outfit` / `Inter`).
- **Telemetry Visualizations**: 16 multi-axis Recharts graphs, dual-axis telemetry monitors, and radar driver performance comparison charts.
- **Integrated AI & ML Engine**: Machine-learned driving style classification (Safe, Moderate, Aggressive) backed by cross-validated multi-channel sensor models.

---

## 🚀 Key Features

### 📊 1. Real-Time Telematics Dashboard (`/dashboard`)
- **Fleet Summary Cards**: Live tracking of Total Distance, Average Speed, Cumulative Fuel Consumed, and Total Logged Trips.
- **16-Column Sensor Telemetry Table**: Complete audit of Speed, RPM, Fuel, Brake Events, Steering Angle, Angular Velocity, Acceleration, Gear, Tire Pressure, Engine Load, Throttle Position, Brake Pressure, and Duration.
- **Multi-Select Trip Comparison Tool**: Compare telemetry metrics across multiple trips simultaneously.
- **16 Interactive Recharts Visualizations**: Toggleable Line/Bar telemetry graphs for performance auditing.
- **Filter & Export Modals**: Dynamic time-range filtering and CSV/JSON report exports.

### 🧠 2. AI-Powered Fleet Intelligence (`/ai-features`)
8 specialized interactive AI modules with dynamic modals:
- **Trip Sentiment Analysis**: Evaluates driver smoothness, aggression, and calm scores.
- **Smart Trip Insights**: Real-time breakdown of efficiency ratings and engine stress levels.
- **Personalized AI Tips**: Contextual driving tips highlighting estimated annual cost savings in ₹/year.
- **Anomaly Detection**: Flags sudden RPM spikes, hard braking incidents, and abnormal telemetry deviations.
- **Predictive Maintenance Diagnostics**: Component wear projections for engine oil, brake pads, and tire rotation.
- **Context-Aware Smart Recommendations**: Weather-aware and efficiency-ranked vehicle guidance.
- **Real-Time AI Coach Simulator**: Interactive speed and RPM slider testbed giving instant driving feedback.
- **Fuel Consumption Predictor**: Distance-based fuel burn and cost estimation calculator.

### 📈 3. Deep Trip Details & Diagnostics (`/trip/:tripId`)
- **Top 3 Diagnostic Score Cards**: Driving Score (with status badge), AI Classifier Output (Model name & Confidence %), and Fuel Efficiency (km/L).
- **15 Sensor Telemetry Tiles**: Dedicated cards with custom icons and color-coded statuses.
- **Health Recommendation Banner**: Actionable advice derived from sensor stress analysis.
- **Maintenance Alerts Section**: Component-specific warning system with status indicators.
- **6 Specialized Telemetry Charts**:
  - *Speed & RPM Analysis* (Dual Y-Axis Line/Bar toggle)
  - *Braking Dynamics* (Brake Pressure Area + Event count Line)
  - *Engine Performance* (Engine Load Area + Acceleration Line)
  - *Steering Dynamics* (Steering Angle Area + Angular Velocity Line)
  - *Fuel Efficiency & Cost Curve* (Cumulative Fuel Area with trip cost calculation)
  - *Driving Performance Spider Chart* (Driver Performance vs. Ideal Performance Radar)

### 🗺️ 4. Smart Route Planner & Optimizer (`/route-planner`)
- **Interactive GIS Map**: Rendered with **React-Leaflet** and OpenStreetMap tiles.
- **Location Controls**: Free-text origin/destination inputs, **Swap Locations** toggle, and **GPS Locate** button.
- **Routing Profiles**: Balanced, Fuel-Efficient, and Fastest highway optimization algorithms.
- **Trip Savings Analysis**: Calculates per-trip savings, monthly estimated savings, and time delta.
- **Saved Routes Drawer**: Bookmark and recall preferred routes.

### 🤖 5. Conversational Telematics Assistant (`/ai-assistant`)
- Integrated chatbot providing natural language queries over vehicle telemetry, fuel savings, and service timelines.
- Bidirectional WebSocket support (`/api/v1/chatbot/ws`) and REST query endpoint (`/api/v1/chatbot/query`).

### 🔬 6. ML Model Architecture Info (`/model-info`)
- Classifier performance metrics: Accuracy, F1-macro score, and 5-fold stratified cross-validation.
- Full breakdown of 14 input telematics channels and target classification classes (Good, Average, Risky).

---

## 🏗️ System Architecture

```mermaid
graph TD
    subgraph Client Layer [Frontend - React 18 SPA]
        UI[React 18 + TypeScript + Vite]
        Store[Auth Context & Axios Interceptors]
        Visuals[Recharts + React-Leaflet GIS]
    end

    subgraph Gateway & API Layer [Backend - FastAPI ASGI]
        FastAPI[FastAPI Gateway :8000]
        CORS[CORS Middleware]
        Security[OAuth2 JWT Bearer Auth & Bcrypt]
    end

    subgraph Service Modules [FastAPI Routers]
        AuthRouter[/api/v1/auth]
        TripRouter[/api/v1/trips - IDOR Protected]
        InsightsRouter[/api/v1/insights]
        RouteRouter[/api/v1/route]
        ChatRouter[/api/v1/chatbot & WebSocket]
    end

    subgraph AI / ML & Telemetry Engines
        RFModel[Random Forest Classifier]
        ScoringEngine[Heuristic Telematics Scorer]
        RoutingEngine[OSRM Route Optimizer]
        NLPService[Vehicle Chatbot Engine]
    end

    subgraph Database Layer
        AsyncDB[(SQLAlchemy AsyncIO + SQLite / PostgreSQL)]
    end

    UI -->|REST APIs & WebSockets| FastAPI
    FastAPI --> CORS --> Security
    Security --> AuthRouter & TripRouter & InsightsRouter & RouteRouter & ChatRouter
    TripRouter & InsightsRouter --> RFModel & ScoringEngine
    RouteRouter --> RoutingEngine
    ChatRouter --> NLPService
    AuthRouter & TripRouter & RouteRouter --> AsyncDB
```

---

## 💻 Tech Stack

| Domain | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend Framework** | **FastAPI** (`0.109.2`) | Asynchronous, high-throughput ASGI REST microservice |
| **ASGI Server** | **Uvicorn** (`0.27.1`) | Production ASGI web server runner |
| **Database & ORM** | **SQLAlchemy 2.0** + `aiosqlite` / `asyncpg` | Asynchronous ORM with connection pooling |
| **Authentication** | **JWT** (`python-jose`) + **Bcrypt** (`passlib`) | Stateless Bearer token security and password hashing |
| **Data Validation** | **Pydantic v2** (`2.6.1`) | Request/Response strict type serialization |
| **Machine Learning** | **Scikit-Learn**, **Joblib**, **Pandas**, **NumPy** | Multi-channel driver risk classification & benchmarking |
| **Frontend Core** | **React 18**, **TypeScript**, **Vite** | Modern, type-safe Single Page Application |
| **Styling & Icons** | **Tailwind CSS**, **Lucide React** | Glassmorphic dark theme and iconography |
| **Data Visualizations**| **Recharts** (`2.12.0`) | Multi-axis area, line, bar, and radar charts |
| **Mapping & GIS** | **React-Leaflet**, **Leaflet** | Interactive route polylines and marker overlays |
| **Testing & CI/CD** | **Pytest**, **Ruff**, **Bandit**, **GitHub Actions** | Automated integration tests, linting, security AST scan |

---

## 🚦 Getting Started

### Prerequisites
- **Python 3.11+** installed
- **Node.js 18+** & **npm** installed
- Git installed

### 1. Clone Repository
```bash
git clone https://github.com/YATHARTHH/vehcile_driving.git
cd vehcile_driving
```

### 2. Backend Setup (FastAPI)
```bash
# Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
# source .venv/bin/activate

# Install backend dependencies
pip install -r requirements.txt

# Launch FastAPI backend server
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
> 💡 **Swagger API Documentation:** Open `http://localhost:8000/docs` in your browser.

### 3. Frontend Setup (React SPA)
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```
> 💡 **Frontend Dashboard:** Open `http://localhost:5173` in your browser.

---

## 🔑 Environment Configuration

Create a `.env` file in the root directory:

```env
# Application Settings
PROJECT_NAME="EcoDriving Analytics Platform"
VERSION="2.0.0"
API_V1_STR="/api/v1"

# Security (Replace with a strong random secret in production)
SECRET_KEY="your_super_secret_jwt_key_here"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Database Connection (Async SQLite or PostgreSQL)
DATABASE_URL="sqlite+aiosqlite:///./instance/trips.db"
# For PostgreSQL:
# DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/ecodriving"
```

---

## 📖 API Documentation

FastAPI automatically generates interactive, OpenAPI-compliant documentation:

| Interface | URL | Description |
| :--- | :--- | :--- |
| **Swagger UI** | `http://localhost:8000/docs` | Interactive API explorer to test endpoints |
| **ReDoc** | `http://localhost:8000/redoc` | Clean, formal API reference documentation |
| **OpenAPI Schema** | `http://localhost:8000/api/v1/openapi.json` | Raw OpenAPI JSON specification |

### Core Endpoints Overview:
- `POST /api/v1/auth/register` - Create user account and auto-seed initial trips
- `POST /api/v1/auth/login` - Authenticate and retrieve JWT Bearer token
- `GET  /api/v1/auth/me` - Fetch authenticated user profile
- `GET  /api/v1/trips` - Retrieve user's logged trips list
- `GET  /api/v1/trips/{trip_id}` - Retrieve detailed telemetry & ML score for a trip (IDOR protected)
- `POST /api/v1/insights/sentiment` - Analyze driving sentiment
- `POST /api/v1/insights/anomaly-detection` - Scan trip for abnormal sensor spikes
- `GET  /api/v1/insights/predictive-maintenance` - Component wear diagnostic timelines
- `GET  /api/v1/insights/model-info` - Classifier architecture and accuracy metadata
- `POST /api/v1/route/optimize` - Calculate multi-scenario eco-routes
- `POST /api/v1/route/save` - Save preferred route
- `POST /api/v1/chatbot/query` - Query AI Assistant with telemetry context

---

## 🧪 Testing & CI/CD Pipeline

The project includes an automated **production CI pipeline** configured in [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

### Run Tests Locally:
```bash
# 1. Run Python Integration & Unit Tests
python -m pytest backend/tests -v --cov=backend --cov-report=term-missing

# 2. Run Ruff Code Quality & Syntax Linter
ruff check backend/ --select E,F,W --ignore E501

# 3. Run Bandit Security AST Scanner
bandit -r backend/ -ll -ii

# 4. Run Frontend TypeScript Typecheck
cd frontend
npx tsc --noEmit

# 5. Build Frontend Production Bundle
npm run build
```

---

## 📂 Repository Structure

```
vehcile_driving/
├── .github/
│   └── workflows/
│       └── ci.yml               # Production GitHub Actions CI pipeline
├── backend/
│   ├── models/                  # SQLAlchemy ORM models (User, Trip, Alert, SavedRoute)
│   ├── routers/                 # Modular FastAPI routers (auth, trips, insights, route, chatbot)
│   ├── schemas/                 # Pydantic v2 validation schemas
│   ├── tests/                   # Pytest integration and unit test suite
│   ├── utils/                   # JWT authentication, password hashing, dependencies
│   ├── config.py                # Environment configuration settings
│   ├── database.py              # Async SQLAlchemy engine and session provider
│   └── main.py                  # FastAPI application entrypoint & middleware
├── frontend/
│   ├── src/
│   │   ├── components/          # Navbar, Sidebar, Footer, UI components
│   │   ├── pages/               # Dashboard, TripDetail, RoutePlanner, AiInsights, ModelInfo, etc.
│   │   ├── services/            # Axios API client layer with JWT interceptors
│   │   ├── store/               # React AuthContext state provider
│   │   ├── types/               # TypeScript interfaces & types
│   │   ├── App.tsx              # Router setup and route guards
│   │   └── index.css            # Tailwind design system & tokens
│   ├── package.json             # Frontend dependencies and build scripts
│   └── vite.config.ts           # Vite configuration & dev proxy
├── ai_insights/                 # Anomaly detection, sentiment, & maintenance modules
├── chatbot/                     # NLP assistant engine and prompt response logic
├── ml_model/                    # Trained model artifacts, benchmark suite, training scripts
├── route_optimization/          # OSRM routing engine & route optimizer logic
├── utils/                       # Synthetic telematics generators & DB helpers
├── requirements.txt             # Python backend dependencies
├── LICENSE                      # MIT Open Source License
└── README.md                    # Project documentation
```

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

<div align="center">
  <sub>Built with ❤️ for advanced vehicle telematics and eco-friendly driving.</sub>
</div>
