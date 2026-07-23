# Screenwriter Assistant MVP

A web application that helps film screenwriters structure and develop scripts by guiding them through key plot points and providing AI-generated feedback.

## Features

- Create and manage screenplay projects
- Structure stories using popular frameworks (Three-Act, Save the Cat, Hero's Journey)
- Interactive editor with section-based organization
- Guiding checklists for each plot point
- AI-powered review and feedback using GPT-4
- Responsive design with keyboard shortcuts
- Real-time content persistence

## Tech Stack

- **Frontend**: React, TypeScript, Vite, Tailwind CSS, Radix UI
- **Backend**: FastAPI, Python, PostgreSQL, OpenAI API
- **Infrastructure**: Docker, Docker Compose

## Prerequisites

- Docker and Docker Compose
- OpenAI API key

## Quick Start

1. Clone the repository:
```bash
git clone <repository-url>
cd screenwriter-assistant
```

2. Create environment files:
```bash
# Backend
cp backend/.env.example backend/.env
# Edit backend/.env and add your OpenAI API key

# Frontend
cp frontend/.env.example frontend/.env
```

3. Start the application:
```bash
docker-compose up --build
```

4. Access the application:
- Frontend: http://localhost:4321
- API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- MCP server (for agents): http://localhost:8000/mcp/ — see [mcp-guide.md](mcp-guide.md) for connecting and using it

## Development

### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/          # API endpoints
│   │   ├── models/       # Database models and schemas
│   │   ├── services/     # Business logic
│   │   └── main.py       # FastAPI application
│   ├── migrations/       # Database migrations
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── hooks/        # Custom React hooks
│   │   ├── lib/          # Utilities and API client
│   │   └── types/        # TypeScript types
│   └── Dockerfile
└── docker-compose.yml
```

## API Endpoints

### Projects
- `GET /api/projects/` - List all projects
- `POST /api/projects/` - Create a new project
- `GET /api/projects/{id}` - Get project details
- `PATCH /api/projects/{id}` - Update project
- `DELETE /api/projects/{id}` - Delete project

### Sections
- `GET /api/sections/{id}` - Get section details
- `PATCH /api/sections/{id}` - Update section content
- `POST /api/sections/{id}/checklist` - Add checklist item
- `PATCH /api/sections/checklist/{id}` - Update checklist item

### Review
- `POST /api/review/` - Get AI review for a section

## Authentication

The MVP uses a mock authentication system for development. In production, implement proper authentication using Supabase or another auth provider.

## Keyboard Shortcuts

- `Cmd/Ctrl + S` - Save current section
- `Cmd/Ctrl + Enter` - Request AI review

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a pull request

## License

MIT License - see LICENSE file for details
