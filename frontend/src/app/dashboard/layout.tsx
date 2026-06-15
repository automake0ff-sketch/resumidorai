import { UserButton } from "@clerk/nextjs";
import Link from "next/link";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ minHeight: "100vh", background: "#0a0a0a", color: "#f5f5f5", fontFamily: "Inter, system-ui, sans-serif" }}>
      {/* Top nav */}
      <header style={{
        borderBottom: "1px solid #1a1a1a",
        padding: "0 1.5rem",
        height: 56,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        position: "sticky",
        top: 0,
        background: "rgba(10,10,10,0.95)",
        backdropFilter: "blur(12px)",
        zIndex: 50,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 32 }}>
          <Link href="/" style={{ fontWeight: 700, fontSize: 17, letterSpacing: "-0.03em", color: "#f5f5f5", textDecoration: "none" }}>
            resumidor<span style={{ color: "#22c55e" }}>AI</span>
          </Link>
          <nav style={{ display: "flex", gap: 4 }}>
            <Link href="/dashboard" style={{ fontSize: 13, color: "#888", padding: "5px 12px", borderRadius: 6, textDecoration: "none" }}>
              Resúmenes
            </Link>
            <Link href="/pricing" style={{ fontSize: 13, color: "#888", padding: "5px 12px", borderRadius: 6, textDecoration: "none" }}>
              Planes
            </Link>
          </nav>
        </div>
        <UserButton afterSignOutUrl="/" />
      </header>

      <main style={{ maxWidth: 860, margin: "0 auto", padding: "2rem 1.5rem" }}>
        {children}
      </main>
    </div>
  );
}
