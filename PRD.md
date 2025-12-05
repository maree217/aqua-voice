# Aqua Voice - Product Requirements Document

## Overview

**Aqua Voice** is a macOS menu bar application that provides system-wide voice typing capabilities. Users can dictate text anywhere on their Mac, with the transcribed text typed directly at the cursor position in any application.

## Problem Statement

Existing voice typing solutions on macOS have limitations:
- Apple's built-in Dictation requires specific app support
- Third-party solutions are often expensive or subscription-based
- Many solutions have latency issues or produce unreliable transcriptions
- Few support simple global hotkeys for quick activation

## Solution

A lightweight, always-available menu bar app that:
- Activates instantly with a global hotkey (double-tap Right Option)
- Uses Deepgram Nova-3 for high-accuracy, low-latency transcription
- Types text directly at the cursor position in any application
- Provides simple controls: Enter to stop, Escape to cancel

## Target Users

- Professionals who need to draft emails, documents, or messages quickly
- Users with accessibility needs or repetitive strain injuries
- Anyone who types faster by speaking than by typing
- Developers and writers who want hands-free text input

## Functional Requirements

### Core Features

| ID | Feature | Priority | Status |
|----|---------|----------|--------|
| F1 | Menu bar app (no Dock icon) | P0 | Done |
| F2 | Double-tap Right Option to start recording | P0 | Done |
| F3 | Enter key to stop recording | P0 | Done |
| F4 | Escape key to cancel and delete typed text | P0 | Done |
| F5 | Single-tap Right Option to stop recording | P1 | Done |
| F6 | Real-time audio streaming to Deepgram | P0 | Done |
| F7 | Text typed at cursor position | P0 | Done |
| F8 | Final transcript copied to clipboard | P1 | Done |
| F9 | Visual indicator (red icon) when recording | P1 | Done |
| F10 | Menu bar controls for manual start/stop | P2 | Done |

### Permissions Required

| Permission | Purpose | macOS Location |
|------------|---------|----------------|
| Accessibility | Type text via keyboard simulation, detect Option key | Privacy & Security > Accessibility |
| Input Monitoring | Detect Enter/Escape keys globally (CGEventTap) | Privacy & Security > Input Monitoring |
| Microphone | Capture audio for transcription | Privacy & Security > Microphone |

### Hotkey Behavior

| State | Action | Result |
|-------|--------|--------|
| Idle | Double-tap Right Option | Start recording |
| Recording | Single-tap Right Option | Stop recording, copy to clipboard |
| Recording | Press Enter | Stop recording, copy to clipboard |
| Recording | Press Escape | Cancel recording, delete typed text |

## Non-Functional Requirements

### Performance
- Transcription latency: < 500ms after speech ends
- App startup time: < 2 seconds
- Memory usage: < 100MB during recording
- CPU usage: < 10% during recording

### Reliability
- No text truncation or loss during transcription
- Graceful handling of network disconnections
- Queue-based processing to prevent race conditions

### Cost Efficiency
- Deepgram Nova-3: ~$0.0043/minute
- Only connect to API while actively recording
- Typical user cost: < $1/month with moderate use

## Technical Architecture

### Components

```
┌─────────────────────────────────────────────────────────┐
│                    Aqua Voice App                        │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │   rumps     │  │  NSEvent    │  │  CGEventTap     │  │
│  │  Menu Bar   │  │  (Option)   │  │  (Enter/Esc)    │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
│         │                │                  │           │
│         └────────────────┼──────────────────┘           │
│                          ▼                              │
│               ┌─────────────────────┐                   │
│               │   AquaVoiceApp      │                   │
│               │   (Main Controller) │                   │
│               └─────────────────────┘                   │
│                    │           │                        │
│         ┌──────────┘           └──────────┐             │
│         ▼                                 ▼             │
│  ┌─────────────┐                  ┌─────────────┐       │
│  │  PyAudio    │                  │   pynput    │       │
│  │  (Capture)  │                  │  (Typing)   │       │
│  └─────────────┘                  └─────────────┘       │
│         │                                               │
│         ▼                                               │
│  ┌─────────────────────────────────────────────────┐   │
│  │           Deepgram WebSocket API                 │   │
│  │           (Nova-3 Speech-to-Text)                │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Key Technologies

| Component | Technology | Purpose |
|-----------|------------|---------|
| Menu Bar | rumps | macOS menu bar integration |
| Audio Capture | PyAudio | Microphone input |
| Speech-to-Text | Deepgram Nova-3 | Real-time transcription |
| Keyboard Typing | pynput | Simulate keystrokes |
| Option Key Detection | NSEvent | Monitor modifier keys |
| Enter/Escape Detection | Quartz CGEventTap | Global key capture |
| App Bundling | py2app | Create .app bundle |

### Data Flow

1. User double-taps Right Option
2. App starts PyAudio stream (16kHz, mono, 16-bit)
3. App opens WebSocket to Deepgram
4. Audio chunks (100ms) sent to Deepgram
5. Deepgram returns final transcripts after detecting speech boundaries
6. Transcripts queued for sequential typing
7. pynput types text at cursor position
8. User presses Enter to stop
9. Complete transcript copied to clipboard
10. WebSocket and audio stream closed

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| DEEPGRAM_API_KEY | Yes | API key from console.deepgram.com |

### Deepgram Settings

| Setting | Value | Reason |
|---------|-------|--------|
| model | nova-3 | Latest, most accurate model |
| language | en | English transcription |
| encoding | linear16 | Raw PCM audio |
| sample_rate | 16000 | Standard for speech |
| interim_results | false | Only final results (prevents truncation) |
| smart_format | false | Raw text without auto-formatting |
| endpointing | 300 | 300ms silence triggers final result |

## Future Considerations

### Phase 2 Features
- Decouple transcription from cursor (buffer mode)
- LLM cleanup for grammar/spelling
- Custom hotkey configuration

### Phase 3 Features
- Multiple language support
- Voice commands ("new paragraph", "delete that")
- Transcription history
- App-specific prompts

## Success Metrics

| Metric | Target |
|--------|--------|
| Transcription accuracy | > 95% |
| User activation time | < 1 second |
| Crash rate | < 1% of sessions |
| Permission setup success | > 90% of users |

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| macOS permission changes | App stops working | Document troubleshooting, check permissions on startup |
| Deepgram API changes | Transcription fails | Pin SDK version, handle errors gracefully |
| Network issues | No transcription | Show error status, copy partial transcript |
| Code signing invalidation | Permissions reset | Document re-adding app to permissions |

## Appendix

### Keyboard Codes

| Key | Code |
|-----|------|
| Right Option | 61 |
| Enter/Return | 36 |
| Escape | 53 |

### NSEvent Masks

| Event | Mask |
|-------|------|
| FlagsChanged (modifiers) | 0x1000 |
| KeyDown | 0x400 |

### CGEventTap Types

| Type | Value | Use |
|------|-------|-----|
| kCGSessionEventTap | Session-level | Global key capture |
| kCGEventTapOptionListenOnly | Listen only | Don't block events |
