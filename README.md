# ResumidorAI 🎬

Resume cualquier video de YouTube con IA en segundos.

**Stack:** Next.js 14 · FastAPI · Firebase (Firestore) · Clerk · Claude AI · Vercel · Railway

---

## Arquitectura

```
Usuario → Next.js (Vercel) → FastAPI (Railway)
                ↓                    ↓
             Clerk Auth        Firestore (Firebase)
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

### 2. Firebase / Firestore
1. Crea un proyecto en [console.firebase.google.com](https://console.firebase.google.com)
2. **Compilación → Firestore Database** → Crear base de datos → modo producción
3. ⚙️ **Configuración del proyecto → Cuentas de servicio** → **Generar nueva clave privada** → descarga el `.json`
4. Ese archivo **no se sube al repo nunca**. Su contenido completo (en una sola línea) va como variable de entorno `FIREBASE_SERVICE_ACCOUNT_JSON` en el paso siguiente.

### 3. Backend
```bash
cd backend
pip install -r requirements.txt

# Variables necesarias en .env:
# ANTHROPIC_API_KEY, FIREBASE_SERVICE_ACCOUNT_JSON (el JSON completo
# de la cuenta de servicio, en una sola línea), CLERK_ISSUER_URL

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

Este monorepo tiene `backend/`, `frontend/` y otras carpetas. Railway necesita saber explícitamente dónde está el backend FastAPI:

