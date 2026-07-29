import assert from "node:assert/strict";
import test from "node:test";

import { createRequestId } from "../app/game/request-id.ts";

test("uses crypto.randomUUID when the browser provides it", () => {
  const expected = "123e4567-e89b-42d3-a456-426614174000";

  assert.equal(
    createRequestId({
      randomUUID: () => expected,
    }),
    expected,
  );
});

test("creates an RFC 4122 UUID when randomUUID is unavailable", () => {
  const requestId = createRequestId({
    getRandomValues: (bytes) => {
      bytes.fill(0);
      return bytes;
    },
  });

  assert.equal(requestId, "00000000-0000-4000-8000-000000000000");
});

test("still creates a valid UUID without a Web Crypto implementation", () => {
  assert.match(
    createRequestId(null),
    /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
  );
});
