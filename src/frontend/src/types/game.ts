export type HPMap = { [playerId: string]: number };

export type AttackPayload = { text: string; image?: string };

export type ServerMessage =
  | { type: "system"; message: string; hp_status: HPMap; current_turn: string }
  | {
      type: "attack";
      sender: string;
      display_text: string;
      damage: number;
      referee_comment: string;
      hp_status: HPMap;
      current_turn: string;
    }
  | {
      type: "npc_attack";
      display_text: string;
      damage: number;
      referee_comment: string;
      hp_status: HPMap;
    }
  | { type: "game_over"; message: string; winner: string }
  | { type: "turn_error"; message: string };

export type LeaderboardEntry = {
  rank: number;
  username: string;
  total_damage: number;
  wins: number;
  losses: number;
};

export type RoundSnapshot = {
  round_number: number;
  attacker: string | null;
  original_text: string | null;
  display_text: string;
  damage: number;
  referee_comment: string;
  hp_snapshot: HPMap;
};
