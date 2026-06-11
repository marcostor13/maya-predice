export interface Team {
  id: number;
  name: string;
  code: string;
  confederation?: string;
  group?: string;
  fifa_rank?: number;
}

export type MatchStage =
  | 'group'
  | 'round_of_32'
  | 'round_of_16'
  | 'quarter_final'
  | 'semi_final'
  | 'third_place'
  | 'final';

export type MatchStatus = 'scheduled' | 'live' | 'finished';

export interface VenueDetail {
  stadium: string;
  city: string;
  country: string;
  capacity: number;
}

export interface Match {
  id: number;
  tournament_id: number;
  external_ref: string;
  home_team_id?: number;
  away_team_id?: number;
  home_placeholder?: string;
  away_placeholder?: string;
  stage: MatchStage;
  group?: string;
  matchday?: number;
  venue?: string;
  venue_detail?: VenueDetail;
  kickoff?: string;
  status: MatchStatus;
  home_goals?: number;
  away_goals?: number;
  minute?: number;
}

/**
 * Partido con datos en vivo (marcador, minuto). Devuelto por los endpoints
 * `/matches/live` y `/matches/today`, ya resuelto con códigos/nombres de
 * selección para pintar directamente en la UI.
 */
export interface LiveMatch {
  id: number;
  home_code?: string | null;
  home_name?: string | null;
  away_code?: string | null;
  away_name?: string | null;
  home_goals?: number | null;
  away_goals?: number | null;
  minute?: number | null;
  status: MatchStatus;
  kickoff?: string | null;
  group?: string | null;
  stage: string;
  venue?: string | null;
  home_placeholder?: string | null;
  away_placeholder?: string | null;
}

export interface ScorelineProb {
  home: number;
  away: number;
  prob: number;
}

export interface Prediction {
  id: number;
  match_id: number;
  model_version: string;
  p_home: number;
  p_draw: number;
  p_away: number;
  expected_home_goals: number;
  expected_away_goals: number;
  scoreline_probs?: ScorelineProb[];
  adjustments?: Record<string, unknown>;
  ensemble?: { model: number[]; market: number[]; weight: number } | null;
  created_at: string;
}

export type PlayerStatus =
  | 'available' | 'injured' | 'suspended' | 'doubtful' | 'out' | 'unknown';
export type Position = 'GK' | 'DEF' | 'MID' | 'FWD' | 'UNKNOWN';
export type SquadRole = 'starter' | 'substitute' | 'reserve' | 'unknown';

export interface Player {
  id: number;
  team_id: number;
  full_name: string;
  position: Position;
  shirt_number?: number;
  club?: string;
  role: SquadRole;
  status: PlayerStatus;
  photo_url?: string;
  info?: string;
  confidence: number;
  sources_count: number;
}

export interface Coach {
  id: number;
  team_id: number;
  name: string;
  nationality?: string;
  status: PlayerStatus;
  photo_url?: string;
  confidence: number;
  sources_count: number;
}

export interface Squad {
  team_code: string;
  team_name: string;
  coach?: Coach;
  players: Player[];
}

export interface TeamSimulation {
  team_code: string;
  team_name: string;
  advance_prob: number;
  round16_prob: number;
  quarter_prob: number;
  semi_prob: number;
  final_prob: number;
  champion_prob: number;
}

export interface Simulation {
  run_id: number;
  model_version: string;
  iterations: number;
  created_at: string;
  teams: TeamSimulation[];
}
