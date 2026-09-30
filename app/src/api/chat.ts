// Chat on a job: GET and POST /api/jobs/{job_id}/messages. Each reader gets every message
// already translated into their own language, with contact details hidden until `confirmed`.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getJson, postJson } from "./client";
import type { Message } from "./types";

/** How often an open chat checks for new messages (contracts/api.md: every 3 s). */
const MESSAGES_REFRESH_INTERVAL_MS = 3_000;

export const chatKeys = {
  /** Under the job's key (see jobs.ts), so it refreshes with the job. */
  messages: (jobId: string) => ["jobs", jobId, "messages"] as const,
};

/**
 * POST /api/jobs/{job_id}/messages. A customer whose job has several quoting providers must
 * say who the message is for with `provider_id`; nobody else needs it.
 */
export type NewMessage = {
  text: string;
  provider_id?: string;
};

/**
 * GET /api/jobs/{job_id}/messages: every message this person may read, oldest first.
 * Fetches the whole list every 3 s while the chat is open. That's cheap because the server
 * caches translations; switch to the contract's ?after=<message_id> if long chats get slow.
 */
export function useMessages(jobId: string) {
  return useQuery({
    queryKey: chatKeys.messages(jobId),
    queryFn: () => getJson<Message[]>(`/api/jobs/${jobId}/messages`),
    refetchInterval: MESSAGES_REFRESH_INTERVAL_MS,
  });
}

/**
 * POST /api/jobs/{job_id}/messages: sends a message. It shows in the list straight away,
 * then the list is fetched again so it matches the server.
 */
export function useSendMessage(jobId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (newMessage: NewMessage) => postJson<Message>(`/api/jobs/${jobId}/messages`, newMessage),
    onSuccess: (message) => {
      queryClient.setQueryData<Message[]>(chatKeys.messages(jobId), (messages = []) => [...messages, message]);
      queryClient.invalidateQueries({ queryKey: chatKeys.messages(jobId) });
    },
  });
}
