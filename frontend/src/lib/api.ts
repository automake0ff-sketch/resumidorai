const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function createApiClient(token: string) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };

  async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const res = await fetch(`${API_URL}${path}`, { ...options, headers });
    if (!res.ok) {
      let message = `Error ${res.status}`;
      try {
        const body = await res.json();
        if (typeof body.detail === "string") {
          message = body.detail;
        } else if (Array.isArray(body.detail)) {
          // FastAPI/Pydantic 422 validation error format
          message = body.detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join(". ") || message;
        }
      } catch {
        // response wasn't JSON, keep default message
      }
      throw new Error(message);
    }
    // 204 No Content
    if (res.status === 204) return undefined as T;
    return res.json();
  }

  return {
    submitSummary: (data: {
      url: string;
      language?: string;
      length?: "short" | "medium" | "detailed";
      include_chapters?: boolean;
      include_key_points?: boolean;
    }) =>
      request<{ job_id: string; status: string }>("/api/summaries", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    getSummary: (jobId: string) =>
      request<Job>(`/api/summaries/${jobId}`),

    listSummaries: (page = 1, perPage = 20) =>
      request<Job[]>(`/api/summaries?page=${page}&per_page=${perPage}`),

    getUsage: () =>
      request<Usage>("/api/summaries/usage/me"),

    deleteSummary: (jobId: string) =>
      request<void>(`/api/summaries/${jobId}`, { method: "DELETE" }),
  };
}

export type Job = {
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

export type Usage = {
  summaries_this_month: number;
  summaries_limit: number;
  plan: string;
};
