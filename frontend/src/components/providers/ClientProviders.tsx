"use client";

import { AuthProvider } from "@/contexts/AuthContext";
import { NuqsAdapter } from "nuqs/adapters/next/app";
import { Provider } from "react-redux";
import { store } from "@/store/store";

export default function ClientProviders({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <Provider store={store}>
      <NuqsAdapter>
        <AuthProvider>{children}</AuthProvider>
      </NuqsAdapter>
    </Provider>
  );
} 