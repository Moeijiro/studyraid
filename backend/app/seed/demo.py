"""Demo world generator.

Replays about ten weeks of study activity for six fictional students through the
real services, in chronological order: quests are created, started, completed or
abandoned, focus sessions run to completion, parties form, challenges start, and
the scheduler runs every six hours to expire quests, send reminders and settle
challenges. XP, levels, streaks, achievements and notifications all come out of
the same code paths a live request uses. Nothing is written straight into
totals.

    python -m app.seed            # create or refresh the demo database
    python -m app.seed --days 90  # longer history
"""

import argparse
import asyncio
import heapq
import logging
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta

from alembic.config import Config
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from alembic import command
from app.api.routes.system import DEMO_EMAIL, DEMO_PASSWORD
from app.core.clock import local_date, utcnow, zone
from app.core.errors import AppError
from app.db import session as db
from app.db.base import Base
from app.db.uow import commit, rollback
from app.engine.rewards import LATE_GRACE, Difficulty
from app.models import ChallengeMetric, Notification, Party, PartyChallenge, PartyInvite, Priority, Quest, User
from app.repositories import quests as quest_repo
from app.seed.content import DESCRIPTIONS, LEGENDARY, PEOPLE, QUEST_TITLES
from app.services import auth, challenges, focus, parties, quests, shop
from app.workers import scheduler

log = logging.getLogger("seed")

Action = Callable[[AsyncSession, datetime], Awaitable[None]]


@dataclass(order=True)
class Event:
    at: datetime
    seq: int
    action: Action = field(compare=False)


class World:
    def __init__(self, days: int, now: datetime, seed: int = 7) -> None:
        self.days = days
        self.now = now
        self.rng = random.Random(seed)
        self.users: dict[str, User] = {}
        self.parties: dict[str, int] = {}
        self._queue: list[Event] = []
        self._seq = 0

    # --- scheduling --------------------------------------------------------------

    def at(self, when: datetime, action: Action) -> None:
        if when <= self.now:
            self._seq += 1
            heapq.heappush(self._queue, Event(when, self._seq, action))

    def local(self, username: str, day: date, hour: float) -> datetime:
        tz = PEOPLE_BY_NAME[username][2]
        h = int(hour)
        m = int((hour - h) * 60)
        return datetime.combine(day, time(h, m), tzinfo=zone(tz)).astimezone(UTC)

    async def run(self, session: AsyncSession) -> None:
        while self._queue:
            event = heapq.heappop(self._queue)
            try:
                await event.action(session, event.at)
                await commit(session)
            except AppError as exc:  # e.g. a quest that expired before its planned completion
                await rollback(session)
                log.debug("skipped event at %s: %s", event.at, exc.message)


PEOPLE_BY_NAME = {p[0]: p for p in PEOPLE}


def _maks_inactive(offset: int) -> bool:
    """Shapes the demo user's history: a 12-day current streak, an earlier run of 22
    days bridged by one streak freeze, and ordinary gaps before that."""
    if offset in (12, 13, 25, 37, 38):
        return True
    if offset > 70:  # the first weeks: trying the app out a few days a week
        return offset % 3 != 0 and offset % 5 != 0
    return offset > 38 and offset % 6 == 0


async def _create_users(session: AsyncSession, world: World, start: datetime) -> None:
    for username, name, tz, _, hue, _ in PEOPLE:
        email = DEMO_EMAIL if username == "maks" else f"{username}@studyraid.dev"
        password = DEMO_PASSWORD if username == "maks" else f"{username}-demo-password"
        user = await auth.register(session, email=email, username=username, display_name=name, password=password, timezone=tz, now=start)
        user.avatar_hue = hue
        world.users[username] = user
    await commit(session)


def _pick_template(world: World, subject: str, legendary_chance: float) -> tuple[str, Difficulty, int]:
    if subject in LEGENDARY and world.rng.random() < legendary_chance:
        title, minutes = world.rng.choice(LEGENDARY[subject])
        return title, Difficulty.LEGENDARY, minutes
    return world.rng.choice(QUEST_TITLES[subject])


