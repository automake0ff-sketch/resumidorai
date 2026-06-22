# ResumidorAI

Resume vídeos de YouTube con IA (Claude Sonnet) — resumen, puntos clave y capítulos en segundos.

**Stack:** Next.js 14 (Vercel) · FastAPI (Railway) · Firestore · Clerk · Stripe · Anthropic Claude

---

## Arquitectura

```
┌─────────────────────┐     HTTPS      ┌──────────────────────────────────────────┐
│   Frontend (Vercel) │ ◄────────────► │         Backend (Railway)                │
│   Next.js 14        │                │  FastAPI + uvicorn                        │
│   Clerk (auth UI)   │                │  ├── /api/summaries  (10 req/min)         │
└─────────────────────┘                │  ├── /api/billing    (5 req/min)          │
                                       │  ├── /api/webhooks   (Clerk + Stripe)     │
          Clerk JWKS ◄─────────────────│  └── /api/health                          │
                                       │                                            │
                                       │  Services                                  │
                                       │  ├── YouTubeService  (transcript pipeline)│
                                       │  ├── VideoSummaryOrchestrator (Claude AI) │
                                       │  └── FirestoreClient (run_in_executor)    │
                                       └──────────────────────────────────────────┘
                                                        │
                                              ┌─────────▼──────────┐
                                              │  Google Firestore   │
                                              │  Collections:       │
                                              │  · user_profiles    │
                                              │  · summary_jobs     │
                                              │  · user_usage       │
                                              └────────────────────┘
```

### Pipeline de IA

```
URL de YouTube
    │
    ▼
YouTubeService.get_transcript()
    ├── Nivel 1: youtube-transcript-api (subtítulos nativos)
    ├── Nivel 2: oEmbed metadata
    └── Nivel 3: yt-dlp + faster-whisper (si ENABLE_WHISPER_FALLBACK=true)
    │
    ▼
VideoSummaryOrchestrator.process()
    ├── Transcript ≤ 14.000 chars → 1 llamada Claude Sonnet (JSON estructurado)
    └── Transcript > 14.000 chars → Chunking + map-reduce
        ├── N chunks × Claude Haiku (paralelo)
        └── 1 síntesis final × Claude Sonnet
    │
    ▼
{ summary, key_points, chapters }
```

---

## Instalación local

### Requisitos

- Python 3.12+
- Node.js 20+
- Cuenta de Firebase (Firestore)
- Cuenta de Clerk
- Cuenta de Stripe
- API key de Anthropic

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edita .env con tus credenciales
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
# Edita .env.local
npm run dev
```

---

## Variables de Entorno

### Backend (`backend/.env`)

| Variable | Descripción | Requerida |
|---|---|---|
| `ANTHROPIC_API_KEY` | API key de Anthropic | ✅ |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | JSON completo de cuenta de servicio Firebase | ✅ |
| `CLERK_ISSUER_URL` | URL del issuer de Clerk (ej: `https://clerk.your-app.com`) | ✅ |
| `CLERK_WEBHOOK_SECRET` | Secret del webhook de Clerk (empieza con `whsec_`) | ✅ |
| `STRIPE_SECRET_KEY` | Secret key de Stripe (`sk_live_...` o `sk_test_...`) | ✅ |
| `STRIPE_WEBHOOK_SECRET` | Secret del webhook de Stripe (`whsec_...`) | ✅ |
| `STRIPE_PRODUCT_STARTER` | Product ID del plan Starter | ✅ |
| `STRIPE_PRODUCT_PRO` | Product ID del plan Pro | ✅ |
| `ENVIRONMENT` | `production` para ocultar `/docs` y activar fail-closed | ✅ en prod |
| `CORS_ORIGINS` | URLs del frontend separadas por coma | ✅ en prod |
| `FRONTEND_URL` | URL base del frontend para redirects de Stripe | ✅ en prod |
| `CLERK_AUDIENCE` | Audience del JWT de Clerk (si está configurado) | Opcional |
| `CLERK_AUTHORIZED_PARTY` | Dominio autorizado para el claim `azp` | Opcional |
| `YOUTUBE_DATA_API_KEY` | YouTube Data API v3 (metadata más precisa) | Opcional |
| `ENABLE_WHISPER_FALLBACK` | `true` para activar faster-whisper como fallback | Opcional |
| `WHISPER_MODEL_SIZE` | `base`, `small`, `medium` (default: `base`) | Opcional |

### Frontend (`frontend/.env.local`)

