import type { ReactNode } from "react";

import { SettingsLayoutClient } from "@/components/settings/SettingsLayoutClient";

export default function SettingsLayout({ children }: { children: ReactNode }) {
  return <SettingsLayoutClient>{children}</SettingsLayoutClient>;
}
