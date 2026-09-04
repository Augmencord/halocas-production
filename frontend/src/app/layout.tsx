import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Sidebar from "../components/Sidebar";
import Header from "../components/Header";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "HALOCAS | Mining Vehicle Collision Avoidance System",
  description:
    "Real-time AI-powered heavy mining collision avoidance, proximity monitoring, and personnel biometric safety system.",
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}): React.JSX.Element {
  return (
    <html lang="en" className={`${inter.variable} dark h-full`}>
      <body className="h-full bg-[#111827] text-gray-100 font-sans flex antialiased selection:bg-[#00FFFF]/20 selection:text-[#00FFFF]">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0 lg:pl-64 md:lg:pl-72 transition-all duration-300">
          <Header />
          <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
