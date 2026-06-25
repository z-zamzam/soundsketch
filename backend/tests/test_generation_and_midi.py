"""Tests for the generation engine and MIDI encoder."""

from prompt_mapper import map_prompt
from generation_engine import generate_fallback
from midi_encoder import encode


def test_fallback_notes_are_in_midi_range():
    params = map_prompt("upbeat and playful")
    notes = generate_fallback(params, seed=1)
    assert notes
    for n in notes:
        assert 0 <= n.pitch <= 127


def test_encoded_file_has_midi_header():
    params = map_prompt("dreamy")
    notes = generate_fallback(params, seed=1)
    data = encode(notes, params.bpm)
    assert data[:4] == b"MThd"


def test_encoded_file_contains_a_track():
    params = map_prompt("calm")
    notes = generate_fallback(params, seed=1)
    data = encode(notes, params.bpm)
    assert b"MTrk" in data
