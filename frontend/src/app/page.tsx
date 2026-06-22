import type { Metadata } from "next";
import Link from "next/link";
import { SignedIn, SignedOut, UserButton } from "@clerk/nextjs";

export const metadata: Metadata = {
  title: "ResumidorAI — Resume videos de YouTube con IA",
  description:
    "Pega cualquier URL de YouTube y obtén un resumen inteligente con puntos clave y capítulos en segundos. Gratis. Sin tarjeta.",
};

const YEAR = new Date().getFullYear();

export default function HomePage() {
  return (
    <div style={{ minHeight: "100vh", background: "#0a0a0a", color: "#f5f5f5", fontFamily: "Inter, system-ui, sans-serif" }}>

      {/* NAV */}
      <nav
        role="navigation"
        aria-label="Navegación principal"
        style={{ borderBottom: "1px solid #1a1a1a", padding: "0 2rem", height: 60, display: "flex", alignItems: "center", justifyContent: "space-between", position: "sticky", top: 0, background: "rgba(10,10,10,0.9)", backdropFilter: "blur(12px)", zIndex: 50 }}
      >
        <Link href="/" aria-label="ResumidorAI inicio" style={{ fontWeight: 700, fontSize: 18, letterSpacing: "-0.03em", textDecoration: "none", color: "#f5f5f5" }}>
          resumidor<span style={{ color: "#22c55e" }}>AI</span>
        </Link>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Link href="/pricing" style={{ fontSize: 14, color: "#888", textDecoration: "none" }}>Precios</Link>
          <SignedOut>
            <Link href="/sign-in" style={{ fontSize: 14, padding: "7px 16px", border: "1px solid #222", borderRadius: 8, color: "#ccc", textDecoration: "none" }}>
              Entrar
            </Link>
            <Link href="/sign-up" style={{ fontSize: 14, padding: "7px 16px", background: "#22c55e", color: "#000", borderRadius: 8, fontWeight: 600, textDecoration: "none" }}>
              Empezar gratis
            </Link>
          </SignedOut>
          <SignedIn>
            <Link href="/dashboard" style={{ fontSize: 14, padding: "7px 16px", background: "#22c55e", color: "#000", borderRadius: 8, fontWeight: 600, textDecoration: "none" }}>
              Dashboard
            </Link>
            <UserButton />
          </SignedIn>
        </div>
      </nav>

      {/* HERO */}
      <main>
        <section style={{ maxWidth: 760, margin: "0 auto", padding: "7rem 2rem 5rem", textAlign: "center" }}>
          <div
            role="status"
            aria-label="Disponible gratis sin tarjeta"
            style={{ display: "inline-block", background: "#14532d", color: "#22c55e", fontSize: 12, fontWeight: 600, padding: "4px 12px", borderRadius: 20, marginBottom: 28, letterSpacing: "0.05em" }}
          >
            GRATIS · SIN TARJETA
          </div>
          <h1 style={{ fontSize: "clamp(2.4rem, 6vw, 4rem)", fontWeight: 800, lineHeight: 1.1, letterSpacing: "-0.04em", marginBottom: 24 }}>
            Resume cualquier video<br />
            <span style={{ color: "#22c55e" }}>en segundos</span>
          </h1>
          <p style={{ fontSize: "1.15rem", color: "#888", lineHeight: 1.7, maxWidth: 500, margin: "0 auto 40px" }}>
            Pega la URL de YouTube y obtén un resumen completo con puntos clave y capítulos. Impulsado por Claude AI.
          </p>
          <SignedOut>
            <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
              <Link href="/sign-up" style={{ padding: "14px 32px", background: "#22c55e", color: "#000", borderRadius: 10, fontWeight: 700, fontSize: 16, textDecoration: "none" }}>
                Empezar gratis →
              </Link>
              <Link href="/pricing" style={{ padding: "14px 32px", border: "1px solid #222", color: "#ccc", borderRadius: 10, fontSize: 16, textDecoration: "none" }}>
                Ver precios
              </Link>
            </div>
          </SignedOut>
          <SignedIn>
            <Link href="/dashboard" style={{ display: "inline-block", padding: "14px 32px", background: "#22c55e", color: "#000", borderRadius: 10, fontWeight: 700, fontSize: 16, textDecoration: "none" }}>
              Ir al dashboard →
            </Link>
          </SignedIn>
        </section>

        {/* DEMO CARD */}
        <section aria-label="Ejemplo de resultado" style={{ maxWidth: 700, margin: "0 auto 6rem", padding: "0 2rem" }}>
          <div style={{ background: "#111", border: "1px solid #222", borderRadius: 16, padding: "2rem", position: "relative", overflow: "hidden" }}>
            <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 2, background: "linear-gradient(90deg, #22c55e, #16a34a)" }} />
            <p style={{ fontSize: 12, color: "#555", marginBottom: 16, fontWeight: 600, letterSpacing: "0.08em" }}>EJEMPLO DE RESULTADO</p>
            <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
              <div aria-hidden="true" style={{ width: 80, height: 52, background: "#1a1a1a", borderRadius: 6, flexShrink: 0 }} />
              <div>
                <p style={{ fontWeight: 600, marginBottom: 4 }}>Cómo funciona la IA en 2025</p>
                <p style={{ fontSize: 12, color: "#555" }}>42 min · YouTube</p>
              </div>
            </div>
            <div style={{ marginBottom: 20 }}>
              <p style={{ fontSize: 12, color: "#22c55e", fontWeight: 600, marginBottom: 8, letterSpacing: "0.06em" }}>RESUMEN</p>
              <p style={{ fontSize: 14, color: "#aaa", lineHeight: 1.7 }}>
                El video explora los fundamentos de los modelos de lenguaje grandes y su impacto en industrias clave. El autor argumenta que la IA generativa representa un cambio de paradigma, no solo una mejora incremental…
              </p>
            </div>
            <div>
              <p style={{ fontSize: 12, color: "#22c55e", fontWeight: 600, marginBottom: 8, letterSpacing: "0.06em" }}>PUNTOS CLAVE</p>
              {[
                "Los LLMs aprenden patrones estadísticos del lenguaje, no reglas explícitas",
                "El scaling de parámetros sigue siendo la estrategia más efectiva",
                "La alineación es el problema técnico más crítico del momento",
              ].map((pt, i) => (
                <div key={i} style={{ display: "flex", gap: 8, marginBottom: 8, alignItems: "flex-start" }}>
                  <span aria-hidden="true" style={{ color: "#22c55e", flexShrink: 0, marginTop: 2 }}>✓</span>
                  <p style={{ fontSize: 13, color: "#888" }}>{pt}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* FEATURES */}
        <section aria-label="Características" style={{ maxWidth: 900, margin: "0 auto 6rem", padding: "0 2rem" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16 }}>
            {[
              { icon: "⚡", title: "Rápido", desc: "Resumen listo en menos de 30 segundos para la mayoría de videos" },
              { icon: "🌍", title: "Multiidioma", desc: "Español, inglés, francés, portugués, alemán e italiano" },
              { icon: "📌", title: "Puntos clave", desc: "Extrae los 5-8 insights más importantes automáticamente" },
              { icon: "🎬", title: "Capítulos", desc: "Detecta y estructura las secciones temáticas del video" },
            ].map((f) => (
              <article key={f.title} style={{ background: "#111", border: "1px solid #1a1a1a", borderRadius: 12, padding: "1.5rem" }}>
                <div aria-hidden="true" style={{ fontSize: 28, marginBottom: 12 }}>{f.icon}</div>
                <h2 style={{ fontWeight: 600, marginBottom: 6, fontSize: 15 }}>{f.title}</h2>
                <p style={{ fontSize: 13, color: "#666", lineHeight: 1.6 }}>{f.desc}</p>
              </article>
            ))}
          </div>
        </section>
      </main>

      {/* FOOTER */}
      <footer style={{ borderTop: "1px solid #1a1a1a", padding: "2rem", textAlign: "center" }}>
        <p style={{ fontSize: 13, color: "#555" }}>
          © {YEAR} ResumidorAI · Hecho con{" "}
          <a href="https://www.anthropic.com" rel="noopener noreferrer" style={{ color: "#555", textDecoration: "none" }}>Claude AI</a>
        </p>
      </footer>
    </div>
  );
}
