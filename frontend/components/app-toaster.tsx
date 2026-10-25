"use client";

import { Toaster } from "react-hot-toast";

export default function AppToaster() {
  return (
    <Toaster
      position="top-right"
      gutter={10}
      toastOptions={{
        duration: 4000,
        style: {
          background: "#fffefa",
          border: "1px solid #e8e5de",
          borderRadius: "12px",
          boxShadow: "0 12px 30px rgba(39, 48, 69, 0.14)",
          color: "#273045",
          fontSize: "14px",
          maxWidth: "min(360px, calc(100vw - 32px))",
        },
        success: { iconTheme: { primary: "#52825b", secondary: "#fffefa" } },
        error: { iconTheme: { primary: "#b3261e", secondary: "#fffefa" } },
      }}
    />
  );
}