def _plan_user_day(world: World, username: str, day: date, offset: int) -> None:
    rng = world.rng
    _, _, _, subjects, _, activity = PEOPLE_BY_NAME[username]
    is_maks = username == "maks"
    active = not _maks_inactive(offset) if is_maks else rng.random() < activity
    today = offset == 0

    # Morning planning happens even on lazy days.
    n_create = rng.choice([2, 3, 3, 3]) if is_maks else rng.choice([1, 2, 2, 3])
    morning = rng.uniform(7.5, 9.5)
    if today and is_maks:
        _plan_maks_today(world, day)
        return
    for i in range(n_create):
        subject = rng.choice(subjects)
        title, difficulty, minutes = _pick_template(world, subject, 0.07 if is_maks else 0.03)
        due_days = rng.choice([1, 1, 2, 2, 3, 4, 5])
        due = None if rng.random() < 0.15 else world.local(username, day + timedelta(days=due_days), rng.choice([18, 20, 21, 23]))

        async def create(session: AsyncSession, now: datetime, u=username, t=title, s=subject, d=difficulty, m=minutes, due=due) -> None:
            open_titles = {q.title for q in await session.scalars(quest_repo.list_query(world.users[u].id, statuses=list(quest_repo.OPEN)))}
            if t in open_titles:  # nobody plans the same assignment twice
                spare = [tpl for tpl in QUEST_TITLES[s] if tpl[0] not in open_titles]
                if not spare:
                    return
                t, d, m = spare[0]
            await quests.create(
                session,
                world.users[u],
                quests.QuestInput(
                    title=t,
                    subject=s,
                    difficulty=d,
                    description=DESCRIPTIONS.get(s, ""),
                    priority=rng.choice([Priority.NORMAL, Priority.NORMAL, Priority.HIGH, Priority.LOW]),
                    estimated_minutes=max(5, m + rng.choice([-10, 0, 0, 5, 15])),
                    due_at=due,
                ),
                now,
            )

        world.at(world.local(username, day, morning + i * 0.05), create)

    world.at(world.local(username, day, morning + 0.3), _start_one(username))

    if not active:
        return

    n_complete = rng.choice([2, 2, 3, 3]) if is_maks else rng.choice([1, 2, 2, 2])
    hours = sorted(rng.uniform(13.0, 22.5) for _ in range(n_complete))
    if is_maks and not today and rng.random() < 0.12:
        hours[-1] = rng.uniform(23.1, 23.8)  # the occasional late night
    if username == "amara" and rng.random() < 0.15:
        hours[0] = rng.uniform(5.3, 6.8)
    for h in hours:
        world.at(world.local(username, day, h), _complete_one(username))

    n_focus = rng.choice([1, 1, 2, 2, 3]) if is_maks else rng.choice([0, 1, 1, 2])
    t = rng.uniform(9.5, 11.0)
    for _ in range(n_focus):
        planned = rng.choice([25, 25, 50, 50, 90] if is_maks else [25, 25, 50])
        world.at(world.local(username, day, t), _focus(username, planned, cancel=rng.random() < 0.05))
        t += planned / 60 + rng.uniform(0.3, 2.5)

    if rng.random() < 0.06:
        world.at(world.local(username, day, 21.9), _abandon_one(username))


def _plan_maks_today(world: World, day: date) -> None:
    """The demo user's current day, laid out relative to the moment the seed runs so
    the dashboard always shows a day in progress: a fresh plan, one quest under
    way, a focus session and two quests already done."""
    midnight = world.local("maks", day, 0.0)
    base = max(midnight + timedelta(minutes=5), world.now - timedelta(hours=4))
    span = world.now - base

    def at(fraction: float) -> datetime:
        return base + span * fraction

    tonight = [world.local("maks", day, 21.0), world.local("maks", day, 23.0)]
    plan = [
        ("Physics", "Circuits practice questions", Difficulty.NORMAL, 45, tonight[0]),
        ("Mathematics", "Problem set 7: integration by parts", Difficulty.HARD, 90, tonight[1]),
        ("Languages", "Spanish vocabulary: 50 cards", Difficulty.EASY, 20, world.local("maks", day + timedelta(days=1), 20.0)),
        ("Computer Science", "Implement a binary search tree", Difficulty.HARD, 90, world.local("maks", day + timedelta(days=2), 21.0)),
    ]
    for i, (subject, title, difficulty, minutes, due) in enumerate(plan):

        async def create(session: AsyncSession, now: datetime, s=subject, t=title, d=difficulty, m=minutes, due=due) -> None:
            maks = world.users["maks"]
            if t in {q.title for q in await session.scalars(quest_repo.list_query(maks.id, statuses=list(quest_repo.OPEN)))}:
                return  # already on the board from an earlier day
            if due <= now:
                due = now + timedelta(hours=26)
            await quests.create(
                session,
                world.users["maks"],
                quests.QuestInput(title=t, subject=s, difficulty=d, description=DESCRIPTIONS.get(s, ""), estimated_minutes=m, due_at=due),
                now,
            )

        world.at(at(0.02 + i * 0.005), create)
    if span >= timedelta(minutes=40):
        world.at(at(0.1), _focus("maks", 25, cancel=False))
    world.at(at(0.72), _complete_one("maks"))
    world.at(at(0.86), _complete_one("maks"))

    world.at(at(0.93), _start_one("maks"))


