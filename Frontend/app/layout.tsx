import type { Metadata } from "next";
import { Inter } from "next/font/google";
import * as React from "react";

import "@/app/globals.css";
import { Providers } from "@/app/providers";

export const metadata: Metadata = {
  title: "Doxa CRM",
  description: "CRM frontend for Doxa sales, marketing, and customer success workflows.",
};

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
