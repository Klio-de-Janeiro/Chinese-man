"use client";

import {
  type FormEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import { GameScreen } from "./components/game-screen";
import { HomeScreen } from "./components/home-screen";
import { LobbyScreen } from "./components/lobby-screen";
import { DEMO_SNAPSHOT } from "./game/demo";
import { createRequestId } from "./game/request-id";
import { decodeSocketMessage } from "./game/socket-protocol";
import type {
  ConnectionStatus,
  Credentials,
  ErrorPayload,
  LegalAction,
  Snapshot,
} from "./game/types";

function apiOrigin(): string {
  if (typeof window === "undefined") {
    return "http://localhost:8000";
  }

  return `${window.location.protocol}//${gameHost()}:8000`;
}

function websocketOrigin(): string {
  if (typeof window === "undefined") {
    return "ws://localhost:8000";
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${gameHost()}:8000`;
}

function gameHost(): string {
  const configured = import.meta.env.VITE_PUBLIC_GAME_HOST?.trim();
  return configured || window.location.hostname;
}

function storageKey(roomId: string): string {
  return `chinese-durak-seat:${roomId.toUpperCase()}`;
}

async function responseJson<T>(response: Response): Promise<T> {
  const data = (await response.json()) as T & ErrorPayload;

  if (!response.ok) {
    throw new Error(
      data.error?.message ?? "Сервер не смог выполнить запрос.",
    );
  }

  return data;
}

export default function Home() {
  const [nickname, setNickname] = useState("Klio");
  const [playerCount, setPlayerCount] = useState<2 | 3>(2);
  const [roomCode, setRoomCode] = useState("");
  const [inviteRoom, setInviteRoom] = useState<string | null>(null);
  const [credentials, setCredentials] = useState<Credentials | null>(null);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [connectionStatus, setConnectionStatus] =
    useState<ConnectionStatus>("disconnected");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [isDemo, setIsDemo] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => {
      const params = new URLSearchParams(window.location.search);
      const roomId = params.get("room")?.trim().toUpperCase();

      if (!roomId) {
        return;
      }

      const stored = window.localStorage.getItem(storageKey(roomId));

      if (stored) {
        try {
          setCredentials(JSON.parse(stored) as Credentials);
          return;
        } catch {
          window.localStorage.removeItem(storageKey(roomId));
        }
      }

      setInviteRoom(roomId);
      setRoomCode(roomId);
    }, 0);

    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!credentials || isDemo) {
      return;
    }

    let active = true;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let heartbeat: ReturnType<typeof setInterval> | null = null;

    function connect(): void {
      setConnectionStatus((current) =>
        current === "connected" ? current : "connecting",
      );

      const socket = new WebSocket(
        `${websocketOrigin()}/api/rooms/${credentials.roomId}/ws` +
          `?token=${encodeURIComponent(credentials.seatToken)}`,
      );
      socketRef.current = socket;

      socket.onopen = () => {
        if (!active) {
          socket.close();
          return;
        }

        setConnectionStatus("connected");
        setError(null);
        heartbeat = setInterval(() => {
          if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: "ping" }));
          }
        }, 20_000);
      };

      socket.onmessage = (event) => {
        const message = decodeSocketMessage(event.data);

        switch (message.kind) {
          case "snapshot":
            setSnapshot(message.snapshot);
            return;
          case "pong":
            return;
          case "error":
          case "invalid":
            setError(message.message);
            return;
        }
      };

      socket.onclose = () => {
        if (heartbeat) {
          clearInterval(heartbeat);
        }

        if (!active) {
          return;
        }

        setConnectionStatus("reconnecting");
        reconnectTimer = setTimeout(connect, 1_500);
      };

      socket.onerror = () => {
        setError(
          "Не удалось подключиться к игровому серверу на порту 8000.",
        );
      };
    }

    connect();

    return () => {
      active = false;

      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
      }

      if (heartbeat) {
        clearInterval(heartbeat);
      }

      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [credentials, isDemo]);

  useEffect(() => {
    if (!notice) {
      return;
    }

    const timer = setTimeout(() => setNotice(null), 2_400);
    return () => clearTimeout(timer);
  }, [notice]);

  const saveCredentials = useCallback((value: Credentials): void => {
    window.localStorage.setItem(storageKey(value.roomId), JSON.stringify(value));
    window.history.replaceState({}, "", `/?room=${value.roomId}`);
    setCredentials(value);
    setInviteRoom(value.roomId);
    setRoomCode(value.roomId);
  }, []);

  async function createRoom(event: FormEvent): Promise<void> {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${apiOrigin()}/api/rooms`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nickname,
          playerCount,
        }),
      });
      saveCredentials(await responseJson<Credentials>(response));
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Не удалось создать комнату.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function joinRoom(event: FormEvent): Promise<void> {
    event.preventDefault();

    if (!inviteRoom) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${apiOrigin()}/api/rooms/${inviteRoom}/join`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ nickname }),
        },
      );
      saveCredentials(await responseJson<Credentials>(response));
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Не удалось войти в комнату.",
      );
    } finally {
      setLoading(false);
    }
  }

  function sendAction(action: LegalAction): void {
    if (isDemo) {
      setNotice(
        `Демо: действие «${action.kind}» выбрано. ` +
          "В реальной комнате оно уйдёт на сервер.",
      );
      return;
    }

    if (
      !snapshot?.game ||
      socketRef.current?.readyState !== WebSocket.OPEN
    ) {
      setError("Соединение с игровой комнатой ещё не установлено.");
      return;
    }

    socketRef.current.send(
      JSON.stringify({
        type: "action",
        requestId: createRequestId(),
        expectedVersion: snapshot.game.version,
        action,
      }),
    );
  }

  async function copyInvite(): Promise<void> {
    if (!snapshot) {
      return;
    }

    const port = window.location.port || "3000";
    const link =
      `${window.location.protocol}//${gameHost()}:${port}` +
      `/?room=${snapshot.room.id}`;

    try {
      await navigator.clipboard.writeText(link);
    } catch {
      const textarea = document.createElement("textarea");
      textarea.value = link;
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      textarea.remove();
    }

    setCopied(true);
    setTimeout(() => setCopied(false), 2_000);
  }

  function leave(): void {
    if (credentials) {
      window.localStorage.removeItem(storageKey(credentials.roomId));
    }

    socketRef.current?.close();
    window.history.replaceState({}, "", "/");
    setCredentials(null);
    setSnapshot(null);
    setInviteRoom(null);
    setRoomCode("");
    setIsDemo(false);
    setConnectionStatus("disconnected");
    setError(null);
  }

  if (snapshot?.game) {
    return (
      <GameScreen
        snapshot={snapshot}
        connectionStatus={connectionStatus}
        isDemo={isDemo}
        onAction={sendAction}
        onCopyInvite={copyInvite}
        copied={copied}
        onLeave={leave}
        notice={notice}
      />
    );
  }

  if (snapshot) {
    return (
      <LobbyScreen
        snapshot={snapshot}
        connectionStatus={connectionStatus}
        onCopyInvite={copyInvite}
        copied={copied}
        onLeave={leave}
      />
    );
  }

  return (
    <HomeScreen
      nickname={nickname}
      setNickname={setNickname}
      playerCount={playerCount}
      setPlayerCount={setPlayerCount}
      roomCode={roomCode}
      setRoomCode={setRoomCode}
      inviteRoom={inviteRoom}
      setInviteRoom={setInviteRoom}
      loading={loading}
      error={error}
      onCreate={createRoom}
      onJoin={joinRoom}
      onDemo={() => {
        setIsDemo(true);
        setConnectionStatus("connected");
        setSnapshot(DEMO_SNAPSHOT);
      }}
    />
  );
}
