export const metadata = {
  title: "Ouroboros - Dashboard Simulation",
  description: "Tableau de bord de suivi du simulateur récursif d'univers Ouroboros",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr">
      <body style={{ margin: 0, padding: 0, fontFamily: "system-ui, sans-serif", background: "#0a0a0c", color: "#f0f0f5" }}>
        {children}
      </body>
    </html>
  );
}
