"""Static material the demo seeder draws from. The people and parties are fictional."""

from app.engine.rewards import Difficulty

QUEST_TITLES: dict[str, list[tuple[str, Difficulty, int]]] = {
    "Mathematics": [
        ("Problem set 7: integration by parts", Difficulty.HARD, 90),
        ("Review limits and continuity", Difficulty.NORMAL, 45),
        ("Linear algebra worksheet: eigenvalues", Difficulty.HARD, 75),
        ("Statistics homework, chapter 4", Difficulty.NORMAL, 50),
        ("Practice exam: derivatives", Difficulty.HARD, 100),
        ("Flashcards: trig identities", Difficulty.EASY, 20),
    ],
    "Physics": [
        ("Lab report: simple pendulum", Difficulty.HARD, 120),
        ("Kinematics problem set", Difficulty.NORMAL, 60),
        ("Read chapter 9: momentum", Difficulty.EASY, 30),
        ("Circuits practice questions", Difficulty.NORMAL, 45),
        ("Derive the rocket equation from scratch", Difficulty.HARD, 60),
    ],
    "Chemistry": [
        ("Balance 20 redox equations", Difficulty.NORMAL, 40),
        ("Organic chemistry flashcards", Difficulty.EASY, 25),
        ("Titration lab write-up", Difficulty.HARD, 90),
        ("Periodic trends summary sheet", Difficulty.NORMAL, 35),
    ],
    "Biology": [
        ("Cell biology notes: membranes", Difficulty.NORMAL, 45),
        ("Genetics problem set", Difficulty.HARD, 70),
        ("Draw the Krebs cycle from memory", Difficulty.NORMAL, 30),
        ("Watch lecture 12 and summarise", Difficulty.EASY, 40),
    ],
    "History": [
        ("Essay outline: the Industrial Revolution", Difficulty.NORMAL, 50),
        ("Read primary sources on 1914", Difficulty.NORMAL, 45),
        ("Timeline flashcards: Cold War", Difficulty.EASY, 20),
        ("Source analysis: the Treaty of Versailles", Difficulty.HARD, 80),
    ],
    "Literature": [
        ("Read Frankenstein, chapters 10–14", Difficulty.NORMAL, 60),
        ("Poetry analysis draft", Difficulty.HARD, 75),
        ("Annotate the opening of Hamlet", Difficulty.NORMAL, 40),
    ],
    "Languages": [
        ("Spanish vocabulary: 50 cards", Difficulty.EASY, 20),
        ("German grammar: the four cases", Difficulty.NORMAL, 40),
        ("Write a 300-word diary entry in Spanish", Difficulty.NORMAL, 35),
        ("Listening practice: one podcast episode", Difficulty.EASY, 25),
    ],
    "Computer Science": [
        ("Implement a binary search tree", Difficulty.HARD, 90),
        ("Dynamic programming exercises", Difficulty.HARD, 80),
        ("Read about hash tables", Difficulty.EASY, 30),
        ("Finish the React to-do assignment", Difficulty.NORMAL, 60),
    ],
    "Personal": [
        ("Plan next week and tidy the desk", Difficulty.EASY, 15),
        ("30-minute run", Difficulty.EASY, 30),
        ("Read 20 pages of a novel", Difficulty.EASY, 25),
    ],
}

LEGENDARY: dict[str, list[tuple[str, int]]] = {
    "Physics": [("Final project: robotics arm report", 240)],
    "Mathematics": [("Mock exam: full paper under timed conditions", 180)],
    "History": [("Research essay draft (3,000 words)", 240)],
    "Computer Science": [("Ship the portfolio website", 240)],
    "Biology": [("Revise the whole genetics unit", 200)],
}

DESCRIPTIONS = {
    "Mathematics": "Show full working. Check answers against the back of the book.",
    "Physics": "Include units and a short error analysis.",
    "Chemistry": "Use the lab handout template.",
    "Biology": "Diagrams count, make them clear.",
    "History": "Cite at least three sources.",
    "Literature": "Note quotes with page numbers for the essay.",
    "Languages": "Say every word out loud.",
    "Computer Science": "Write tests first.",
    "Personal": "",
}

# username, display name, time zone, subjects, avatar hue, activity level (0..1)
PEOPLE = [
    ("maks", "Maks", "Europe/Kyiv", ["Mathematics", "Physics", "Computer Science", "Languages", "History", "Chemistry"], 265, 0.92),
    ("lina", "Lina", "Europe/Warsaw", ["Biology", "Chemistry", "Languages", "Literature"], 330, 0.85),
    ("oskar", "Oskar", "Europe/Berlin", ["Mathematics", "Physics", "Computer Science"], 200, 0.7),
    ("yuki", "Yuki", "Asia/Tokyo", ["Literature", "History", "Languages"], 150, 0.78),
    ("amara", "Amara", "Europe/London", ["Biology", "Mathematics", "Personal"], 25, 0.6),
    ("dev", "Dev", "Asia/Kolkata", ["Physics", "Mathematics", "Computer Science"], 95, 0.8),
]
