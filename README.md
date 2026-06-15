# VideoSummary AI — MVP SaaS

Resume videos de YouTube con IA usando FastAPI, Claude, Supabase, Vercel y Clerk.

## Stack

| Capa | Tecnología |
|------|-----------|
| Frontend | Next.js 14 + Clerk (auth) → Vercel |
| Backend API | FastAPI + Python → Railway / Render |
| Base de datos | Supabase (PostgreSQL) |
| IA | Claude claude-sonnet-4-6 (Anthropic) |
| Auth | Clerk |
| Pagos | Stripe |
| Transcripción | youtube-transcript-api |

## Arquitectura del sistema

```
Usuario
  │
  ▼
[Next.js / Vercel]  ──auth──▶  [Clerk]
  │ JWT token
  ▼
[FastAPI / Railway]
  ├── GET /api/health
  ├── POST /api/summaries          → crea job + inicia background task
  ├── GET  /api/summaries/{id}     → estado + resultado
  ├── GET  /api/summaries          → historial
  ├── GET  /api/summaries/usage/me → uso del mes
  ├── POST /api/webhooks/clerk     → sync usuarios
  └── POST /api/webhooks/stripe    → gestión planes
       │
       ▼
  [Agentes IA]
  ├── TranscriptCleanerAgent    → limpia el transcript
  ├── SummaryGeneratorAgent     → genera el resumen
  ├── KeyPointsAgent            → extrae puntos clave
  └── ChapterDetectorAgent      → detecta capítulos
       │
       ▼
  [Supabase]
  ├── user_profiles
  ├── summary_jobs
  └── user_usage
```

## Setup en 10 pasos

### 1. Clonar y estructura
```bash
git clone <tu-repo>
cd videosummary
```

### 2. Supabase
1. Crea proyecto en https://supabase.com
2. Ve a SQL Editor
3. Ejecuta todo el contenido de `supabase_migrations.sql`
4. Copia `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` (Settings → API → service_role)

### 3. Clerk
1. Crea app en https://clerk.com
2. Configura OAuth (Google recomendado)
3. Ve a Webhooks → Add endpoint → URL: `https://tu-backend.railway.app/api/webhooks/clerk`
4. Eventos a escuchar: `user.created`, `user.updated`, `user.deleted`
5. Copia Publishable Key, Secret Key, Webhook Secret

### 4. Anthropic
1. Consigue API key en https://console.anthropic.com
2. Añade créditos

### 5. Backend (Railway)
```bash
cd backend
cp .env.example .env
# Rellena todas las variables

# Desarrollo local:
pip install -r requirements.txt
uvicorn app.main:app --reload

# Deploy con Railway:
# 1. railway login
# 2. railway init
# 3. railway up
# 4. Configura variables de entorno en dashboard de Railway
```

### 6. Frontend (Vercel)
```bash
cd frontend
cp .env.example .env.local
# Rellena variables

# Desarrollo local:
npm install
npm run dev

# Deploy:
vercel deploy
# Configura env vars en dashboard de Vercel
```

### 7. Stripe (opcional para planes pagos)
1. Crea productos en https://stripe.com: Starter ($9/mes), Pro ($29/mes)
2. Configura webhook → `https://tu-backend.railway.app/api/webhooks/stripe`
3. Eventos: `checkout.session.completed`, `customer.subscription.deleted`

## Planes y límites

| Plan | Precio | Resúmenes/mes |
|------|--------|---------------|
| Free | $0 | 5 |
| Starter | $9 | 50 |
| Pro | $29 | 200 |
| Unlimited | $79 | ∞ |

## Agentes IA

El sistema usa 4 agentes especializados que se ejecutan en pipeline:

1. **TranscriptCleanerAgent** — Limpia el texto bruto de YouTube (muletillas, errores OCR, puntuación)
2. **SummaryGeneratorAgent** — Genera el resumen en el idioma y longitud solicitados
3. **KeyPointsAgent** — Extrae 5-8 puntos clave en JSON estructurado
4. **ChapterDetectorAgent** — Detecta secciones temáticas con timestamps

Todos usan el modelo `claude-sonnet-4-6` y están en `backend/app/agents/summary_agent.py`.

Los prompts están en `backend/app/prompts/prompts.py` — edítalos para ajustar el tono y formato.

## Estructura de archivos

```
videosummary/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app
│   │   ├── api/
│   │   │   ├── summaries.py           # Endpoints principales
│   │   │   ├── webhooks.py            # Clerk + Stripe webhooks
│   │   │   └── health.py
│   │   ├── agents/
│   │   │   └── summary_agent.py       # 4 agentes IA + orquestador
│   │   ├── prompts/
│   │   │   └── prompts.py             # Todos los prompts del sistema
│   │   ├── services/
│   │   │   ├── youtube.py             # Extracción de transcripts
│   │   │   └── job_processor.py       # Pipeline de procesamiento
│   │   ├── auth/
│   │   │   └── clerk.py               # Verificación JWT Clerk
│   │   ├── db/
│   │   │   └── supabase.py            # Cliente Supabase
│   │   └── models/
│   │       └── schemas.py             # Pydantic models
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── layout.tsx             # ClerkProvider
│       │   ├── page.tsx               # Landing
│       │   └── dashboard/page.tsx     # App principal
│       ├── lib/
│       │   └── api.ts                 # Cliente API
│       └── middleware.ts              # Auth middleware
├── supabase_migrations.sql            # Schema completo
└── vercel.json                        # Config Vercel
```

## Variables de entorno

### Backend
```env
ANTHROPIC_API_KEY=sk-ant-...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
CLERK_ISSUER_URL=https://xxx.clerk.accounts.dev
CLERK_WEBHOOK_SECRET=whsec_...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### Frontend
```env
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_...
CLERK_SECRET_KEY=sk_live_...
NEXT_PUBLIC_API_URL=https://tu-backend.railway.app
```

## Próximos pasos para escalar

- [ ] Redis + Celery para jobs async en producción (mejor que BackgroundTasks)
- [ ] Soporte para Vimeo, Loom, MP4 directo
- [ ] Dashboard de admin con métricas
- [ ] Exportar resúmenes a PDF/Notion/Obsidian
- [ ] API pública para developers
- [ ] Rate limiting con slowapi
