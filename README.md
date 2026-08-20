# Foundations Counselling Academy

> **"Workplaces where people thrive — measurably."**

Foundations Counselling Academy is a Pameltex Group company based in Gaborone, Botswana, specialising in evidence-based workplace mental health, employee wellbeing, and organisational development across Southern Africa.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features & Capabilities](#key-features--capabilities)
- [System Architecture](#system-architecture)
- [Repository Structure](#repository-structure)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Credits & Contact](#credits--contact)

---

## 🌟 Overview

Foundations Counselling Academy delivers comprehensive solutions to support individual wellbeing and organisational performance. Grounded in clinical expertise and industrial psychology, our programmes help organisations build psychologically safe, high-performing workplaces aligned with international standards such as **ISO 45003**.

### Core Service Areas:
1. **EAP & Counselling** — Confidential employee assistance programmes, crisis intervention, trauma debriefing, and personalised mental health support.
2. **Corporate Training** — Workshops and CPD-accredited courses covering mental health first aid, leader resilience, and psychological safety.
3. **Psychosocial Risk Management** — ISO 45003-aligned workplace risk assessments, hazard identification, and structured mitigation roadmaps.
4. **Organisational Development** — Culture assessments, change management, leadership coaching, and high-performance team alignment.

---

## ✨ Key Features & Capabilities

- **Interactive Service & Solution Explorer** — Dedicated pages detailing outcomes, methodologies, target audiences, and industry applications.
- **Learning Hub & Course Catalog** — Previews of CPD-accredited self-paced and cohort-based executive courses with LMS/Moodle integration.
- **Dynamic Intake & Assessment System** — Multi-step interactive intake flow (`/intake`) for corporate and individual client onboarding.
- **AI Assistant ("Aliana")** — Embedded conversational AI powered by FastAPI and OpenAI/Emergent LLM integration to assist HR managers, answer service queries, and capture qualified leads.
- **Lead Capture & Contact Management** — Secure asynchronous submission handling with MongoDB persistence.
- **Responsive & Accessible UI** — Crafted with Tailwind CSS, Radix UI primitives, Framer Motion animations, and mobile-first responsive design.

---

## 🏗 System Architecture

The application is architected as a decoupled modern full-stack application:

```
┌────────────────────────────────────────────────────────┐
│               Frontend (React 19 + SPA)                │
│    Tailwind CSS · Radix UI · Framer Motion · CRACO     │
└───────────────────────────┬────────────────────────────┘
                            │ HTTP / JSON API
┌───────────────────────────▼────────────────────────────┐
│               Backend (FastAPI + Python)               │
│          Async Motor · Pydantic v2 · Uvicorn           │
└─────────────┬───────────────────────────┬──────────────┘
              │                           │
┌─────────────▼─────────────┐ ┌───────────▼──────────────┐
│       MongoDB Database    │ │   OpenAI / LLM Service   │
│  Leads, Contacts, Chats   │ │    "Aliana" AI Chatbot   │
└───────────────────────────┘ └──────────────────────────┘
```

---

## 📁 Repository Structure

```text
.
├── backend/                  # FastAPI backend service
│   ├── server.py             # API routes, LLM integration, and MongoDB handlers
│   ├── requirements.txt      # Python dependencies
│   └── tests/                # Backend test suite
├── frontend/                 # React 19 single-page application
│   ├── public/               # Static assets and index.html
│   ├── src/
│   │   ├── components/       # Reusable UI components (Navbar, Footer, Chatbot, etc.)
│   │   ├── data/             # Site configuration, navigation, courses & services
│   │   ├── pages/            # Page views (Home, Services, Learning, Intake, etc.)
│   │   ├── hooks/            # Custom React hooks
│   │   ├── lib/              # Utility functions and helpers
│   │   ├── App.js            # Router configuration and application shell
│   │   └── index.css         # Global styling and Tailwind directives
│   ├── package.json          # Node dependencies and scripts
│   ├── tailwind.config.js    # Tailwind configuration and design tokens
│   └── craco.config.js       # CRACO build configurations
└── README.md                 # Project documentation
```

---

## 🛠 Tech Stack

### Frontend
- **Framework:** React 19
- **Routing:** React Router v7
- **Styling:** Tailwind CSS v3, PostCSS, Autoprefixer
- **UI Primitives & Components:** Radix UI, Lucide Icons, Embla Carousel, Sonner (Toasts)
- **Animations:** Framer Motion
- **Build Tool:** CRACO / Webpack

### Backend
- **Framework:** FastAPI
- **ASGI Server:** Uvicorn
- **Database Driver:** Motor (Async PyMongo driver)
- **Data Validation:** Pydantic v2 & Email Validator
- **AI Integration:** Emergent LLM Integration / OpenAI GPT

---

## 🚀 Getting Started

### Prerequisites

Ensure the following are installed on your machine:
- **Node.js:** `v18.x` or higher
- **Yarn:** `v1.22+` (or `npm`)
- **Python:** `3.10+`
- **MongoDB:** Local instance or MongoDB Atlas cluster URI

---

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   ```bash
   # Linux/macOS
   python3 -m venv venv
   source venv/bin/activate

   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables in a `.env` file (see [Environment Variables](#environment-variables)).

5. Start the FastAPI server:
   ```bash
   uvicorn server:app --reload --host 0.0.0.0 --port 8000
   ```
   The API will be accessible at `http://localhost:8000`. Interactive Swagger API docs are available at `http://localhost:8000/docs`.

---

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   yarn install
   # or: npm install
   ```

3. Configure frontend environment variables in `.env` if custom endpoints are needed:
   ```env
   REACT_APP_BACKEND_URL=http://localhost:8000
   ```

4. Start the development server:
   ```bash
   yarn start
   # or: npm start
   ```
   Open [http://localhost:3000](http://localhost:3000) to view the application in your browser.

5. Build for production:
   ```bash
   yarn build
   # or: npm run build
   ```

---

## ⚙️ Environment Variables

### Backend (`backend/.env`)

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `MONGO_URL` | MongoDB connection connection URI | `mongodb://localhost:27017` |
| `DB_NAME` | MongoDB database name | `foundations_db` |
| `EMERGENT_LLM_KEY` | API Key for Emergent / OpenAI LLM integration | `your_llm_api_key_here` |
| `CORS_ORIGINS` | Comma-separated list of allowed origins | `http://localhost:3000,https://academyfoundations.com` |

### Frontend (`frontend/.env`)

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `REACT_APP_BACKEND_URL` | Base URL for FastAPI backend API | `http://localhost:8000` |

---

## 🔌 API Reference

All backend routes are prefixed with `/api`:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/` | Health check endpoint |
| `POST` | `/api/contact` | Submit a general inquiry / contact form |
| `GET` | `/api/contact` | List received contact submissions |
| `POST` | `/api/chat/lead` | Record a prospective lead captured via AI Chatbot |
| `GET` | `/api/chat/leads` | Retrieve captured chatbot leads |
| `POST` | `/api/chat/message` | Send a message to "Aliana" AI assistant and get response |
| `GET` | `/api/chat/history/{session_id}` | Retrieve conversation history for a given session |

---

## 🏢 Credits & Contact

- **Company:** Foundations Counselling Academy (A Pameltex Group company)
- **Location:** Plot 18680 Khuhurutse St Phase 2, Gaborone, Botswana
- **Email:** [info@academyfoundations.com](mailto:info@academyfoundations.com)
- **Phone:** +267 72 534 203
- **Web Development & Design:** [Ras Ali Labs](https://www.rasalilabs.com)
