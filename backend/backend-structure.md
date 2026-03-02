# Backend Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   └── schemas.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── endpoints/
│   │   │   ├── __init__.py
│   │   │   ├── projects.py
│   │   │   ├── sections.py
│   │   │   └── review.py
│   │   └── dependencies.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── openai_service.py
│   │   └── auth_service.py
│   └── utils/
│       ├── __init__.py
│       └── validators.py
├── migrations/
│   └── init_db.sql
├── requirements.txt
├── Dockerfile
└── .env.example
```
