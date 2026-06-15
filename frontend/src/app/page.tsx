import Link from "next/link";
import { SignedIn, SignedOut } from "@clerk/nextjs";

export default function HomePage() {
  return (
    <main style={{ minHeight: "100vh", fontFamily: "system-ui, sans-serif" }}>
      {/* Nav */}
      <nav style={{ padding: "1rem 2rem", display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "0.5px solid #eee" }}>
        <span style={{ fontWeight: 600, fontSize: 18 }}>VideoSummary AI</span>
        <div style={{ display: "flex", gap: 12 }}>
          <Link href="/pricing" style={{ fontSize: 14, color: "#666", textDecoration: "none" }}>Precios</Link>
          <SignedOut>
            <Link href="/sign-in" style={{ fontSize: 14, padding: "6px 16px", border: "1px solid #ddd", borderRadius: 8, textDecoration: "none", color: "#333" }}>Entrar</Link>
            <Link href="/sign-up" style={{ fontSize: 14, padding: "6px 16px", background: "#111", color: "#fff", borderRadius: 8, textDecoration: "none" }}>Empezar gratis</Link>
          </SignedOut>
          <SignedIn>
            <Link href="/dashboard" style={{ fontSize: 14, padding: "6px 16px", background: "#111", color: "#fff", borderRadius: 8, textDecoration: "none" }}>Dashboard</Link>
          </SignedIn>
        </div>
      </nav>

      {/* Hero */}
      <section style={{ maxWidth: 720, margin: "0 auto", padding: "6rem 2rem", textAlign: "center" }}>
        <h1 style={{ fontSize: "clamp(2rem, 5vw, 3.5rem)", fontWeight: 700, lineHeight: 1.15, marginBottom: "1.5rem" }}>
          Resume cualquier video de YouTube en segundos
        </h1>
        <p style={{ fontSize: "1.125rem", color: "#555", lineHeight: 1.7, marginBottom: "2.5rem", maxWidth: 520, margin: "0 auto 2.5rem" }}>
          Pega la URL, elige el idioma y obtén un resumen inteligente con puntos clave, capítulos y más. Impulsado por Claude AI.
        </p>
        <SignedOut>
          <Link href="/sign-up" style={{ display: "inline-block", padding: "14px 32px", background: "#111", color: "#fff", borderRadius: 10, textDecoration: "none", fontSize: 16, fontWeight: 500 }}>
            Empezar gratis — sin tarjeta
          </Link>
        </SignedOut>
        <SignedIn>
          <Link href="/dashboard" style={{ display: "inline-block", padding: "14px 32px", background: "#111", color: "#fff", borderRadius: 10, textDecoration: "none", fontSize: 16, fontWeight: 500 }}>
            Ir al dashboard →
          </Link>
        </SignedIn>
      </section>

      {/* Features */}
      <section style={{ maxWidth: 900, margin: "0 auto", padding: "0 2rem 6rem", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: 24 }}>
        {[
          { icon: "⚡", title: "Rápido", desc: "Resumen en menos de 30 segundos para la mayoría de videos." },
          { icon: "🌍", title: "Multiidioma", desc: "Genera el resumen en español, inglés, francés y más." },
          { icon: "📌", title: "Puntos clave", desc: "Extrae los insights más valiosos de forma automática." },
          { icon: "🎬", title: "Capítulos", desc: "Detecta y organiza las secciones temáticas del video." },
        ].map((f) => (
          <div key={f.title} style={{ padding: "1.5rem", border: "0.5px solid #eee", borderRadius: 12 }}>
            <div style={{ fontSize: 28, marginBottom: 12 }}>{f.icon}</div>
            <h3 style={{ fontWeight: 600, marginBottom: 8 }}>{f.title}</h3>
            <p style={{ fontSize: 14, color: "#666", lineHeight: 1.6, margin: 0 }}>{f.desc}</p>
          </div>
        ))}
      </section>
    </main>
  );
}
