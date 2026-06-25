"""
Maps a mood prompt (free text) to musical parameters.

The idea: certain words suggest a certain feel. "happy" leans major and a bit
faster, "sad" leans minor and slower, and so on. A small lookup table holds
these hints, and we combine the hints from all recognised words in the prompt.
This is kept simple and rule-based on purpose so the behaviour is easy to follow
and test.
"""

from dataclasses import dataclass, asdict
from typing import Dict, List
import re


# Keys we can pick from, grouped by mode.
MAJOR_KEYS = ["C", "G", "D", "A", "F"]
MINOR_KEYS = ["Am", "Em", "Dm", "Bm", "Cm"]

MAX_PROMPT_LENGTH = 200


@dataclass
class MusicParameters:
    """The musical settings we derive from a prompt."""
    temperature: float
    key: str
    mode: str
    bpm: int
    density: float
    bars: int
    descriptors: List[str]

    def to_dict(self) -> Dict:
        return asdict(self)


# Each mood word nudges some of the settings. Values are added to the defaults
# and then kept within sensible limits.
LEXICON = {
    "happy":      {"mode": "major", "bpm": 20, "temperature": 0.1, "density": 0.1},
    "joyful":     {"mode": "major", "bpm": 25, "temperature": 0.15, "density": 0.2},
    "upbeat":     {"mode": "major", "bpm": 30, "density": 0.2},
    "playful":    {"mode": "major", "bpm": 15, "temperature": 0.2, "density": 0.15},
    "bright":     {"mode": "major", "bpm": 10, "density": 0.1},
    "hopeful":    {"mode": "major", "bpm": 5,  "temperature": 0.05},
    "calm":       {"mode": "major", "bpm": -20, "temperature": -0.1, "density": -0.2},
    "dreamy":     {"mode": "major", "bpm": -15, "temperature": 0.1, "density": -0.1},
    "romantic":   {"mode": "major", "bpm": -10, "temperature": -0.05, "density": -0.05},
    "peaceful":   {"mode": "major", "bpm": -25, "density": -0.25},
    "gentle":     {"mode": "major", "bpm": -15, "density": -0.2},
    "relaxed":    {"mode": "major", "bpm": -20, "density": -0.15},
    "sad":        {"mode": "minor", "bpm": -25, "temperature": -0.05, "density": -0.2},
    "melancholy": {"mode": "minor", "bpm": -20, "density": -0.15},
    "dark":       {"mode": "minor", "bpm": -10, "temperature": 0.05},
    "tense":      {"mode": "minor", "bpm": 10, "temperature": 0.2, "density": 0.15},
    "mysterious": {"mode": "minor", "bpm": -5, "temperature": 0.15},
    "haunting":   {"mode": "minor", "bpm": -15, "temperature": 0.1},
    "energetic":  {"mode": "major", "bpm": 35, "temperature": 0.1, "density": 0.25},
    "intense":    {"mode": "minor", "bpm": 30, "temperature": 0.2, "density": 0.3},
    "epic":       {"mode": "minor", "bpm": 20, "temperature": 0.1, "density": 0.2},
    "glitchy":    {"mode": "minor", "bpm": 15, "temperature": 0.35, "density": 0.3},
}

# Starting values before any mood words are applied.
DEFAULT_TEMPERATURE = 0.9
DEFAULT_BPM = 110
DEFAULT_DENSITY = 0.5


class PromptError(ValueError):
    """Raised when a prompt is empty or too long."""


def _clamp(value, low, high):
    return max(low, min(high, value))


def map_prompt(prompt: str) -> MusicParameters:
    """Turn a mood prompt into MusicParameters. Raises PromptError if invalid."""
    if prompt is None or not prompt.strip():
        raise PromptError("Prompt must not be empty.")
    if len(prompt) > MAX_PROMPT_LENGTH:
        raise PromptError("Prompt is too long (max %d characters)." % MAX_PROMPT_LENGTH)

    words = re.findall(r"[a-z]+", prompt.lower())

    temperature = DEFAULT_TEMPERATURE
    bpm = DEFAULT_BPM
    density = DEFAULT_DENSITY
    found = []
    major_votes = 0
    minor_votes = 0

    for word in words:
        rule = LEXICON.get(word)
        if not rule:
            continue
        found.append(word)
        temperature += rule.get("temperature", 0)
        bpm += rule.get("bpm", 0)
        density += rule.get("density", 0)
        if rule.get("mode") == "major":
            major_votes += 1
        elif rule.get("mode") == "minor":
            minor_votes += 1

    # Decide major or minor based on which got more votes.
    if minor_votes > major_votes:
        mode = "minor"
    else:
        mode = "major"

    temperature = round(_clamp(temperature, 0.1, 1.5), 2)
    bpm = int(_clamp(bpm, 60, 180))
    density = round(_clamp(density, 0.1, 1.0), 2)

    # Longer, more descriptive prompts get a longer melody.
    bars = 16 if len(found) >= 3 else 8

    # Pick a key from the right group. Using the word count keeps it stable.
    keys = MINOR_KEYS if mode == "minor" else MAJOR_KEYS
    key = keys[len(found) % len(keys)]

    return MusicParameters(
        temperature=temperature,
        key=key,
        mode=mode,
        bpm=bpm,
        density=density,
        bars=bars,
        descriptors=found,
    )
