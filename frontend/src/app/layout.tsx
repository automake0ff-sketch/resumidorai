import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { dark } from "@clerk/themes";
import "../styles/globals.css";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://resumidorai.com";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "ResumidorAI — Resume videos de YouTube con IA",
    template: "%s | ResumidorAI",
  },
  description:
    "Pega cualquier URL de YouTube y obtén un resumen inteligente con puntos clave y capítulos en segundos. Impulsado por Claude AI.",
  keywords: [
    "resumir video youtube",
    "resumen youtube IA",
    "resumidor de videos",
    "youtube summarizer español",
    "inteligencia artificial resumen",
    "claude AI resumen",
    "puntos clave youtube",
  ],
  authors: [{ name: "ResumidorAI" }],
  creator: "ResumidorAI",
  openGraph: {
    title: "ResumidorAI — Resume videos de YouTube con IA",
    description:
      "Resúmenes inteligentes de YouTube con puntos clave y capítulos en segundos. Impulsado por Claude AI.",
    url: SITE_URL,
    siteName: "ResumidorAI",
    type: "website",
    locale: "es_ES",
    images: [
      {
        url: `${SITE_URL}/og-image.png`,
        width: 1200,
        height: 630,
        alt: "ResumidorAI — Resume videos de YouTube con IA",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "ResumidorAI — Resume videos de YouTube con IA",
    description: "Resúmenes inteligentes de YouTube en segundos",
    images: [`${SITE_URL}/og-image.png`],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true },
  },
  alternates: {
    canonical: SITE_URL,
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider
      appearance={{ baseTheme: dark }}
      signInUrl="/sign-in"
      signUpUrl="/sign-up"
      afterSignInUrl="/dashboard"
      afterSignUpUrl="/dashboard"
    >
      <html lang="es">
        <head>
          <link rel="icon" href="/favicon.ico" sizes="any" />
          <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
        </head>
        <body>{children}</body>
      </html>
    </ClerkProvider>
  );
}
