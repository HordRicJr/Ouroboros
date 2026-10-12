"use client";

import React, { useEffect, useState, useCallback } from "react";

interface UniverseInfo {
  id: string;
  seed: number;
  tick: number;
  date: string;
  year: number;
  day_of_year: number;
  clans_count: number;
  languages_count: number;
  technologies_known: number;
  active_wars_count: number;
  chronicles_count: number;
  active_disasters_count: number;
  sacred_sites_count: number;
  settlements_count: number;
  legal_codes_count: number;
  trials_count: number;
  trade_routes_count: number;
  expeditions_count: number;
  currencies_count: number;
  kingdoms_count: number;
  wonders_count: number;
  civilization_phase: string;
  ouroboros_cycle: number;
  notables_count: number;
  ai_budget: {
    total_calls: number;
    max_total_calls: number;
    calls_this_tick: number;
    max_calls_per_tick: number;
  };
}

interface Notable {
  id: number;
  name: string;
  sex: string;
  age: number;
  alive: boolean;
  cell: [number, number];
  title: string;
  memories_count: number;
}

interface Settlement {
  id: number;
  name: string;
  tier: number;
  tier_title: string;
  buildings: string[];
  food_stores: number;
  defense_bonus: number;
}

interface TradeRoute {
  id: number;
  name: string;
  primary_good: string;
  distance: number;
  volume_traded: number;
}

interface Chronicle {
  year: number;
  tick: number;
  title: string;
  text: string;
  epoch: string;
}

