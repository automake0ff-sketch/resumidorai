import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { dark } from "@clerk/themes";
import "../styles/globals.css";

export const metadata: Metadata = {
  title: "ResumidorAI — Resume videos con IA",
  description: "Pega cualquier URL de YouTube y obtén un resumen inteligente en segundos. Gratis.",
  keywords: ["resumir video", "youtube resumen", "IA", "inteligencia artificial"],
  openGraph: {
    title: "ResumidorAI — Resume videos con IA",
    description: "Resúmenes inteligentes de YouTube en segundos",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider appearance={{ baseTheme: dark }}>
      <html lang="es">
        <body>{children}</body>
      </html>
    </ClerkProvider>
  );
}
