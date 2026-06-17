"use client";

import { Toaster as Sonner, type ToasterProps } from "sonner";

export function Toaster(props: ToasterProps) {
  return (
    <Sonner
      closeButton
      position="top-right"
      richColors
      toastOptions={{
        classNames: {
          error: "border-red-200",
          success: "border-emerald-200",
        },
      }}
      {...props}
    />
  );
}
