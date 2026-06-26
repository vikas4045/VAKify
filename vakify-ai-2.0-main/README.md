# Vakify

Vakify is an AI-powered adaptive learning platform with a polished Figma-based frontend and a Flask/Postgres backend. It combines:

- natural chat-style tutoring
- chat-synced coding labs
- saved conversation threads
- task and quiz flows
- rewards and progress tracking
- admin and moderation tools

## What’s Included

- AI Chat with saved threads and contextual replies
- Coding Lab that can sync a task from the latest chat
- Database-backed chat history, feedback, tasks, and submissions
- OpenAI-powered response generation and study/task creation
- Flask API with JWT auth
- Vercel-friendly frontend build output

## Tech Stack

- Frontend: React, TypeScript, Vite, Tailwind CSS
- Backend: Flask, Flask-JWT-Extended, Flask-SQLAlchemy, Flask-CORS
- Database: SQLite locally, Postgres/Neon in deployment
- AI: OpenAI Responses API

## Project Structure

- `src/` - React frontend
- `backend/` - Flask API and services
- `tests/` - backend integration tests
- `vercel.json` - Vercel build config and SPA fallback routing
- `render.yaml` - Render web service and Postgres setup for the Flask API

## Local Development

### Frontend

```bash
npm install
npm run dev
```

The frontend runs on:

- `http://localhost:5173`

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 run.py
```

The backend runs on:

- `http://127.0.0.1:5001`

## Environment Variables

Create `backend/.env` with the values your deployment needs.

```env
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
DATABASE_URL=sqlite:///adaptive_learning.db
OPENAI_API_KEY=your-openai-key
ELEVENLABS_API_KEY=your-elevenlabs-api-key
ELEVENLABS_VOICE_ID=EXAVITQu4vr4xnSDxMaL
ELEVENLABS_MODEL_ID=eleven_multilingual_v2
LEONARDO_API_KEY=your-leonardo-api-key
LEONARDO_MODEL_ID=your-leonardo-model-id
CORS_ORIGINS=*
APP_ENV=development
FLASK_DEBUG=0
```

For Postgres or Neon, set `DATABASE_URL` to your Postgres connection string.

For deployment, set these server-side values:

```env
APP_ENV=production
SECRET_KEY=your-strong-secret
JWT_SECRET_KEY=your-strong-jwt-secret
DATABASE_URL=your-postgres-connection-string
OPENAI_API_KEY=your-openai-key
ELEVENLABS_API_KEY=your-elevenlabs-api-key
ELEVENLABS_VOICE_ID=EXAVITQu4vr4xnSDxMaL
ELEVENLABS_MODEL_ID=eleven_multilingual_v2
LEONARDO_API_KEY=your-leonardo-api-key
LEONARDO_MODEL_ID=your-leonardo-model-id
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=https://your-vercel-domain/auth/google/callback
CORS_ORIGINS=https://your-vercel-domain
```

## Main Features

### AI Chat

- Saves each conversation as a thread
- Stores question, response, feedback, and thread metadata in the database
- Supports rich formatted assistant replies
- Supports image generation in chat when `LEONARDO_API_KEY` is configured

### Coding Lab

- Loads a task from the latest chat automatically
- Stores generated lab tasks in the database
- Accepts stdin input
- Saves each run as a submission

### Progress and Rewards

- XP, levels, streaks, quiz history, downloads, and practice activity are persisted in the backend

### Admin and Moderation

- Admin and moderation views read from real backend data
- Feedback can be flagged and reviewed

## Testing

Run backend tests:

```bash
python3 -m pytest
```

Run a production frontend build:

```bash
npm run build
```

## Deployment Notes

- Frontend deploys to Vercel
- Backend deploys to Render with Postgres
- Vite builds to `dist/`
- `vercel.json` is configured with:

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```

### Vercel

- Framework preset: Vite
- Build command: `npm run build`
- Output directory: `dist`
- Environment variable: `VITE_API_BASE_URL=https://<your-render-api-domain>`

### Render

- Use `render.yaml` from the repo root
- It provisions a Python web service and a managed Postgres database
- After Render creates the API URL, copy it into Vercel as `VITE_API_BASE_URL`
- Add the Google, OpenAI, and ElevenLabs secrets in the Render dashboard if you prefer not to sync them from the repo

## API Summary

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `GET /api/chat/threads`
- `POST /api/chat/threads`
- `POST /api/chat`
- `GET /api/chat/history`
- `GET /api/lab/task`
- `POST /api/lab/task/sync`
- `POST /api/lab/run`
- `GET /api/lab/submissions`

## Notes

- The app uses real saved data now, not demo-only placeholders.
- The coding lab can generate tasks from the latest chat response.
- The backend is designed to work with SQLite locally and Postgres in deployment.
