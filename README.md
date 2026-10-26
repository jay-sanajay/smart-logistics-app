# 🚚 Cloud-Native Logistics Platform with Automated CI/CD

[![CI/CD Pipeline](https://github.com/jay-sanajay/smart-logistics-app/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/jay-sanajay/smart-logistics-app/actions)
[![Docker](https://img.shields.io/badge/Docker-Multi--Stage%20Build-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![AWS Deployment](https://img.shields.io/badge/AWS-ECR%20%7C%20ECS-232F3E?logo=amazon-aws&logoColor=white)](https://aws.amazon.com/)
[![Testing](https://img.shields.io/badge/Testing-Pytest%20Suite-0A9EDC?logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![Backend](https://img.shields.io/badge/Backend-FastAPI%20%7C%20Python-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Database](https://img.shields.io/badge/Database-PostgreSQL%20%7C%20Asyncpg-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Machine Learning](https://img.shields.io/badge/ML-Scikit--Learn-F7931E?logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-Vercel-black?logo=vercel)](https://smart-logistics-app.vercel.app/)

A high-performance, containerized cloud-native logistics intelligence platform featuring automated CI/CD pipelines, multi-stop geospatial routing, Scikit-Learn machine learning predictions, zero-downtime rolling updates, and full system observability.

🌐 **Live Application:** [smart-logistics-app.vercel.app](https://smart-logistics-app.vercel.app/)

---

## 🌟 Key Engineering Capabilities

* **Containerized Microservices:** Production-grade multi-stage Docker build separating compilation dependencies from a stripped Python 3.11 runtime, running as a non-root system user for security compliance.
* **Automated CI/CD with GitHub Actions:** Every push triggers an automated workflow running Flake8 linting, Pytest integration tests, Docker image building with GitHub Actions cache, commit-SHA tagging, and automated push to Amazon ECR.
* **High-Throughput Asynchronous Backend:** Built on FastAPI with SQLAlchemy 2.0 (`AsyncSession` + `asyncpg`), enabling non-blocking database queries across 10,000+ seeded logistics records.
* **Automated Health Checks & Observability:** Custom `/health` probes verifying database connectivity and ML model readiness, with request-latency tracking middleware reporting execution duration via `X-Process-Time` headers.
* **Multi-Stop Route Optimization:** Geocodes physical addresses with OpenCage and calculates optimal stop sequences using Haversine distance heuristics and Mapbox traffic-aware routing.
* **ML-Powered ETA Prediction:** Serialized Scikit-Learn Random Forest regression pipeline predicting delivery duration with 87% accuracy based on traffic, weather, stops, and distance.
* **Automated Dispatch Reporting:** Programmatically generates multi-page PDF manifests via ReportLab—including embedded client-side map captures—and delivers them asynchronously via `aiosmtplib`.

---

## 🏗️ Cloud-Native Architecture

```
                    ┌───────────────────────────────────────────────┐
                    │            Frontend (Vercel)                  │
                    │  React 19 (Vite) + Leaflet + OpenStreetMap    │
                    │  HTML-to-Image Canvas + Responsive CSS UI     │
                    └───────────────────────┬───────────────────────┘
                                            │ HTTPS / REST (JSON)
                                            ▼
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                           Containerized Backend (Docker / AWS)                            │
│                                  FastAPI + Uvicorn                                        │
│                                                                                           │
│  ┌──────────────────────┐  ┌───────────────────────┐  ┌──────────────────────┐  ┌───────┐ │
│  │   Auth & Security    │  │  Routing & Heuristics │  │     ML Predictor     │  │  AI   │ │
│  │ OAuth2 / JWT, Bcrypt │  │  Haversine + Mapbox   │  │ RandomForest Pipeline│  │Gemini │ │
│  │ RBAC (Admin/Driver)  │  │  OpenCage Geocoding   │  │  (weather/traffic)   │  │ Flash │ │
│  └──────────────────────┘  └───────────────────────┘  └──────────────────────┘  └───────┘ │
│                                         │                                                 │
│                 ┌───────────────────────┴────────────────────────┐                        │
│                 │      Observability & Automated Dispatch        │                        │
│                 │      /health Probes + ReportLab + aiosmtplib   │                        │
│                 └────────────────────────────────────────────────┘                        │
└─────────────────────────────────┬─────────────────────────────────────────────────────────┘
                                  │ Async SQLAlchemy / asyncpg
                                  ▼
                ┌───────────────────────────────────┐
                │       PostgreSQL Database         │
                │  - Users (RBAC)                   │
                │  - RouteHistory (Base64 imagery)  │
                │  - DeliveryLogs (10K+ records)    │
                └───────────────────────────────────┘
```

---

## 🔄 CI/CD Pipeline Workflow

The repository includes a production GitHub Actions pipeline (`.github/workflows/ci-cd.yml`):

1. **Continuous Integration (CI):**
   * Checks out code and provisions Python 3.11 environment.
   * Runs Flake8 syntax and error checks.
   * Executes the full automated test suite using `pytest tests/ -v`.
   * Publishes test artifact results.
2. **Continuous Deployment (CD):**
   * Configures AWS credentials via IAM roles/secrets.
   * Authenticates with Amazon Elastic Container Registry (ECR).
   * Builds the Docker image utilizing GitHub Actions cache (`type=gha`).
   * Tags the image with both `:latest` and the unique Git commit SHA (`${{ github.sha }}`).
   * Pushes container image to Amazon ECR and triggers zero-downtime rolling update.

---

## 🧪 Automated Testing Suite

The project includes unit and API integration tests in `tests/test_api.py`:

```bash
# Run tests locally
pytest tests/ -v

# Run with test coverage
pytest tests/ --cov=. --cov-report=term-missing
```

| Test Case | Description | Expected Status |
|---|---|---|
| `test_health_check_endpoint` | Verifies `/health` probe returns service readiness | 200 OK |
| `test_predict_eta_valid_payload` | Tests ML prediction with standard logistics features | 200 OK |
| `test_predict_eta_missing_required_fields` | Verifies Pydantic schema validation on missing fields | 422 Unprocessable |
| `test_predict_eta_invalid_types` | Tests type-safety and rejection of malformed values | 422 Unprocessable |
| `test_unauthenticated_protected_route` | Ensures OAuth2 Bearer protection blocks unauthorized calls | 401 Unauthorized |
| `test_suggest_locations_missing_query` | Verifies query parameter validation | 400 Bad Request |
| `test_request_process_time_header` | Confirms custom latency middleware populates `X-Process-Time` | Header Verified |

---

## 🐳 Docker & Local Setup

### 1. Run Everything with Docker Compose (Recommended)
```bash
# Clone the repository
git clone https://github.com/jay-sanajay/smart-logistics-app.git
cd smart-logistics-app

# Spin up PostgreSQL and containerized FastAPI API
docker-compose up --build -d

# Verify container health
docker-compose ps
```

The API will be available at `http://localhost:8000` with Swagger docs at `http://localhost:8000/docs`.

### 2. Run Locally without Docker
```bash
# Set up Python virtual environment
python -m venv venv
venv\Scripts\activate   # Windows
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run FastAPI with live reload
uvicorn main:app --reload --port 8000
```

---

## 🛠️ Tech Stack Summary

* **Backend & API:** Python 3.11, FastAPI, Uvicorn (ASGI), Pydantic
* **DevOps & Cloud:** Docker (Multi-stage), Docker Compose, GitHub Actions, AWS (ECR/ECS), Render, Vercel
* **Database & Persistence:** PostgreSQL, SQLAlchemy 2.0 (AsyncSession), asyncpg, psycopg2
* **Machine Learning:** Scikit-Learn (RandomForestRegressor, ColumnTransformer), Pandas, Joblib
* **Geospatial & Mapping:** Mapbox Directions API, OpenCage Geocoding, Leaflet, OpenStreetMap
* **Quality & Testing:** Pytest, HTTPX, Flake8
* **Frontend:** React 19, Vite 6, HTML-to-Image, Axios
