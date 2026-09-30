// Paying for a job: the agreed plan, changing it (both sides must agree), and paying in the app.
//
// Card details never touch the app. Paying sends the browser to the payment company's hosted
// checkout (our test page in the demo, PayFast when it's switched on), which brings it back to
// the job page. The payment company tells the server the result, so the job page just keeps
// refreshing until the receipt shows up.
//
// Cached under ["jobs", jobId, "payment"], so a job's state change (confirm, "It's done") also
// refreshes what's due.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getJson, postJson } from "./client";
import { jobKeys } from "./jobs";
import type { PaymentMethod } from "./types";

/** Often enough that a receipt shows soon after coming back from the checkout. */
const PAYMENT_REFRESH_INTERVAL_MS = 5_000;

/** deposit (once confirmed), balance (the rest after a deposit) or full (everything at once). */
export type PaymentKind = "deposit" | "balance" | "full";

/** What the two sides agreed. `deposit_rands` is 0 unless the method is in_app_split. */
export type PaymentPlan = {
  method: PaymentMethod;
  total_rands: number;
  deposit_rands: number;
  agreed_at: string;
};

/** A change one side asked for, waiting for the other side's answer. */
export type PaymentPlanChange = {
  id: string;
  method: PaymentMethod;
  deposit_rands: number;
  proposed_by_me: boolean;
  created_at: string;
};

/** A payment that went through. `gateway` is "mock" (the test checkout) or "payfast". */
export type Receipt = {
  id: string;
  kind: PaymentKind;
  amount_rands: number;
  paid_at: string;
  gateway: "mock" | "payfast";
  reference: string;
  /**
   * Set when the job was cancelled after paying: refunded (given back), refund_owed (the Fixa
   * team pays it back) or under_review (work had started, so the team decides). Null otherwise.
   */
  refund_state: RefundState | null;
  refund_at: string | null;
};

export type RefundState = "refunded" | "refund_owed" | "under_review";

/** GET /api/jobs/{job_id}/payment: everything the job page shows about paying. */
export type JobPayment = {
  plan: PaymentPlan | null;
  paid_rands: number;
  /** What the customer can pay in the app now, or null (cash, all paid, or not yet). */
  due: { kind: PaymentKind; amount_rands: number } | null;
  /** True before the work starts and before any money has moved. */
  can_change: boolean;
  change: PaymentPlanChange | null;
  receipts: Receipt[];
};

/** POST /api/jobs/{job_id}/payment/changes. */
export type NewPlanChange = {
  method: PaymentMethod;
  deposit_rands?: number;
};

export type PlanChangeAnswer = {
  changeId: string;
  answer: "agree" | "decline";
};

/** POST /api/jobs/{job_id}/payments: where to send the browser to pay. */
export type Checkout = {
  payment_id: string;
  checkout_url: string;
  /** GET: open the URL. POST: submit `fields` to it as a form (PayFast's signed form). */
  method: "GET" | "POST";
  fields: Record<string, string>;
};

export const paymentKeys = {
  payment: (jobId: string) => [...jobKeys.job(jobId), "payment"] as const,
};

/** GET /api/jobs/{job_id}/payment, for the job's customer and its picked provider. */
export function useJobPayment(jobId: string) {
  return useQuery({
    queryKey: paymentKeys.payment(jobId),
    queryFn: () => getJson<JobPayment>(`/api/jobs/${jobId}/payment`),
    refetchInterval: PAYMENT_REFRESH_INTERVAL_MS,
  });
}

/** Puts the payment view the server answered with into the cache. */
function useUpdateCachedPayment(jobId: string) {
  const queryClient = useQueryClient();
  return (payment: JobPayment) => queryClient.setQueryData(paymentKeys.payment(jobId), payment);
}

/** POST /api/jobs/{job_id}/payment/changes: ask the other side to pay a different way. */
export function useAskPlanChange(jobId: string) {
  const updateCachedPayment = useUpdateCachedPayment(jobId);
  return useMutation({
    mutationFn: (change: NewPlanChange) => postJson<JobPayment>(`/api/jobs/${jobId}/payment/changes`, change),
    onSuccess: updateCachedPayment,
  });
}

/**
 * POST /api/jobs/{job_id}/payment/changes/{change_id}/agree or /decline. Declining your own
 * change takes it back.
 */
export function useAnswerPlanChange(jobId: string) {
  const updateCachedPayment = useUpdateCachedPayment(jobId);
  return useMutation({
    mutationFn: ({ changeId, answer }: PlanChangeAnswer) =>
      postJson<JobPayment>(`/api/jobs/${jobId}/payment/changes/${changeId}/${answer}`),
    onSuccess: updateCachedPayment,
  });
}

/**
 * Sends the browser to the checkout: opens the URL, or builds and submits the payment
 * company's form. Either way the page is left, and comes back to the job afterwards.
 */
export function openCheckout(checkout: Checkout) {
  if (checkout.method === "GET") {
    window.location.assign(checkout.checkout_url);
    return;
  }
  const form = document.createElement("form");
  form.method = "POST";
  form.action = checkout.checkout_url;
  for (const [name, value] of Object.entries(checkout.fields)) {
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = name;
    input.value = value;
    form.append(input);
  }
  document.body.append(form);
  form.submit();
}

/** POST /api/jobs/{job_id}/payments, then off to the checkout (customer only). */
export function usePayDue(jobId: string) {
  return useMutation({
    mutationFn: () => postJson<Checkout>(`/api/jobs/${jobId}/payments`),
    onSuccess: openCheckout,
  });
}
