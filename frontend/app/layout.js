import "./globals.css";

export const metadata = {
  title: "Sam2 Voice",
  description: "Local conversational agent dashboard",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
