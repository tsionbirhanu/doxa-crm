"use client";

import { cn } from "@/lib/utils";
import type { ProjectHealth } from "@/types/api";

const healthConfig: Record<ProjectHealth, { dot: string; label: string; ring: string; text: string }> = {
  green: {
    dot: "bg-emerald-500",
    label: "On Track",
    ring: "ring-emerald-100 bg-emerald-50",
    text: "text-emerald-700",
  },
  red: {
    dot: "bg-red-500",
    label: "Delayed",
    ring: "ring-red-100 bg-red-50",
    text: "text-red-700",
  },
  yellow: {
    dot: "bg-amber-500",
    label: "At Risk",
    ring: "ring-amber-100 bg-amber-50",
    text: "text-amber-700",
  },
};

interface HealthPillProps {
  health: ProjectHealth;
  size?: "sm" | "lg";
}

export function HealthPill({ health, size = "sm" }: HealthPillProps) {
  const config = healthConfig[health];

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full font-medium ring-1 ring-inset",
        config.ring,
        config.text,
        size === "lg" ? "gap-2.5 px-3.5 py-2 text-sm" : "gap-2 px-2.5 py-1 text-xs",
      )}
    >
      <span className={cn("rounded-full", config.dot, size === "lg" ? "h-3 w-3" : "h-2 w-2")} />
      {config.label}
    </span>
  );
}

export function getHealthLabel(health: ProjectHealth): string {
  return healthConfig[health].label;
}
