"use client";

import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@clerk/nextjs";
import { UserButton } from "@clerk/nextjs";
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
  created_at: string;
  error?: string;
};

type Usage = {
  summaries_this_month: number;
  summaries_limit: number;
  plan: string;
};

export default function DashboardPage() {
  const { getToken } = useAuth();
  const [url, setUrl] = useState("");
  const [language, setLanguage] = useState("es");
  const [length, setLength] = useState<"short" | "medium" | "detailed">("medium");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const getApi = useCallback(async () => {
    const token = await getToken();
    return createApiClient(token!);
  }, [getToken]);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const api = await getApi();
      const [jobsData, usageData] = await Promise.all([
        api.listSummaries(),
        api.getUsage(),
      ]);
      setJobs(jobsData);
      setUsage(usageData);
    } catch (e) {
      console.error(e);
    }
  }

  async function submitSummary() {
    if (!url.trim()) return;
    setLoading(true);
    setError("");
    try {
      const api = await getApi();
      const job = await api.submitSummary({ url, language, length });
      setJobs((prev) => [job, ...prev]);
      setUrl("");
      pollJob(job.job_id);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function pollJob(jobId: string) {
    const interval = setInterval(async () => {
      try {
        const api = await getApi();
        const updated = await api.getSummary(jobId);
        setJobs((prev) =>
          prev.map((j) => (j.job_id === jobId ? updated : j))
        );
        if (updated.status === "completed" || updated.status === "failed") {
          clearInterval(interval);
          loadData();
        }
      } catch (e) {
        clearInterval(interval);
      }
    }, 3000);
  }

  function formatDuration(s?: number) {
    if (!s) return "";
    const m = Math.floor(s / 60);
    const h = Math.floor(m / 60);
    if (h) return `${h}h ${m % 60}m`;
    return `${m}m`;
  }

  return (
    <div style={{ minHeight: "100vh", background: "var(--color-background-tertiary)", fontFamily: "var(--font-sans)" }}>
      {/* Header */}
      <header style={{ background: "var(--color-background-primary)", borderBottom: "0.5px solid var(--color-border-tertiary)", padding: "0 2rem", height: 56, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontWeight: 500, fontSize: 16 }}>VideoSummary AI</span>
        <UserButton />
      </header>

      <div style={{ maxWidth: 900, margin: "0 auto", padding: "2rem 1rem" }}>
        {/* Usage banner */}
        {usage && (
          <div style={{ background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)", borderRadius: "var(--border-radius-lg)", padding: "1rem 1.25rem", marginBottom: "1.5rem", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div>
              <span style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>Plan {usage.plan} · Este mes</span>
              <div style={{ fontWeight: 500, fontSize: 15, marginTop: 2 }}>
                {usage.summaries_this_month} / {usage.summaries_limit} resúmenes
              </div>
            </div>
            <div style={{ width: 160, height: 6, background: "var(--color-background-secondary)", borderRadius: 3, overflow: "hidden" }}>
              <div style={{ height: "100%", borderRadius: 3, background: usage.summaries_this_month / usage.summaries_limit > 0.8 ? "#E24B4A" : "#1D9E75", width: `${Math.min(100, (usage.summaries_this_month / usage.summaries_limit) * 100)}%` }} />
            </div>
          </div>
        )}

        {/* Submit form */}
        <div style={{ background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)", borderRadius: "var(--border-radius-lg)", padding: "1.5rem", marginBottom: "1.5rem" }}>
          <p style={{ fontSize: 13, color: "var(--color-text-secondary)", marginBottom: 12 }}>Pega la URL de cualquier video de YouTube</p>
          <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
            <input
              type="url"
              placeholder="https://youtube.com/watch?v=..."
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submitSummary()}
              style={{ flex: 1 }}
            />
            <button onClick={submitSummary} disabled={loading || !url.trim()}>
              {loading ? "Enviando..." : "Resumir"}
            </button>
          </div>
          <div style={{ display: "flex", gap: 12 }}>
            <select value={language} onChange={(e) => setLanguage(e.target.value)} style={{ fontSize: 13 }}>
              <option value="es">Español</option>
              <option value="en">English</option>
              <option value="fr">Français</option>
              <option value="pt">Português</option>
            </select>
            <select value={length} onChange={(e) => setLength(e.target.value as any)} style={{ fontSize: 13 }}>
              <option value="short">Corto (~150 palabras)</option>
              <option value="medium">Medio (~300 palabras)</option>
              <option value="detailed">Detallado (~600 palabras)</option>
            </select>
          </div>
          {error && <p style={{ color: "var(--color-text-danger)", fontSize: 13, marginTop: 8 }}>{error}</p>}
        </div>

        {/* Jobs list */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {jobs.map((job) => (
            <div
              key={job.job_id}
              onClick={() => job.status === "completed" && setSelectedJob(job)}
              style={{
                background: "var(--color-background-primary)",
                border: `0.5px solid ${selectedJob?.job_id === job.job_id ? "var(--color-border-info)" : "var(--color-border-tertiary)"}`,
                borderRadius: "var(--border-radius-lg)",
                padding: "1rem 1.25rem",
                cursor: job.status === "completed" ? "pointer" : "default",
                display: "flex",
                gap: 16,
                alignItems: "flex-start",
              }}
            >
              {job.thumbnail && (
                <img src={job.thumbnail} alt="" style={{ width: 80, height: 52, objectFit: "cover", borderRadius: "var(--border-radius-md)", flexShrink: 0 }} />
              )}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                  <StatusBadge status={job.status} />
                  {job.duration_seconds && (
                    <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>{formatDuration(job.duration_seconds)}</span>
                  )}
                </div>
                <p style={{ fontSize: 14, fontWeight: 500, margin: "0 0 4px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {job.title || job.url}
                </p>
                {job.status === "completed" && job.summary && (
                  <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: 0, overflow: "hidden", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}>
                    {job.summary}
                  </p>
                )}
                {job.status === "failed" && (
                  <p style={{ fontSize: 13, color: "var(--color-text-danger)", margin: 0 }}>{job.error}</p>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Detail panel */}
        {selectedJob && selectedJob.status === "completed" && (
          <div style={{ marginTop: "1.5rem", background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)", borderRadius: "var(--border-radius-lg)", padding: "1.5rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1.25rem" }}>
              <h2 style={{ fontSize: 18, fontWeight: 500, margin: 0 }}>{selectedJob.title}</h2>
              <button onClick={() => setSelectedJob(null)} style={{ fontSize: 13 }}>Cerrar</button>
            </div>

            {selectedJob.summary && (
              <div style={{ marginBottom: "1.25rem" }}>
                <p style={{ fontSize: 12, color: "var(--color-text-secondary)", marginBottom: 8, fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.05em" }}>Resumen</p>
                <p style={{ fontSize: 15, lineHeight: 1.7, margin: 0 }}>{selectedJob.summary}</p>
              </div>
            )}

            {selectedJob.key_points && selectedJob.key_points.length > 0 && (
              <div style={{ marginBottom: "1.25rem" }}>
                <p style={{ fontSize: 12, color: "var(--color-text-secondary)", marginBottom: 8, fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.05em" }}>Puntos clave</p>
                <ul style={{ margin: 0, paddingLeft: "1.25rem" }}>
                  {selectedJob.key_points.map((pt, i) => (
                    <li key={i} style={{ fontSize: 14, lineHeight: 1.6, marginBottom: 6 }}>{pt}</li>
                  ))}
                </ul>
              </div>
            )}

            {selectedJob.chapters && selectedJob.chapters.length > 0 && (
              <div>
                <p style={{ fontSize: 12, color: "var(--color-text-secondary)", marginBottom: 8, fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.05em" }}>Capítulos</p>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {selectedJob.chapters.map((ch, i) => (
                    <div key={i} style={{ display: "flex", gap: 12, fontSize: 13 }}>
                      <span style={{ color: "var(--color-text-secondary)", fontVariantNumeric: "tabular-nums", minWidth: 40 }}>{Math.floor(ch.start_seconds / 60)}:{String(ch.start_seconds % 60).padStart(2, "0")}</span>
                      <div>
                        <span style={{ fontWeight: 500 }}>{ch.title}</span>
                        <p style={{ margin: "2px 0 0", color: "var(--color-text-secondary)", lineHeight: 1.5 }}>{ch.summary}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, { bg: string; color: string; label: string }> = {
    pending:    { bg: "var(--color-background-warning)", color: "var(--color-text-warning)", label: "En cola" },
    processing: { bg: "var(--color-background-info)",    color: "var(--color-text-info)",    label: "Procesando..." },
    completed:  { bg: "var(--color-background-success)", color: "var(--color-text-success)", label: "Listo" },
    failed:     { bg: "var(--color-background-danger)",  color: "var(--color-text-danger)",  label: "Error" },
  };
  const s = styles[status] || styles.pending;
  return (
    <span style={{ fontSize: 12, padding: "2px 8px", borderRadius: "var(--border-radius-md)", background: s.bg, color: s.color, fontWeight: 500 }}>
      {s.label}
    </span>
  );
}
