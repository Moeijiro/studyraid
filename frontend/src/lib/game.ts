import type { Difficulty, Tier } from "./types";

export const DIFFICULTY: Record<Difficulty, { label: string; color: string; base: number }> = {
  easy: { label: "Easy", color: "var(--color-easy)", base: 20 },
  normal: { label: "Normal", color: "var(--color-normal)", base: 40 },
  hard: { label: "Hard", color: "var(--color-hard)", base: 75 },
  legendary: { label: "Legendary", color: "var(--color-legendary)", base: 150 },
};

export const TIER: Record<Tier, { label: string; color: string }> = {
  bronze: { label: "Bronze", color: "var(--color-bronze)" },
  silver: { label: "Silver", color: "var(--color-silver)" },
  gold: { label: "Gold", color: "var(--color-gold)" },
};

/** Rank titles shown next to the level. Cosmetic only. */
export function rankTitle(level: number) {
  if (level >= 30) return "Archmage";
  if (level >= 20) return "Sage";
  if (level >= 15) return "Scholar";
  if (level >= 10) return "Adept";
  if (level >= 5) return "Apprentice";
  return "Novice";
}

export const SUBJECTS = ["Mathematics", "Physics", "Chemistry", "Biology", "Computer Science", "History", "Literature", "Languages", "Art", "Personal"];

/** A stable hue per subject, so the same subject is the same color everywhere. */
export function subjectHue(subject: string) {
  const fixed: Record<string, number> = {
    mathematics: 250, physics: 205, chemistry: 160, biology: 130, "computer science": 285,
    history: 30, literature: 340, languages: 55, art: 310, personal: 185,
  };
  const key = subject.trim().toLowerCase();
  if (key in fixed) return fixed[key];
  let h = 0;
  for (const ch of key) h = (h * 31 + ch.charCodeAt(0)) % 360;
  return h;
}

/** Mirrors the backend's base XP formula for instant previews (the server stays authoritative). */
export function previewXp(difficulty: Difficulty, minutes: number | null) {
  return DIFFICULTY[difficulty].base + Math.round(Math.min(Math.max(minutes ?? 0, 0), 240) * 0.3);
}

export const TIMEZONES = (() => {
  try {
    return (Intl as unknown as { supportedValuesOf(k: string): string[] }).supportedValuesOf("timeZone");
  } catch {
    return ["UTC"];
  }
})();
