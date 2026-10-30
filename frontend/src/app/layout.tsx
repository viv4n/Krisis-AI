import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/components/ThemeProvider";

export const metadata: Metadata = {
  title: "Krisis AI // Damage Mapper - DSU Digital Twin Command",
  description: "High-end dark mode tactical command dashboard for damage mapping and spatial consensus.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" data-matrix="cyber-neon" suppressHydrationWarning>
      <body className="antialiased bg-[#090B10] text-[#F8FAFC]">
        <ThemeProvider>
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
