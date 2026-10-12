import type { Metadata } from "next";
import { Cinzel, Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const cinzel = Cinzel({ subsets: ["latin"], weight: ["600", "700"], variable: "--font-cinzel", display: "swap" });

export const metadata: Metadata = {
  title: "Ouroboros — Simulateur récursif d'univers",
  description:
    "Tableau de bord en temps réel de la simulation Ouroboros : écologie, habitants notables, civilisations et cycles.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className={`${inter.variable} ${cinzel.variable}`}>
      <body style={{ fontFamily: "var(--font-inter), system-ui, sans-serif" }}>{children}</body>
    </html>
  );
}
