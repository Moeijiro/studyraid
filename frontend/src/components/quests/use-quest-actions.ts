"use client";

import { useCallback } from "react";
import { ApiError, del, post } from "@/lib/api";
import { invalidate } from "@/lib/store";
import type { Completion, Quest } from "@/lib/types";
import { useRewardFeedback, useToasts } from "@/components/game/toasts";

const AFFECTED = ["/api/quests", "/api/me/summary", "/api/analytics", "/api/me/heatmap", "/api/me/achievements", "/api/parties", "/api/leaderboards"];

export function useQuestActions() {
  const reward = useRewardFeedback();
  const { push } = useToasts();

  const fail = useCallback((e: unknown) => push({ kind: "error", title: e instanceof ApiError ? e.message : "Something went wrong." }), [push]);

  const complete = useCallback(
    async (q: Quest) => {
      try {
        const r = await post<Completion>(`/api/quests/${q.id}/complete`);
        reward(r, q.title, r.level_before);
        invalidate(...AFFECTED);
        return r;
      } catch (e) {
        fail(e);
        invalidate("/api/quests", "/api/me/summary");
      }
    },
    [reward, fail],
  );

  const transition = useCallback(
    async (q: Quest, action: "start" | "abandon") => {
      try {
        await post(`/api/quests/${q.id}/${action}`);
        invalidate("/api/quests", "/api/me/summary", "/api/analytics");
      } catch (e) {
        fail(e);
      }
    },
    [fail],
  );

  const remove = useCallback(
    async (q: Quest) => {
      try {
        await del(`/api/quests/${q.id}`);
        invalidate("/api/quests", "/api/me/summary");
      } catch (e) {
        fail(e);
      }
    },
    [fail],
  );

  return { complete, start: (q: Quest) => transition(q, "start"), abandon: (q: Quest) => transition(q, "abandon"), remove };
}
