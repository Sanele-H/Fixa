// The report button: flag a job, a provider or a message the checks missed. The team reviews it.

import { useMutation } from "@tanstack/react-query";
import { postJson } from "./client";
import type { ReportReason, ReportTargetType } from "./types";

/** POST /api/reports. One report per person, target and reason (409 if repeated). */
export type NewReport = {
  target_type: ReportTargetType;
  target_id: string;
  reason: ReportReason;
  note?: string;
};

export function useSendReport() {
  return useMutation({
    mutationFn: (report: NewReport) => postJson<{ id: string; status: string }>("/api/reports", report),
  });
}
