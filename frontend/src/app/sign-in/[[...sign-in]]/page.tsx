import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
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
      <SignIn
        path="/sign-in"
        routing="path"
        signUpUrl="/sign-up"
        afterSignInUrl="/dashboard"
      />
    </div>
  );
}
