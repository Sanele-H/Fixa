// A provider's work record: logging work done outside the app, and exporting the record as a PDF.

import { useMutation, useQuery } from "@tanstack/react-query";
import { getBlob, getJson, postJson } from "./client";
import type { OffAppJob, RecordExport, RecordMode, RecordSummary } from "./types";

export const recordKeys = {
  summary: ["record", "summary"] as const,
};

/**
 * POST /api/off-app-jobs. `date` is "YYYY-MM-DD". The customer gets an SMS, and the job
 * counts once they reply YES.
 */
export type NewOffAppJob = {
  customer_phone: string;
  trade_task: string;
  date: string;
  suburb: string;
  amount_rands?: number;
};

/** POST /api/off-app-jobs: logs a past job (provider only). 429 when a monthly or daily limit is hit. */
export function useLogOffAppJob() {
  return useMutation({
    mutationFn: (newOffAppJob: NewOffAppJob) => postJson<OffAppJob>("/api/off-app-jobs", newOffAppJob),
  });
}

/** GET /api/record/summary: the ARPL trade and months of experience for "My record" (provider only). */
export function useRecordSummary() {
  return useQuery({
    queryKey: recordKeys.summary,
    queryFn: () => getJson<RecordSummary>("/api/record/summary"),
  });
}

/** POST /api/record/export: makes the PDF and its verify code (provider only). 429 after too many in a day. */
export function useExportRecord() {
  return useMutation({
    mutationFn: (mode: RecordMode) => postJson<RecordExport>("/api/record/export", { mode }),
  });
}

/**
 * Downloads an export's PDF from its `download_url`. The link needs the login token, so it
 * can't be a plain <a href>: fetch the file with this, then share it (Web Share API) or open
 * it with URL.createObjectURL.
 */
export function readRecordPdf(recordExport: RecordExport) {
  return getBlob(recordExport.download_url);
}
