export const CRM_ROLES = [
  "super_admin",
  "sales_manager",
  "sales_rep",
  "marketing_manager",
  "marketing_rep",
  "customer_success",
  "read_only",
] as const;

export type CrmRole = (typeof CRM_ROLES)[number];

export interface DoxaUser {
  id: string;
  email: string;
  full_name: string;
  role: CrmRole;
}

export interface DoxaSession {
  user: DoxaUser;
  token: string;
}

export function isCrmRole(value: unknown): value is CrmRole {
  return typeof value === "string" && CRM_ROLES.includes(value as CrmRole);
}

export function normalizeRole(value: unknown): CrmRole {
  return isCrmRole(value) ? value : "sales_rep";
}
