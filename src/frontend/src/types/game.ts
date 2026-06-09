// src/frontend/src/types/game.ts
export type HPMap = { [playerId: string]: number }

export type AttackPayload = { text: string; image?: string }

export type ServerMessage =
  | { type: 'system'; message: string; hp_status: HPMap; current_turn: string }
  | { type: 'attack'; sender: string; original_text: string; display_text: string; damage: number; referee_comment: string; hp_status: HPMap; current_turn: string }
  | { type: 'npc_typing'; npc_text: string }
  | { type: 'npc_attack'; npc_text: string; display_text: string; damage: number; referee_comment: string; hp_status: HPMap; current_turn: string }
  | { type: 'game_over'; message: string; winner: string }
  | { type: 'turn_error'; message: string }
  | { type: 'error'; message: string }
  | { type: 'challenge_declined'; message: string }
  | { type: 'player_typing'; sender: string; text: string }

export type ChatEntry =
  | { id: number; kind: 'system'; displayText: string }
  | { id: number; kind: 'attack'; sender: string; displayText: string; damage: number; isNpc: boolean; isPending?: boolean }
  | { id: number; kind: 'referee'; displayText: string }

export type LeaderboardEntry = {
  rank: number
  username: string
  total_damage: number
  wins: number
  losses: number
}

export type RoundSnapshot = {
  round_number: number
  attacker: string | null
  original_text: string | null
  display_text: string
  damage: number
  referee_comment: string
  hp_snapshot: HPMap
}

export type MatchRecord = {
  matchId: string
  opponent: string
  result: 'win' | 'loss'
  totalDamage: number
  roundCount: number
  timestamp: number
}
