"""
Turns musical parameters into something the app can play.

Two things happen here:
  1. We build a small config object telling the in-browser MusicVAE model how
     to generate (temperature, how many 2-bar chunks, tempo).
  2. We also build a simple "fallback" melody on the server. If the browser
     model fails to load, the app still has a melody to play. This also lets us
     test the backend without needing a browser.

The fallback melody just walks up and down the notes of the chosen scale. It is
basic but always valid.
"""

from dataclasses import dataclass, field
from typing import Dict, List
import random

from prompt_mapper import MusicParameters


MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]
MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10]

# MIDI note number for the root of each key (middle range).
KEY_ROOT = {
    "C": 60, "G": 67, "D": 62, "A": 69, "F": 65,
    "Am": 69, "Em": 64, "Dm": 62, "Bm": 71, "Cm": 60,
}


@dataclass
class Note:
    """One note: pitch, when it starts, how long, how loud."""
    pitch: int
    start: float
    duration: float
    velocity: int = 80

    def to_dict(self) -> Dict:
        return {
            "pitch": self.pitch,
            "start": round(self.start, 4),
            "duration": round(self.duration, 4),
            "velocity": self.velocity,
        }


@dataclass
class GenerationResult:
    """What we send back: the parameters, the model config, and a fallback melody."""
    parameters: MusicParameters
    model_config: Dict
    fallback_notes: List[Note] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "parameters": self.parameters.to_dict(),
            "model_config": self.model_config,
            "fallback_notes": [n.to_dict() for n in self.fallback_notes],
        }


def _build_model_config(params: MusicParameters) -> Dict:
    """Settings the browser model uses when it samples a melody."""
    return {
        "checkpoint": "mel_2bar_small",
        "temperature": params.temperature,
        "num_samples": 1,
        "segments": params.bars // 2,
        "qpm": params.bpm,
    }


def _scale_for(params: MusicParameters) -> List[int]:
    """Return the notes of the chosen scale as MIDI numbers."""
    root = KEY_ROOT.get(params.key, 60)
    intervals = MINOR_SCALE if params.mode == "minor" else MAJOR_SCALE
    return [root + i for i in intervals]


def generate_fallback(params: MusicParameters, seed=None) -> List[Note]:
    """Build a simple melody from the parameters. Pass a seed for repeatable output."""
    rng = random.Random(seed)
    scale = _scale_for(params)
    # Add the octave above so the melody can move a bit higher too.
    notes_pool = scale + [p + 12 for p in scale]

    total_beats = params.bars * 4  # 4 beats per bar
    notes = []
    position = 0.0
    index = len(scale) // 2  # start somewhere in the middle

    while position < total_beats:
        # Move up or down the scale by a small step.
        index += rng.choice([-2, -1, -1, 1, 1, 2])
        index = max(0, min(len(notes_pool) - 1, index))
        pitch = notes_pool[index]

        # Busier prompts use more short notes.
        duration = 0.5 if rng.random() < params.density else 1.0
        notes.append(Note(pitch, position, duration, rng.randint(70, 95)))
        position += duration

    # Don't let the last note run past the end.
    if notes and notes[-1].start + notes[-1].duration > total_beats:
        notes[-1].duration = max(0.5, total_beats - notes[-1].start)

    return notes


def generate(params: MusicParameters, seed=None) -> GenerationResult:
    """Build the full result for a set of parameters."""
    return GenerationResult(
        parameters=params,
        model_config=_build_model_config(params),
        fallback_notes=generate_fallback(params, seed=seed),
    )
