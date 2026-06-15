import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <div style={{
      minHeight: "100vh",
      background: "#0a0a0a",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      flexDirection: "column",
      gap: 32,
    }}>
      <a href="/" style={{ fontWeight: 700, fontSize: 20, letterSpacing: "-0.03em", color: "#f5f5f5", textDecoration: "none" }}>
        resumidor<span style={{ color: "#22c55e" }}>AI</span>
      </a>
      <SignUp
        path="/sign-up"
        routing="path"
        signInUrl="/sign-in"
        afterSignUpUrl="/dashboard"
      />
    </div>
  );
}
