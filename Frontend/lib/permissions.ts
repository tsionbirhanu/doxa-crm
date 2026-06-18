"use client";

import { authClient } from "@/lib/auth-client";
import { normalizeRole, type CrmRole } from "@/lib/auth-types";
import { useAuthStore } from "@/stores/auth-store";

const salesWriteRoles = new Set<CrmRole>(["super_admin", "sales_manager", "sales_rep"]);
const leadWriteRoles = new Set<CrmRole>(["super_admin", "sales_manager", "sales_rep", "marketing_manager", "marketing_rep"]);
const contactWriteRoles = new Set<CrmRole>([
  "super_admin",
  "sales_manager",
  "sales_rep",
  "marketing_manager",
  "marketing_rep",
  "customer_success",
]);
const accountWriteRoles = new Set<CrmRole>(["super_admin", "sales_manager", "sales_rep", "customer_success"]);
const activityWriteRoles = new Set<CrmRole>([
  "super_admin",
  "sales_manager",
  "sales_rep",
  "marketing_manager",
  "marketing_rep",
  "customer_success",
]);
const campaignWriteRoles = new Set<CrmRole>(["super_admin", "marketing_manager", "marketing_rep"]);
const projectWriteRoles = new Set<CrmRole>(["super_admin", "sales_manager", "customer_success"]);
const pipelineAdminRoles = new Set<CrmRole>(["super_admin", "sales_manager"]);
const settingsRoles = new Set<CrmRole>(["super_admin", "sales_manager"]);

export interface Permissions {
  canAccessSettings: boolean;
  canAdminPipeline: boolean;
  canManageUsers: boolean;
  canWriteAccounts: boolean;
  canWriteActivities: boolean;
  canWriteCampaigns: boolean;
  canWriteContacts: boolean;
  canWriteDeals: boolean;
  canWriteLeads: boolean;
  canWriteProjects: boolean;
  canWriteTasks: boolean;
  role: CrmRole;
}

export function permissionsForRole(role: CrmRole): Permissions {
  return {
    canAccessSettings: settingsRoles.has(role),
    canAdminPipeline: pipelineAdminRoles.has(role),
    canManageUsers: role === "super_admin",
    canWriteAccounts: accountWriteRoles.has(role),
    canWriteActivities: activityWriteRoles.has(role),
    canWriteCampaigns: campaignWriteRoles.has(role),
    canWriteContacts: contactWriteRoles.has(role),
    canWriteDeals: salesWriteRoles.has(role),
    canWriteLeads: leadWriteRoles.has(role),
    canWriteProjects: projectWriteRoles.has(role),
    canWriteTasks: activityWriteRoles.has(role),
    role,
  };
}

export function usePermissions(): Permissions {
  const session = authClient.useSession();
  const storedUser = useAuthStore((state) => state.user);
  const role = normalizeRole(session.data?.user?.role ?? storedUser?.role);
  return permissionsForRole(role);
}
