"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";

interface LostReasonModalProps {
  isPending?: boolean;
  onCancel: () => void;
  onConfirm: (reason: string) => void;
  open: boolean;
}

export function LostReasonModal({ isPending = false, onCancel, onConfirm, open }: LostReasonModalProps) {
  const [reason, setReason] = useState("");

  return (
    <Dialog
      onOpenChange={(nextOpen) => {
        if (!nextOpen) {
          setReason("");
          onCancel();
        }
      }}
      open={open}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Why was this deal lost?</DialogTitle>
          <DialogDescription>Add the lost reason before moving the deal into Closed Lost.</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4">
          <textarea
            className="min-h-28 w-full rounded-md border border-[var(--input)] bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
            onChange={(event) => setReason(event.target.value)}
            placeholder="Competitor, no budget, timing, poor fit..."
            value={reason}
          />
          <div className="flex justify-end gap-3">
            <Button disabled={isPending} onClick={onCancel} type="button" variant="outline">
              Cancel
            </Button>
            <Button disabled={reason.trim().length === 0 || isPending} onClick={() => onConfirm(reason.trim())} type="button" variant="destructive">
              Mark as Lost
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
