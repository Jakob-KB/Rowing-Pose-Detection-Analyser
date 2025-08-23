import random
from pathlib import Path
import uuid
from time import time_ns


def get_random_name() -> str:
    ADJECTIVES = [
        "Silent", "Golden", "Quantum", "Majestic", "Frosty", "Shy", "Bold",
        "Radiant", "Velvety", "Hidden", "Witty", "Zany", "Lively", "Eager",
        "Rapid", "Swift", "Crimson", "Cosmic", "Bouncy", "Brisk", "Cheery",
        "Gentle", "Mellow", "Chilly", "Curious", "Playful", "Mystic", "Nimble"
    ]

    NOUNS = [
        "Echo", "Pulse", "Labyrinth", "Nexus", "Odyssey", "Signal", "Summit",
        "Vertex", "Mirage", "Beacon", "Galaxy", "Whisper", "Harbor", "Fragment",
        "Crystal", "Voyager", "Orbit", "Flame", "Nova", "Dust", "Cloud", "Meadow",
        "Horizon", "Circuit", "Pattern", "Memory", "Sparkle"
    ]

    number = f"{random.randint(0, 99):02d}"
    adjective = random.choice(ADJECTIVES)
    noun = random.choice(NOUNS)

    while len(adjective) + len(noun) > 16:
        adjective = random.choice(ADJECTIVES)
        noun = random.choice(NOUNS)

    return f"{adjective}-{noun}-{number}"

def now_s() -> int:
    return int(time_ns() // 1_000_000_000)

def new_id() -> str:
    return str(uuid.uuid4())

def validate_file_path(path: Path) -> None:
    if not isinstance(path, Path):
        raise TypeError("video_path must be a pathlib.Path")
    if not path.exists():
        raise FileNotFoundError(f"Video file does not exist: {path}")

def format_timecode(t_sec: float) -> str:
    ms_total = int(round(t_sec * 1000.0))
    s, ms = divmod(max(ms_total, 0), 1000)
    h, s = divmod(s, 3600); m, s = divmod(s, 60)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"