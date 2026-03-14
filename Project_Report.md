# Cloud Cost Optimisation Advisor
## Comprehensive Project Report

### 1. Executive Summary
The **Cloud Cost Optimisation Advisor** is a production-grade, advisory-only cloud analytics platform built with FastAPI and React. It provides secure, multi-user, hybrid cloud cost optimization insights.

The platform's primary goal is to address the lack of centralized cost visibility and explainable recommendations in native cloud tools. It supports two distinct data ingestion modes:
1. **LIVE Mode:** Direct integration with AWS Cost Explorer API.
2. **UPLOAD Mode:** Offline billing dataset ingestion via CSV exports (AWS/Azure).

Authentication is handled via Firebase (JWT-based), ensuring secure processing of analysis requests. The system operates strictly in an advisory capacity and does not perform automated infrastructure changes.

### 2. Architecture Overview
The system follows a Client-Server, RESTful API architecture with stateless processing. 

**Key Components:**
*   **Frontend (React SPA):** Handles UI, Firebase Authentication SDK, Mode Selector (Live vs. Upload), and sends JWT tokens and analysis requests.
*   **Authentication (Firebase):** Supports Email/Password & Google login. Issues and verifies JWT tokens.
*   **Backend API (FastAPI):** Exposes versioned endpoints (`/api/v1/`), includes JWT validation middleware, Pydantic request validation, and centralized exception handling.
*   **Data Ingestion Layer (Strategy Pattern):** Easily integrates different data sources (`LiveAWSDataSource` utilizing `boto3`, and `UploadedFileDataSource` for parsing CSVs). 
*   **Normalization Layer:** Converts all heterogeneous ingestion outputs into a unified internal model (`NormalizedCostDataset`). This ensures the analytics logic is agnostic to the data source.
*   **Analytics Layer (Pandas):** Processes the normalized dataset to perform aggregations, cost breakdowns, time-series calculations, and heuristic-based waste detection.
*   **Recommendation Engine:** Applies deterministic rules to produce structured recommendations including resource ID, issue type, suggested actions, estimated savings, risk levels, and explanations.

**Data Flow:**
User → React SPA → Firebase Auth → FastAPI → Data Ingestion Layer → Normalization Layer → Pandas Analytics Engine → Recommendation Engine → JSON Response → React UI

### 3. Technology Stack
*   **Frontend:** React, React Router, Axios/Fetch API, Recharts/Chart.js, Tailwind CSS or Modern CSS Modules. Hosted on Render.com (Static Site).
*   **Backend:** Python, FastAPI, Pydantic. Hosted on Render.com (Web Service).
*   **Data Processing:** Pandas (Analytics), `boto3` (AWS API Integration).
*   **Security & Identity:** Firebase (Authentication), Environment Variables (Secrets).

### 4. API Design & Core Endpoints
The API is designed as a stateless, RESTful interface:
*   `GET /api/v1/health`: Health check endpoint.
*   `POST /api/v1/analyze`: Unified endpoint for both LIVE and UPLOAD ingestion modes.
*   `GET /api/v1/summary`: Returns aggregated cost metrics.
*   `GET /api/v1/cost-breakdown`: Returns service-level cost distribution.
*   `GET /api/v1/recommendations`: Returns advisory optimization recommendations.

### 5. Capabilities & Features
*   **Hybrid Ingestion:** Evaluate live AWS operations or perform deterministic testing with uploaded CSV datasets.
*   **Secure & Compliant:** Features JWT validation, read-only IAM permissions, environment-based credentials, comprehensive CSV injection prevention, and file size restrictions.
*   **Advisory Engine:** Analyzes cost distribution, identifies underutilized resources, and predicts monthly savings conservatively.

### 6. Architectural Strengths & Future Proofing
The architecture is deliberately over-engineered to be interview-defendable. Its primary strengths are:
*   Clean separation of concerns.
*   Pluggable ingestion strategy for future cloud providers (e.g., AzureLiveDataSource).
*   Stateless and horizontally scalable backend.
*   No persistent storage required in v1, though highly extensible to PostgreSQL or Redis.

### 7. Typical Interview Questions & Answers
**Q: Why use a Strategy Pattern for Data Ingestion?**
*A:* It decoupled the analytics logic from the specific source of data. The analytics engine only cares about the `NormalizedCostDataset`, meaning adding an Azure integration in the future only requires writing a new ingestion class, with zero changes to analytics.

**Q: How is security handled for CSV uploads?**
*A:* We implement strict schema validation, enforce realistic file size limits, use chunked parsing (via Pandas) to avoid memory overload, and provide robust CSV injection prevention. Files are processed in-memory and immediately discarded.

**Q: Why is the backend stateless?**
*A:* A stateless backend allows for effortless horizontal scaling. If user load increases, we can deploy multiple instances of the FastAPI backend behind a load balancer without worrying about shared session state.

**Q: Why use Firebase for authentication?**
*A:* It offloads the complexity and security risks of identity lifecycle management (like hashing passwords, handling MFA, and password resets) to a proven service, allowing us to focus purely on the cost optimization business logic.
