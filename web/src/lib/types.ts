export interface UniverseInfo {
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
    max_total_calls: number;
    total_calls: number;
    max_cost_usd: number;
    estimated_cost_usd: number;
  };
}

export interface Notable {
  id: number;
  name: string;
  sex: string;
  age: number;
  alive: boolean;
  cell: [number, number];
  title: string;
  memories_count: number;
}

export interface Settlement {
  id: number;
  name: string;
  cell: [number, number];
  clan_id: number;
  tier: number;
  tier_title: string;
  buildings: string[];
  food_stores: number;
  defense_bonus: number;
}

export interface TradeRoute {
  id: number;
  name: string;
  primary_good: string;
  distance: number;
  volume_traded: number;
}

export interface Chronicle {
  id: number;
  year: number;
  category: string;
  title: string;
  narrative: string;
  involved_clans: string[];
}

export interface Deity {
  id: number;
  name: string;
  title: string;
  domain: string;
  symbol: string;
}

export interface WorldMapInfo {
  width: number;
  height: number;
  sea_level: number;
  land_fraction: number;
  biomes_present: string[];
  rivers_cells_count: number;
}

export interface ChatMessage {
  sender: "me" | "them";
  author: string;
  text: string;
}

export const PHASES = ["Aube", "Ascension", "Apogée", "Crise", "Renaissance"] as const;

export const PHASE_TONES: Record<string, string> = {
  Aube: "#5bb8f5",
  Ascension: "#4fd1a5",
  Apogée: "#f2b84b",
  Crise: "#ef6b73",
  Renaissance: "#b48cf6",
};
