import "@/app/globals.css";
import type { Metadata } from "next";
import ClientProviders from "@/components/providers/ClientProviders";

export const metadata: Metadata = {
  title: "Thothy",
  description: "Thothy",
};

// TODO: Replace NuqsAdapter with useState and props
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body suppressHydrationWarning>
        <ClientProviders>{children}</ClientProviders>
      </body>
    </html>
  );
}