export default function Home() {
  const [universe, setUniverse] = useState<UniverseInfo | null>(null);
  const [notables, setNotables] = useState<Notable[]>([]);
  const [settlements, setSettlements] = useState<Settlement[]>([]);
  const [tradeRoutes, setTradeRoutes] = useState<TradeRoute[]>([]);
  const [chronicles, setChronicles] = useState<Chronicle[]>([]);
  const [selectedNotable, setSelectedNotable] = useState<Notable | null>(null);
  const [chatQuestion, setChatQuestion] = useState("");
  const [chatHistory, setChatHistory] = useState<{ sender: string; text: string }[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [stepping, setStepping] = useState(false);
  const [activeTab, setActiveTab] = useState<"overview" | "notables" | "civilization" | "chronicles">("overview");

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://13-49-23-84.sslip.io";

  const refreshAll = useCallback(async () => {
    try {
      const [resU, resN, resS, resT, resC] = await Promise.all([
        fetch(`${apiUrl}/universes/main`),
        fetch(`${apiUrl}/universes/main/notables`),
        fetch(`${apiUrl}/universes/main/settlements`),
        fetch(`${apiUrl}/universes/main/trade`),
        fetch(`${apiUrl}/universes/main/chronicles`),
      ]);

      if (resU.ok) setUniverse(await resU.json());
      if (resN.ok) {
        const notabs: Notable[] = await resN.json();
        setNotables(notabs);
        if (!selectedNotable && notabs.length > 0) setSelectedNotable(notabs[0]);
      }
      if (resS.ok) setSettlements(await resS.json());
      if (resT.ok) {
        const tData = await resT.json();
        setTradeRoutes(tData.routes || []);
      }
      if (resC.ok) setChronicles(await resC.json());
    } catch (err) {
      console.error("Erreur de synchronisation avec l'API Ouroboros:", err);
    }
  }, [apiUrl, selectedNotable]);

  useEffect(() => {
    refreshAll();
    const interval = setInterval(refreshAll, 10000);
    return () => clearInterval(interval);
  }, [refreshAll]);

  const handleStep = async (days: number) => {
    setStepping(true);
    try {
      await fetch(`${apiUrl}/universes/main/step`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ days }),
      });
      await refreshAll();
    } catch (e) {
      console.error(e);
    } finally {
      setStepping(false);
    }
  };

  const handleAskNotable = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedNotable || !chatQuestion.trim() || chatLoading) return;

    const q = chatQuestion.trim();
    setChatQuestion("");
    setChatHistory((prev) => [...prev, { sender: "Voyageur", text: q }]);
    setChatLoading(true);

    try {
      const res = await fetch(`${apiUrl}/universes/main/notables/${selectedNotable.id}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, mock: false }),
      });
      const data = await res.json();
      setChatHistory((prev) => [
        ...prev,
        { sender: selectedNotable.name, text: data.answer || "..." },
      ]);
    } catch {
      setChatHistory((prev) => [
        ...prev,
        { sender: "Système", text: "Le notable est silencieux pour le moment." },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  const getPhaseColor = (phase?: string) => {
    switch (phase) {
      case "Aube": return "#38bdf8";
      case "Ascension": return "#4ade80";
      case "Apogée": return "#fbbf24";
      case "Crise": return "#f87171";
      case "Renaissance": return "#c084fc";
      default: return "#94a3b8";
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
      {/* Top Navbar */}
      <header
        style={{
          borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
          background: "rgba(10, 10, 16, 0.85)",
          backdropFilter: "blur(12px)",
          position: "sticky",
          top: 0,
          zIndex: 50,
          padding: "1rem 2rem",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <div
            style={{
              width: "38px",
              height: "38px",
              borderRadius: "50%",
              background: "linear-gradient(135deg, #a855f7, #3b82f6)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: "900",
              fontSize: "1.2rem",
              boxShadow: "0 0 15px rgba(168, 85, 247, 0.4)",
            }}
          >
            ♾️
          </div>
          <div>
            <h1
              style={{
                margin: 0,
                fontSize: "1.25rem",
                letterSpacing: "0.08em",
                fontFamily: "'Cinzel', serif",
                background: "linear-gradient(to right, #f8fafc, #cbd5e1)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
              }}
            >
              OUROBOROS
            </h1>
            <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
              Simulateur Récursif de Civilisations
            </span>
          </div>
        </div>

        {/* Global Cycle & Date */}
        <div style={{ display: "flex", alignItems: "center", gap: "1.5rem" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              padding: "0.35rem 0.85rem",
              borderRadius: "20px",
              background: "rgba(255, 255, 255, 0.04)",
              border: `1px solid ${getPhaseColor(universe?.civilization_phase)}`,
            }}
          >
            <span
              style={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                background: getPhaseColor(universe?.civilization_phase),
                boxShadow: `0 0 8px ${getPhaseColor(universe?.civilization_phase)}`,
              }}
            />
            <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "#f8fafc" }}>
              Cycle {universe?.ouroboros_cycle || 1} — {universe?.civilization_phase || "Aube"}
            </span>
          </div>

          <div style={{ fontSize: "0.9rem", color: "#94a3b8" }}>
            Année <strong style={{ color: "#f1f5f9" }}>{universe?.year ?? 0}</strong> (Jour {universe?.day_of_year ?? 0})
          </div>

          {/* Step Time Controls */}
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button
              onClick={() => handleStep(1)}
              disabled={stepping}
              style={{
                background: "rgba(255, 255, 255, 0.05)",
                border: "1px solid rgba(255, 255, 255, 0.15)",
                color: "#f8fafc",
                borderRadius: "8px",
                padding: "0.4rem 0.8rem",
                cursor: stepping ? "not-allowed" : "pointer",
                fontSize: "0.85rem",
                fontWeight: 500,
                transition: "all 0.2s",
              }}
            >
              +1 Jour
            </button>
            <button
              onClick={() => handleStep(30)}
              disabled={stepping}
              style={{
                background: "rgba(59, 130, 246, 0.15)",
                border: "1px solid rgba(59, 130, 246, 0.4)",
                color: "#60a5fa",
                borderRadius: "8px",
                padding: "0.4rem 0.8rem",
                cursor: stepping ? "not-allowed" : "pointer",
                fontSize: "0.85rem",
                fontWeight: 600,
                transition: "all 0.2s",
              }}
            >
              +1 Mois
            </button>
            <button
              onClick={() => handleStep(365)}
              disabled={stepping}
              style={{
                background: "linear-gradient(135deg, #a855f7, #6366f1)",
                border: "none",
                color: "#fff",
                borderRadius: "8px",
                padding: "0.4rem 1rem",
                cursor: stepping ? "not-allowed" : "pointer",
                fontSize: "0.85rem",
                fontWeight: 700,
                boxShadow: "0 0 12px rgba(168, 85, 247, 0.4)",
                transition: "all 0.2s",
              }}
            >
              +1 An ⏳
            </button>
          </div>
        </div>
      </header>

      {/* Main Tabs Navigation */}
      <nav
        style={{
          display: "flex",
          gap: "1.5rem",
          padding: "0.5rem 2rem",
          background: "rgba(15, 15, 22, 0.5)",
          borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
        }}
      >
        {[
          { key: "overview", label: "Vue d&apos;ensemble & Monde", icon: "🌍" },
          { key: "notables", label: "Habitants Notables & Dialogue IA", icon: "👤" },
          { key: "civilization", label: "Institutions, Villes & Commerce", icon: "🏛️" },
          { key: "chronicles", label: "Chroniques & Mémoires Épiques", icon: "📜" },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as typeof activeTab)}
            style={{
              background: "none",
              border: "none",
              borderBottom: activeTab === tab.key ? "2px solid #a855f7" : "2px solid transparent",
              color: activeTab === tab.key ? "#f8fafc" : "#64748b",
              padding: "0.75rem 0.5rem",
              fontSize: "0.95rem",
              fontWeight: activeTab === tab.key ? 600 : 400,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              transition: "all 0.2s",
            }}
          >
            <span>{tab.icon}</span>
            <span>{tab.label}</span>
          </button>
        ))}
      </nav>

      {/* Main Dashboard Workspace */}
      <main style={{ padding: "2rem", flex: 1, maxWidth: "1600px", margin: "0 auto", width: "100%", boxSizing: "border-box" }}>
        {activeTab === "overview" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
            {/* Top Stat Cards Grid */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                gap: "1.25rem",
              }}
            >
              {[
                { label: "Clans Humains", val: universe?.clans_count, color: "#38bdf8", icon: "🏕️" },
                { label: "Habitants Notables", val: universe?.notables_count, color: "#a855f7", icon: "👑" },
                { label: "Bourgs & Hameaux", val: universe?.settlements_count, color: "#4ade80", icon: "🏘️" },
                { label: "Routes Marchandes", val: universe?.trade_routes_count, color: "#facc15", icon: "🐪" },
                { label: "Royaumes Unifiés", val: universe?.kingdoms_count, color: "#f472b6", icon: "⚔️" },
                { label: "Grandes Merveilles", val: universe?.wonders_count, color: "#fb923c", icon: "🏛️" },
                { label: "Lois & Procès", val: `${universe?.legal_codes_count || 0} / ${universe?.trials_count || 0}`, color: "#e879f9", icon: "⚖️" },
                { label: "Budget IA Restant", val: `${(universe?.ai_budget.max_total_calls ?? 0) - (universe?.ai_budget.total_calls ?? 0)} req`, color: "#2dd4bf", icon: "🧠" },
              ].map((card, i) => (
                <div
                  key={i}
                  style={{
                    padding: "1.25rem",
                    borderRadius: "14px",
                    background: "rgba(20, 20, 30, 0.6)",
                    border: "1px solid rgba(255, 255, 255, 0.06)",
                    backdropFilter: "blur(10px)",
                    display: "flex",
                    alignItems: "center",
                    gap: "1rem",
                  }}
                >
                  <div
                    style={{
                      fontSize: "1.8rem",
                      padding: "0.6rem",
                      borderRadius: "12px",
                      background: "rgba(255, 255, 255, 0.03)",
                    }}
                  >
                    {card.icon}
                  </div>
                  <div>
                    <div style={{ fontSize: "0.8rem", color: "#94a3b8" }}>{card.label}</div>
                    <div style={{ fontSize: "1.4rem", fontWeight: 700, color: card.color, marginTop: "0.2rem" }}>
                      {card.val ?? 0}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Middle Section: Settlements & Trade Routes */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
              {/* Settlements Panel */}
              <div
                style={{
                  padding: "1.5rem",
                  borderRadius: "16px",
                  background: "rgba(20, 20, 30, 0.6)",
                  border: "1px solid rgba(255, 255, 255, 0.06)",
                }}
              >
                <h2 style={{ fontSize: "1.1rem", margin: "0 0 1rem 0", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <span>🏘️</span> Colonies & Campements Actifs ({settlements.length})
                </h2>
                <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", maxHeight: "380px", overflowY: "auto" }}>
                  {settlements.map((s) => (
                    <div
                      key={s.id}
                      style={{
                        padding: "1rem",
                        borderRadius: "10px",
                        background: "rgba(255, 255, 255, 0.02)",
                        border: "1px solid rgba(255, 255, 255, 0.04)",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: 600, color: "#f8fafc" }}>{s.name}</div>
                        <div style={{ fontSize: "0.8rem", color: "#38bdf8", marginTop: "0.2rem" }}>
                          Rang {s.tier} : {s.tier_title}
                        </div>
                        <div style={{ fontSize: "0.75rem", color: "#64748b", marginTop: "0.2rem" }}>
                          Bâtiments : {s.buildings.join(", ")}
                        </div>
                      </div>
                      <div style={{ textAlign: "right" }}>
                        <div style={{ fontSize: "0.85rem", color: "#4ade80" }}>🌾 {Math.round(s.food_stores)} vivres</div>
                        <div style={{ fontSize: "0.8rem", color: "#94a3b8" }}>🛡️ Défense +{s.defense_bonus}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Trade Routes Panel */}
              <div
                style={{
                  padding: "1.5rem",
                  borderRadius: "16px",
                  background: "rgba(20, 20, 30, 0.6)",
                  border: "1px solid rgba(255, 255, 255, 0.06)",
                }}
              >
                <h2 style={{ fontSize: "1.1rem", margin: "0 0 1rem 0", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <span>🐪</span> Pistes & Routes Commerciales ({tradeRoutes.length})
                </h2>
                <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", maxHeight: "380px", overflowY: "auto" }}>
                  {tradeRoutes.length === 0 ? (
                    <div style={{ color: "#64748b", fontSize: "0.9rem", textAlign: "center", padding: "2rem" }}>
                      Les premières pistes de caravanes sont en cours d&apos;exploration par les nomades...
                    </div>
                  ) : (
                    tradeRoutes.map((r) => (
                      <div
                        key={r.id}
                        style={{
                          padding: "1rem",
                          borderRadius: "10px",
                          background: "rgba(255, 255, 255, 0.02)",
                          border: "1px solid rgba(255, 255, 255, 0.04)",
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                        }}
                      >
                        <div>
                          <div style={{ fontWeight: 600, color: "#f8fafc" }}>{r.name}</div>
                          <div style={{ fontSize: "0.8rem", color: "#facc15", marginTop: "0.2rem" }}>
                            Denrée : {r.primary_good}
                          </div>
                        </div>
                        <div style={{ textAlign: "right" }}>
                          <div style={{ fontSize: "0.85rem", color: "#94a3b8" }}>📏 {r.distance} lieues</div>
                          <div style={{ fontSize: "0.8rem", color: "#4ade80" }}>📦 {Math.round(r.volume_traded)} échangés</div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Notables & Total Immersion LLM Chat */}
        {activeTab === "notables" && (
          <div style={{ display: "grid", gridTemplateColumns: "350px 1fr", gap: "2rem", height: "700px" }}>
            {/* Notables Sidebar List */}
            <div
              style={{
                borderRadius: "16px",
                background: "rgba(20, 20, 30, 0.6)",
                border: "1px solid rgba(255, 255, 255, 0.06)",
                padding: "1.25rem",
                display: "flex",
                flexDirection: "column",
                overflow: "hidden",
              }}
            >
              <h2 style={{ fontSize: "1.1rem", margin: "0 0 1rem 0" }}>Habitants Notables ({notables.length})</h2>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem", overflowY: "auto", flex: 1 }}>
                {notables.map((n) => (
                  <div
                    key={n.id}
                    onClick={() => {
                      setSelectedNotable(n);
                      setChatHistory([]);
                    }}
                    style={{
                      padding: "0.85rem",
                      borderRadius: "10px",
                      background: selectedNotable?.id === n.id ? "rgba(168, 85, 247, 0.15)" : "rgba(255, 255, 255, 0.02)",
                      border: selectedNotable?.id === n.id ? "1px solid rgba(168, 85, 247, 0.5)" : "1px solid rgba(255, 255, 255, 0.04)",
                      cursor: "pointer",
                      transition: "all 0.2s",
                    }}
                  >
                    <div style={{ fontWeight: 600, color: "#f8fafc" }}>
                      {n.sex === "M" ? "♂" : "♀"} {n.name} ({Math.round(n.age)} ans)
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "#a855f7", marginTop: "0.2rem" }}>
                      {n.title}
                    </div>
                    <div style={{ fontSize: "0.7rem", color: "#64748b", marginTop: "0.2rem" }}>
                      Emplacement : [{n.cell[0]}, {n.cell[1]}]
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Chat Conversation Box */}
            <div
              style={{
                borderRadius: "16px",
                background: "rgba(20, 20, 30, 0.6)",
                border: "1px solid rgba(255, 255, 255, 0.06)",
                display: "flex",
                flexDirection: "column",
                overflow: "hidden",
              }}
            >
              {selectedNotable ? (
                <>
                  <div
                    style={{
                      padding: "1.25rem 1.5rem",
                      borderBottom: "1px solid rgba(255, 255, 255, 0.06)",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <div>
                      <h3 style={{ margin: 0, fontSize: "1.15rem", color: "#f8fafc" }}>{selectedNotable.name}</h3>
                      <div style={{ fontSize: "0.8rem", color: "#a855f7" }}>{selectedNotable.title}</div>
                    </div>
                    <div style={{ fontSize: "0.8rem", color: "#64748b" }}>
                      Immersion totale active • Inférence locale
                    </div>
                  </div>

                  {/* Messages Feed */}
                  <div style={{ flex: 1, padding: "1.5rem", overflowY: "auto", display: "flex", flexDirection: "column", gap: "1rem" }}>
                    {chatHistory.length === 0 ? (
                      <div style={{ color: "#64748b", textAlign: "center", margin: "auto", maxWidth: "400px" }}>
                        Posez une question à cet habitant sur sa vie, ses peurs, ses croyances ou l&apos;état de son clan.
                      </div>
                    ) : (
                      chatHistory.map((msg, i) => (
                        <div
                          key={i}
                          style={{
                            alignSelf: msg.sender === "Voyageur" ? "flex-end" : "flex-start",
                            maxWidth: "75%",
                            padding: "0.85rem 1.15rem",
                            borderRadius: "14px",
                            background: msg.sender === "Voyageur" ? "linear-gradient(135deg, #a855f7, #6366f1)" : "rgba(255, 255, 255, 0.05)",
                            border: msg.sender === "Voyageur" ? "none" : "1px solid rgba(255, 255, 255, 0.08)",
                            color: "#f8fafc",
                            lineHeight: "1.5",
                          }}
                        >
                          <div style={{ fontSize: "0.75rem", fontWeight: 700, marginBottom: "0.25rem", color: msg.sender === "Voyageur" ? "#f1f5f9" : "#a855f7" }}>
                            {msg.sender}
                          </div>
                          <div>{msg.text}</div>
                        </div>
                      ))
                    )}
                    {chatLoading && (
                      <div style={{ alignSelf: "flex-start", color: "#a855f7", fontSize: "0.9rem", fontStyle: "italic" }}>
                        {selectedNotable.name} médite et formule sa réponse...
                      </div>
                    )}
                  </div>

                  {/* Prompt Input Form */}
                  <form
                    onSubmit={handleAskNotable}
                    style={{
                      padding: "1rem 1.5rem",
                      borderTop: "1px solid rgba(255, 255, 255, 0.06)",
                      display: "flex",
                      gap: "0.75rem",
                    }}
                  >
                    <input
                      type="text"
                      value={chatQuestion}
                      onChange={(e) => setChatQuestion(e.target.value)}
                      placeholder={`Parler à ${selectedNotable.name}...`}
                      style={{
                        flex: 1,
                        padding: "0.85rem 1.25rem",
                        borderRadius: "10px",
                        border: "1px solid rgba(255, 255, 255, 0.12)",
                        background: "rgba(0, 0, 0, 0.3)",
                        color: "#f8fafc",
                        fontSize: "0.95rem",
                        outline: "none",
                      }}
                    />
                    <button
                      type="submit"
                      disabled={chatLoading || !chatQuestion.trim()}
                      style={{
                        padding: "0.85rem 1.5rem",
                        borderRadius: "10px",
                        background: "linear-gradient(135deg, #a855f7, #6366f1)",
                        border: "none",
                        color: "#fff",
                        fontWeight: 600,
                        cursor: chatLoading || !chatQuestion.trim() ? "not-allowed" : "pointer",
                      }}
                    >
                      Envoyer
                    </button>
                  </form>
                </>
              ) : (
                <div style={{ margin: "auto", color: "#64748b" }}>Sélectionnez un habitant notable</div>
              )}
            </div>
          </div>
        )}

        {/* Chronicles & Historical Legends */}
        {activeTab === "chronicles" && (
          <div
            style={{
              borderRadius: "16px",
              background: "rgba(20, 20, 30, 0.6)",
              border: "1px solid rgba(255, 255, 255, 0.06)",
              padding: "2rem",
            }}
          >
            <h2 style={{ fontSize: "1.3rem", margin: "0 0 1.5rem 0", fontFamily: "'Cinzel', serif" }}>
              Rouleau des Chroniques Historiques
            </h2>
            {chronicles.length === 0 ? (
              <div style={{ color: "#64748b", textAlign: "center", padding: "3rem" }}>
                Aucune chronique majeure n&apos;a encore été scellée par les bardes pour cette première année.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
                {chronicles.map((c, i) => (
                  <div
                    key={i}
                    style={{
                      padding: "1.25rem 1.5rem",
                      borderRadius: "12px",
                      background: "rgba(255, 255, 255, 0.02)",
                      border: "1px solid rgba(255, 255, 255, 0.05)",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                      <span style={{ fontWeight: 700, color: "#facc15", fontSize: "1.1rem" }}>{c.title}</span>
                      <span style={{ fontSize: "0.8rem", color: "#64748b" }}>Année {c.year} • {c.epoch}</span>
                    </div>
                    <p style={{ margin: 0, color: "#cbd5e1", lineHeight: 1.6 }}>{c.text}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Institutions & Realms Tab */}
        {activeTab === "civilization" && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
            <div
              style={{
                borderRadius: "16px",
                background: "rgba(20, 20, 30, 0.6)",
                border: "1px solid rgba(255, 255, 255, 0.06)",
                padding: "1.5rem",
              }}
            >
              <h3 style={{ margin: "0 0 1rem 0", fontSize: "1.1rem" }}>⚖️ Justice & Lois Coutumières</h3>
              <p style={{ color: "#94a3b8", fontSize: "0.9rem" }}>
                Codes de lois actifs : <strong>{universe?.legal_codes_count ?? 0}</strong>
              </p>
              <p style={{ color: "#94a3b8", fontSize: "0.9rem" }}>
                Procès & Ordalies tenus : <strong>{universe?.trials_count ?? 0}</strong>
              </p>
            </div>

            <div
              style={{
                borderRadius: "16px",
                background: "rgba(20, 20, 30, 0.6)",
                border: "1px solid rgba(255, 255, 255, 0.06)",
                padding: "1.5rem",
              }}
            >
              <h3 style={{ margin: "0 0 1rem 0", fontSize: "1.1rem" }}>👑 Royaumes & Alliances</h3>
              <p style={{ color: "#94a3b8", fontSize: "0.9rem" }}>
                Royaumes unifiés : <strong>{universe?.kingdoms_count ?? 0}</strong>
              </p>
              <p style={{ color: "#94a3b8", fontSize: "0.9rem" }}>
                Monnaies forgées : <strong>{universe?.currencies_count ?? 0}</strong>
              </p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