| Variable | Descripción |
|---|---|
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Publishable key de Clerk |
| `CLERK_SECRET_KEY` | Secret key de Clerk |
| `NEXT_PUBLIC_API_URL` | URL del backend (ej: `https://resumidorai-production.up.railway.app`) |
| `NEXT_PUBLIC_SITE_URL` | URL pública del frontend (para SEO y og:image) |

---

## Despliegue

### Backend (Railway)

1. Conecta el repositorio a Railway
2. Establece **Root Directory = `backend`** en la configuración del servicio (Dashboard > Settings > Source)
3. Añade todas las variables de entorno del backend
4. Railway usa `railway.toml` automáticamente (start command, health check, restart policy)

> ⚠️ `ENVIRONMENT=production` debe estar configurado en Railway para ocultar `/docs` y activar protecciones de producción.

### Frontend (Vercel)

1. Conecta el repositorio a Vercel
2. Establece **Root Directory = `frontend`** en la configuración del proyecto
3. Añade las variables de entorno del frontend

### Firestore — Índices requeridos

Crea los siguientes índices compuestos en Firebase Console (Firestore > Indexes):

| Colección | Campos | Orden |
|---|---|---|
| `summary_jobs` | `clerk_user_id` ASC, `created` DESC | Compuesto |
| `user_usage` | `clerk_user_id` ASC, `month` ASC | Compuesto |

> Sin estos índices, las queries con `where` + `order_by` fallarán en producción.

---

## Tests

```bash
cd backend
python -m pytest tests/ -v
# 49 tests, 0 failures
```

Cobertura de tests:
- Validación de URLs y SSRF (`test_schemas.py`)
- Extracción de video ID y parsing de duración (`test_youtube_service.py`)
- Parsing de filtros Firestore y serialización (`test_firestore_client.py`)
- Prompts de IA, caching, y lógica de chunking (`test_prompts.py`)

---

## Solución de Problemas

### `/docs` visible en producción
Asegúrate de que `ENVIRONMENT=production` esté configurado en Railway (no `NODE_ENV` ni `ENV`).

### Error "FIREBASE_SERVICE_ACCOUNT_JSON no es JSON válido"
El JSON exportado de Firebase contiene saltos de línea literales en el campo `private_key`. El cliente lo corrige automáticamente, pero si persiste, usa `jq -c` para comprimirlo: `cat service-account.json | jq -c`.

### Transcripción falla con "YouTube está bloqueando"
Las IPs de Railway son detectadas como bots por YouTube para algunos vídeos. Usa vídeos con subtítulos/CC activados. Si necesitas Whisper para todos los vídeos, considera un proxy residencial o desplegar en un servidor con IP doméstica.

### Jobs quedan en "Procesando" para siempre
El dashboard hace polling automático durante 10 minutos. Si supera ese tiempo, el job se marca como fallado. Revisa los logs de Railway para el error real.

### Race condition en cuotas
Con tráfico muy alto, dos requests simultáneas del mismo usuario pueden superar el límite antes de que el contador se actualice. Esta limitación es conocida y se resolverá en v1.2 con Firestore Transactions.

---

## Costes estimados de IA (Anthropic Claude)

| Escenario | Coste actual | Con prompt caching | Con llamada unificada + caching |
|---|---|---|---|
| 100 usuarios (3 trial) | $78 | $48 | $30 |
| 1.000 usuarios (10 avg) | $2.606 | $1.615 | $900 |
| 10.000 usuarios (10 avg) | $26.064 | $16.150 | $9.000 |
| Plan Starter (50 resúm) | $13,03/usuario | $8,07 | $4,50 |
| Plan Pro (200 resúm) | $52,12/usuario | $32,30 | $18,00 |

> ⚠️ El plan Pro ($29/mes ingreso) tiene coste de $52 sin optimizaciones. Con llamada unificada + prompt caching: ~$18 → margen positivo.

---

## Roadmap

### v1.2 (próximo)
- [ ] Firestore Transactions para contador de cuotas atómico (race condition fix)
- [ ] Redis worker para jobs durables (reemplaza BackgroundTasks)
- [ ] Caché de resúmenes: mismo video_id → resultado cacheado

### v1.3
- [ ] Extensión de Chrome/Firefox
- [ ] Export a Notion, Obsidian, Markdown
- [ ] Búsqueda semántica en historial (Firestore Vector)
- [ ] Compartir resúmenes con URL pública

### v2.0
- [ ] Plan Agency/Team con múltiples usuarios
- [ ] API pública (Zapier, Make)
- [ ] Resúmenes de playlists completas

---

## Licencia

Privativo — © 2026 ResumidorAI
