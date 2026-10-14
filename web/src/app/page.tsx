"use client";

import {
  Activity,
  BarChart3,
  BookOpenText,
  Castle,
  CheckCircle2,
  ChevronsRight,
  Clock3,
  Coins,
  Crown,
  Download,
  FastForward,
  FlaskConical,
  Gavel,
  GitBranch,
  Globe2,
  Landmark,
  Loader2,
  MapPin,
  MessageSquareText,
  Play,
  Pause,
  RefreshCw,
  Route,
  Scale,
  ScrollText,
  Send,
  Sparkles,
  Sprout,
  Tent,
  User,
  UserRound,
  Users,
  Wheat,
  Shield,
  Brain,
  Infinity as InfinityIcon,
  Wallet,
  RotateCcw,
  Calendar,
  CalendarDays,
  Sun,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { TerritoryMap } from "@/components/TerritoryMap";
import { Empty, Panel, StatCard } from "@/components/ui";
import {
  PHASES,
  PHASE_TONES,
  type AICallLogEntry,
  type BranchMetadataInfo,
  type ChatMessage,
  type Chronicle,
  type Deity,
  type MetricsSummary,
  type Notable,
  type PersonInfo,
  type SeasonalMetric,
  type Settlement,
  type TradeRoute,
  type UniverseInfo,
  type WorldMapInfo,
} from "@/lib/types";

type Tab = "overview" | "notables" | "civilization" | "chronicles" | "research";

const NAV: { key: Tab; label: string; icon: typeof Globe2 }[] = [
  { key: "overview", label: "Vue d'ensemble", icon: Globe2 },
  { key: "notables", label: "Habitants notables", icon: MessageSquareText },
  { key: "civilization", label: "Civilisation", icon: Landmark },
  { key: "chronicles", label: "Chroniques", icon: ScrollText },
  { key: "research", label: "Recherche & Émergence", icon: FlaskConical },
];

const TITLES: Record<Tab, { title: string; sub: string }> = {
  overview: { title: "Vue d'ensemble", sub: "État du monde, territoires et établissements" },
  notables: { title: "Habitants notables", sub: "Dialogue en immersion totale avec les figures de l'univers" },
  civilization: { title: "Civilisation", sub: "Institutions, commerce, croyances et pouvoir" },
  chronicles: { title: "Chroniques", sub: "Mémoire épique consignée par les bardes" },
  research: { title: "Recherche & Émergence (PIMMUR)", sub: "Métriques scientifiques, inégalités Gini, entropie, branches et journal d'appels" },
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function apiFetch(path: string, init?: RequestInit, timeoutMs = 12000): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const url = API_BASE ? `${API_BASE}${path}` : path;
    const res = await fetch(url, {
      ...init,
      signal: controller.signal,
    });
    clearTimeout(timer);
    return res;
  } catch (err) {
    clearTimeout(timer);
    throw err;
  }
}

async function getJson<T>(path: string): Promise<T | null> {
  try {
    const res = await apiFetch(path, { cache: "no-store" }, 10000);
    return res.ok ? ((await res.json()) as T) : null;
  } catch {
    return null;
  }
}

