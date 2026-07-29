import type { SuitName } from "./cards";

export type RoomStatus = "waiting" | "paused" | "playing" | "finished";

export type ConnectionStatus =
  | "disconnected"
  | "connecting"
  | "connected"
  | "reconnecting";

export type ActionKind =
  | "attack"
  | "defend"
  | "transfer"
  | "take"
  | "pass_attack";

export type Credentials = {
  roomId: string;
  playerId: string;
  seatToken: string;
  maxPlayers: 2 | 3;
  botCount: number;
  rulesVersion: string;
};

export type LegalAction = {
  kind: ActionKind;
  card: number | null;
  targetSlot: number | null;
};

export type TableSlot = {
  slot: number;
  attack: number;
  defense: number | null;
};

export type PlayerView = {
  id: string;
  index: number;
  nickname: string;
  connected: boolean;
  isBot: boolean;
  isYou: boolean;
  cardCount: number;
  hand?: number[];
  placement: number;
  isDurak: boolean;
};

export type GameView = {
  version: number;
  phase: string;
  dealer: number;
  mainAttacker: number;
  defender: number;
  eligibleAttackers: number;
  passedAttackers: number;
  attackCount: number;
  attackLimit: number;
  deckCount: number;
  discardCount: number;
  trump: SuitName;
  trumpCard: number;
  transferLocked: boolean;
  takeDeclared: boolean;
  draw: boolean;
  table: TableSlot[];
  legalActions: LegalAction[];
  technicalLoser: string | null;
};

export type ActivityEvent = {
  id: string;
  kind: string;
  message: string;
  at: string;
};

export type Snapshot = {
  type: "snapshot";
  room: {
    id: string;
    status: RoomStatus;
    maxPlayers: number;
    connectedPlayers: number;
    reconnectTimeoutSeconds: number;
    createdAt: string;
  };
  you: {
    id: string;
    index: number;
    nickname: string;
  };
  players: PlayerView[];
  game: GameView | null;
  events: ActivityEvent[];
  rulesVersion: string;
};

export type ErrorPayload = {
  error?: {
    code?: string;
    message?: string;
  };
};
