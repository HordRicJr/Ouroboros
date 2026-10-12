"use client";

import { useEffect, useState } from "react";

export default function Home() {
  const [health, setHealth] = useState<string>("Vérification...");
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://13-49-23-84.sslip.io";

  useEffect(() => {
    fetch(`${apiUrl}/api/health`)
      .then((res) => res.json())
      .then((data) => setHealth(data.api === "ok" ? "Connecté au moteur" : "Hors ligne"))
      .catch(() => setHealth("Serveur inaccessible"));
  }, [apiUrl]);

  return (
    <main style={{ padding: "3rem", maxWidth: "900px", margin: "0 auto" }}>
      <header style={{ marginBottom: "2rem" }}>
        <h1 style={{ fontSize: "2.5rem", fontWeight: "700", color: "#e2e8f0" }}>Ouroboros Simulation</h1>
        <p style={{ color: "#94a3b8" }}>Simulateur récursif d'univers avec émergence écologique et habitants notables.</p>
      </header>

      <div style={{ display: "grid", gap: "1.5rem", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))" }}>
        <section style={{ padding: "1.5rem", borderRadius: "12px", background: "#13131a", border: "1px solid #27273a" }}>
          <h2 style={{ fontSize: "1.2rem", color: "#38bdf8" }}>État de l'API</h2>
          <p style={{ fontSize: "1.1rem", margin: "0.5rem 0" }}>Statut : <strong>{health}</strong></p>
          <small style={{ color: "#64748b" }}>URL : {apiUrl}</small>
        </section>

        <section style={{ padding: "1.5rem", borderRadius: "12px", background: "#13131a", border: "1px solid #27273a" }}>
          <h2 style={{ fontSize: "1.2rem", color: "#a855f7" }}>Moteur & Modèle IA</h2>
          <p style={{ margin: "0.5rem 0" }}>Inférence locale : <strong>llama.cpp (Qwen 4B GGUF)</strong></p>
          <small style={{ color: "#64748b" }}>Port local EC2 : 8080 (ouroboros-llm)</small>
        </section>
      </div>
    </main>
  );
}
