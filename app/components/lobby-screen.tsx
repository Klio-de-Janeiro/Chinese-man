import type { ConnectionStatus, Snapshot } from "../game/types";

export function LobbyScreen({
  snapshot,
  connectionStatus,
  onCopyInvite,
  copied,
  onLeave,
}: {
  snapshot: Snapshot;
  connectionStatus: ConnectionStatus;
  onCopyInvite: () => void;
  copied: boolean;
  onLeave: () => void;
}) {
  const missing = snapshot.room.maxPlayers - snapshot.players.length;

  return (
    <main className="lobby-shell">
      <div className="lobby-card">
        <span className="eyebrow">
          <span className="live-dot" />
          Приватная комната
        </span>
        <h1>Комната #{snapshot.room.id}</h1>
        <p>
          Ждём ещё {missing}{" "}
          {missing === 1 ? "игрока" : "игроков"}. Партия начнётся
          автоматически, когда все места будут заняты.
        </p>

        <div className="seat-grid">
          {Array.from({ length: snapshot.room.maxPlayers }).map((_, index) => {
            const player = snapshot.players[index];

            return (
              <div
                key={player?.id ?? `empty-${index}`}
                className={player ? "seat seat--occupied" : "seat"}
              >
                <span className="seat__avatar">
                  {player ? player.nickname.slice(0, 1).toUpperCase() : "+"}
                </span>
                <span>
                  <strong>{player?.nickname ?? "Свободное место"}</strong>
                  <small>
                    {player
                      ? player.connected
                        ? "В сети"
                        : "Подключается"
                      : "Отправьте ссылку другу"}
                  </small>
                </span>
              </div>
            );
          })}
        </div>

        <div className="invite-box">
          <div>
            <small>Код приглашения</small>
            <strong>{snapshot.room.id}</strong>
          </div>
          <button type="button" onClick={onCopyInvite}>
            {copied ? "Ссылка скопирована" : "Скопировать ссылку"}
          </button>
        </div>

        <div className="lobby-meta">
          <span>
            Соединение:{" "}
            <strong>
              {connectionStatus === "connected"
                ? "установлено"
                : "подключаемся…"}
            </strong>
          </span>
          <button type="button" onClick={onLeave}>
            Покинуть комнату
          </button>
        </div>
      </div>
    </main>
  );
}
