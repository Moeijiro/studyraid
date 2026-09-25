// Shapes returned by the StudyRaid API.

export type Difficulty = "easy" | "normal" | "hard" | "legendary";
export type Priority = "low" | "normal" | "high";
export type QuestStatus = "planned" | "active" | "completed" | "failed" | "expired";

export type User = {
  id: number;
  email: string;
  username: string;
  display_name: string;
  timezone: string;
  avatar_hue: number;
  show_on_leaderboards: boolean;
  created_at: string;
};

export type TokenResponse = { access_token: string; expires_at: string; user: User };

export type Level = { level: number; total_xp: number; xp_into_level: number; xp_for_level: number; progress: number };

export type Quest = {
  id: number;
  title: string;
  description: string;
  subject: string;
  difficulty: Difficulty;
  priority: Priority;
  status: QuestStatus;
  estimated_minutes: number | null;
  due_at: string | null;
  base_xp: number;
  xp_awarded: number | null;
  coins_awarded: number | null;
  created_at: string;
  started_at: string | null;
  closed_at: string | null;
};

export type RewardLine = { label: string; xp: number };
export type AchievementBrief = { code: string; name: string; icon: string; tier: Tier };

export type Completion = {
  quest: Quest;
  xp: number;
  coins: number;
  breakdown: RewardLine[];
  level_before: number;
  level: Level;
  streak: number;
  achievements: AchievementBrief[];
};

export type Tier = "bronze" | "silver" | "gold";

export type Achievement = {
  code: string;
  name: string;
  description: string;
  icon: string;
  tier: Tier;
  xp: number;
  target: number;
  progress: number;
  unlocked_at: string | null;
};

export type DayPoint = { date: string; xp: number; focus_minutes: number; quests: number };

export type Contribution = { user_id: number; display_name: string; avatar_hue: number; value: number };

export type Challenge = {
  id: number;
  party_id: number;
  title: string;
  metric: "quests_completed" | "focus_minutes" | "xp";
  unit: string;
  target: number;
  progress: number;
  reward_xp: number;
  starts_at: string;
  ends_at: string;
  status: "active" | "completed" | "failed";
  completed_at: string | null;
  contributions: Contribution[];
};

export type PartySummary = {
  id: number;
  name: string;
  description: string;
  icon: string;
  hue: number;
  member_count: number;
  role: "owner" | "member" | null;
  weekly_xp: number;
  active_challenge: Challenge | null;
};

export type PartyMember = {
  user_id: number;
  username: string;
  display_name: string;
  avatar_hue: number;
  role: "owner" | "member";
  joined_at: string;
  weekly_xp: number;
  weekly_quests: number;
  weekly_focus_minutes: number;
  weekly_share: number;
  total_xp: number;
};

export type ActivityItem = { id: number; user_id: number; display_name: string; avatar_hue: number; kind: string; text: string; xp: number; at: string };

export type PartyDetail = Omit<PartySummary, "active_challenge"> & {
  invite_code: string | null;
  party_xp: number;
  week_starts_at: string;
  members: PartyMember[];
  challenges: Challenge[];
  past_challenges: Challenge[];
  activity: ActivityItem[];
};

export type Invite = { id: number; party: { id: number; name: string; icon: string; hue: number }; from: string; created_at: string };

export type FocusSession = {
  id: number;
  quest_id: number | null;
  planned_minutes: number;
  status: "active" | "completed" | "cancelled";
  started_at: string;
  ended_at: string | null;
  actual_minutes: number;
  xp_awarded: number;
  quest_title?: string | null;
};

export type FocusSummary = {
  today_sessions: number;
  today_minutes: number;
  week_sessions: number;
  week_minutes: number;
  total_sessions: number;
  total_minutes: number;
};

export type Streak = { current: number; longest: number; active_today: boolean; at_risk: boolean; freezes: number };

export type Summary = {
  user: User;
  level: Level;
  coins: number;
  streak: Streak;
  weekly_xp: number;
  today_quests: Quest[];
  completed_today: Quest[];
  upcoming_quests: Quest[];
  week: DayPoint[];
  focus: FocusSummary;
  active_focus_id: number | null;
  recent_achievements: Achievement[];
  parties: PartySummary[];
  unread_notifications: number;
};

export type Notification = { id: number; kind: string; title: string; body: string; link: string | null; created_at: string; read: boolean };

export type HeatDay = { date: string; xp: number; level: number; active: boolean; frozen: boolean };
export type Heatmap = { start: string; end: string; thresholds: number[]; days: HeatDay[] };

export type Analytics = {
  days: number;
  series: DayPoint[];
  totals: { xp: number; quests_completed: number; focus_minutes: number; focus_sessions: number; active_days: number; avg_daily_xp: number };
  completion_rate: number | null;
  closed_quests: { completed: number; failed: number; expired: number };
  most_productive_weekday: { weekday: number; name: string; avg_xp: number } | null;
  weekday_avg_xp: { weekday: number; name: string; avg_xp: number }[];
  best_day: DayPoint | null;
  subjects: { subject: string; quests: number; xp: number; focus_minutes: number }[];
  top_subject: string | null;
  weekly: { week_start: string; xp: number }[];
};

export type LeaderboardRow = { user_id: number; display_name: string; username: string; avatar_hue: number; value: number; is_me: boolean; rank: number };
export type Leaderboard = { scope: string; metric: "xp" | "quests" | "focus"; since: string; rows: LeaderboardRow[] };

export type RealtimeEvent =
  | { type: "hello" | "ping" }
  | { type: "xp"; amount: number; coins: number; source: string; balance: number; level: Level }
  | { type: "level_up"; level: number }
  | { type: "streak"; current: number; longest: number; active_today: boolean }
  | { type: "achievement"; achievement: Achievement }
  | { type: "notification"; notification: Notification }
  | { type: "challenge_progress"; challenge_id: number; party_id: number; progress: number; target: number; by_user_id: number }
  | { type: "challenge_completed"; challenge_id: number; party_id: number; title: string }
  | { type: "quest_completed"; quest_id: number; xp: number }
  | { type: "party_activity"; user_id: number; display_name: string }
  | { type: "focus_started" | "focus_completed" | "party_invite" | "party_member_joined" | "party_member_left"; [key: string]: unknown };
