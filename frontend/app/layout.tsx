import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "IntiApp",
  description: "RAG App",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <link rel="icon" href="inti_logo.png" />
      <link rel="icon" href="static/inti_logo.png" />
      <body>{children}</body>
    </html>
  );
}
