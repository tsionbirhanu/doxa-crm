import { Calendar, CheckSquare, Mail, Phone, StickyNote, type LucideIcon } from "lucide-react";

import type { ActivityType } from "@/types/api";

interface ActivityTypeIconProps {
  className?: string;
  type: ActivityType | "deal";
}

export function getActivityTypeIcon(type: ActivityType | "deal"): LucideIcon {
  const icons: Record<ActivityType | "deal", LucideIcon> = {
    call: Phone,
    deal: CheckSquare,
    email: Mail,
    meeting: Calendar,
    note: StickyNote,
    task: CheckSquare,
  };

  return icons[type];
}

export function ActivityTypeIcon({ className, type }: ActivityTypeIconProps) {
  const Icon = getActivityTypeIcon(type);
  return <Icon className={className} aria-hidden="true" />;
}
