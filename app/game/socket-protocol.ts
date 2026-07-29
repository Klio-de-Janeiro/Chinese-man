import type { Snapshot } from "./types";

export type DecodedSocketMessage =
  | {
      kind: "snapshot";
      snapshot: Snapshot;
    }
  | {
      kind: "pong";
    }
  | {
      kind: "error" | "invalid";
      message: string;
    };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

/**
 * Decode the small server-to-browser WebSocket protocol without trusting
 * arbitrary JSON shapes. In particular, heartbeat `pong` messages are valid
 * protocol traffic and must not be interpreted as server errors.
 */
export function decodeSocketMessage(data: unknown): DecodedSocketMessage {
  if (typeof data !== "string") {
    return {
      kind: "invalid",
      message: "Игровой сервер прислал сообщение неизвестного формата.",
    };
  }

  let payload: unknown;

  try {
    payload = JSON.parse(data);
  } catch {
    return {
      kind: "invalid",
      message: "Игровой сервер прислал повреждённое сообщение.",
    };
  }

  if (!isRecord(payload) || typeof payload.type !== "string") {
    return {
      kind: "invalid",
      message: "Игровой сервер прислал сообщение неизвестного формата.",
    };
  }

  if (payload.type === "snapshot") {
    return {
      kind: "snapshot",
      snapshot: payload as Snapshot,
    };
  }

  if (payload.type === "pong") {
    return { kind: "pong" };
  }

  if (payload.type === "error") {
    const error = isRecord(payload.error) ? payload.error : null;
    const message =
      error && typeof error.message === "string" && error.message.trim()
        ? error.message
        : "Игровой сервер отклонил команду без описания причины.";

    return {
      kind: "error",
      message,
    };
  }

  return {
    kind: "invalid",
    message: `Игровой сервер прислал неподдерживаемое сообщение «${payload.type}».`,
  };
}
