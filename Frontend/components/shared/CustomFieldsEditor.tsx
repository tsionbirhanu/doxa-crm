"use client";

import { Plus, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export interface CustomFieldRow {
  id: string;
  key: string;
  value: string;
}

interface CustomFieldsEditorProps {
  disabled?: boolean;
  onChange: (rows: CustomFieldRow[]) => void;
  rows: CustomFieldRow[];
}

function createRow(): CustomFieldRow {
  return {
    id: crypto.randomUUID(),
    key: "",
    value: "",
  };
}

export function customFieldsRecordToRows(record: Record<string, string | number | boolean> | undefined): CustomFieldRow[] {
  return Object.entries(record ?? {}).map(([key, value], index) => ({
    id: `${key}-${index}`,
    key,
    value: String(value),
  }));
}

export function customFieldRowsToRecord(rows: CustomFieldRow[]): Record<string, string | number | boolean> {
  return rows.reduce<Record<string, string | number | boolean>>((record, row) => {
    const key = row.key.trim();
    if (!key) {
      return record;
    }

    const value = row.value.trim();
    if (value.toLowerCase() === "true") {
      record[key] = true;
      return record;
    }

    if (value.toLowerCase() === "false") {
      record[key] = false;
      return record;
    }

    const numericValue = Number(value);
    record[key] = value !== "" && Number.isFinite(numericValue) ? numericValue : value;
    return record;
  }, {});
}

export function CustomFieldsEditor({ disabled = false, onChange, rows }: CustomFieldsEditorProps) {
  function updateRow(id: string, patch: Partial<Pick<CustomFieldRow, "key" | "value">>) {
    onChange(rows.map((row) => (row.id === id ? { ...row, ...patch } : row)));
  }

  function removeRow(id: string) {
    onChange(rows.filter((row) => row.id !== id));
  }

  return (
    <div className="space-y-3">
      {rows.map((row) => (
        <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]" key={row.id}>
          <Input disabled={disabled} onChange={(event) => updateRow(row.id, { key: event.target.value })} placeholder="Field" value={row.key} />
          <Input disabled={disabled} onChange={(event) => updateRow(row.id, { value: event.target.value })} placeholder="Value" value={row.value} />
          <Button disabled={disabled} onClick={() => removeRow(row.id)} size="icon" type="button" variant="ghost">
            <X className="h-4 w-4" aria-hidden="true" />
            <span className="sr-only">Remove field</span>
          </Button>
        </div>
      ))}
      <Button disabled={disabled} onClick={() => onChange([...rows, createRow()])} size="sm" type="button" variant="outline">
        <Plus className="h-4 w-4" aria-hidden="true" />
        Add Field
      </Button>
    </div>
  );
}
