"use client";

import {
  Activity,
  BookOpenText,
  Castle,
  ChevronsRight,
  Clock3,
  Coins,
  Crown,
  FastForward,
  Gavel,
  Globe2,
  Landmark,
  Loader2,
  MapPin,
  MessageSquareText,
  Play,
  Pause,
  RefreshCw,
  Route,
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
  type ChatMessage,
  type Chronicle,
  type Deity,
  type Notable,
  type Settlement,
  type TradeRoute,
  type UniverseInfo,
  type WorldMapInfo,
} from "@/lib/types";

type Tab = "overview" | "notables" | "civilization" | "chronicles";

const NAV: { key: Tab; label: string; icon: typeof Globe2 }[] = [
  { key: "overview", label: "Vue d'ensemble", icon: Globe2 },
  { key: "notables", label: "Habitants notables", icon: MessageSquareText },
  { key: "civilization", label: "Civilisation", icon: Landmark },
  { key: "chronicles", label: "Chroniques", icon: ScrollText },
];

const TITLES: Record<Tab, { title: string; sub: string }> = {
  overview: { title: "Vue d'ensemble", sub: "État du monde, territoires et établissements" },
  notables: { title: "Habitants notables", sub: "Dialogue en immersion totale avec les figures de l'univers" },
  civilization: { title: "Civilisation", sub: "Institutions, commerce, croyances et pouvoir" },
  chronicles: { title: "Chroniques", sub: "Mémoire épique consignée par les bardes" },
};

const API = process.env.NEXT_PUBLIC_API_URL || "https://13-49-23-84.sslip.io";

