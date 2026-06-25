"""Tests for the prompt mapper."""

import pytest

from prompt_mapper import map_prompt, PromptError, MAX_PROMPT_LENGTH


def test_empty_prompt_is_rejected():
    with pytest.raises(PromptError):
        map_prompt("")


def test_overlong_prompt_is_rejected():
    with pytest.raises(PromptError):
        map_prompt("a" * (MAX_PROMPT_LENGTH + 1))


def test_happy_prompt_is_major():
    params = map_prompt("happy")
    assert params.mode == "major"


def test_sad_prompt_is_minor():
    params = map_prompt("sad")
    assert params.mode == "minor"


def test_unknown_words_use_defaults():
    params = map_prompt("xyzzy qwerty")
    assert params.descriptors == []
    assert params.bpm == 110


def test_recognised_words_are_returned():
    params = map_prompt("dreamy and romantic")
    assert "dreamy" in params.descriptors
    assert "romantic" in params.descriptors
