"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Save } from "lucide-react";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import {
  CustomFieldsEditor,
  customFieldRowsToRecord,
  customFieldsRecordToRows,
  type CustomFieldRow,
} from "@/components/shared/CustomFieldsEditor";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Sheet, SheetBody, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { api } from "@/lib/api";
import type { Account, AccountCreate, AccountTier, AccountUpdate, User } from "@/types/api";

const accountTiers: AccountTier[] = ["enterprise", "smb", "startup"];

const accountFormSchema = z.object({
  address_city: z.string().optional(),
  address_country: z.string().optional(),
  address_street: z.string().optional(),
  custom_fields: z.array(
    z.object({
      id: z.string(),
      key: z.string(),
      value: z.string(),
    }),
  ),
  industry: z.string().min(1, "Industry is required."),
  name: z.string().min(1, "Name is required."),
  owner_id: z.string().optional(),
  size: z.string().min(1, "Size is required."),
  tier: z.enum(accountTiers),
  website: z.string().min(1, "Website is required."),
});

type AccountFormValues = z.infer<typeof accountFormSchema>;

interface AccountFormProps {
  account?: Account | null;
  onOpenChange: (open: boolean) => void;
  onSaved?: (account: Account) => void;
  open: boolean;
}

function addressValue(account: Account | null | undefined, key: string): string {
  const value = account?.address?.[key];
  return typeof value === "string" ? value : "";
}

function emptyValues(): AccountFormValues {
  return {
    address_city: "",
    address_country: "",
    address_street: "",
    custom_fields: [],
    industry: "",
    name: "",
    owner_id: "",
    size: "",
    tier: "smb",
    website: "",
  };
}

function valuesFromAccount(account?: Account | null): AccountFormValues {
  if (!account) {
    return emptyValues();
  }

  return {
    address_city: addressValue(account, "city"),
    address_country: addressValue(account, "country"),
    address_street: addressValue(account, "street"),
    custom_fields: customFieldsRecordToRows(account.custom_fields),
    industry: account.industry,
    name: account.name,
    owner_id: account.owner_id,
    size: account.size,
    tier: account.tier,
    website: account.website,
  };
}

function fieldError(message?: string) {
  return message ? <p className="mt-1 text-xs text-red-600">{message}</p> : null;
}

function buildPayload(values: AccountFormValues): AccountCreate | AccountUpdate {
  return {
    address: {
      city: values.address_city ?? "",
      country: values.address_country ?? "",
      street: values.address_street ?? "",
    },
    custom_fields: customFieldRowsToRecord(values.custom_fields),
    industry: values.industry,
    name: values.name,
    owner_id: values.owner_id || null,
    size: values.size,
    tier: values.tier,
    website: values.website,
  };
}

export function AccountForm({ account, onOpenChange, onSaved, open }: AccountFormProps) {
  const queryClient = useQueryClient();
  const form = useForm<AccountFormValues>({
    defaultValues: valuesFromAccount(account),
    resolver: zodResolver(accountFormSchema),
  });
  const customFields = form.watch("custom_fields");

  useEffect(() => {
    if (open) {
      form.reset(valuesFromAccount(account));
    }
  }, [account, form, open]);

  const usersQuery = useQuery({
    queryFn: () => api.get<User[]>("/users/"),
    queryKey: ["users", "owner-select"],
    retry: false,
  });

  const saveAccount = useMutation({
    mutationFn: (values: AccountFormValues) => {
      const payload = buildPayload(values);
      if (account) {
        return api.patch<Account, AccountUpdate>(`/accounts/${account.id}`, payload);
      }

      return api.post<Account, AccountCreate>("/accounts/", payload as AccountCreate);
    },
    onSuccess: (savedAccount) => {
      void queryClient.invalidateQueries({ queryKey: ["accounts"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      onSaved?.(savedAccount);
      onOpenChange(false);
    },
  });

  const submitting = saveAccount.isPending;

  return (
    <Sheet onOpenChange={onOpenChange} open={open}>
      <SheetContent>
        <SheetHeader>
          <SheetTitle>{account ? "Edit Account" : "New Account"}</SheetTitle>
          <SheetDescription>{account ? "Update firmographic and ownership fields." : "Create an account for contacts and deals."}</SheetDescription>
        </SheetHeader>
        <form className="flex min-h-0 flex-1 flex-col" onSubmit={form.handleSubmit((values) => saveAccount.mutate(values))}>
          <SheetBody className="space-y-5">
            <div>
              <Label htmlFor="account_name">Name</Label>
              <Input id="account_name" disabled={submitting} {...form.register("name")} />
              {fieldError(form.formState.errors.name?.message)}
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <Label htmlFor="industry">Industry</Label>
                <Input id="industry" disabled={submitting} {...form.register("industry")} />
                {fieldError(form.formState.errors.industry?.message)}
              </div>
              <div>
                <Label htmlFor="size">Size</Label>
                <Input id="size" disabled={submitting} {...form.register("size")} />
                {fieldError(form.formState.errors.size?.message)}
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <Label htmlFor="website">Website</Label>
                <Input id="website" disabled={submitting} {...form.register("website")} />
                {fieldError(form.formState.errors.website?.message)}
              </div>
              <div>
                <Label htmlFor="tier">Tier</Label>
                <select
                  className="h-10 w-full rounded-md border border-[var(--input)] bg-white px-3 text-sm text-slate-950"
                  disabled={submitting}
                  id="tier"
                  {...form.register("tier")}
                >
                  {accountTiers.map((tier) => (
                    <option key={tier} value={tier}>
                      {tier}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <Label htmlFor="owner_id">Owner</Label>
              <select
                className="h-10 w-full rounded-md border border-[var(--input)] bg-white px-3 text-sm text-slate-950"
                disabled={submitting}
                id="owner_id"
                {...form.register("owner_id")}
              >
                <option value="">Current user</option>
                {(usersQuery.data ?? []).map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.full_name}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <div>
                <Label htmlFor="address_street">Street</Label>
                <Input id="address_street" disabled={submitting} {...form.register("address_street")} />
              </div>
              <div>
                <Label htmlFor="address_city">City</Label>
                <Input id="address_city" disabled={submitting} {...form.register("address_city")} />
              </div>
              <div>
                <Label htmlFor="address_country">Country</Label>
                <Input id="address_country" disabled={submitting} {...form.register("address_country")} />
              </div>
            </div>

            <div>
              <Label>Custom Fields</Label>
              <div className="mt-2">
                <CustomFieldsEditor
                  disabled={submitting}
                  onChange={(rows: CustomFieldRow[]) => form.setValue("custom_fields", rows, { shouldDirty: true })}
                  rows={customFields}
                />
              </div>
            </div>

            {saveAccount.isError ? (
              <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">Could not save account.</div>
            ) : null}
          </SheetBody>
          <SheetFooter>
            <Button disabled={submitting} onClick={() => onOpenChange(false)} type="button" variant="outline">
              Cancel
            </Button>
            <Button className="bg-[#2563EB] hover:bg-blue-700" disabled={submitting} type="submit">
              <Save className="h-4 w-4" aria-hidden="true" />
              Save Account
            </Button>
          </SheetFooter>
        </form>
      </SheetContent>
    </Sheet>
  );
}
