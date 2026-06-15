"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useAuth } from "@clerk/nextjs";
import { createApiClient } from "@/lib/api";

type Job = {
  job_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  url: string;
  title?: string;
  thumbnail?: string;
  duration_seconds?: number;
  summary?: string;
  key_points?: string[];
  chapters?: { start_seconds: number; title: string; summary: string }[];
  language: string;
  created?: string;
  error?: string;
};

type Usage = { summaries_this_month: number; summaries_limit: number; plan: string };

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

const STATUS_CONFIG = {
  pending:    { label: "En cola",      color: "#eab308", bg: "rgba(234,179,8,0.1)" },
  processing: { label: "Procesando…",  color: "#3b82f6", bg: "rgba(59,130,246,0.1)" },
  completed:  { label: "Listo",        color: "#22c55e", bg: "rgba(34,197,94,0.1)" },
  failed:     { label: "Error",        color: "#ef4444", bg: "rgba(239,68,68,0.1)" },
};

export default function DashboardPage() {
  const { getToken } = useAuth();
  const [url, setUrl] = useState("");
  const [language, setLanguage] = useState("es");
  const [length, setLength] = useState<"short" | "medium" | "detailed">("medium");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selected, setSelected] = useState<Job | null>(null);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const pollers = useRef<Record<string, NodeJS.Timeout>>({});

  const api = useCallback(async () => {
    const token = await getToken();
    return createApiClient(token!);
  }, [getToken]);

  useEffect(() => {
    loadAll();
    return () => Object.values(pollers.current).forEach(clearInterval);
  }, []);

  async function loadAll() {
    try {
      const client = await api();
      const [jobsData, usageData] = await Promise.all([client.listSummaries(), client.getUsage()]);
      setJobs(jobsData);
      setUsage(usageData);
      // Resume polling for unfinished jobs
      jobsData.forEach((j: Job) => {
        if (j.status === "pending" || j.status === "processing") startPolling(j.job_id);
      });
    } catch { /* silent */ }
  }

  function startPolling(jobId: string) {
    if (pollers.current[jobId]) return;
    pollers.current[jobId] = setInterval(async () => {
      try {
        const client = await api();
        const updated = await client.getSummary(jobId);
        setJobs(prev => prev.map(j => j.job_id === jobId ? updated : j));
        if (updated.status === "completed" || updated.status === "failed") {
          clearInterval(pollers.current[jobId]);
          delete pollers.current[jobId];
          setSelected(prev => prev?.job_id === jobId ? updated : prev);
          const client2 = await api();
          setUsage(await client2.getUsage());
        }
      } catch {
        clearInterval(pollers.current[jobId]);
        delete pollers.current[jobId];
      }
    }, 3000);
  }

  async function submit() {
    if (!url.trim()) return;
    setSubmitting(true);
    setError("");
    try {
      const client = await api();
      const job = await client.submitSummary({ url: url.trim(), language, length, include_chapters: true, include_key_points: true });
      setJobs(prev => [job, ...prev]);
      setUrl("");
      startPolling(job.job_id);
    } catch (e: any) {
      setError(e.message || "Error al enviar");
    } finally {
      setSubmitting(false);
    }
  }

  async function deleteJob(jobId: string, e: React.MouseEvent) {
    e.stopPropagation();
    const client = await api();
    await client.deleteSummary(jobId);
    setJobs(prev => prev.filter(j => j.job_id !== jobId));
    if (selected?.job_id === jobId) setSelected(null);
  }

  function copySummary() {
    if (!selected?.summary) return;
    navigator.clipboard.writeText(selected.summary);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const pct = usage ? Math.min(100, (usage.summaries_this_month / usage.summaries_limit) * 100) : 0;
  const atLimit = usage ? usage.summaries_this_month >= usage.summaries_limit : false;

  return (
    <div>
      {/* Usage bar */}
      {usage && (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", background: "#111", border: "1px solid #1a1a1a", borderRadius: 10, padding: "12px 16px", marginBottom: 20 }}>
          <div>
            <span style={{ fontSize: 12, color: "#555", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600 }}>Plan {usage.plan}</span>
            <p style={{ fontSize: 14, fontWeight: 500, marginTop: 2, color: pct > 80 ? "#ef4444" : "#f5f5f5" }}>
              {usage.summaries_this_month} / {usage.summaries_limit} resúmenes este mes
            </p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ width: 120, height: 4, background: "#1a1a1a", borderRadius: 2, overflow: "hidden" }}>
              <div style={{ height: "100%", borderRadius: 2, background: pct > 80 ? "#ef4444" : "#22c55e", width: `${pct}%`, transition: "width 0.5s" }} />
            </div>
            {atLimit && (
              <a href="/pricing" style={{ fontSize: 12, padding: "5px 12px", background: "#22c55e", color: "#000", borderRadius: 6, fontWeight: 600, textDecoration: "none" }}>Actualizar</a>
            )}
          </div>
        </div>
      )}

      {/* Submit form */}
      <div style={{ background: "#111", border: "1px solid #1a1a1a", borderRadius: 12, padding: "1.5rem", marginBottom: 24 }}>
        <p style={{ fontSize: 13, color: "#555", marginBottom: 12 }}>Pega la URL de un video de YouTube</p>
        <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
          <input
            type="url"
            placeholder="https://youtube.com/watch?v=..."
            value={url}
            onChange={e => setUrl(e.target.value)}
            onKeyDown={e => e.key === "Enter" && !submitting && submit()}
            style={{ flex: 1, background: "#0d0d0d", border: "1px solid #222", borderRadius: 8, color: "#f5f5f5", fontSize: 14, padding: "10px 14px", outline: "none", fontFamily: "inherit" }}
            disabled={atLimit}
          />
          <button
            onClick={submit}
            disabled={submitting || !url.trim() || atLimit}
            style={{ background: "#22c55e", color: "#000", border: "none", borderRadius: 8, padding: "10px 20px", fontWeight: 600, fontSize: 14, cursor: "pointer", opacity: (submitting || !url.trim() || atLimit) ? 0.5 : 1, whiteSpace: "nowrap", fontFamily: "inherit" }}
          >
            {submitting ? "Enviando…" : "Resumir →"}
          </button>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <select value={language} onChange={e => setLanguage(e.target.value)}
            style={{ background: "#0d0d0d", border: "1px solid #222", borderRadius: 6, color: "#aaa", fontSize: 13, padding: "7px 10px", outline: "none", fontFamily: "inherit" }}>
            <option value="es">🇪🇸 Español</option>
            <option value="en">🇬🇧 English</option>
            <option value="fr">🇫🇷 Français</option>
            <option value="pt">🇵🇹 Português</option>
            <option value="de">🇩🇪 Deutsch</option>
          </select>
          <select value={length} onChange={e => setLength(e.target.value as any)}
            style={{ background: "#0d0d0d", border: "1px solid #222", borderRadius: 6, color: "#aaa", fontSize: 13, padding: "7px 10px", outline: "none", fontFamily: "inherit" }}>
            <option value="short">Corto ~150 palabras</option>
            <option value="medium">Medio ~300 palabras</option>
            <option value="detailed">Detallado ~600 palabras</option>
          </select>
        </div>
        {error && <p style={{ color: "#ef4444", fontSize: 13, marginTop: 10 }}>{error}</p>}
        {atLimit && <p style={{ color: "#eab308", fontSize: 13, marginTop: 10 }}>Has alcanzado el límite de tu plan. <a href="/pricing" style={{ color: "#22c55e" }}>Actualiza aquí</a></p>}
      </div>

      {/* Two-column layout: list + detail */}
      <div style={{ display: "grid", gridTemplateColumns: selected ? "320px 1fr" : "1fr", gap: 16, alignItems: "start" }}>

        {/* Job list */}
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {jobs.length === 0 && (
            <div style={{ textAlign: "center", padding: "4rem 2rem", color: "#555" }}>
              <p style={{ fontSize: 32, marginBottom: 12 }}>🎬</p>
              <p style={{ fontSize: 14 }}>Aún no tienes resúmenes.<br />¡Pega una URL arriba para empezar!</p>
            </div>
          )}
          {jobs.map(job => {
            const st = STATUS_CONFIG[job.status];
            const isActive = selected?.job_id === job.job_id;
            return (
              <div
                key={job.job_id}
                onClick={() => job.status === "completed" && setSelected(isActive ? null : job)}
                style={{
                  background: isActive ? "#0d1f17" : "#111",
                  border: `1px solid ${isActive ? "#22c55e" : "#1a1a1a"}`,
                  borderRadius: 10,
                  padding: "12px 14px",
                  cursor: job.status === "completed" ? "pointer" : "default",
                  transition: "all 0.15s",
                }}
              >
                <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                  {job.thumbnail && (
                    <img src={job.thumbnail} alt="" style={{ width: 64, height: 42, objectFit: "cover", borderRadius: 5, flexShrink: 0 }} />
                  )}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
                      <span style={{ fontSize: 11, fontWeight: 600, color: st.color, background: st.bg, padding: "2px 7px", borderRadius: 4 }}>{st.label}</span>
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <span style={{ fontSize: 11, color: "#555" }}>{timeAgo(job.created)}</span>
                        <button onClick={e => deleteJob(job.job_id, e)} style={{ background: "transparent", border: "none", color: "#444", fontSize: 14, cursor: "pointer", padding: "0 2px", lineHeight: 1 }}>×</button>
                      </div>
                    </div>
                    <p style={{ fontSize: 13, fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: "#e5e5e5" }}>
                      {job.title || job.url}
                    </p>
                    {job.duration_seconds && (
                      <p style={{ fontSize: 11, color: "#555", marginTop: 2 }}>{fmtDuration(job.duration_seconds)}</p>
                    )}
                    {job.status === "failed" && (
                      <p style={{ fontSize: 11, color: "#ef4444", marginTop: 4 }}>{job.error}</p>
                    )}
                    {(job.status === "pending" || job.status === "processing") && (
                      <div style={{ marginTop: 6, height: 2, background: "#1a1a1a", borderRadius: 1, overflow: "hidden" }}>
                        <div style={{ height: "100%", width: "40%", background: "#3b82f6", borderRadius: 1, animation: "pulse 1.5s infinite" }} />
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
          <div style={{ background: "#111", border: "1px solid #1a1a1a", borderRadius: 12, padding: "1.5rem", position: "sticky", top: 72 }}>
            {/* Header */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
              <div style={{ flex: 1, minWidth: 0, marginRight: 12 }}>
                <p style={{ fontSize: 15, fontWeight: 600, lineHeight: 1.4 }}>{selected.title}</p>
                {selected.duration_seconds && (
                  <p style={{ fontSize: 12, color: "#555", marginTop: 4 }}>{fmtDuration(selected.duration_seconds)}</p>
                )}
              </div>
              <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
                <button onClick={copySummary} style={{ background: "#1a1a1a", border: "1px solid #222", color: "#aaa", borderRadius: 6, padding: "6px 12px", fontSize: 12, cursor: "pointer", fontFamily: "inherit" }}>
                  {copied ? "✓ Copiado" : "Copiar"}
                </button>
                <button onClick={() => setSelected(null)} style={{ background: "transparent", border: "1px solid #222", color: "#666", borderRadius: 6, padding: "6px 10px", fontSize: 16, cursor: "pointer", lineHeight: 1 }}>×</button>
              </div>
            </div>

            {/* Summary */}
            {selected.summary && (
              <div style={{ marginBottom: 20 }}>
                <p style={{ fontSize: 11, color: "#22c55e", fontWeight: 700, letterSpacing: "0.08em", marginBottom: 10 }}>RESUMEN</p>
                <p style={{ fontSize: 14, color: "#bbb", lineHeight: 1.75 }}>{selected.summary}</p>
              </div>
            )}

            {/* Key points */}
            {selected.key_points && selected.key_points.length > 0 && (
              <div style={{ marginBottom: 20 }}>
                <p style={{ fontSize: 11, color: "#22c55e", fontWeight: 700, letterSpacing: "0.08em", marginBottom: 10 }}>PUNTOS CLAVE</p>
                <ul style={{ listStyle: "none" }}>
                  {selected.key_points.map((pt, i) => (
                    <li key={i} style={{ display: "flex", gap: 8, marginBottom: 8, alignItems: "flex-start" }}>
                      <span style={{ color: "#22c55e", flexShrink: 0, marginTop: 1, fontSize: 13 }}>✓</span>
                      <span style={{ fontSize: 13, color: "#aaa", lineHeight: 1.6 }}>{pt}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Chapters */}
            {selected.chapters && selected.chapters.length > 0 && (
              <div>
                <p style={{ fontSize: 11, color: "#22c55e", fontWeight: 700, letterSpacing: "0.08em", marginBottom: 10 }}>CAPÍTULOS</p>
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {selected.chapters.map((ch, i) => (
                    <div key={i} style={{ display: "flex", gap: 10 }}>
                      <span style={{ fontSize: 11, color: "#555", fontFamily: "monospace", minWidth: 38, marginTop: 1 }}>{fmtTime(ch.start_seconds)}</span>
                      <div>
                        <p style={{ fontSize: 13, fontWeight: 500, color: "#e5e5e5", marginBottom: 2 }}>{ch.title}</p>
                        <p style={{ fontSize: 12, color: "#666", lineHeight: 1.5 }}>{ch.summary}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Source link */}
            <div style={{ marginTop: 20, paddingTop: 20, borderTop: "1px solid #1a1a1a" }}>
              <a href={selected.url} target="_blank" rel="noopener noreferrer"
                style={{ fontSize: 12, color: "#555", textDecoration: "none", display: "flex", alignItems: "center", gap: 4 }}>
                ↗ Ver video original
              </a>
            </div>
          </div>
        )}
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { transform: translateX(-100%); }
          50% { transform: translateX(250%); }
        }
      `}</style>
    </div>
  );
}