def _start_one(username: str) -> Action:
    async def action(session: AsyncSession, now: datetime) -> None:
        user = await session.get(User, _uid(username))
        planned = list(await session.scalars(quest_repo.list_query(user.id, statuses=[quest_repo.OPEN[0]]).limit(1)))  # type: ignore[union-attr]
        if planned:
            await quests.start(session, planned[0], now)

    return action


def _complete_one(username: str) -> Action:
    async def action(session: AsyncSession, now: datetime) -> None:
        user = await session.get(User, _uid(username))
        assert user is not None
        candidates = [
            q
            for q in await session.scalars(quest_repo.list_query(user.id, statuses=list(quest_repo.OPEN)))
            if q.created_at < now and (q.due_at is None or now <= q.due_at + LATE_GRACE)
        ]
        if not candidates:
            return
        # Mostly the most urgent quest, sometimes whatever looks fun.
        quest = candidates[0] if SEED_RNG.random() < 0.7 else SEED_RNG.choice(candidates)
        await quests.complete(session, user, quest, now)

    return action


def _focus(username: str, planned: int, cancel: bool) -> Action:
    async def start(session: AsyncSession, now: datetime) -> None:
        user = await session.get(User, _uid(username))
        assert user is not None
        open_quests = list(await session.scalars(quest_repo.list_query(user.id, statuses=list(quest_repo.OPEN)).limit(3)))
        quest_id = open_quests[0].id if open_quests and SEED_RNG.random() < 0.75 else None
        fs = await focus.start(session, user, planned_minutes=planned, quest_id=quest_id, now=now)
        await session.flush()
        end = now + timedelta(minutes=planned if not cancel else planned // 3, seconds=SEED_RNG.randint(5, 80))

        async def finish(session: AsyncSession, at: datetime, fs_id: int = fs.id) -> None:
            owner = await session.get(User, _uid(username))
            assert owner is not None
            if cancel:
                await focus.cancel(session, owner, fs_id, at)
            else:
                await focus.complete(session, owner, fs_id, at)

        _world().at(end, finish)  # still running if `end` is after the demo's "now"

    return start


def _abandon_one(username: str) -> Action:
    async def action(session: AsyncSession, now: datetime) -> None:
        user = await session.get(User, _uid(username))
        open_quests = list(await session.scalars(quest_repo.list_query(user.id, statuses=list(quest_repo.OPEN))))  # type: ignore[union-attr]
        if open_quests:
            await quests.abandon(session, SEED_RNG.choice(open_quests), now)

    return action


_UIDS: dict[str, int] = {}
SEED_RNG = random.Random(11)
_CURRENT: list[World] = []


def _world() -> World:
    return _CURRENT[-1]


def _uid(username: str) -> int:
    return _UIDS[username]


def _plan_social(world: World, today: date, days: int) -> None:
    def day(offset: int) -> date:
        return today - timedelta(days=offset)

    library_offset = min(days - 5, 58)
    olympiad_offset = min(days - 10, 40)

    async def create_library(session: AsyncSession, now: datetime) -> None:
        maks = await session.get(User, _uid("maks"))
        party = await parties.create(
            session,
            maks,
            name="Night Library",
            description="Late-night study crew. Finals are coming, we don't panic.",  # type: ignore[arg-type]
            icon="moon",
            hue=265,
            now=now,
        )
        world.parties["library"] = party.id
        for name in ("lina", "oskar", "yuki"):
            await parties.invite(session, maks, party.id, name, now)  # type: ignore[arg-type]

    world.at(world.local("maks", day(library_offset), 19.0), create_library)

    for i, name in enumerate(("lina", "oskar", "yuki")):

        async def accept(session: AsyncSession, now: datetime, n=name) -> None:
            user = await session.get(User, _uid(n))
            invite = await session.scalar(select(PartyInvite).where(PartyInvite.invitee_id == _uid(n), PartyInvite.status == "pending"))
            if invite is not None:
                await parties.respond(session, user, invite.id, True, now)  # type: ignore[arg-type]

        world.at(world.local("maks", day(library_offset), 19.5 + i * 1.3), accept)

    async def amara_joins(session: AsyncSession, now: datetime) -> None:
        party = await session.get(Party, world.parties["library"])
        await parties.join_by_code(session, await session.get(User, _uid("amara")), party.invite_code, now)  # type: ignore[arg-type,union-attr]

    world.at(world.local("maks", day(library_offset - 9), 17.0), amara_joins)

    async def create_olympiad(session: AsyncSession, now: datetime) -> None:
        dev = await session.get(User, _uid("dev"))
        party = await parties.create(
            session,
            dev,
            name="Physics Olympiad",
            description="Problem of the day, every day.",
            icon="atom",
            hue=200,
            now=now,  # type: ignore[arg-type]
        )
        world.parties["olympiad"] = party.id
        await parties.join_by_code(session, await session.get(User, _uid("maks")), party.invite_code, now)  # type: ignore[arg-type]
        await parties.join_by_code(session, await session.get(User, _uid("oskar")), party.invite_code, now + timedelta(hours=2))  # type: ignore[arg-type]

    world.at(world.local("dev", day(olympiad_offset), 18.0), create_olympiad)

    # Weekly challenges, created by each party's leader on Monday morning.
    monday = today - timedelta(days=today.weekday())
    week = 0
    while True:
        start = monday - timedelta(weeks=week)
        offset = (today - start).days
        if offset >= library_offset:
            break
        quests_week = week % 2 == 0

        # The running week's challenges get placeholder targets that can't be reached
        # during the replay; _tune_current_challenges sets the real target at the end.
        current = week == 0

        async def library_challenge(session: AsyncSession, now: datetime, qw=quests_week, cur=current, week=week) -> None:
            maks = await session.get(User, _uid("maks"))
            party = await session.get(Party, world.parties["library"])
            if qw:
                target = 500 if cur else (25 if week % 4 < 2 else 50)
                await challenges.create(
                    session,
                    maks,
                    party,
                    title=f"Complete {target} quests this week",
                    metric=ChallengeMetric.QUESTS_COMPLETED,
                    target=target,
                    duration_days=7,
                    now=now,
                )  # type: ignore[arg-type]
            else:
                target = 20_000 if cur else (600 if week % 4 < 2 else 900)
                await challenges.create(
                    session,
                    maks,
                    party,
                    title=f"Study {target // 60} hours together",
                    metric=ChallengeMetric.FOCUS_MINUTES,
                    target=target,
                    duration_days=7,
                    now=now,
                )  # type: ignore[arg-type]

        world.at(world.local("maks", start, 9.0), library_challenge)
        if offset < olympiad_offset:

            async def olympiad_challenge(session: AsyncSession, now: datetime, cur=current) -> None:
                dev = await session.get(User, _uid("dev"))
                party = await session.get(Party, world.parties["olympiad"])
                await challenges.create(
                    session,
                    dev,
                    party,
                    title="Earn 2,500 XP together",
                    metric=ChallengeMetric.XP,
                    target=100_000 if cur else 2500,
                    duration_days=7,
                    now=now,
                )  # type: ignore[arg-type]

            world.at(world.local("dev", start, 10.0), olympiad_challenge)
        week += 1

    async def buy_freeze(session: AsyncSession, now: datetime) -> None:
        await shop.buy_streak_freeze(session, await session.get(User, _uid("maks")), now)  # type: ignore[arg-type]

    world.at(world.local("maks", day(33), 20.0), buy_freeze)


def _plan_scheduler(world: World, start: datetime) -> None:
    t = start.replace(minute=0, second=0, microsecond=0)
    while t <= world.now:

        async def tick(session: AsyncSession, now: datetime) -> None:
            await quests.expire_overdue(session, now)
            await scheduler.remind_due_soon(session, now)
            await scheduler.streak_jobs(session, now)
            await challenges.settle_expired(session, now)

        world.at(t, tick)
        t += timedelta(hours=6)


async def _tune_current_challenges(session: AsyncSession, now: datetime) -> None:
    """The running week's challenges were created with unreachable placeholder
    targets. Here each gets a real target so the demo shows it about 70% done.
    Progress is still computed from the replayed activity; only the goal is chosen."""
    for ch in await session.scalars(select(PartyChallenge).where(PartyChallenge.ends_at > now)):
        members = await parties.party_repo.members(session, ch.party_id)
        progress = sum((await challenges.contributions(session, ch, members, now)).values())
        low, _ = challenges.TARGET_BOUNDS[ch.metric]
        target = max(low, int(progress / 0.72))
        step = {ChallengeMetric.QUESTS_COMPLETED: 1, ChallengeMetric.FOCUS_MINUTES: 30, ChallengeMetric.XP: 100}[ch.metric]
        target = max(progress + step, round(target / step) * step)
        ch.target = target
        ch.reward_xp = challenges.default_reward(ch.metric, target, len(members))
        if ch.metric == ChallengeMetric.QUESTS_COMPLETED:
            ch.title = f"Complete {target} quests this week"
        elif ch.metric == ChallengeMetric.FOCUS_MINUTES:
            ch.title = f"Study {target // 60} hours together" if target % 60 == 0 else f"Focus {target} minutes together"
        else:
            ch.title = f"Earn {target:,} XP together"


async def build(days: int = 100) -> dict[str, object]:
    now = utcnow().replace(second=0, microsecond=0)
    world = World(days, now)
    _CURRENT.append(world)
    maks_today = local_date(now, PEOPLE_BY_NAME["maks"][2])
    first_day = maks_today - timedelta(days=days)
    start = datetime.combine(first_day, time(0, 0), tzinfo=UTC)

    async with db.SessionLocal() as session:
        await _create_users(session, world, start)
        _UIDS.update({name: u.id for name, u in world.users.items()})
        for offset in range(days - 1, -1, -1):
            day = maks_today - timedelta(days=offset)
            for username in PEOPLE_BY_NAME:
                _plan_user_day(world, username, day, offset)
        _plan_social(world, maks_today, days)
        _plan_scheduler(world, start + timedelta(days=1))
        await world.run(session)

        # Current-week challenges might have been settled by the simulated week so far;
        # reopen and re-target them (see _tune_current_challenges).
        await _tune_current_challenges(session, now)

        # Everything older than a day has been seen; keep the recent ones unread.
        await session.execute(update(Notification).where(Notification.created_at < now - timedelta(hours=48)).values(read_at=now))
        await commit(session)

        maks = await session.get(User, _uid("maks"))
        assert maks is not None
        open_count = len(list(await session.scalars(quest_repo.list_query(maks.id, statuses=list(quest_repo.OPEN)))))
        completed = await session.scalar(select(Quest.id).where(Quest.user_id == maks.id).order_by(Quest.id.desc()).limit(1))
        return {"users": len(world.users), "maks_xp": maks.total_xp, "maks_open_quests": open_count, "last_quest_id": completed}


async def migrate() -> None:
    await asyncio.to_thread(command.upgrade, Config("alembic.ini"), "head")


async def reset_schema() -> None:
    """Drop everything, then rebuild the schema through the real migrations."""
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
    await migrate()


async def main(days: int, if_empty: bool) -> None:
    if if_empty:
        # Container start-up: migrate, and seed only a brand-new database.
        await migrate()
        async with db.SessionLocal() as session:
            if await session.scalar(select(User.id).limit(1)) is not None:
                log.info("database already has data; not seeding")
                return
    else:
        await reset_schema()
    summary = await build(days)
    log.info("demo world ready: %s", summary)
    print(f"Demo ready. Sign in as {DEMO_EMAIL} / {DEMO_PASSWORD}")


def cli() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Create the StudyRaid demo database (drops existing data).")
    parser.add_argument("--days", type=int, default=100, help="days of history to generate (21-120)")
    parser.add_argument("--if-empty", action="store_true", help="migrate, and seed only if there are no users yet")
    args = parser.parse_args()
    asyncio.run(main(max(21, min(args.days, 120)), args.if_empty))
