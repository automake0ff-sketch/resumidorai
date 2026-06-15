const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function createApiClient(token: string) {
  const headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };

  return {
    async submitSummary(data: {
      url: string;
      language?: string;
      length?: "short" | "medium" | "detailed";
      include_chapters?: boolean;
      include_key_points?: boolean;
    }) {
      const res = await fetch(`${API_URL}/api/summaries`, {
        method: "POST", headers, body: JSON.stringify(data),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Error al enviar");
      }
      return res.json();
    },

    async getSummary(jobId: string) {
      const res = await fetch(`${API_URL}/api/summaries/${jobId}`, { headers });
      if (!res.ok) throw new Error("No encontrado");
      return res.json();
    },

    async listSummaries(page = 1, perPage = 20) {
      const res = await fetch(`${API_URL}/api/summaries?page=${page}&per_page=${perPage}`, { headers });
      if (!res.ok) throw new Error("Error al cargar");
      return res.json();
    },

    async getUsage() {
      const res = await fetch(`${API_URL}/api/summaries/usage/me`, { headers });
      if (!res.ok) throw new Error("Error");
      return res.json();
    },

    async deleteSummary(jobId: string) {
      await fetch(`${API_URL}/api/summaries/${jobId}`, { method: "DELETE", headers });
    },
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;