export default function Home() {
  const [tab, setTab] = useState<Tab>("overview");
  const [online, setOnline] = useState<boolean | null>(null);
  const [universe, setUniverse] = useState<UniverseInfo | null>(null);
  const [world, setWorld] = useState<WorldMapInfo | null>(null);
  const [notables, setNotables] = useState<Notable[]>([]);
  const [settlements, setSettlements] = useState<Settlement[]>([]);
  const [routes, setRoutes] = useState<TradeRoute[]>([]);
  const [chronicles, setChronicles] = useState<Chronicle[]>([]);
  const [deities, setDeities] = useState<Deity[]>([]);
  const [people, setPeople] = useState<PersonInfo[]>([]);
  const [selected, setSelected] = useState<Notable | null>(null);
  const [chats, setChats] = useState<Record<number, ChatMessage[]>>({});
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [stepping, setStepping] = useState<number | null>(null);
  const [resetting, setResetting] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState<number>(1);
  const [metricsSummary, setMetricsSummary] = useState<MetricsSummary | null>(null);
  const [latestMetric, setLatestMetric] = useState<SeasonalMetric | null>(null);
  const [metricsHistory, setMetricsHistory] = useState<SeasonalMetric[]>([]);
  const [branchMeta, setBranchMeta] = useState<BranchMetadataInfo | null>(null);
  const [aiLogs, setAiLogs] = useState<AICallLogEntry[]>([]);
  const [forkName, setForkName] = useState("");
  const [forking, setForking] = useState(false);
  const [forkSuccess, setForkSuccess] = useState<string | null>(null);
  const feedRef = useRef<HTMLDivElement>(null);

  const refreshFull = useCallback(async () => {
    const [u, w, n, s, t, c, p, peo, met, logs] = await Promise.all([
      getJson<UniverseInfo>("/universes/main"),
      getJson<WorldMapInfo>("/universes/main/map"),
      getJson<Notable[]>("/universes/main/notables"),
      getJson<Settlement[]>("/universes/main/settlements"),
      getJson<{ routes: TradeRoute[] }>("/universes/main/trade"),
      getJson<Chronicle[]>("/universes/main/chronicles"),
      getJson<{ deities: Deity[] }>("/universes/main/pantheon"),
      getJson<PersonInfo[]>("/universes/main/people"),
      getJson<{ summary: MetricsSummary; latest: SeasonalMetric; history: SeasonalMetric[]; branch: BranchMetadataInfo }>("/universes/main/metrics"),
      getJson<{ total_calls: number; logs: AICallLogEntry[] }>("/universes/main/ai_logs"),
    ]);
    setOnline(u !== null);
    if (u) {
      setUniverse(u);
      if (u.is_running !== undefined) {
        setIsPlaying(Boolean(u.is_running));
      }
      if (u.speed) {
        setSpeed(u.speed);
      }
    }
    if (w) setWorld(w);
    if (n) {
      setNotables(n);
      setSelected((cur) => cur ?? n[0] ?? null);
    }
    if (s) setSettlements(s);
    if (t) setRoutes(t.routes ?? []);
    if (c) setChronicles(c);
    if (p) setDeities(p.deities ?? []);
    if (peo) setPeople(peo);
    if (met) {
      setMetricsSummary(met.summary);
      setLatestMetric(met.latest);
      setMetricsHistory(met.history ?? []);
      setBranchMeta(met.branch ?? null);
    }
    if (logs) {
      setAiLogs(logs.logs ?? []);
    }
  }, []);

  const consecutiveErrorsRef = useRef(0);

  const refreshTick = useCallback(async () => {
    // Health d'abord : léger, ne dépend pas du chargement de l'univers
    try {
      const health = await apiFetch("/api/health", { cache: "no-store" }, 5000);
      if (!health.ok) {
        consecutiveErrorsRef.current += 1;
        if (consecutiveErrorsRef.current >= 5) setOnline(false);
        return;
      }
      setOnline(true);
      consecutiveErrorsRef.current = 0;
    } catch {
      consecutiveErrorsRef.current += 1;
      if (consecutiveErrorsRef.current >= 5) setOnline(false);
      return;
    }

    const u = await getJson<UniverseInfo>("/universes/main");
    if (u) {
      setUniverse((prev) => {
        if (prev && (prev.settlements_count !== u.settlements_count || prev.notables_count !== u.notables_count)) {
          refreshFull();
        }
        return u;
      });
      if (u.is_running !== undefined) {
        setIsPlaying(Boolean(u.is_running));
      }
      if (u.speed) {
        setSpeed(u.speed);
      }
    }
  }, [refreshFull]);

  // Initialisation et rafraîchissement global périodique (espacé pour ne pas saturer l'API 8 Go)
  useEffect(() => {
    refreshFull();
    const id = setInterval(refreshFull, 30000);
    return () => clearInterval(id);
  }, [refreshFull]);

  // Suivi léger H24 — un seul endpoint, rythme modéré
  useEffect(() => {
    if (!isPlaying) return;
    const intervalMs = speed === 30 ? 4000 : speed === 5 ? 5000 : 6000;
    const timer = setInterval(refreshTick, intervalMs);
    return () => clearInterval(timer);
  }, [isPlaying, speed, refreshTick]);

  useEffect(() => {
    feedRef.current?.scrollTo({ top: feedRef.current.scrollHeight, behavior: "smooth" });
  }, [chats, asking, selected]);

  const togglePlay = async () => {
    const nextState = !isPlaying;
    setIsPlaying(nextState);
    try {
      if (nextState) {
        await apiFetch(`/universes/main/play?speed=${speed}`, { method: "POST" });
      } else {
        await apiFetch(`/universes/main/pause`, { method: "POST" });
      }
    } catch (e) {
      console.warn("Erreur togglePlay serveur:", e);
    }
    await refreshTick();
  };

  const changeSpeed = async (newSpeed: number) => {
    setSpeed(newSpeed);
    try {
      await apiFetch(`/universes/main/speed?speed=${newSpeed}`, { method: "POST" });
    } catch (e) {
      console.warn("Erreur changeSpeed:", e);
    }
    await refreshTick();
  };

  const step = async (days: number) => {
    setStepping(days);
    try {
      await apiFetch(`/universes/main/step`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ days }),
      });
      await refreshFull();
    } catch (e) {
      console.error("Erreur de pas:", e);
    } finally {
      setStepping(null);
    }
  };

  const reset = async () => {
    if (!confirm("Voulez-vous réinitialiser l'univers à l'instant originel (Jour 0) ? La simulation H24 reprendra à zéro.")) return;
    setResetting(true);
    try {
      await apiFetch(`/universes/main/reset`, { method: "POST" });
      setSelected(null);
      setChats({});
      await refreshFull();
    } catch (e) {
      console.error("Erreur reset univers:", e);
    } finally {
      setResetting(false);
    }
  };

  const ask = async (e: React.FormEvent) => {
    e.preventDefault();
    const q = question.trim();
    if (!selected || !q || asking) return;
    const pid = selected.id;
    setQuestion("");
    setChats((c) => ({ ...c, [pid]: [...(c[pid] ?? []), { sender: "me", author: "Voyageur", text: q }] }));
    setAsking(true);
    let answer = "Le notable reste silencieux pour le moment.";
    try {
      const res = await apiFetch(`/universes/main/notables/${pid}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, mock: false }),
      }, 15000);
      if (res.ok) {
        const data = await res.json();
        answer = data.response || answer;
        if (data.influence || data.title) {
          setSelected((prev) =>
            prev && prev.id === pid
              ? { ...prev, title: data.title || prev.title, rank_grade: data.rank_grade || prev.rank_grade, influence: data.influence || prev.influence, memories_count: (prev.memories_count || 0) + 1 }
              : prev
          );
        }
      }
    } catch {
      /* réponse par défaut */
    }
    setChats((c) => ({ ...c, [pid]: [...(c[pid] ?? []), { sender: "them", author: selected.name, text: answer }] }));
    setAsking(false);
    refreshFull();
  };

  const handleFork = async (e: React.FormEvent) => {
    e.preventDefault();
    if (forking) return;
    setForking(true);
    setForkSuccess(null);
    try {
      const childName = forkName.trim() || `branch_an_${Math.abs(universe?.year ?? 0)}_${Date.now().toString().slice(-4)}`;
      const res = await apiFetch(`/universes/main/fork`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          child_id: childName,
          description: "Branche contrefactuelle observée depuis l'interface",
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setForkSuccess(`Branche créée avec succès : ${data.child_id}`);
        setForkName("");
        await refreshFull();
      } else {
        const err = await res.json();
        alert(`Erreur de branchement: ${err.detail || "inconnue"}`);
      }
    } catch (e) {
      console.error("Erreur fork:", e);
    } finally {
      setForking(false);
    }
  };

  const handleExportCsv = async () => {
    try {
      const res = await apiFetch("/universes/main/metrics/export?format=csv");
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `ouroboros_metrics_an_${Math.abs(universe?.year ?? 0)}.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      }
    } catch (err) {
      console.error("Erreur téléchargement CSV:", err);
    }
  };

  const phase = universe?.civilization_phase ?? "Aube";
  const tone = PHASE_TONES[phase] ?? "#8b7cf6";
  const budget = universe?.ai_budget;
  const budgetPct = budget ? Math.min(100, (budget.total_calls / Math.max(budget.max_total_calls, 1)) * 100) : 0;
  const messages = selected ? chats[selected.id] ?? [] : [];

  return (
    <div className="app">
      {/* ---------- Sidebar ---------- */}
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <InfinityIcon size={22} />
          </div>
          <div>
            <div className="brand-name" style={{ fontFamily: "var(--font-cinzel), Georgia, serif" }}>
              OUROBOROS
            </div>
            <div className="brand-sub">Simulateur d&apos;univers récursif</div>
          </div>
        </div>

        <nav className="nav">
          <div className="nav-label">Navigation</div>
          {NAV.map(({ key, label, icon: Icon }) => (
            <button key={key} id={`nav-${key}`} className={`nav-item ${tab === key ? "active" : ""}`} onClick={() => setTab(key)}>
              <Icon size={18} />
              <span>{label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="status-row">
            <span className={`dot ${online === null ? "" : online ? "online" : "offline"}`} />
            <strong style={{ color: "var(--text)" }}>
              {online === null ? "Connexion…" : online ? (isPlaying ? "Moteur H24 actif" : "Moteur en pause") : "Moteur inaccessible"}
            </strong>
          </div>
          <div style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>
            {online ? (isPlaying ? "Simulation continue en cours" : "Simulation en pause") : "En attente du moteur de simulation…"}
          </div>
          {budget && (
            <>
              <div className="status-row" style={{ justifyContent: "space-between" }}>
                <span style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>
                  <Brain size={13} /> Budget IA
                </span>
                <span>
                  {budget.total_calls}/{budget.max_total_calls}
                </span>
              </div>
              <div className="progress">
                <div style={{ width: `${budgetPct}%` }} />
              </div>
            </>
          )}
        </div>
      </aside>

      {/* ---------- Content ---------- */}
      <div className="content">
        <header className="topbar">
          <div>
            <h1 className="page-title">{TITLES[tab].title}</h1>
            <p className="page-sub">{TITLES[tab].sub}</p>
          </div>
          <div className="topbar-right">
            <span className="chip" style={{ borderColor: tone }} title={`Cycle ${universe?.ouroboros_cycle ?? 1} : Phase ${phase}`}>
              <Sparkles size={15} style={{ color: tone }} />
              Cycle {universe?.ouroboros_cycle ?? 1} · {phase}
            </span>
            <span className="chip" style={{ borderColor: "rgba(91, 184, 245, 0.4)" }} title={universe?.date || ""}>
              <CalendarDays size={15} style={{ color: "#5bb8f5" }} />
              <strong>
                {universe && universe.year < 0
                  ? `${Math.abs(universe.year)} av. J.-C.`
                  : `An ${universe?.year ?? 0}`}
              </strong>
              <span style={{ color: "var(--text-muted)" }}>·</span>
              <span>Jour {universe?.day ?? (universe ? universe.day_of_year + 1 : 1)} / {universe?.year_length ?? 365}</span>
            </span>
            {universe?.season && (
              <span className="chip" style={{ borderColor: "rgba(242, 184, 75, 0.3)" }}>
                <Sun size={15} style={{ color: "#f2b84b" }} />
                <span>{universe.season}</span>
                <span style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>({Math.round((universe.season_phase ?? 0) * 100)}%)</span>
              </span>
            )}
            {/* BOUTON DÉMARRER / PAUSE SERVEUR H24 */}
            <button
              id="btn-play-pause"
              className={`btn ${isPlaying ? "btn-pause" : "btn-play"}`}
              onClick={togglePlay}
              title={isPlaying ? "Mettre le moteur serveur en pause" : "Démarrer le moteur serveur 24/7"}
            >
              {isPlaying ? (
                <>
                  <Pause size={15} fill="currentColor" />
                  <span>Pause</span>
                  <span className="pulse-dot" />
                </>
              ) : (
                <>
                  <Play size={15} fill="currentColor" />
                  <span>Démarrer H24</span>
                </>
              )}
            </button>

            {/* SÉLECTEUR DE VITESSE */}
            <div className="speed-group" title="Vitesse de la simulation sur le serveur">
              <button
                id="speed-1x"
                className={`speed-btn ${speed === 1 ? "active" : ""}`}
                onClick={() => changeSpeed(1)}
                title="1 jour simulé par seconde (vitesse par défaut)"
              >
                1x
              </button>
              <button
                id="speed-5x"
                className={`speed-btn ${speed === 5 ? "active" : ""}`}
                onClick={() => changeSpeed(5)}
                title="5 jours simulés par seconde"
              >
                5x
              </button>
              <button
                id="speed-30x"
                className={`speed-btn ${speed === 30 ? "active" : ""}`}
                onClick={() => changeSpeed(30)}
                title="1 mois (30 jours) par tick rapide"
              >
                30x
              </button>
            </div>

            {/* AVANCE MANUELLE */}
            <div className="btn-group" title="Intervenir : avancer manuellement dans le temps">
              <button id="step-day" className="btn" disabled={stepping !== null} onClick={() => step(1)} title="Avancer de 1 jour">
                {stepping === 1 ? <Loader2 size={14} className="spin" /> : <span>+1 j</span>}
              </button>
              <button id="step-month" className="btn" disabled={stepping !== null} onClick={() => step(30)} title="Avancer de 1 mois">
                {stepping === 30 ? <Loader2 size={14} className="spin" /> : <span>+1 m</span>}
              </button>
              <button id="step-year" className="btn" disabled={stepping !== null} onClick={() => step(365)} title="Avancer de 1 an">
                {stepping === 365 ? <Loader2 size={14} className="spin" /> : <span>+1 an</span>}
              </button>
            </div>

            <button id="refresh" className="btn chip" onClick={refreshFull} aria-label="Actualiser" title="Actualiser toutes les données">
              <RefreshCw size={15} />
            </button>

            {/* BOUTON REDÉMARRER */}
            <button
              id="reset-universe"
              className="btn-reset"
              disabled={resetting || stepping !== null}
              onClick={reset}
              aria-label="Redémarrer"
              title="Réinitialiser l'univers au Jour 0 (le moteur H24 repart à zéro)"
            >
              {resetting ? <Loader2 size={15} className="spin" /> : <RotateCcw size={15} />}
              <span>Redémarrer</span>
            </button>
          </div>
        </header>

        <main className="main">
          {/* ===== Overview ===== */}
          {tab === "overview" && (
            <>
              <div className="stat-grid">
                <StatCard
                  icon={Users}
                  label="Population mondiale"
                  value={`${universe?.population ?? (people.length || 0)} habitants`}
                  sub={`${people[0]?.clan_name ?? "Bande pionnière"} (chasseurs-cueilleurs)`}
                  tone="#4fd1a5"
                />
                <StatCard
                  icon={Calendar}
                  label="Date & Chronologie"
                  value={
                    universe && universe.year < 0
                      ? `${Math.abs(universe.year)} av. J.-C.`
                      : `An ${universe?.year ?? 0}`
                  }
                  sub={universe?.cultural_frame === "biblical" ? "Cadre biblique (expérimental)" : "Cadre neutre · an 0"}
                  tone="#5bb8f5"
                />
                <StatCard
                  icon={Sun}
                  label="Saison en cours"
                  value={universe?.season ?? "Printemps"}
                  sub={`Jour ${universe?.day ?? 1} / ${universe?.year_length ?? 365}`}
                  tone="#f2b84b"
                />
                <StatCard
                  icon={Tent}
                  label="Clans & Tribus"
                  value={`${universe?.clans_count ?? 1} ${((universe?.clans_count ?? 1) > 1) ? "clans" : "clan"}`}
                  sub={people[0]?.clan_name ?? "Clan fondateur"}
                  tone="#38bdf8"
                />
                <StatCard
                  icon={Crown}
                  label="Notables vivants"
                  value={`${universe?.notables_count ?? (notables.length || 0)} notables`}
                  sub="Conseillers & doyens du clan"
                  tone="#8b7cf6"
                />
                <StatCard
                  icon={Castle}
                  label="Établissements"
                  value={`${universe?.settlements_count ?? (settlements.length || 1)} ${((universe?.settlements_count ?? settlements.length) > 1) ? "campements" : "campement"}`}
                  sub={settlements[0]?.name ?? "Campement d'origine"}
                  tone="#f08a5d"
                />
                <StatCard
                  icon={Route}
                  label="Routes commerciales"
                  value={universe?.trade_routes_count ?? 0}
                  sub="S'activera dès 2+ clans"
                  tone="#fbbf24"
                />
                <StatCard
                  icon={Landmark}
                  label="Royaumes & Merveilles"
                  value={`${universe?.kingdoms_count ?? 0} / ${universe?.wonders_count ?? 0}`}
                  sub="Nécessite villes et bourgs"
                  tone="#ec7fb6"
                />
              </div>

              {/* Barre de progression de l'année */}
              <div style={{ padding: "16px 20px", borderRadius: "var(--radius)", background: "var(--surface)", border: "1px solid var(--border)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px", fontSize: "0.85rem", flexWrap: "wrap", gap: "8px" }}>
                  <span style={{ display: "inline-flex", alignItems: "center", gap: "8px", fontWeight: 600 }}>
                    <CalendarDays size={16} style={{ color: "#5bb8f5" }} />
                    Progression de l&apos;année {universe && universe.year < 0 ? `${Math.abs(universe.year)} av. J.-C.` : `An ${universe?.year ?? 0}`}
                    {isPlaying ? (
                      <span className="live-pill" title="Le moteur tourne en continu 24/7 sur le serveur">
                        <span className="pulse-dot" /> Serveur H24 actif ({speed}x)
                      </span>
                    ) : (
                      <span className="live-pill" style={{ background: "rgba(245, 158, 11, 0.15)", borderColor: "rgba(245, 158, 11, 0.4)", color: "#fbbf24" }}>
                        ⏸️ Moteur en pause
                      </span>
                    )}
                  </span>
                  <span style={{ color: "var(--text-muted)" }}>
                    Jour {universe?.day ?? 1} sur {universe?.year_length ?? 365} ({Math.round(((universe?.day ?? 1) / (universe?.year_length ?? 365)) * 100)} %) · {universe?.season ?? "Printemps"}
                  </span>
                </div>
                <div className="progress" style={{ height: "10px" }}>
                  <div style={{ width: `${Math.min(100, Math.round(((universe?.day ?? 1) / (universe?.year_length ?? 365)) * 100))}%`, transition: "width 0.3s ease" }} />
                </div>
              </div>

              {/* Panneau explicatif des habitants et de la lignée */}
              <Panel icon={Users} title="Habitants du monde & Lignée humaine" badge={`${people.length || (universe?.population ?? 0)} personnes vivantes`}>
                {people.length === 0 ? (
                  <Empty icon={Users} text="Chargement des habitants du monde…" />
                ) : (
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "12px", padding: "4px" }}>
                    {people.map((p) => {
                      const father = p.father_id ? people.find((x) => x.id === p.father_id) : null;
                      const mother = p.mother_id ? people.find((x) => x.id === p.mother_id) : null;
                      const emoji =
                        p.age < 3
                          ? "👶"
                          : p.age < 14
                          ? p.sex === "M"
                            ? "👦"
                            : "👧"
                          : p.age >= 45
                          ? p.sex === "M"
                            ? "👴"
                            : "👵"
                          : p.sex === "M"
                          ? "👨"
                          : "👩";
                      return (
                        <div
                          key={p.id}
                          style={{
                            padding: "12px 14px",
                            borderRadius: "var(--radius-sm)",
                            background: "rgba(255, 255, 255, 0.03)",
                            border: "1px solid var(--border)",
                            display: "flex",
                            alignItems: "center",
                            gap: "12px",
                          }}
                        >
                          <span style={{ fontSize: "1.8rem" }}>{emoji}</span>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
                              <strong style={{ fontSize: "0.95rem" }}>{p.name}</strong>
                              <span
                                style={{
                                  fontSize: "0.7rem",
                                  padding: "2px 6px",
                                  borderRadius: "4px",
                                  background: p.notable ? "rgba(139, 92, 246, 0.2)" : "rgba(79, 209, 165, 0.2)",
                                  color: p.notable ? "#a78bfa" : "#4fd1a5",
                                  fontWeight: 600,
                                }}
                              >
                                {p.role}
                              </span>
                            </div>
                            <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginTop: "3px" }}>
                              {p.age < 1 ? "Nourrisson (< 1 an)" : `${Math.floor(p.age)} ans`} · {p.sex === "M" ? "Homme" : "Femme"} · {p.clan_name ?? people[0]?.clan_name ?? "Clan pionnier"}
                            </div>
                            {father && mother ? (
                              <div style={{ fontSize: "0.72rem", color: "#5bb8f5", marginTop: "2px" }}>
                                ↳ Lignée : enfant de {father.name} &amp; {mother.name}
                              </div>
                            ) : father ? (
                              <div style={{ fontSize: "0.72rem", color: "#5bb8f5", marginTop: "2px" }}>
                                ↳ Lignée : enfant de {father.name}
                              </div>
                            ) : mother ? (
                              <div style={{ fontSize: "0.72rem", color: "#5bb8f5", marginTop: "2px" }}>
                                ↳ Lignée : enfant de {mother.name}
                              </div>
                            ) : (
                              <div style={{ fontSize: "0.72rem", color: "#9ca3af", marginTop: "2px" }}>
                                ↳ Génération fondatrice
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </Panel>

              <div className="grid-2">
                <Panel icon={MapPin} title="Carte des territoires" badge={world ? `${Math.round(world.land_fraction * 100)} % de terres` : undefined} flush>
                  {world ? (
                    <TerritoryMap width={world.width} height={world.height} settlements={settlements} notables={notables} />
                  ) : (
                    <Empty icon={Globe2} text="Chargement de la carte du monde…" />
                  )}
                </Panel>

                <Panel icon={Castle} title="Établissements" badge={settlements.length}>
                  {settlements.length === 0 ? (
                    <Empty icon={Tent} text="Aucun établissement pour le moment." />
                  ) : (
                    settlements.map((s) => (
                      <div className="row" key={s.id}>
                        <div>
                          <div className="row-title">{s.name}</div>
                          <div className="row-sub">
                            Niveau {s.tier} · {s.tier_title}
                          </div>
                          <div className="row-sub">{s.buildings.join(" · ")}</div>
                        </div>
                        <div className="row-meta">
                          <span className="meta-item">
                            <Wheat size={14} style={{ color: "var(--success)" }} /> {Math.round(s.food_stores)} vivres
                          </span>
                          <span className="meta-item">
                            <Shield size={14} style={{ color: "var(--info)" }} /> Défense +{s.defense_bonus}
                          </span>
                        </div>
                      </div>
                    ))
                  )}
                </Panel>
              </div>

              <div className="grid-2">
                <Panel icon={Sprout} title="Écologie du monde">
                  <div className="kv">
                    <span>Niveau de la mer</span>
                    <strong>{world ? world.sea_level.toFixed(2) : "—"}</strong>
                  </div>
                  <div className="kv">
                    <span>Cours d&apos;eau (cellules)</span>
                    <strong>{world?.rivers_cells_count ?? "—"}</strong>
                  </div>
                  <div className="kv">
                    <span>Biomes présents</span>
                    <strong>{world?.biomes_present.length ?? "—"}</strong>
                  </div>
                  <div className="kv">
                    <span>Langues parlées</span>
                    <strong>{universe?.languages_count ?? 0}</strong>
                  </div>
                  <div className="kv">
                    <span>Technologies connues</span>
                    <strong>{universe?.technologies_known ?? 0}</strong>
                  </div>
                  <div className="kv">
                    <span>Guerres en cours</span>
                    <strong>{universe?.active_wars_count ?? 0}</strong>
                  </div>
                </Panel>

                <Panel icon={Brain} title="Budget d'intelligence artificielle">
                  <div className="kv">
                    <span>Appels utilisés</span>
                    <strong>
                      {budget?.total_calls ?? 0} / {budget?.max_total_calls ?? 0}
                    </strong>
                  </div>
                  <div className="kv">
                    <span>Coût estimé</span>
                    <strong>
                      ${budget?.estimated_cost_usd?.toFixed(4) ?? "0.0000"} / ${budget?.max_cost_usd ?? 0}
                    </strong>
                  </div>
                  <div className="progress" style={{ marginTop: 14 }}>
                    <div style={{ width: `${budgetPct}%` }} />
                  </div>
                </Panel>
              </div>
            </>
          )}

          {/* ===== Notables ===== */}
          {tab === "notables" && (
            <div>
              {/* Carte explicative : Intérêt et impact des dialogues */}
              <div
                style={{
                  marginBottom: 16,
                  padding: "14px 18px",
                  borderRadius: "var(--radius)",
                  background: "linear-gradient(135deg, rgba(139, 92, 246, 0.12) 0%, rgba(56, 189, 248, 0.08) 100%)",
                  border: "1px solid rgba(139, 92, 246, 0.25)",
                  display: "flex",
                  gap: 16,
                  alignItems: "center",
                  flexWrap: "wrap",
                }}
              >
                <div style={{ fontSize: "1.8rem" }}>🔮</div>
                <div style={{ flex: 1, minWidth: 260 }}>
                  <strong style={{ color: "#c4b5fd", fontSize: "0.95rem" }}>
                    Quel est l&apos;impact d&apos;un dialogue avec un habitant ?
                  </strong>
                  <div style={{ fontSize: "0.82rem", color: "var(--text-muted)", marginTop: 4, lineHeight: 1.45 }}>
                    Vos paroles sont perçues comme un songe ou une voix mystérieuse. L&apos;habitant <strong>délibère de façon autonome</strong> selon ses traits de personnalité (Big Five) pour accueillir, douter ou rejeter vos suggestions, sans qu&apos;aucun tabou ne soit imposé arbitrairement. Toute discussion marque aussi la branche comme <strong>intervention observatrice</strong>.
                  </div>
                </div>
              </div>

              <div className="chat-layout">
                <Panel icon={Users} title="Hiérarchie des Notables" badge={`${notables.length} figures`}>
                  {notables.length === 0 ? (
                    <Empty icon={UserRound} text="Aucun notable éveillé pour le moment." />
                  ) : (
                    notables.map((n) => (
                      <button key={n.id} className={`person ${selected?.id === n.id ? "active" : ""}`} onClick={() => setSelected(n)}>
                        <div className={`avatar ${n.sex === "F" ? "f" : ""}`}>
                          {n.sex === "F" ? <UserRound size={20} /> : <User size={20} />}
                        </div>
                        <div style={{ minWidth: 0, textAlign: "left" }}>
                          <div className="person-name" style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                            <span>{n.name}</span>
                            <span style={{ fontSize: "0.7rem", opacity: 0.75 }}>({Math.floor(n.age)} ans)</span>
                            <span
                              style={{
                                fontSize: "0.68rem",
                                padding: "1px 6px",
                                borderRadius: "4px",
                                background: "rgba(139, 92, 246, 0.2)",
                                color: "#a78bfa",
                                fontWeight: 600,
                              }}
                            >
                              {n.rank_grade ?? "Dirigeant"}
                            </span>
                          </div>
                          <div className="person-sub" style={{ marginTop: 2 }}>
                            {n.title}
                          </div>
                        </div>
                      </button>
                    ))
                  )}
                </Panel>

                <section className="panel fade-in" style={{ minHeight: 0 }}>
                  {selected ? (
                    <>
                      <div className="panel-head">
                        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                          <div className={`avatar ${selected.sex === "F" ? "f" : ""}`}>
                            {selected.sex === "F" ? <UserRound size={20} /> : <User size={20} />}
                          </div>
                          <div>
                            <div className="row-title" style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                              <span>{selected.name}</span>
                              <span
                                style={{
                                  fontSize: "0.74rem",
                                  padding: "2px 8px",
                                  borderRadius: "10px",
                                  background: "rgba(139, 92, 246, 0.25)",
                                  color: "#c4b5fd",
                                  fontWeight: 600,
                                }}
                              >
                                {selected.rank_grade ?? "Dirigeant"}
                              </span>
                              {selected.influence !== undefined && (
                                <span style={{ fontSize: "0.72rem", color: "#fbbf24", fontWeight: 600 }}>
                                  ★ {selected.influence} influence
                                </span>
                              )}
                            </div>
                            <div className="row-sub" style={{ marginTop: 2 }}>
                              {selected.title} · {selected.sex === "M" ? "Homme" : "Femme"} de {Math.floor(selected.age)} ans
                            </div>
                          </div>
                        </div>
                        <span className="badge">
                          {selected.memories_count} souvenir{selected.memories_count > 1 ? "s" : ""}
                        </span>
                      </div>

                      {/* Croyances et vision du monde */}
                      {selected.beliefs && selected.beliefs.length > 0 && (
                        <div style={{ padding: "8px 16px", background: "rgba(0, 0, 0, 0.15)", borderBottom: "1px solid var(--border)", fontSize: "0.75rem", color: "var(--text-muted)" }}>
                          <span style={{ color: "#a78bfa", fontWeight: 600 }}>Croyances : </span>
                          {selected.beliefs.slice(0, 2).join(" · ")}
                        </div>
                      )}

                      <div className="chat-feed" ref={feedRef}>
                        {messages.length === 0 && !asking ? (
                          <Empty
                            icon={MessageSquareText}
                            text={`Posez une question à ${selected.name} : sur sa famille, ses enfants, son rôle de ${selected.rank_grade ?? "chef"}, ses peurs ou donnez-lui un conseil divin.`}
                          />
                        ) : (
                          messages.map((m, i) => (
                            <div key={i} className={`bubble ${m.sender === "me" ? "me" : ""}`}>
                              <div className="bubble-author">{m.author}</div>
                              {m.text}
                            </div>
                          ))
                        )}
                        {asking && (
                          <div className="bubble">
                            <div className="bubble-author">{selected.name}</div>
                            <Loader2 size={16} className="spin" />
                          </div>
                        )}
                      </div>

                      <form className="chat-form" onSubmit={ask}>
                        <input
                          id="chat-input"
                          className="input"
                          value={question}
                          onChange={(e) => setQuestion(e.target.value)}
                          placeholder={`Parler à ${selected.name} (ex: "qui es-tu ?", "comment va ton fils Pelega ?", "un conseil pour la paix...")`}
                        />
                        <button id="chat-send" type="submit" className="btn btn-primary" disabled={asking || !question.trim()}>
                          <Send size={15} />
                          Envoyer
                        </button>
                      </form>
                    </>
                  ) : (
                    <Empty icon={UserRound} text="Sélectionnez un habitant pour échanger." />
                  )}
                </section>
              </div>
            </div>
          )}

          {/* ===== Civilization ===== */}
          {tab === "civilization" && (
            <>
              <Panel icon={InfinityIcon} title="Cycle de l'Ouroboros" badge={`Cycle ${universe?.ouroboros_cycle ?? 1}`} flush>
                <div className="phases">
                  {PHASES.map((p) => (
                    <div key={p} className={`phase ${p === phase ? "current" : ""}`} style={{ ["--tone" as string]: PHASE_TONES[p] }}>
                      {p}
                    </div>
                  ))}
                </div>
              </Panel>

              <div className="grid-2">
                <Panel icon={Route} title="Routes commerciales" badge={routes.length}>
                  {routes.length === 0 ? (
                    <Empty icon={Route} text="Aucune route commerciale n'est encore ouverte." />
                  ) : (
                    routes.map((r) => (
                      <div className="row" key={r.id}>
                        <div>
                          <div className="row-title">{r.name}</div>
                          <div className="row-sub">{r.primary_good}</div>
                        </div>
                        <div className="row-meta">
                          <span className="meta-item">
                            <MapPin size={14} /> {r.distance} lieues
                          </span>
                          <span className="meta-item">
                            <Wallet size={14} style={{ color: "var(--success)" }} /> {Math.round(r.volume_traded)} échangés
                          </span>
                        </div>
                      </div>
                    ))
                  )}
                </Panel>

                <Panel icon={Sparkles} title="Panthéon" badge={deities.length}>
                  {deities.length === 0 ? (
                    <Empty icon={Sparkles} text="Aucune divinité vénérée." />
                  ) : (
                    deities.map((d) => (
                      <div className="row" key={d.id}>
                        <div>
                          <div className="row-title">{d.name}</div>
                          <div className="row-sub">{d.title}</div>
                        </div>
                        <div className="row-meta">
                          <span className="badge">{d.domain}</span>
                        </div>
                      </div>
                    ))
                  )}
                </Panel>
              </div>

              <div className="grid-2">
                <Panel icon={Gavel} title="Justice & institutions">
                  <div className="kv">
                    <span>Codes de lois</span>
                    <strong>{universe?.legal_codes_count ?? 0}</strong>
                  </div>
                  <div className="kv">
                    <span>Procès tenus</span>
                    <strong>{universe?.trials_count ?? 0}</strong>
                  </div>
                  <div className="kv">
                    <span>Sites sacrés</span>
                    <strong>{universe?.sacred_sites_count ?? 0}</strong>
                  </div>
                </Panel>
                <Panel icon={Coins} title="Pouvoir & économie">
                  <div className="kv">
                    <span>Royaumes</span>
                    <strong>{universe?.kingdoms_count ?? 0}</strong>
                  </div>
                  <div className="kv">
                    <span>Monnaies en usage</span>
                    <strong>{universe?.currencies_count ?? 0}</strong>
                  </div>
                  <div className="kv">
                    <span>Expéditions de caravanes</span>
                    <strong>{universe?.expeditions_count ?? 0}</strong>
                  </div>
                </Panel>
              </div>
            </>
          )}

          {/* ===== Chronicles ===== */}
          {tab === "chronicles" && (
            <Panel icon={BookOpenText} title="Rouleau des chroniques" badge={chronicles.length} flush>
              {chronicles.length === 0 ? (
                <Empty icon={ScrollText} text="Aucune chronique n'a encore été scellée. Faites avancer le temps pour écrire l'histoire." />
              ) : (
                <div className="timeline">
                  {[...chronicles].reverse().map((c) => (
                    <article className="tl-item" key={c.id}>
                      <div className="tl-head">
                        <span className="tl-title">{c.title}</span>
                        <span className="tl-year">
                          An {c.year} · {c.category}
                        </span>
                      </div>
                      <p className="tl-text">{c.narrative}</p>
                    </article>
                  ))}
                </div>
              )}
            </Panel>
          )}

          {/* ===== Research & Emergence (PIMMUR) ===== */}
          {tab === "research" && (
            <>
              {/* Header de Branche & Contrôle Expérimental */}
              <div
                style={{
                  background: "linear-gradient(135deg, rgba(30, 27, 75, 0.45), rgba(17, 24, 39, 0.6))",
                  border: "1px solid rgba(139, 92, 246, 0.25)",
                  borderRadius: "var(--radius)",
                  padding: "16px 20px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 16,
                  flexWrap: "wrap",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                  <div
                    style={{
                      width: 44,
                      height: 44,
                      borderRadius: 12,
                      background: "rgba(139, 92, 246, 0.2)",
                      display: "grid",
                      placeItems: "center",
                      color: "#c4b5fd",
                    }}
                  >
                    <GitBranch size={22} />
                  </div>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                      <strong style={{ fontSize: "1rem", color: "#e0e7ff" }}>
                        Branche : {universe?.id ?? "main"}
                      </strong>
                      <span
                        style={{
                          fontSize: "0.72rem",
                          padding: "2px 8px",
                          borderRadius: "12px",
                          background:
                            branchMeta?.branch_type === "observer_intervention"
                              ? "rgba(239, 107, 115, 0.2)"
                              : "rgba(79, 209, 165, 0.2)",
                          color:
                            branchMeta?.branch_type === "observer_intervention"
                              ? "#ef6b73"
                              : "#4fd1a5",
                          fontWeight: 600,
                        }}
                      >
                        {branchMeta?.branch_type === "observer_intervention"
                          ? "● Intervention observatrice"
                          : "● Baseline pure (Référence)"}
                      </span>
                    </div>
                    <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginTop: 2 }}>
                      {branchMeta?.description || "Évolution naturelle sans forçage scénaristique."}
                      {branchMeta?.parent_universe_id && (
                        <span> · Dérivé de <strong>{branchMeta.parent_universe_id}</strong> à l&apos;An {branchMeta.fork_year}</span>
                      )}
                    </div>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                  <button
                    type="button"
                    onClick={handleExportCsv}
                    className="btn chip"
                    style={{ textDecoration: "none", color: "#e8eaf2", display: "inline-flex", alignItems: "center", gap: 6, cursor: "pointer" }}
                    title="Télécharger l'intégralité des métriques saisonnières au format CSV pour analyse R / Python / Pandas"
                  >
                    <Download size={14} style={{ color: "var(--accent)" }} />
                    Export CSV
                  </button>

                  <form onSubmit={handleFork} style={{ display: "flex", gap: 6 }}>
                    <input
                      className="input"
                      style={{ padding: "6px 12px", fontSize: "0.8rem", width: 180 }}
                      placeholder="Nom de la branche..."
                      value={forkName}
                      onChange={(e) => setForkName(e.target.value)}
                    />
                    <button
                      type="submit"
                      className="btn btn-primary"
                      style={{ padding: "6px 12px", fontSize: "0.8rem" }}
                      disabled={forking}
                    >
                      {forking ? <Loader2 size={13} className="spin" /> : <GitBranch size={13} />}
                      Forker
                    </button>
                  </form>
                </div>
              </div>

              {forkSuccess && (
                <div
                  style={{
                    padding: "10px 16px",
                    borderRadius: "var(--radius-sm)",
                    background: "rgba(79, 209, 165, 0.15)",
                    border: "1px solid rgba(79, 209, 165, 0.3)",
                    color: "var(--success)",
                    fontSize: "0.82rem",
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                  }}
                >
                  <CheckCircle2 size={16} />
                  <span>{forkSuccess}</span>
                </div>
              )}

              {/* Les 4 Piliers Scientifiques */}
              <div className="stat-grid">
                <StatCard
                  icon={Scale}
                  label="Inégalité d'Influence (Gini)"
                  value={latestMetric ? latestMetric.gini_influence.toFixed(3) : "0.000"}
                  sub={`Moyenne : ${(metricsSummary?.averages.gini_influence ?? 0).toFixed(3)} · Réseau de déférence`}
                  tone="#c4b5fd"
                />
                <StatCard
                  icon={Coins}
                  label="Inégalité de Ressources (Gini)"
                  value={latestMetric ? latestMetric.gini_resources.toFixed(3) : "0.000"}
                  sub={`Moyenne : ${(metricsSummary?.averages.gini_resources ?? 0).toFixed(3)} · Stocks alimentaires`}
                  tone="#4fd1a5"
                />
                <StatCard
                  icon={Activity}
                  label="Entropie Comportementale"
                  value={latestMetric ? latestMetric.behavioral_entropy.toFixed(3) : "1.000"}
                  sub={`Shannon H : ${(metricsSummary?.averages.behavioral_entropy ?? 0).toFixed(3)} (1.0 = diversité max)`}
                  tone="#38bdf8"
                />
                <StatCard
                  icon={Users}
                  label="Densité du Réseau Social"
                  value={latestMetric ? latestMetric.network_density.toFixed(3) : "0.000"}
                  sub={`${latestMetric?.active_social_ties ?? 0} liens de conseil & médiation`}
                  tone="#f2b84b"
                />
              </div>

              {/* Conformité aux Principes PIMMUR */}
              <Panel icon={CheckCircle2} title="Validité Scientifique – Principes PIMMUR (Zhou et al.)">
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
                    gap: 12,
                    fontSize: "0.82rem",
                  }}
                >
                  <div style={{ background: "rgba(255,255,255,0.03)", padding: 12, borderRadius: "var(--radius-sm)", border: "1px solid var(--border)" }}>
                    <div style={{ fontWeight: 600, color: "#818cf8", marginBottom: 4 }}>1. Profils Psychologiques (P)</div>
                    <div style={{ color: "var(--text-muted)", lineHeight: 1.4 }}>
                      Big Five (OCEAN) avec transmission héréditaire partielle et inventaire de compétences individuelles.
                    </div>
                  </div>
                  <div style={{ background: "rgba(255,255,255,0.03)", padding: 12, borderRadius: "var(--radius-sm)", border: "1px solid var(--border)" }}>
                    <div style={{ fontWeight: 600, color: "#818cf8", marginBottom: 4 }}>2. Perception Locale Stricte (I)</div>
                    <div style={{ color: "var(--text-muted)", lineHeight: 1.4 }}>
                      Aucun agrégat macro-statistique ou inventaire mondial injecté dans le contexte perceptuel.
                    </div>
                  </div>
                  <div style={{ background: "rgba(255,255,255,0.03)", padding: 12, borderRadius: "var(--radius-sm)", border: "1px solid var(--border)" }}>
                    <div style={{ fontWeight: 600, color: "#818cf8", marginBottom: 4 }}>3. Flux de Mémoire Épisodique (M)</div>
                    <div style={{ color: "var(--text-muted)", lineHeight: 1.4 }}>
                      Décroissance exponentielle (oubli e^-λΔt), importance cognitive et synthèses réflexives périodiques.
                    </div>
                  </div>
                  <div style={{ background: "rgba(255,255,255,0.03)", padding: 12, borderRadius: "var(--radius-sm)", border: "1px solid var(--border)" }}>
                    <div style={{ fontWeight: 600, color: "#818cf8", marginBottom: 4 }}>4. Contrôle Minimal (M)</div>
                    <div style={{ color: "var(--text-muted)", lineHeight: 1.4 }}>
                      Prompts purement situationnels. Aucune consigne impérative de statut ou de comportement imposé.
                    </div>
                  </div>
                  <div style={{ background: "rgba(255,255,255,0.03)", padding: 12, borderRadius: "var(--radius-sm)", border: "1px solid var(--border)" }}>
                    <div style={{ fontWeight: 600, color: "#818cf8", marginBottom: 4 }}>5. Non-Conscience de l&apos;Étude (U)</div>
                    <div style={{ color: "var(--text-muted)", lineHeight: 1.4 }}>
                      Les habitants s&apos;éprouvent comme des êtres vivants de leur époque, sans métadonnées de simulation.
                    </div>
                  </div>
                  <div style={{ background: "rgba(255,255,255,0.03)", padding: 12, borderRadius: "var(--radius-sm)", border: "1px solid var(--border)" }}>
                    <div style={{ fontWeight: 600, color: "#818cf8", marginBottom: 4 }}>6. Calibration Démographique (R)</div>
                    <div style={{ color: "var(--text-muted)", lineHeight: 1.4 }}>
                      Démographie calibrée de chasseurs-cueilleurs : mortalité infantile 30-40%, longévité naturelle ~60 ans.
                    </div>
                  </div>
                </div>
              </Panel>

              {/* Table des Métriques Historiques */}
              <Panel icon={BarChart3} title="Séries Temporelles Saisonnières" badge={`${metricsHistory.length} instantanés`}>
                {metricsHistory.length === 0 ? (
                  <Empty icon={BarChart3} text="Aucun instantané saisonnier consigné pour le moment. Laissez la simulation progresser." />
                ) : (
                  <div style={{ overflowX: "auto", maxHeight: 380 }}>
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem", textAlign: "left" }}>
                      <thead>
                        <tr style={{ borderBottom: "1px solid var(--border)", color: "var(--text-muted)" }}>
                          <th style={{ padding: "8px 12px" }}>Année / Saison</th>
                          <th style={{ padding: "8px 12px" }}>Population</th>
                          <th style={{ padding: "8px 12px" }}>Naissances / Décès</th>
                          <th style={{ padding: "8px 12px" }}>Gini Influence</th>
                          <th style={{ padding: "8px 12px" }}>Gini Ressources</th>
                          <th style={{ padding: "8px 12px" }}>Entropie (Shannon)</th>
                          <th style={{ padding: "8px 12px" }}>Déférence Max</th>
                          <th style={{ padding: "8px 12px" }}>Coutumes & Tabous</th>
                        </tr>
                      </thead>
                      <tbody>
                        {[...metricsHistory].slice(-15).reverse().map((m, idx) => (
                          <tr
                            key={idx}
                            style={{
                              borderBottom: "1px solid rgba(255,255,255,0.04)",
                              background: idx % 2 === 0 ? "rgba(255,255,255,0.01)" : "transparent",
                            }}
                          >
                            <td style={{ padding: "8px 12px", fontWeight: 600 }}>
                              {m.year < 0 ? `${Math.abs(m.year)} av. J.-C.` : `An ${m.year}`} · {m.season}
                            </td>
                            <td style={{ padding: "8px 12px" }}>{m.population}</td>
                            <td style={{ padding: "8px 12px", color: "var(--text-muted)" }}>
                              <span style={{ color: "var(--success)" }}>+{m.births_this_year}</span> / <span style={{ color: "var(--danger)" }}>-{m.deaths_this_year}</span>
                            </td>
                            <td style={{ padding: "8px 12px", color: "#c4b5fd" }}>{m.gini_influence.toFixed(3)}</td>
                            <td style={{ padding: "8px 12px", color: "#4fd1a5" }}>{m.gini_resources.toFixed(3)}</td>
                            <td style={{ padding: "8px 12px", color: "#38bdf8" }}>{m.behavioral_entropy.toFixed(3)}</td>
                            <td style={{ padding: "8px 12px", color: "#f2b84b" }}>{m.max_deference.toFixed(1)}</td>
                            <td style={{ padding: "8px 12px" }}>
                              {m.active_customs_count} coutumes · {m.active_taboos_count} tabous
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </Panel>

              {/* Journal d'Appels IA Auditable */}
              <Panel icon={FlaskConical} title="Journal d'Appels IA Auditable (Traçabilité)" badge={`${aiLogs.length} appels récents`}>
                {aiLogs.length === 0 ? (
                  <Empty icon={FlaskConical} text="Aucun appel IA récent consigné dans le journal auditable." />
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 10, maxHeight: 420, overflowY: "auto" }}>
                    {aiLogs.slice(0, 10).map((log) => (
                      <div
                        key={log.record_id}
                        style={{
                          background: "rgba(0,0,0,0.25)",
                          border: "1px solid var(--border)",
                          borderRadius: "var(--radius-sm)",
                          padding: "10px 14px",
                          fontSize: "0.78rem",
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6, flexWrap: "wrap", gap: 6 }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <span
                              style={{
                                fontSize: "0.7rem",
                                padding: "1px 6px",
                                borderRadius: "4px",
                                background: "rgba(139, 92, 246, 0.2)",
                                color: "#c4b5fd",
                                fontWeight: 600,
                              }}
                            >
                              {log.kind}
                            </span>
                            <strong>Agent #{log.agent_id ?? "Système"}</strong>
                            <span style={{ color: "var(--text-dim)" }}>
                              (An {log.year < 0 ? `${Math.abs(log.year)} av. J.-C.` : log.year})
                            </span>
                          </div>
                          <div style={{ color: "var(--text-muted)", fontSize: "0.72rem" }}>
                            {log.model_name} · {log.duration_ms} ms · Temp {log.temperature}
                          </div>
                        </div>

                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginTop: 4 }}>
                          <div style={{ background: "rgba(0,0,0,0.2)", padding: 8, borderRadius: 6, border: "1px solid rgba(255,255,255,0.03)" }}>
                            <div style={{ color: "var(--text-dim)", fontSize: "0.68rem", textTransform: "uppercase", marginBottom: 2 }}>Prompt Minimal</div>
                            <div style={{ maxHeight: 70, overflowY: "auto", whiteSpace: "pre-wrap", color: "var(--text-muted)" }}>{log.prompt}</div>
                          </div>
                          <div style={{ background: "rgba(0,0,0,0.2)", padding: 8, borderRadius: 6, border: "1px solid rgba(255,255,255,0.03)" }}>
                            <div style={{ color: "var(--text-dim)", fontSize: "0.68rem", textTransform: "uppercase", marginBottom: 2 }}>Décision / Réponse IA</div>
                            <div style={{ maxHeight: 70, overflowY: "auto", whiteSpace: "pre-wrap", color: "#e2e8f0" }}>{log.response}</div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </Panel>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
