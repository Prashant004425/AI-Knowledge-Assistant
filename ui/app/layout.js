import "./globals.css";

export const metadata = {
  title: "AI Knowledge Assistant",
  description: "Chat interface for AI Knowledge Assistant",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
