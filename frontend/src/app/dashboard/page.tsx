"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useAuth } from "@clerk/nextjs";
import { useSearchParams, useRouter } from "next/navigation";
import { createApiClient, type Job, type Usage } from "@/lib/api";

function fmtDuration(s?: number) {
  if (!s) return "";
  const m = Math.floor(s / 60), h = Math.floor(m / 60);
  return h ? `${h}h ${m % 60}m` : `${m}m`;
}

function fmtTime(s: number) {
  const m = Math.floor(s / 60), sec = s % 60;
  return `${m}:${String(sec).padStart(2, "0")}`;
}

function timeAgo(iso?: string) {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "ahora";
  if (m < 60) return `hace ${m}m`;
  const h = Math.floor(m / 60);
  if (h < 24) return `hace ${h}h`;
  return `hace ${Math.floor(h / 24)}d`;
}

const STATUS: Record<string, { label: string; color: string; bg: string }> = {
  pending:    { label: "En cola",     color: "#eab308", bg: "rgba(234,179,8,0.12)" },
  processing: { label: "Procesando…", color: "#3b82f6", bg: "rgba(59,130,246,0.12)" },
  completed:  { label: "Listo",       color: "#22c55e", bg: "rgba(34,197,94,0.12)" },
  failed:     { label: "Error",       color: "#ef4444", bg: "rgba(239,68,68,0.12)" },
};

