"""
Writes a list of notes to a standard MIDI (.mid) file.

I wrote this by hand against the MIDI file format instead of using a library,
to keep the dependencies small and because the format is not too hard for the
simple case we need: one track, one instrument, notes turning on and off.
"""

from typing import List
import struct

from generation_engine import Note


# How many "ticks" make up one beat. 480 is a common value.
TICKS_PER_BEAT = 480


def _variable_length(value: int) -> bytes:
    """MIDI stores delta times as variable-length numbers. This encodes one."""
    buffer = value & 0x7F
    result = bytearray()
    value >>= 7
    while value:
        buffer <<= 8
        buffer |= ((value & 0x7F) | 0x80)
        value >>= 7
    while True:
        result.append(buffer & 0xFF)
        if buffer & 0x80:
            buffer >>= 8
        else:
            break
    return bytes(result)


def _build_track(notes: List[Note], bpm: int) -> bytes:
    """Build the track chunk: tempo, instrument, then all the note events."""
    events = bytearray()

    # Tempo (microseconds per beat).
    micros_per_beat = int(60_000_000 / max(1, bpm))
    events += _variable_length(0)
    events += b"\xFF\x51\x03"
    events += struct.pack(">I", micros_per_beat)[1:]

    # Choose a piano sound on channel 0.
    events += _variable_length(0)
    events += bytes([0xC0, 0x00])

    # Turn each note into an "on" event and an "off" event.
    raw = []
    for n in notes:
        start_tick = int(round(n.start * TICKS_PER_BEAT))
        end_tick = int(round((n.start + n.duration) * TICKS_PER_BEAT))
        pitch = max(0, min(127, n.pitch))
        velocity = max(1, min(127, n.velocity))
        raw.append((start_tick, 0, pitch, velocity))
        raw.append((end_tick, 1, pitch, 0))

    # Sort by time; put note-offs before note-ons at the same time.
    raw.sort(key=lambda e: (e[0], -e[1]))

    last_tick = 0
    for tick, kind, pitch, velocity in raw:
        events += _variable_length(tick - last_tick)
        last_tick = tick
        if kind == 0:
            events += bytes([0x90, pitch, velocity])  # note on
        else:
            events += bytes([0x80, pitch, 0])          # note off

    # End of track.
    events += _variable_length(0)
    events += b"\xFF\x2F\x00"

    return b"MTrk" + struct.pack(">I", len(events)) + bytes(events)


def encode(notes: List[Note], bpm: int) -> bytes:
    """Return the bytes of a complete .mid file for the given notes."""
    track = _build_track(notes, bpm)
    # Header: format 0, one track, the tick resolution.
    header = b"MThd" + struct.pack(">IHHH", 6, 0, 1, TICKS_PER_BEAT)
    return header + track