1. En [railway.com](https://railway.com) → **New Project** → **Deploy from GitHub repo** → selecciona este repo
2. En el servicio creado → **Settings → Root Directory** → escribe `backend` (sin esto, Railway intenta analizar la raíz del repo, no encuentra ningún lenguaje reconocible y el deploy falla con un error de Railpack)
3. **Settings → Networking** → **Generate Domain** para obtener una URL pública `https://xxx.up.railway.app`
4. Variables en **Variables**:
```
ANTHROPIC_API_KEY=sk-ant-...

FIREBASE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"...",...}
# El JSON completo de la cuenta de servicio de Firebase, en una sola línea.
# Se obtiene en Firebase Console -> Configuración del proyecto ->
# Cuentas de servicio -> Generar nueva clave privada.

CLERK_ISSUER_URL=https://discrete-reptile-59.clerk.accounts.dev
CLERK_WEBHOOK_SECRET=whsec_...   # del Webhook de Clerk, ver sección siguiente

YOUTUBE_DATA_API_KEY=...          # opcional, mejora duración/metadata
ENABLE_WHISPER_FALLBACK=true
WHISPER_MODEL_SIZE=base
# ⚠️ El plan gratuito de Railway da 512MB de RAM. faster-whisper + sus
# dependencias (ctranslate2, av) pueden agotar esa memoria al cargar el
# modelo la primera vez que se usa el fallback, especialmente si el backend
# ya está procesando resúmenes con Anthropic en paralelo. Si ves el servicio
# reiniciarse sin motivo aparente (OOM kill), pon ENABLE_WHISPER_FALLBACK=false
# o sube de plan en Railway antes de reactivarlo.

STRIPE_SECRET_KEY=sk_test_...     # o sk_live_... en producción real
STRIPE_WEBHOOK_SECRET=whsec_...   # del Webhook de Stripe, ver sección siguiente
STRIPE_PRODUCT_STARTER=prod_UiLxrL4q3jo0d5
STRIPE_PRODUCT_PRO=prod_UiLxoqpYqemCDN

CORS_ORIGINS=https://tu-app.vercel.app
FRONTEND_URL=https://tu-app.vercel.app
```
5. Copia la URL pública que te da Railway para este servicio — la necesitas para el siguiente paso

**Conecta el frontend al backend:**
En Vercel → **Settings → Environment Variables** → actualiza:
```
NEXT_PUBLIC_API_URL=https://tu-backend.up.railway.app
```
Y haz **Redeploy**. Sin este paso exacto, el frontend sigue intentando llamar a `localhost:8000` (que no existe en el navegador del usuario) y verás el error `Failed to fetch` al intentar resumir un video.

### Webhooks (necesarios para que los pagos y el registro funcionen)

**Clerk** → [Dashboard](https://dashboard.clerk.com) → Webhooks → Add Endpoint:
- URL: `https://tu-backend.up.railway.app/api/webhooks/clerk`
- Eventos: `user.created`, `user.updated`, `user.deleted`
- Copia el "Signing Secret" → pégalo en `CLERK_WEBHOOK_SECRET` en Railway

**Stripe** → [Dashboard](https://dashboard.stripe.com/webhooks) → Add endpoint:
- URL: `https://tu-backend.up.railway.app/api/webhooks/stripe`
- Eventos: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`
- Copia el "Signing secret" → pégalo en `STRIPE_WEBHOOK_SECRET` en Railway

### Frontend → Vercel

**Paso crítico — Root Directory:** este repo es un monorepo (`backend/` + `frontend/`). Vercel necesita saber que el proyecto Next.js vive en `frontend/`, y esto **solo se configura en el dashboard**, no en `vercel.json`:

1. En [vercel.com](https://vercel.com) → tu proyecto → **Settings → General**
2. **Root Directory** → click "Edit" → selecciona `frontend`
3. Guarda. Esto hace que Vercel ejecute `npm install` y `npm run build` ya dentro de `frontend/`, sin necesitar `cd frontend &&` en ningún comando (de hecho, poner `cd frontend &&` ahí es la causa más común del error `exit code 1`, porque con Root Directory configurado el comando ya se ejecuta en esa carpeta).

Luego, en **Settings → Environment Variables**, añade:
```
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/dashboard
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/dashboard
NEXT_PUBLIC_API_URL=https://tu-backend.railway.app
```

Redeploy (Deployments → ⋯ → Redeploy) después de cambiar el Root Directory o las env vars.

> ⚠️ **Error `MIDDLEWARE_INVOCATION_FAILED` / `Missing publishableKey`**: significa que `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` no llegó al middleware en runtime. Pasos para resolverlo:
> 1. Confirma que las 7 variables están en **Settings → Environment Variables**, no solo guardadas como borrador.
> 2. Verifica que estén marcadas para el environment correcto: si el deploy que falla es de producción (rama `main`), la variable debe tener tickado **Production** (y/o **Preview** si pruebas desde un PR). Vercel permite limitarlas por environment y es fácil dejarlas solo en uno.
> 3. **Las env vars no se aplican a deploys ya existentes.** Después de añadirlas o editarlas, ve a **Deployments**, abre el deploy afectado → `⋯` → **Redeploy**. Un simple refresh de la página no sirve.
> 4. Las claves `pk_test_...` y `sk_test_...` deben copiarse completas y sin espacios; un solo carácter de menos provoca este mismo error.

> ⚠️ **Error `Failed to fetch` al pegar una URL y darle a "Resumir"**: el navegador no encuentra ningún backend al que llamar. Casi siempre es una de estas dos causas:
> 1. `NEXT_PUBLIC_API_URL` en Vercel sigue apuntando a `http://localhost:8000` o a un placeholder tipo `https://tu-backend.railway.app` — actualízala con la URL real que Railway te dio para el servicio del backend, y haz Redeploy.
> 2. El backend FastAPI directamente no está desplegado todavía. Pegar la URL en el navegador (`https://tu-backend.up.railway.app/api/health`) debe devolver `{"status":"ok",...}`; si da timeout o 404, el backend no está corriendo y hay que completar el paso "Backend → Railway" de arriba.

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
│   │   │   ├── billing.py            # Checkout y portal de Stripe
│   │   │   ├── webhooks.py           # Clerk + Stripe sync
│   │   │   └── health.py
│   │   ├── auth/clerk.py             # Verificación JWT
│   │   ├── db/firestore_client.py    # Cliente Firestore (Firebase Admin SDK)
│   │   ├── services/
│   │   │   ├── youtube.py            # Extracción transcripts + Whisper fallback
│   │   │   ├── stripe_service.py     # Checkout, portal, resolución de planes
│   │   │   └── job_processor.py      # Pipeline completo
│   │   └── models/schemas.py
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
