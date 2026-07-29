import type { FormEvent } from "react";

export function HomeScreen({
  nickname,
  setNickname,
  playerCount,
  setPlayerCount,
  roomCode,
  setRoomCode,
  inviteRoom,
  setInviteRoom,
  loading,
  error,
  onCreate,
  onJoin,
  onDemo,
}: {
  nickname: string;
  setNickname: (value: string) => void;
  playerCount: 2 | 3;
  setPlayerCount: (value: 2 | 3) => void;
  roomCode: string;
  setRoomCode: (value: string) => void;
  inviteRoom: string | null;
  setInviteRoom: (value: string | null) => void;
  loading: boolean;
  error: string | null;
  onCreate: (event: FormEvent) => void;
  onJoin: (event: FormEvent) => void;
  onDemo: () => void;
}) {
  return (
    <main className="home-shell">
      <div className="home-glow home-glow--one" />
      <div className="home-glow home-glow--two" />

      <header className="brand-bar">
        <span className="brand-mark">КД</span>
        <span>
          <strong>Китайский Дурак</strong>
          <small>Переводная карточная игра</small>
        </span>
      </header>

      <section className="home-hero">
        <div className="home-copy">
          <span className="eyebrow">
            <span className="live-dot" />
            Комната запускается за минуту
          </span>
          <h1>
            Один стол.
            <br />
            Цена ошибки — <em>вся куча.</em>
          </h1>
          <p>
            Создайте приватную комнату, отправьте ссылку друзьям и играйте
            прямо в браузере. Сервер проверяет каждый ход по правилам
            переводного «Китайского Дурака».
          </p>

          <div className="feature-row">
            <span>2–3 игрока</span>
            <span>52 карты</span>
            <span>До 12 карт на столе</span>
          </div>
        </div>

        <div className="entry-panel">
          {inviteRoom ? (
            <>
              <div className="entry-panel__heading">
                <span className="panel-icon">↗</span>
                <div>
                  <span>Приглашение в комнату</span>
                  <strong>#{inviteRoom}</strong>
                </div>
              </div>

              <form onSubmit={onJoin} className="entry-form">
                <label>
                  Ваше имя
                  <input
                    value={nickname}
                    onChange={(event) => setNickname(event.target.value)}
                    placeholder="Например, Klio"
                    minLength={2}
                    maxLength={24}
                    autoFocus
                    required
                  />
                </label>
                <button className="primary-button" disabled={loading}>
                  {loading ? "Подключаемся…" : "Занять место"}
                </button>
              </form>

              <button
                type="button"
                className="text-button"
                onClick={() => setInviteRoom(null)}
              >
                Ввести другой код
              </button>
            </>
          ) : (
            <>
              <div className="entry-tabs" aria-label="Вход в игру">
                <span className="entry-tabs__active">Создать комнату</span>
                <span>или войти по коду</span>
              </div>

              <form onSubmit={onCreate} className="entry-form">
                <label>
                  Ваше имя
                  <input
                    value={nickname}
                    onChange={(event) => setNickname(event.target.value)}
                    placeholder="Например, Klio"
                    minLength={2}
                    maxLength={24}
                    required
                  />
                </label>

                <fieldset>
                  <legend>Количество игроков</legend>
                  <div className="segmented-control">
                    {[2, 3].map((count) => (
                      <button
                        key={count}
                        type="button"
                        className={playerCount === count ? "is-active" : ""}
                        onClick={() => setPlayerCount(count as 2 | 3)}
                      >
                        {count} игрока
                      </button>
                    ))}
                  </div>
                </fieldset>

                <button className="primary-button" disabled={loading}>
                  {loading ? "Создаём…" : "Создать приватную комнату"}
                </button>
              </form>

              <div className="join-by-code">
                <input
                  value={roomCode}
                  onChange={(event) =>
                    setRoomCode(event.target.value.toUpperCase())
                  }
                  placeholder="Код комнаты"
                  maxLength={6}
                  aria-label="Код комнаты"
                />
                <button
                  type="button"
                  onClick={() => {
                    if (roomCode.trim()) {
                      setInviteRoom(roomCode.trim().toUpperCase());
                    }
                  }}
                >
                  Войти
                </button>
              </div>
            </>
          )}

          {error ? (
            <p className="form-error" role="alert">
              {error}
            </p>
          ) : null}

          <button type="button" className="demo-button" onClick={onDemo}>
            <span>◈</span>
            Посмотреть демонстрационный стол
          </button>
        </div>
      </section>

      <footer className="home-footer">
        <span>Правила: chinese-durak/0.2.1-draft</span>
        <span>Без аккаунтов · приватная ссылка · reconnect 120 сек.</span>
      </footer>
    </main>
  );
}
