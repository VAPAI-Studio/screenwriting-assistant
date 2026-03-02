# Screenwriter Assistant MVP - Detailed Setup Guide

## Project Setup from Scratch

### 1. Create Project Structure

```bash
# Create main project directory
mkdir screenwriter-assistant
cd screenwriter-assistant

# Create backend structure
mkdir -p backend/app/{api/endpoints,models,services,utils}
mkdir -p backend/migrations

# Create frontend structure
mkdir -p frontend/src/{components/{Layout,Projects,Editor,UI},hooks,lib,types}
mkdir -p frontend/public
```

### 2. Initialize Git Repository

```bash
git init
echo "# Screenwriter Assistant MVP" > README.md

# Create .gitignore
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
.Python
env/
venv/
.env

# Node
node_modules/
dist/
.env.local
.env.development.local
.env.test.local
.env.production.local

# IDEs
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Docker
postgres_data/
EOF

git add .
git commit -m "Initial commit"
```

### 3. Backend Setup

```bash
cd backend

# Create Python virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install fastapi uvicorn sqlalchemy psycopg2-binary openai pydantic pydantic-settings python-jose passlib python-multipart

# Generate requirements.txt
pip freeze > requirements.txt

# Create environment file
cp .env.example .env
# Edit .env and add your OpenAI API key
```

### 4. Frontend Setup

```bash
cd ../frontend

# Initialize npm project
npm create vite@latest . -- --template react-ts

# Install dependencies
npm install @radix-ui/react-dialog @radix-ui/react-dropdown-menu @radix-ui/react-select @radix-ui/react-slot @radix-ui/react-tabs @radix-ui/react-toast
npm install @tanstack/react-query class-variance-authority clsx lucide-react react-router-dom tailwind-merge
npm install -D tailwindcss postcss autoprefixer @types/react @types/react-dom

# Initialize Tailwind CSS
npx tailwindcss init -p

# Create environment file
cp .env.example .env
```

### 5. Database Setup

```bash
# Start PostgreSQL with Docker
docker run --name screenwriter-db -e POSTGRES_USER=screenwriter -e POSTGRES_PASSWORD=password -e POSTGRES_DB=screenwriter_db -p 5432:5432 -d postgres:15-alpine

# Apply migrations
cd backend
export DATABASE_URL=postgresql://screenwriter:password@localhost:5432/screenwriter_db
psql $DATABASE_URL -f migrations/init_db.sql

# Seed the database with sample data
python seed_data.py
```

### 6. Running the Application

#### Option 1: Using Docker Compose (Recommended)

```bash
# From the project root
docker-compose up --build
```

#### Option 2: Running Services Individually

Terminal 1 - Backend:
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Terminal 2 - Frontend:
```bash
cd frontend
npm run dev
```

### 7. Accessing the Application

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### 8. Testing the Application

1. Open http://localhost:5173 in your browser
2. Create a new project
3. Navigate to the project editor
4. Fill in sections with your story content
5. Use the checklist to guide your writing
6. Click "Review" to get AI feedback on your sections
7. Test keyboard shortcuts:
   - Cmd/Ctrl + S: Save (automatic on blur)
   - Cmd/Ctrl + Enter: Request AI review

### 9. Development Workflow

1. Backend changes:
   - Edit files in `backend/app/`
   - Changes auto-reload with uvicorn
   - Test API endpoints at http://localhost:8000/docs

2. Frontend changes:
   - Edit files in `frontend/src/`
   - Changes auto-reload with Vite
   - Browser updates automatically

3. Database changes:
   - Add new migrations to `backend/migrations/`
   - Apply with `psql $DATABASE_URL -f migrations/new_migration.sql`

### 10. Environment Variables

Backend (.env):
```
DATABASE_URL=postgresql://screenwriter:password@localhost:5432/screenwriter_db
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o
SECRET_KEY=your-secret-key-here
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
MAX_TOKENS=1500
MAX_SECTION_LENGTH=1500
CACHE_TTL=900
```

Frontend (.env):
```
VITE_API_URL=http://localhost:8000/api
```

### 11. Production Deployment

1. Backend:
   - Use proper authentication (Supabase/Auth0)
   - Set secure SECRET_KEY
   - Configure CORS for production domain
   - Use production database
   - Deploy to cloud provider (AWS, GCP, Heroku)

2. Frontend:
   - Build for production: `npm run build`
   - Deploy to static hosting (Vercel, Netlify)
   - Configure environment variables
   - Set up proper domain and SSL

### 12. Next Steps

1. Implement proper authentication
2. Add user management
3. Enhance AI prompts for better feedback
4. Add export functionality (PDF, Fountain format)
5. Implement collaborative features
6. Add more story frameworks
7. Create onboarding tutorial
8. Add analytics and monitoring