async function getJson<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API}${path}`);
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
  const [selected, setSelected] = useState<Notable | null>(null);
  const [chats, setChats] = useState<Record<number, ChatMessage[]>>({});
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [stepping, setStepping] = useState<number | null>(null);
  const [resetting, setResetting] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState<number>(1);
  const feedRef = useRef<HTMLDivElement>(null);

  const isPlayingRef = useRef(isPlaying);
  isPlayingRef.current = isPlaying;
  const speedRef = useRef(speed);
  speedRef.current = speed;
  const loopActiveRef = useRef(false);
  const hasUserToggled = useRef(false);

  const refresh = useCallback(async () => {
    const [u, w, n, s, t, c, p] = await Promise.all([
      getJson<UniverseInfo>("/universes/main"),
      getJson<WorldMapInfo>("/universes/main/map"),
      getJson<Notable[]>("/universes/main/notables"),
      getJson<Settlement[]>("/universes/main/settlements"),
      getJson<{ routes: TradeRoute[] }>("/universes/main/trade"),
      getJson<Chronicle[]>("/universes/main/chronicles"),
      getJson<{ deities: Deity[] }>("/universes/main/pantheon"),
    ]);
    setOnline(u !== null);
    if (u) {
      setUniverse(u);
      if (u.is_running !== undefined && !hasUserToggled.current) {
        setIsPlaying(Boolean(u.is_running));
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
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 10000);
    return () => clearInterval(id);
  }, [refresh]);

  // Boucle d'exécution continue quand la simulation est démarrée
  useEffect(() => {
    if (!isPlaying) return;
    let mounted = true;

    // Intervalle adapté à la vitesse choisie : 1x = 1000ms (1s = 1 jour), 5x = 500ms, 30x = 250ms
    const intervalMs = speed === 1 ? 1000 : speed === 5 ? 500 : 250;
    const timer = setInterval(async () => {
      if (!mounted || !isPlayingRef.current || loopActiveRef.current) return;
      loopActiveRef.current = true;
      try {
        await fetch(`${API}/universes/main/step`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ days: speedRef.current }),
        });
        await refresh();
      } catch (err) {
        console.error("Erreur de simulation continue:", err);
      } finally {
        loopActiveRef.current = false;
      }
    }, intervalMs);

    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, [isPlaying, speed, refresh]);

  const togglePlay = async () => {
    hasUserToggled.current = true;
    const nextState = !isPlaying;
    setIsPlaying(nextState);
    try {
      if (nextState) {
        await fetch(`${API}/universes/main/play?speed=${speedRef.current}`, { method: "POST" });
      } else {
        await fetch(`${API}/universes/main/pause`, { method: "POST" });
      }
    } catch (e) {
      console.warn("Appel API play/pause fallback vers boucle locale:", e);
    }
    await refresh();
  };

  const step = async (days: number) => {
    setStepping(days);
    try {
      await fetch(`${API}/universes/main/step`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ days }),
      });
      await refresh();
    } catch (e) {
      console.error("Erreur de pas:", e);
    } finally {
      setStepping(null);
    }
  };

  const reset = async () => {
    if (!confirm("Voulez-vous redémarrer la simulation à l'instant originel (Jour 0) ?")) return;
    hasUserToggled.current = true;
    setIsPlaying(false);
    setResetting(true);
    try {
      await fetch(`${API}/universes/main/pause`, { method: "POST" });
      await fetch(`${API}/universes/main/reset`, { method: "POST" });
      setSelected(null);
      setChats({});
      await refresh();
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
      const res = await fetch(`${API}/universes/main/notables/${pid}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, mock: true }),
      });
      if (res.ok) {
        const data = await res.json();
        answer = data.response || answer;
      }
    } catch {
      /* réponse par défaut */
    }
    setChats((c) => ({ ...c, [pid]: [...(c[pid] ?? []), { sender: "them", author: selected.name, text: answer }] }));
    setAsking(false);
    refresh();
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
              {online === null ? "Connexion…" : online ? "Moteur connecté" : "Serveur inaccessible"}
            </strong>
          </div>
          <div style={{ wordBreak: "break-all" }}>{API.replace("https://", "")}</div>
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
              <strong>An {universe?.year ?? 0}</strong>
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
            {/* BOUTON DÉMARRER / PAUSE */}
            <button
              id="btn-play-pause"
              className={`btn ${isPlaying ? "btn-pause" : "btn-play"}`}
              onClick={togglePlay}
              title={isPlaying ? "Mettre la simulation en pause" : "Démarrer la simulation (avance automatique du temps)"}
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
                  <span>Démarrer</span>
                </>
              )}
            </button>

            {/* SÉLECTEUR DE VITESSE */}
            <div className="speed-group" title="Vitesse d'écoulement du temps">
              <button
                id="speed-1x"
                className={`speed-btn ${speed === 1 ? "active" : ""}`}
                onClick={() => setSpeed(1)}
                title="1 jour simulé par seconde"
              >
                1x
              </button>
              <button
                id="speed-5x"
                className={`speed-btn ${speed === 5 ? "active" : ""}`}
                onClick={() => setSpeed(5)}
                title="5 jours par seconde"
              >
                5x
              </button>
              <button
                id="speed-30x"
                className={`speed-btn ${speed === 30 ? "active" : ""}`}
                onClick={() => setSpeed(30)}
                title="1 mois (30 jours) par tick rapide"
              >
                30x
              </button>
            </div>

            {/* AVANCE MANUELLE */}
            <div className="btn-group" title="Avancer manuellement dans le temps">
              <button id="step-day" className="btn" disabled={stepping !== null || isPlaying} onClick={() => step(1)} title="Avancer de 1 jour">
                {stepping === 1 ? <Loader2 size={14} className="spin" /> : <span>+1 j</span>}
              </button>
              <button id="step-month" className="btn" disabled={stepping !== null || isPlaying} onClick={() => step(30)} title="Avancer de 1 mois">
                {stepping === 30 ? <Loader2 size={14} className="spin" /> : <span>+1 m</span>}
              </button>
              <button id="step-year" className="btn" disabled={stepping !== null || isPlaying} onClick={() => step(365)} title="Avancer de 1 an">
                {stepping === 365 ? <Loader2 size={14} className="spin" /> : <span>+1 an</span>}
              </button>
            </div>

            <button id="refresh" className="btn chip" onClick={refresh} aria-label="Actualiser" title="Actualiser les données">
              <RefreshCw size={15} />
            </button>

            {/* BOUTON REDÉMARRER */}
            <button
              id="reset-universe"
              className="btn-reset"
              disabled={resetting || stepping !== null}
              onClick={reset}
              aria-label="Redémarrer"
              title="Redémarrer la simulation au jour 0"
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
                <StatCard icon={Calendar} label="Date & Calendrier" value={`An ${universe?.year ?? 0}`} tone="#5bb8f5" />
                <StatCard icon={Sun} label="Saison en cours" value={universe?.season ?? "Printemps"} tone="#f2b84b" />
                <StatCard icon={Tent} label="Clans" value={universe?.clans_count ?? 0} tone="#4fd1a5" />
                <StatCard icon={Users} label="Habitants notables" value={universe?.notables_count ?? 0} tone="#8b7cf6" />
                <StatCard icon={Castle} label="Établissements" value={universe?.settlements_count ?? 0} tone="#38bdf8" />
                <StatCard icon={Route} label="Routes commerciales" value={universe?.trade_routes_count ?? 0} tone="#fbbf24" />
                <StatCard icon={Crown} label="Royaumes" value={universe?.kingdoms_count ?? 0} tone="#ec7fb6" />
                <StatCard icon={Landmark} label="Merveilles" value={universe?.wonders_count ?? 0} tone="#f08a5d" />
              </div>

              {/* Barre de progression de l'année */}
              <div style={{ padding: "16px 20px", borderRadius: "var(--radius)", background: "var(--surface)", border: "1px solid var(--border)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px", fontSize: "0.85rem", flexWrap: "wrap", gap: "8px" }}>
                  <span style={{ display: "inline-flex", alignItems: "center", gap: "8px", fontWeight: 600 }}>
                    <CalendarDays size={16} style={{ color: "#5bb8f5" }} />
                    Progression de l&apos;année {universe?.year ?? 0}
                    {isPlaying && (
                      <span className="live-pill">
                        <span className="pulse-dot" /> Simulation active ({speed}x)
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
            <div className="chat-layout">
              <Panel icon={Users} title="Habitants" badge={notables.length}>
                {notables.length === 0 ? (
                  <Empty icon={UserRound} text="Aucun notable éveillé." />
                ) : (
                  notables.map((n) => (
                    <button key={n.id} className={`person ${selected?.id === n.id ? "active" : ""}`} onClick={() => setSelected(n)}>
                      <div className={`avatar ${n.sex === "F" ? "f" : ""}`}>
                        {n.sex === "F" ? <UserRound size={20} /> : <User size={20} />}
                      </div>
                      <div style={{ minWidth: 0 }}>
                        <div className="person-name">
                          {n.name} · {Math.round(n.age)} ans
                        </div>
                        <div className="person-sub">{n.title}</div>
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
                          <div className="row-title">{selected.name}</div>
                          <div className="row-sub" style={{ marginTop: 0 }}>
                            {selected.title}
                          </div>
                        </div>
                      </div>
                      <span className="badge">
                        {selected.memories_count} souvenir{selected.memories_count > 1 ? "s" : ""}
                      </span>
                    </div>

                    <div className="chat-feed" ref={feedRef}>
                      {messages.length === 0 && !asking ? (
                        <Empty icon={MessageSquareText} text="Posez une question sur sa vie, ses peurs, ses croyances ou son clan." />
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
                        placeholder={`Parler à ${selected.name}…`}
                      />
                      <button id="chat-send" type="submit" className="btn btn-primary" disabled={asking || !question.trim()}>
                        <Send size={15} />
                        Envoyer
                      </button>
                    </form>
                  </>
                ) : (
                  <Empty icon={UserRound} text="Sélectionnez un habitant." />
                )}
              </section>
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
        </main>
      </div>
    </div>
  );
}
