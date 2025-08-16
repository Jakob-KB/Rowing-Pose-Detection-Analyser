
import random

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