"use client";

import { Download } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { downloadReport, type ExportParams } from "@/lib/report-export";

interface ExportButtonsProps {
  params?: ExportParams;
  report: string;
}

export function ExportButtons({ params = {}, report }: ExportButtonsProps) {
  const [exporting, setExporting] = useState<"csv" | "pdf" | null>(null);

  async function runExport(format: "csv" | "pdf") {
    setExporting(format);
    try {
      await downloadReport(format, report, params);
    } finally {
      setExporting(null);
    }
  }

  return (
    <>
      <Button disabled={exporting !== null} onClick={() => void runExport("csv")} size="sm" type="button" variant="outline">
        <Download className="h-4 w-4" aria-hidden="true" />
        {exporting === "csv" ? "Exporting" : "Export CSV"}
      </Button>
      <Button disabled={exporting !== null} onClick={() => void runExport("pdf")} size="sm" type="button" variant="outline">
        <Download className="h-4 w-4" aria-hidden="true" />
        {exporting === "pdf" ? "Exporting" : "Export PDF"}
      </Button>
    </>
  );
}
