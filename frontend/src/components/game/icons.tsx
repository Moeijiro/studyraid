import {
  Atom, BookOpen, Brain, CalendarCheck, ChevronsUp, Compass, Crown, Flame, FlameKindling, GraduationCap, Leaf, Lock, Map as MapIcon,
  Moon, Rocket, Shapes, Shield, Skull, Star, Sunrise, Sword, Timer, Trophy, Users, WandSparkles, Zap, type LucideIcon,
} from "lucide-react";

// Achievement and party icons arrive from the API as names.
const ICONS: Record<string, LucideIcon> = {
  sword: Sword, map: MapIcon, "graduation-cap": GraduationCap, wand: WandSparkles, skull: Skull, "flame-kindling": FlameKindling,
  lock: Lock, brain: Brain, timer: Timer, flame: Flame, shield: Shield, moon: Moon, sunrise: Sunrise, "calendar-check": CalendarCheck,
  shapes: Shapes, "chevrons-up": ChevronsUp, users: Users, trophy: Trophy, star: Star, crown: Crown, book: BookOpen, rocket: Rocket,
  atom: Atom, leaf: Leaf, zap: Zap, compass: Compass,
};

export function NamedIcon({ name, className }: { name: string; className?: string }) {
  const Icon = ICONS[name] ?? Star;
  return <Icon className={className} aria-hidden="true" />;
}
