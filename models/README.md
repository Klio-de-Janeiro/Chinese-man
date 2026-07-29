# Release models

The API looks for two generated release artifacts:

```text
bot_v1.onnx
bot_v1_metadata.json
```

They are intentionally not committed. Run the export step after imitation
learning, PPO self-play, and evaluation. Until compatible artifacts are
installed, the API uses `HeuristicAgent` and reports that fallback through
`GET /api/bot/status`.

Never place an untrained model here: a valid file is treated as a release
candidate only when its metadata matches the current rules, ML schema, and
encoder versions.
