import assert from "node:assert/strict";
import test from "node:test";

import { decodeSocketMessage } from "../app/game/socket-protocol.ts";

test("accepts heartbeat pong without treating it as an error", () => {
  assert.deepEqual(decodeSocketMessage('{"type":"pong"}'), {
    kind: "pong",
  });
});

test("reads a structured server error", () => {
  assert.deepEqual(
    decodeSocketMessage(
      '{"type":"error","error":{"message":"Ход недоступен."}}',
    ),
    {
      kind: "error",
      message: "Ход недоступен.",
    },
  );
});

test("uses a safe fallback when an error has no message", () => {
  assert.deepEqual(decodeSocketMessage('{"type":"error"}'), {
    kind: "error",
    message: "Игровой сервер отклонил команду без описания причины.",
  });
});

test("does not throw on invalid JSON", () => {
  assert.deepEqual(decodeSocketMessage("{"), {
    kind: "invalid",
    message: "Игровой сервер прислал повреждённое сообщение.",
  });
});

test("passes a snapshot through to the UI", () => {
  const message = decodeSocketMessage(
    '{"type":"snapshot","room":{"id":"ABC123"}}',
  );

  assert.equal(message.kind, "snapshot");

  if (message.kind === "snapshot") {
    assert.equal(message.snapshot.room.id, "ABC123");
  }
});