export default function DashboardPage() {
  const { getToken } = useAuth();
  const searchParams = useSearchParams();
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [language, setLanguage] = useState("es");
  const [length, setLength] = useState<"short" | "medium" | "detailed">("medium");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selected, setSelected] = useState<Job | null>(null);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(true);
  const [checkoutBanner, setCheckoutBanner] = useState<"success" | "cancelled" | null>(null);
  const [portalLoading, setPortalLoading] = useState(false);
  const pollers = useRef<Record<string, ReturnType<typeof setInterval>>>({});

  const getApi = useCallback(async () => {
    const token = await getToken();
    if (!token) throw new Error("No autenticado");
    return createApiClient(token);
  }, [getToken]);

  useEffect(() => {
    loadAll();
    // capture ref value at effect time
    const currentPollers = pollers.current;
    return () => {
      Object.values(currentPollers).forEach(clearInterval);
    };
  }, []);

  // Tras volver de Stripe Checkout, el webhook de Stripe puede tardar unos
  // segundos en activar el plan. Reintentamos getUsage varias veces para no
  // mostrarle al usuario "límite alcanzado" justo después de pagar.
  useEffect(() => {
    const checkout = searchParams.get("checkout");
    if (!checkout) return;

    setCheckoutBanner(checkout === "success" ? "success" : "cancelled");
    router.replace("/dashboard");

    if (checkout === "success") {
      let attempts = 0;
      const maxAttempts = 6; // ~18s de margen para que el webhook procese
      const interval = setInterval(async () => {
        attempts++;
        try {
          const client = await getApi();
          const fresh = await client.getUsage();
          setUsage(fresh);
          if (fresh.plan === "starter" || fresh.plan === "pro" || attempts >= maxAttempts) {
            clearInterval(interval);
          }
        } catch {
          if (attempts >= maxAttempts) clearInterval(interval);
        }
      }, 5000); // Reduced from 3s to 5s — saves ~40% polling requests
      return () => clearInterval(interval);
    }
  }, [searchParams, router, getApi]);

  useEffect(() => {
    if (!checkoutBanner) return;
    const timeout = setTimeout(() => setCheckoutBanner(null), 8000);
    return () => clearTimeout(timeout);
  }, [checkoutBanner]);

  async function loadAll() {
    setLoading(true);
    try {
      const client = await getApi();
      const [jobsData, usageData] = await Promise.all([
        client.listSummaries(),
        client.getUsage(),
      ]);
      setJobs(jobsData);
      setUsage(usageData);
      jobsData.forEach((j) => {
        if (j.status === "pending" || j.status === "processing") startPolling(j.job_id);
      });
    } catch (e) {
      console.error("Error cargando datos:", e);
    } finally {
      setLoading(false);
    }
  }

  function startPolling(jobId: string) {
    if (pollers.current[jobId]) return;
    const MAX_POLL_MS = 10 * 60 * 1000; // 10 minutes timeout
    const startedAt = Date.now();
    pollers.current[jobId] = setInterval(async () => {
      // Auto-stop polling after 10 minutes to prevent infinite loops
      if (Date.now() - startedAt > MAX_POLL_MS) {
        clearInterval(pollers.current[jobId]);
        delete pollers.current[jobId];
        setJobs((prev) =>
          prev.map((j) =>
            j.job_id === jobId && (j.status === "pending" || j.status === "processing")
              ? { ...j, status: "failed" as const, error: "Tiempo de espera agotado (10 min)" }
              : j
          )
        );
        return;
      }
      try {
        const client = await getApi();
        const updated = await client.getSummary(jobId);
        setJobs((prev) => prev.map((j) => (j.job_id === jobId ? updated : j)));
        if (updated.status === "completed" || updated.status === "failed") {
          clearInterval(pollers.current[jobId]);
          delete pollers.current[jobId];
          setSelected((prev) => (prev?.job_id === jobId ? updated : prev));
          const client2 = await getApi();
          setUsage(await client2.getUsage());
        }
      } catch {
        clearInterval(pollers.current[jobId]);
        delete pollers.current[jobId];
      }
    }, 5000); // 5s interval — saves ~40% polling requests vs original 3s
  }

  async function submit() {
    const trimmed = url.trim();
    if (!trimmed) return;

    const isYouTube = /(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/)|youtu\.be\/)[\w-]{11}/.test(trimmed);
    if (!isYouTube) {
      setError("Pega una URL válida de YouTube (youtube.com o youtu.be)");
      return;
    }

    setSubmitting(true);
    setError("");
    try {
      const client = await getApi();
      const job = await client.submitSummary({
        url: trimmed, language, length,
        include_chapters: true, include_key_points: true, include_transcript: true,
      });
      const newJob: Job = { ...job, url: trimmed, language, status: "pending" as const };
      setJobs((prev) => [newJob, ...prev]);
      setUrl("");
      startPolling(job.job_id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error al enviar");
    } finally {
      setSubmitting(false);
    }
  }

  async function openBillingPortal() {
    setPortalLoading(true);
    try {
      const client = await getApi();
      const { checkout_url } = await client.openBillingPortal();
      window.location.href = checkout_url;
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "No se pudo abrir el portal de facturación");
      setPortalLoading(false);
    }
  }

  async function deleteJob(jobId: string, e: React.MouseEvent) {
    e.stopPropagation();
    try {
      const client = await getApi();
      await client.deleteSummary(jobId);
      setJobs((prev) => prev.filter((j) => j.job_id !== jobId));
      if (selected?.job_id === jobId) setSelected(null);
      clearInterval(pollers.current[jobId]);
      delete pollers.current[jobId];
    } catch {}
  }

  function copySummary() {
    if (!selected?.summary) return;
    navigator.clipboard.writeText(
      [
        selected.title,
        "",
        "RESUMEN",
        selected.summary,
        "",
        selected.key_points?.length
          ? "PUNTOS CLAVE\n" + selected.key_points.map((p) => `• ${p}`).join("\n")
          : "",
      ].join("\n").trim()
    );
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const pct = usage ? Math.min(100, (usage.summaries_this_month / usage.summaries_limit) * 100) : 0;
  const atLimit = usage ? usage.summaries_this_month >= usage.summaries_limit : false;

  return (
    <div>
      {checkoutBanner === "success" && (
        <div style={{ background: "rgba(34,197,94,0.1)", border: "1px solid #22c55e", borderRadius: 10, padding: "12px 16px", marginBottom: 16, fontSize: 13, color: "#4ade80" }}>
          ✓ Pago confirmado. Estamos activando tu plan, puede tardar unos segundos en reflejarse abajo.
        </div>
      )}
      {checkoutBanner === "cancelled" && (
        <div style={{ background: "rgba(234,179,8,0.1)", border: "1px solid #eab308", borderRadius: 10, padding: "12px 16px", marginBottom: 16, fontSize: 13, color: "#eab308" }}>
          Pago cancelado. Puedes intentarlo de nuevo cuando quieras desde la página de precios.
        </div>
      )}
      {/* Usage bar */}
      {usage && (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", background: "#111", border: "1px solid #1a1a1a", borderRadius: 10, padding: "12px 16px", marginBottom: 20 }}>
          <div>
            <span style={{ fontSize: 11, color: "#555", textTransform: "uppercase", letterSpacing: "0.07em", fontWeight: 600 }}>
              Plan {usage.plan === "trial" ? "de prueba" : usage.plan === "none" ? "sin suscripción" : usage.plan}
            </span>
            <p style={{ fontSize: 14, fontWeight: 500, marginTop: 2, color: pct > 80 ? "#ef4444" : "#e5e5e5" }}>
              {usage.summaries_this_month} / {usage.summaries_limit} resúmenes este mes
            </p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ width: 120, height: 4, background: "#1a1a1a", borderRadius: 2, overflow: "hidden" }}>
              <div style={{ height: "100%", borderRadius: 2, background: pct > 80 ? "#ef4444" : "#22c55e", width: `${pct}%`, transition: "width 0.5s ease" }} />
            </div>
            {(usage.plan === "starter" || usage.plan === "pro") && (
              <button
                onClick={openBillingPortal}
                disabled={portalLoading}
                style={{ fontSize: 12, padding: "5px 12px", background: "transparent", border: "1px solid #333", color: "#aaa", borderRadius: 6, fontWeight: 500, cursor: "pointer", whiteSpace: "nowrap", fontFamily: "inherit" }}
              >
                {portalLoading ? "Abriendo…" : "Gestionar suscripción"}
              </button>
            )}
            {atLimit && (
              <a href="/pricing" style={{ fontSize: 12, padding: "5px 12px", background: "#22c55e", color: "#000", borderRadius: 6, fontWeight: 600, textDecoration: "none", whiteSpace: "nowrap" }}>
                Actualizar
              </a>
            )}
          </div>
        </div>
      )}

      {/* Submit form */}
      <div style={{ background: "#111", border: "1px solid #1a1a1a", borderRadius: 12, padding: "1.5rem", marginBottom: 20 }}>
        <p style={{ fontSize: 13, color: "#555", marginBottom: 12 }}>Pega la URL de un video de YouTube</p>
        <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
          <input
            type="url"
            placeholder="https://youtube.com/watch?v=..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !submitting && !atLimit && submit()}
            disabled={atLimit}
            style={{
              flex: 1, background: "#0d0d0d", border: "1px solid #222", borderRadius: 8,
              color: "#f5f5f5", fontSize: 14, padding: "10px 14px", outline: "none", fontFamily: "inherit",
              transition: "border-color 0.15s",
            }}
          />
          <button
            onClick={submit}
            disabled={submitting || !url.trim() || atLimit}
            style={{
              background: "#22c55e", color: "#000", border: "none", borderRadius: 8,
              padding: "10px 20px", fontWeight: 600, fontSize: 14, cursor: "pointer",
              opacity: submitting || !url.trim() || atLimit ? 0.5 : 1,
              whiteSpace: "nowrap", fontFamily: "inherit", transition: "opacity 0.15s",
            }}
          >
            {submitting ? "Enviando…" : "Resumir →"}
          </button>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {(["es", "en", "fr", "pt", "de", "it"] as const).map((lang) => (
            <button
              key={lang}
              onClick={() => setLanguage(lang)}
              style={{
                background: language === lang ? "#1a2a1a" : "transparent",
                border: `1px solid ${language === lang ? "#22c55e" : "#222"}`,
                color: language === lang ? "#22c55e" : "#666",
                borderRadius: 6, padding: "5px 12px", fontSize: 12, cursor: "pointer", fontFamily: "inherit",
              }}
            >
              {{ es: "🇪🇸 ES", en: "🇬🇧 EN", fr: "🇫🇷 FR", pt: "🇵🇹 PT", de: "🇩🇪 DE", it: "🇮🇹 IT" }[lang]}
            </button>
          ))}
          <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
            {(["short", "medium", "detailed"] as const).map((l) => (
              <button
                key={l}
                onClick={() => setLength(l)}
                style={{
                  background: length === l ? "#1a2a1a" : "transparent",
                  border: `1px solid ${length === l ? "#22c55e" : "#222"}`,
                  color: length === l ? "#22c55e" : "#666",
                  borderRadius: 6, padding: "5px 12px", fontSize: 12, cursor: "pointer", fontFamily: "inherit",
                }}
              >
                {{ short: "Corto", medium: "Medio", detailed: "Detallado" }[l]}
              </button>
            ))}
          </div>
        </div>
        {error && (
          <p style={{ color: "#ef4444", fontSize: 13, marginTop: 10, padding: "8px 12px", background: "rgba(239,68,68,0.08)", borderRadius: 6 }}>
            ⚠ {error.includes("/pricing") ? (
              <>
                {error.split("/pricing")[0]}
                <a href="/pricing" style={{ color: "#ef4444", textDecoration: "underline" }}>página de precios</a>
                {error.split("/pricing")[1]}
              </>
            ) : error}
          </p>
        )}
        {atLimit && (
          <p style={{ color: "#eab308", fontSize: 13, marginTop: 10 }}>
            {usage?.plan === "trial" || usage?.plan === "none"
              ? <>Tu prueba gratuita terminó. <a href="/pricing" style={{ color: "#22c55e", textDecoration: "underline" }}>Elige un plan para seguir resumiendo</a></>
              : <>Límite mensual alcanzado. <a href="/pricing" style={{ color: "#22c55e", textDecoration: "underline" }}>Mejora tu plan</a></>}
          </p>
        )}
      </div>

      {/* Main content */}
      {loading ? (
        <div style={{ textAlign: "center", padding: "4rem", color: "#555" }}>
          <div style={{ width: 24, height: 24, border: "2px solid #333", borderTopColor: "#22c55e", borderRadius: "50%", animation: "spin 0.8s linear infinite", margin: "0 auto 12px" }} />
          <p style={{ fontSize: 14 }}>Cargando resúmenes…</p>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: selected ? "minmax(280px, 340px) 1fr" : "1fr", gap: 16, alignItems: "start" }}>

          {/* Job list */}
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {jobs.length === 0 ? (
              <div style={{ textAlign: "center", padding: "5rem 2rem", color: "#444" }}>
                <p style={{ fontSize: 40, marginBottom: 16 }}>🎬</p>
                <p style={{ fontSize: 15, fontWeight: 500, marginBottom: 8, color: "#666" }}>Sin resúmenes todavía</p>
                <p style={{ fontSize: 13, lineHeight: 1.6 }}>Pega una URL de YouTube arriba<br />y empieza a resumir en segundos</p>
              </div>
            ) : jobs.map((job) => {
              const st = STATUS[job.status] || STATUS.pending;
              const isActive = selected?.job_id === job.job_id;
              return (
                <div
                  key={job.job_id}
                  onClick={() => job.status === "completed" && setSelected(isActive ? null : job)}
                  style={{
                    background: isActive ? "#0d1f17" : "#111",
                    border: `1px solid ${isActive ? "#22c55e" : "#1a1a1a"}`,
                    borderRadius: 10, padding: "12px 14px",
                    cursor: job.status === "completed" ? "pointer" : "default",
                    transition: "all 0.15s",
                  }}
                >
                  <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                    {job.thumbnail && (
                      <img src={job.thumbnail} alt="" style={{ width: 68, height: 44, objectFit: "cover", borderRadius: 5, flexShrink: 0 }} />
                    )}
                    {!job.thumbnail && (
                      <div style={{ width: 68, height: 44, background: "#1a1a1a", borderRadius: 5, flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20 }}>🎬</div>
                    )}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
                        <span style={{ fontSize: 11, fontWeight: 600, color: st.color, background: st.bg, padding: "2px 7px", borderRadius: 4 }}>
                          {st.label}
                        </span>
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <span style={{ fontSize: 11, color: "#444" }}>{timeAgo(job.created)}</span>
                          <button
                            onClick={(e) => deleteJob(job.job_id, e)}
                            style={{ background: "transparent", border: "none", color: "#444", fontSize: 16, cursor: "pointer", padding: "0 2px", lineHeight: 1, fontFamily: "inherit" }}
                            title="Eliminar"
                          >×</button>
                        </div>
                      </div>
                      <p style={{ fontSize: 13, fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: "#e0e0e0", marginBottom: 2 }}>
                        {job.title || new URL(job.url).hostname}
                      </p>
                      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                        {job.duration_seconds && (
                          <span style={{ fontSize: 11, color: "#444" }}>{fmtDuration(job.duration_seconds)}</span>
                        )}
                        <span style={{ fontSize: 11, color: "#444" }}>{job.language.toUpperCase()}</span>
                      </div>
                      {job.status === "failed" && (
                        <p style={{ fontSize: 11, color: "#ef4444", marginTop: 4 }}>{job.error}</p>
                      )}
                      {(job.status === "pending" || job.status === "processing") && (
                        <div style={{ marginTop: 8, height: 2, background: "#1a1a1a", borderRadius: 1, overflow: "hidden" }}>
                          <div style={{ height: "100%", width: "30%", background: "#3b82f6", borderRadius: 1, animation: "shimmer 1.5s ease-in-out infinite" }} />
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Detail panel */}
          {selected && (
            <div style={{ background: "#111", border: "1px solid #1a1a1a", borderRadius: 12, padding: "1.5rem", position: "sticky", top: 72, maxHeight: "calc(100vh - 100px)", overflowY: "auto" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
                <div style={{ flex: 1, minWidth: 0, marginRight: 12 }}>
                  <p style={{ fontSize: 15, fontWeight: 600, lineHeight: 1.4, color: "#f0f0f0" }}>{selected.title}</p>
                  <div style={{ display: "flex", gap: 10, marginTop: 4 }}>
                    {selected.duration_seconds && <span style={{ fontSize: 12, color: "#555" }}>{fmtDuration(selected.duration_seconds)}</span>}
                    <span style={{ fontSize: 12, color: "#555" }}>{selected.language.toUpperCase()}</span>
                  </div>
                </div>
                <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
                  <button
                    onClick={copySummary}
                    style={{ background: "#1a1a1a", border: "1px solid #2a2a2a", color: copied ? "#22c55e" : "#888", borderRadius: 6, padding: "6px 12px", fontSize: 12, cursor: "pointer", fontFamily: "inherit", transition: "color 0.2s" }}
                  >
                    {copied ? "✓ Copiado" : "Copiar"}
                  </button>
                  <button
                    onClick={() => setSelected(null)}
                    style={{ background: "transparent", border: "1px solid #222", color: "#555", borderRadius: 6, padding: "6px 10px", fontSize: 18, cursor: "pointer", lineHeight: 1, fontFamily: "inherit" }}
                  >×</button>
                </div>
              </div>

              {/* Summary */}
              {selected.summary && (
                <section style={{ marginBottom: 24 }}>
                  <p style={{ fontSize: 10, color: "#22c55e", fontWeight: 700, letterSpacing: "0.1em", marginBottom: 10 }}>RESUMEN</p>
                  <p style={{ fontSize: 14, color: "#b0b0b0", lineHeight: 1.8 }}>{selected.summary}</p>
                </section>
              )}

              {/* Key points */}
              {selected.key_points && selected.key_points.length > 0 && (
                <section style={{ marginBottom: 24 }}>
                  <p style={{ fontSize: 10, color: "#22c55e", fontWeight: 700, letterSpacing: "0.1em", marginBottom: 10 }}>PUNTOS CLAVE</p>
                  <ul style={{ listStyle: "none" }}>
                    {selected.key_points.map((pt, i) => (
                      <li key={i} style={{ display: "flex", gap: 10, marginBottom: 10, alignItems: "flex-start" }}>
                        <span style={{ color: "#22c55e", flexShrink: 0, marginTop: 2, fontSize: 12 }}>✓</span>
                        <span style={{ fontSize: 13, color: "#999", lineHeight: 1.65 }}>{pt}</span>
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              {/* Transcript */}
              {selected.transcript && (
                <section style={{ marginBottom: 24 }}>
                  <p style={{ fontSize: 10, color: "#22c55e", fontWeight: 700, letterSpacing: "0.1em", marginBottom: 10 }}>TRANSCRIPCIÓN</p>
                  <p style={{ fontSize: 13, color: "#888", lineHeight: 1.8, maxHeight: 200, overflowY: "auto", padding: "8px 12px", background: "#0a0a0a", borderRadius: 6 }}>{selected.transcript}</p>
                </section>
              )}

              {/* Chapters */}
              {selected.chapters && selected.chapters.length > 0 && (
                <section style={{ marginBottom: 20 }}>
                  <p style={{ fontSize: 10, color: "#22c55e", fontWeight: 700, letterSpacing: "0.1em", marginBottom: 10 }}>CAPÍTULOS</p>
                  <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                    {selected.chapters.map((ch, i) => (
                      <div key={i} style={{ display: "flex", gap: 12 }}>
                        <span style={{ fontSize: 11, color: "#444", fontFamily: "monospace", minWidth: 40, paddingTop: 1 }}>{fmtTime(ch.start_seconds)}</span>
                        <div>
                          <p style={{ fontSize: 13, fontWeight: 500, color: "#d0d0d0", marginBottom: 2 }}>{ch.title}</p>
                          <p style={{ fontSize: 12, color: "#666", lineHeight: 1.55 }}>{ch.summary}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              <div style={{ borderTop: "1px solid #1a1a1a", paddingTop: 16, marginTop: 4 }}>
                <a href={selected.url} target="_blank" rel="noopener noreferrer"
                  style={{ fontSize: 12, color: "#444", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 4 }}>
                  ↗ Ver en YouTube
                </a>
              </div>
            </div>
          )}
        </div>
      )}

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes shimmer {
          0% { transform: translateX(-200%); }
          100% { transform: translateX(500%); }
        }
      `}</style>
    </div>
  );
}
