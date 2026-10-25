import type { Metadata } from "next";
import AppToaster from "../components/app-toaster";
import "./globals.css";

export const metadata: Metadata = {
  title: "Klyro AI | Private knowledge, clear answers",
  description: "A private, grounded AI workspace for your team's knowledge.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className="h-full antialiased"
    >
      <body className="min-h-full flex flex-col">
        {children}
        <AppToaster />
      </body>
    </html>
  );
}
