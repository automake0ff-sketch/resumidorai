import Link from "next/link";
import { SignedIn, SignedOut } from "@clerk/nextjs";

const plans = [
  {
    name: "Free",
    price: "0",
    desc: "Para probar el servicio",
    limit: "5 resúmenes / mes",
    features: ["Resumen principal", "Puntos clave", "Idioma español e inglés"],
    cta: "Empezar gratis",
    href: "/sign-up",
    highlight: false,
  },
  {
    name: "Starter",
    price: "9",
    desc: "Para uso regular",
    limit: "50 resúmenes / mes",
    features: ["Todo de Free", "Capítulos automáticos", "Todos los idiomas", "Longitud personalizable"],
    cta: "Elegir Starter",
    href: "/sign-up",
    highlight: true,
  },
  {
    name: "Pro",
    price: "29",
    desc: "Para equipos y creadores",
    limit: "200 resúmenes / mes",
    features: ["Todo de Starter", "Transcripción completa", "Exportar a texto", "Soporte prioritario"],
    cta: "Elegir Pro",
    href: "/sign-up",
    highlight: false,
  },
];

export default function PricingPage() {
  return (
    <div style={{ minHeight: "100vh", background: "#0a0a0a", color: "#f5f5f5", fontFamily: "Inter, system-ui, sans-serif" }}>
      <nav style={{ borderBottom: "1px solid #1a1a1a", padding: "0 2rem", height: 60, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <Link href="/" style={{ fontWeight: 700, fontSize: 18, letterSpacing: "-0.03em", color: "#f5f5f5", textDecoration: "none" }}>
          resumidor<span style={{ color: "#22c55e" }}>AI</span>
        </Link>
        <div style={{ display: "flex", gap: 12 }}>
          <SignedOut>
            <Link href="/sign-in" style={{ fontSize: 14, padding: "7px 16px", border: "1px solid #222", borderRadius: 8, color: "#ccc", textDecoration: "none" }}>Entrar</Link>
          </SignedOut>
          <SignedIn>
            <Link href="/dashboard" style={{ fontSize: 14, padding: "7px 16px", background: "#22c55e", color: "#000", borderRadius: 8, fontWeight: 600, textDecoration: "none" }}>Dashboard</Link>
          </SignedIn>
        </div>
      </nav>

      <section style={{ maxWidth: 900, margin: "0 auto", padding: "5rem 2rem" }}>
        <div style={{ textAlign: "center", marginBottom: "4rem" }}>
          <h1 style={{ fontSize: "clamp(2rem, 5vw, 3rem)", fontWeight: 800, letterSpacing: "-0.04em", marginBottom: 16 }}>Planes simples y transparentes</h1>
          <p style={{ fontSize: 16, color: "#888" }}>Empieza gratis. Actualiza cuando necesites más.</p>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 20 }}>
          {plans.map((plan) => (
            <div key={plan.name} style={{
              background: plan.highlight ? "#0d1f17" : "#111",
              border: `1px solid ${plan.highlight ? "#22c55e" : "#1a1a1a"}`,
              borderRadius: 16,
              padding: "2rem",
              position: "relative",
            }}>
              {plan.highlight && (
                <div style={{ position: "absolute", top: -12, left: "50%", transform: "translateX(-50%)", background: "#22c55e", color: "#000", fontSize: 11, fontWeight: 700, padding: "3px 12px", borderRadius: 20, letterSpacing: "0.06em" }}>
                  MÁS POPULAR
                </div>
              )}
              <p style={{ fontSize: 13, color: "#666", marginBottom: 8 }}>{plan.desc}</p>
              <p style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>{plan.name}</p>
              <div style={{ display: "flex", alignItems: "baseline", gap: 4, marginBottom: 8 }}>
                <span style={{ fontSize: 36, fontWeight: 800, letterSpacing: "-0.04em" }}>${plan.price}</span>
                <span style={{ fontSize: 13, color: "#666" }}>/mes</span>
              </div>
              <p style={{ fontSize: 13, color: plan.highlight ? "#22c55e" : "#888", marginBottom: 24, fontWeight: 500 }}>{plan.limit}</p>
              <ul style={{ listStyle: "none", marginBottom: 28 }}>
                {plan.features.map((f) => (
                  <li key={f} style={{ display: "flex", gap: 8, marginBottom: 10, alignItems: "center" }}>
                    <span style={{ color: "#22c55e", fontSize: 14 }}>✓</span>
                    <span style={{ fontSize: 13, color: "#aaa" }}>{f}</span>
                  </li>
                ))}
              </ul>
              <Link href={plan.href} style={{
                display: "block",
                textAlign: "center",
                padding: "11px 20px",
                background: plan.highlight ? "#22c55e" : "transparent",
                border: plan.highlight ? "none" : "1px solid #333",
                color: plan.highlight ? "#000" : "#ccc",
                borderRadius: 8,
                fontWeight: 600,
                fontSize: 14,
                textDecoration: "none",
              }}>
                {plan.cta}
              </Link>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
