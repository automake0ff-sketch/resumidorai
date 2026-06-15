-- ═══════════════════════════════════════════════════
-- VideoSummary AI - Schema de Base de Datos
-- Ejecutar en Supabase SQL Editor
-- ═══════════════════════════════════════════════════

-- ─── Extensiones ──────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── Tabla: Perfiles de usuario ───────────────────
CREATE TABLE IF NOT EXISTS user_profiles (
  user_id       TEXT PRIMARY KEY,                        -- ID de Clerk
  email         TEXT NOT NULL,
  name          TEXT,
  plan          TEXT NOT NULL DEFAULT 'free'
                CHECK (plan IN ('free', 'starter', 'pro', 'unlimited')),
  stripe_customer_id TEXT UNIQUE,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  deleted_at    TIMESTAMPTZ
);

-- ─── Tabla: Jobs de resumen ───────────────────────
CREATE TABLE IF NOT EXISTS summary_jobs (
  id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id             TEXT NOT NULL REFERENCES user_profiles(user_id),
  url                 TEXT NOT NULL,
  language            TEXT NOT NULL DEFAULT 'es',
  length              TEXT NOT NULL DEFAULT 'medium'
                      CHECK (length IN ('short', 'medium', 'detailed')),
  include_chapters    BOOLEAN DEFAULT TRUE,
  include_key_points  BOOLEAN DEFAULT TRUE,
  include_transcript  BOOLEAN DEFAULT FALSE,
  status              TEXT NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
  
  -- Metadatos del video
  title               TEXT,
  thumbnail           TEXT,
  duration_seconds    INTEGER,
  
  -- Resultados IA
  summary             TEXT,
  key_points          JSONB,
  chapters            JSONB,
  transcript          TEXT,
  
  -- Control
  error               TEXT,
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  started_at          TIMESTAMPTZ,
  completed_at        TIMESTAMPTZ
);

-- ─── Tabla: Uso mensual ───────────────────────────
CREATE TABLE IF NOT EXISTS user_usage (
  user_id   TEXT NOT NULL REFERENCES user_profiles(user_id),
  month     TEXT NOT NULL,           -- formato: "2024-01"
  count     INTEGER DEFAULT 0,
  PRIMARY KEY (user_id, month)
);

-- ─── Índices de rendimiento ───────────────────────
CREATE INDEX idx_summary_jobs_user_id   ON summary_jobs(user_id);
CREATE INDEX idx_summary_jobs_status    ON summary_jobs(status);
CREATE INDEX idx_summary_jobs_created   ON summary_jobs(created_at DESC);
CREATE INDEX idx_user_usage_user_month  ON user_usage(user_id, month);

-- ─── Row Level Security (RLS) ─────────────────────
-- NOTA: Con service_role key del backend, RLS no aplica.
-- Para llamadas desde frontend con anon key, habilitar:

ALTER TABLE user_profiles  ENABLE ROW LEVEL SECURITY;
ALTER TABLE summary_jobs   ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_usage     ENABLE ROW LEVEL SECURITY;

-- Políticas para anon/authenticated (si llamas desde frontend)
-- Los usuarios solo ven sus propios datos
CREATE POLICY "users_own_profile" ON user_profiles
  FOR ALL USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

CREATE POLICY "users_own_jobs" ON summary_jobs
  FOR ALL USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

CREATE POLICY "users_own_usage" ON user_usage
  FOR ALL USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

-- ─── Función RPC: Incrementar uso ─────────────────
CREATE OR REPLACE FUNCTION increment_usage(p_user_id TEXT, p_month TEXT)
RETURNS VOID AS $$
BEGIN
  INSERT INTO user_usage (user_id, month, count)
  VALUES (p_user_id, p_month, 1)
  ON CONFLICT (user_id, month)
  DO UPDATE SET count = user_usage.count + 1;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ─── Vista: Dashboard de administración ───────────
CREATE OR REPLACE VIEW admin_stats AS
SELECT
  COUNT(DISTINCT user_id)                             AS total_users,
  COUNT(*)                                            AS total_jobs,
  COUNT(*) FILTER (WHERE status = 'completed')        AS completed_jobs,
  COUNT(*) FILTER (WHERE status = 'failed')           AS failed_jobs,
  AVG(EXTRACT(EPOCH FROM (completed_at - started_at)))
    FILTER (WHERE status = 'completed')               AS avg_processing_seconds,
  DATE_TRUNC('day', created_at)                       AS day
FROM summary_jobs
GROUP BY DATE_TRUNC('day', created_at)
ORDER BY day DESC;
