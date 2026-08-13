# Story 1 - Voice transcription for Telegram voice notes

## Problem

Telegram voice notes are arriving, but the gateway only handles text. Voice messages need to be downloaded, converted if needed, transcribed locally, and then passed into the existing text message flow.

## Goal

Let a voice note follow the same approval, inbox, Hermes, and reply path as a normal Telegram text message.

## Scope

- Detect Telegram `message.voice`, `message.audio`, and audio-bearing `message.document` updates
- Download the file from Telegram
- Normalize the audio into a format the local transcriber can read
- Run local transcription on the Pi
- Feed the transcript into the existing `handle_message()` path
- Keep the current Telegram text path unchanged

## Acceptance criteria

- A Telegram voice note is treated as input, not ignored
- A successful transcription produces the same downstream behavior as a text message
- If transcription fails, the gateway logs the failure and does not send a broken reply
- The approval/inbox flow stays the same
- The transcription code is written as a reusable helper, not hard-wired to Telegram

## Notes

The transcription layer should be channel-agnostic. Telegram should be one adapter. Discord or any other channel that can provide a downloadable audio file should be able to reuse the same transcription code by handing audio into the shared helper.

That means the adapter owns channel-specific work like receiving the message and downloading the file, while the transcription helper only cares about local audio input.
