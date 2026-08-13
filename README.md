# Online Learning Platform - README

A production-grade online learning platform that generates personalized, AI-powered computer science tutorials. Users can input their background information and Claude API credentials to receive step-by-step curriculum generation with formula derivations, code examples, and practice exercises.

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 16+ (for frontend)
- PostgreSQL 15+
- Redis 7+
- MinIO (object storage)
- Docker Compose (recommended for development)

### Development Setup

1. **Copy environment template**:
   ```bash
   cp .env.example .env
   # Edit .env with your database and other settings
   ```

2. **Start the development environment** (using Docker):
   ```bash
   docker-compose up --build -d
   ```

3. **Initialize the database**:
   ```bash
   cd backend
   python src/initdb.py
   ```

4. **Run the backend server**:
   ```bash
   uvicorn src.api.main:app --reload --port 8000
   ```

5. **Run the Celery worker** (in a separate terminal):
   ```bash
   celery -A tasks.generation_tasks worker --loglevel=info
   ```

6. **Start the frontend**:
   ```bash
   cd frontend
   npm install
   npm start
   ```

The app will be available at `http://localhost:3000` and the API at `http://localhost:8000`.

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | JWT secret key (use `openssl rand -hex 32`) |
| `CRYPTO_KEY` | Yes | 32-byte hex string for AES encryption of API keys |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `REDIS_URL` | Yes | Redis URL for Celery broker |
| `MINIO_ENDPOINT` | No | MinIO/S3 endpoint for file storage |

## 📁 Project Structure

```
online-learning-platform/
├── backend/                  # FastAPI backend
│   ├── src/
│   │   ├── api/              # API endpoints
│   │   ├── models/           # SQLAlchemy models
│   │   ├── services/         # Business logic services
│   │   └── tests/            # Unit/integration tests
│   ├── requirements.txt      # Python dependencies
│   ├── conftest.py           # Pytest configuration
│   └── initdb.py             # DB initialization
├── frontend/                 # React + TypeScript frontend
│   ├── src/
│   │   ├── components/       # Reusable UI components
│   │   ├── pages/            Page views
│   │   └── hooks/            Custom React hooks
│   ├── package.json          # Node dependencies
│   └── tsconfig.json         # TypeScript config
├── docker-compose.yml        # Development environment
├── .env.example              # Environment template
├── requirements.txt          # Global dependencies
└── README.md                 # This file
```

## 🔐 Security Notes

- All user-provided Claude API keys are encrypted using AES-GCM before storage
- Passwords are hashed with bcrypt
- All API endpoints require JWT authentication
- Rate limiting is applied to prevent abuse
- Content security scanning detects PII and profanity

## 🧪 Testing

Run all tests:
```bash
cd backend
pytest tests/ -v
```

Run only auth tests:
```bash
pytest tests/test_auth.py -v
```

## 📈 Future Roadmap

- [x] User registration/login (MVP)
- [x] Profile management (MVP)
- [x] Claude API config storage (encrypted) (MVP)
- [x] P3 — Experience Enhancements (2026-08-13)
  - OAuth third-party login (Google, GitHub)
  - PDF tutorial export
  - Admin link visible only to admin users
- [ ] Knowledge inference from profile (MVP - partially done)
- [ ] Course outline generation via LLM (MVP)
- [ ] Chapter-by-chapter generation with prerequisite checks (MVP)
- [ ] Tutorial display with Markdown/Formula rendering (in progress)
- [ ] Public course catalog (search, sort, like, report)
- [x] Content export (Markdown/PDF)
- [x] OAuth2 login (Google/GitHub)
- [ ] Administrator dashboard
- [ ] Mobile responsive design

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Create a Pull Request

---

*Built with ❤️ for lifelong learners everywhere.*