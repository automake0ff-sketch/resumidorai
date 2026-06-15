# ResumidorAI 🎬

Resume cualquier video de YouTube con IA en segundos.

**Stack:** Next.js 14 · FastAPI · PocketBase · Clerk · Claude AI · Vercel · Railway

---

## Arquitectura

```
Usuario → Next.js (Vercel) → FastAPI (Railway)
                ↓                    ↓
             Clerk Auth        PocketBase DB
                                    ↓
                             Agentes IA (Claude)
                                    ↓
                          YouTube Transcript API
```

## Setup rápido

### 1. Clonar
```bash
git clone https://github.com/automake0ff-sketch/resumidorai.git
cd resumidorai
```

### 2. PocketBase
```bash
# Descarga PocketBase desde https://pocketbase.io/docs/
./pocketbase serve

# Configura las colecciones:
cd backend
cp .env.example .env
# Rellena POCKETBASE_URL, POCKETBASE_ADMIN_EMAIL, POCKETBASE_ADMIN_PASSWORD

python setup_pocketbase.py
```
Admin UI disponible en: `http://localhost:8090/_/`

### 3. Backend
```bash
cd backend
pip install -r requirements.txt

# Variables necesarias en .env:
# ANTHROPIC_API_KEY, POCKETBASE_URL, POCKETBASE_ADMIN_EMAIL,
# POCKETBASE_ADMIN_PASSWORD, CLERK_ISSUER_URL

uvicorn app.main:app --reload --port 8000
```

### 4. Frontend
```bash
cd frontend
npm install

# Crea .env.local con:
# NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
# CLERK_SECRET_KEY=sk_test_...
# NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
# NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
# NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/dashboard
# NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/dashboard
# NEXT_PUBLIC_API_URL=http://localhost:8000

npm run dev
```

### 5. Clerk Webhook (sync usuarios)
En [Clerk Dashboard](https://dashboard.clerk.com):
- Webhooks → Add Endpoint
- URL: `https://tu-backend.railway.app/api/webhooks/clerk`
- Eventos: `user.created`, `user.updated`

---

## Deploy a producción

### Backend → Railway
```bash
railway login
railway init
railway up
```
Variables en Railway Dashboard:
```
ANTHROPIC_API_KEY=sk-ant-...
POCKETBASE_URL=https://tu-pocketbase.fly.dev
POCKETBASE_ADMIN_EMAIL=admin@...
POCKETBASE_ADMIN_PASSWORD=...
CLERK_ISSUER_URL=https://discrete-reptile-59.clerk.accounts.dev
CORS_ORIGINS=https://tu-app.vercel.app
```

### Frontend → Vercel
Conecta el repo en [vercel.com](https://vercel.com) y añade:
```
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/dashboard
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/dashboard
NEXT_PUBLIC_API_URL=https://tu-backend.railway.app
```

### PocketBase → Fly.io (recomendado)
```bash
fly launch --name resumidorai-pb
fly deploy
```

---

## Estructura del proyecto

```
resumidorai/
├── backend/
│   ├── app/
│   │   ├── main.py                   # FastAPI entry point
│   │   ├── agents/summary_agent.py   # 4 agentes IA + orquestador
│   │   ├── prompts/prompts.py        # Prompts optimizados
│   │   ├── api/
│   │   │   ├── summaries.py          # CRUD endpoints
│   │   │   ├── webhooks.py           # Clerk sync
│   │   │   └── health.py
│   │   ├── auth/clerk.py             # Verificación JWT
│   │   ├── db/pocketbase.py          # Cliente PocketBase REST
│   │   ├── services/
│   │   │   ├── youtube.py            # Extracción transcripts
│   │   │   └── job_processor.py      # Pipeline completo
│   │   └── models/schemas.py
│   ├── setup_pocketbase.py           # Script de setup inicial
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── page.tsx              # Landing
│       │   ├── pricing/page.tsx      # Precios
│       │   ├── dashboard/
│       │   │   ├── layout.tsx        # Nav del dashboard
│       │   │   └── page.tsx          # App principal
│       │   ├── sign-in/[[...sign-in]]/page.tsx
│       │   └── sign-up/[[...sign-up]]/page.tsx
│       ├── lib/api.ts                # Cliente API tipado
│       ├── middleware.ts             # Auth middleware Clerk
│       └── styles/globals.css
├── vercel.json
├── railway.toml
└── README.md
```

## Planes

| Plan | Resúmenes/mes | Precio |
|------|--------------|--------|
| Free | 5 | $0 |
| Starter | 50 | $9/mes |
| Pro | 200 | $29/mes |

## Agentes IA

| Agente | Descripción |
|--------|-------------|
| `TranscriptCleanerAgent` | Limpia y normaliza el texto bruto de YouTube |
| `SummaryGeneratorAgent` | Genera resumen en idioma y longitud seleccionados |
| `KeyPointsAgent` | Extrae 5-8 insights principales en JSON |
| `ChapterDetectorAgent` | Detecta secciones temáticas con timestamps |
