export const chartColors = {
  amber: "#F59E0B",
  blue: "#2563EB",
  blueSoft: "#93C5FD",
  green: "#10B981",
  navy: "#0F2444",
  red: "#EF4444",
  sky: "#EFF6FF",
  slate: "#64748B",
};

export function formatMonth(month: string): string {
  const [year, monthNumber] = month.split("-");
  const date = new Date(Number(year), Number(monthNumber) - 1, 1);
  return date.toLocaleDateString("en-US", { month: "short", year: "2-digit" });
}

export function daysOverdue(date: string): number {
  const due = new Date(date);
  const now = new Date();
  const diff = now.getTime() - due.getTime();
  return Math.max(0, Math.ceil(diff / 86400000));
}

export function percent(part: number, total: number): number {
  return total > 0 ? Math.round((part / total) * 1000) / 10 : 0;
}
