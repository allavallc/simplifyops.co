"""Baseline tests for gateway.transcription.looks_transcribable_file — a pure classifier."""

from gateway.transcription import looks_transcribable_file


def test_audio_mime_is_transcribable():
    assert looks_transcribable_file(mime_type="audio/ogg") is True


def test_non_audio_mime_without_filename_is_not():
    assert looks_transcribable_file(mime_type="image/png") is False


def test_audio_suffix_is_transcribable():
    assert looks_transcribable_file(filename="voice.mp3") is True


def test_suffix_match_is_case_insensitive():
    assert looks_transcribable_file(filename="VOICE.OPUS") is True


def test_non_audio_suffix_is_not():
    assert looks_transcribable_file(filename="notes.txt") is False


def test_no_arguments_is_not_transcribable():
    assert looks_transcribable_file() is False
