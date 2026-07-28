import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Китайский Дурак — приватная игра",
  description:
    "Создайте комнату и играйте в переводного Китайского Дурака онлайн.",
  other: {
    "codex-preview": "development",
  },
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}
