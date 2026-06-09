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

export interface Match {
  id: number;
  tournament_id: number;
  home_team_id: number;
  away_team_id: number;
  stage: MatchStage;
  group?: string;
  venue?: string;
  kickoff?: string;
  status: MatchStatus;
  home_goals?: number;
  away_goals?: number;
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
  created_at: string;
}
