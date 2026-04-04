import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Local RAG Chat",
  description: "Streaming RAG chat interface",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
