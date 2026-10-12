import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Ouroboros — Simulateur Récursif d'Univers",
  description: "Tableau de bord de suivi en temps réel de la simulation Ouroboros (Écologie, Notables, Civilisations, Cycles)",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Cinzel:wght@500;700;900&family=Inter:wght@300;400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body
        style={{
          margin: 0,
          padding: 0,
          backgroundColor: "#07070a",
          color: "#e2e8f0",
          fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
          minHeight: "100vh",
          overflowX: "hidden",
        }}
      >
        {children}
      </body>
    </html>
  );
}
