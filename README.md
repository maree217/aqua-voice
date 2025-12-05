# Aqua Voice

**System-wide voice typing for macOS** - Type anywhere with your voice using Deepgram Nova-3.

## Features

- **Menu bar app** - Runs silently in menu bar, no Dock icon
- **Batch transcription** - Text appears in chunks after brief pauses (reliable, no truncation)
- **Works everywhere** - Types directly wherever your cursor is (any app)
- **Global hotkeys** - Double-tap Right Option to start, Enter to stop, Escape to cancel
- **Clipboard backup** - Final text always copied to clipboard

## Installation

### Prerequisites

- macOS 10.15+ (Catalina or later)
- Python 3.9+
- [Deepgram API key](https://console.deepgram.com) (free $200 credit to start)

### Setup

```bash
# Clone the repo
git clone https://github.com/maree217/aqua-voice.git
cd aqua-voice

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with your API key
echo "DEEPGRAM_API_KEY=your_key_here" > .env
```

## Building the App

```bash
# Build the app
python setup.py py2app

# Copy to Applications folder (recommended)
cp -R dist/"Aqua Voice.app" /Applications/

# Sign the app
codesign --force --sign - /Applications/"Aqua Voice.app"
```

Then launch from `/Applications/Aqua Voice.app`.

## Required Permissions

After first launch, grant these permissions in **System Settings > Privacy & Security**:

| Permission | Location | Required For |
|------------|----------|--------------|
| **Accessibility** | Privacy & Security > Accessibility | Keyboard typing and Option key detection |
| **Input Monitoring** | Privacy & Security > Input Monitoring | Enter/Escape key detection (CGEventTap) |
| **Microphone** | Privacy & Security > Microphone | Audio capture |

**Important:** After rebuilding the app, you must **remove and re-add** it in both Accessibility and Input Monitoring settings, then restart the app.

## Controls

| Action | Key |
|--------|-----|
| **Start recording** | Double-tap **Right Option** (⌥) |
| **Stop recording** | **Enter** or single tap **Right Option** |
| **Cancel recording** | **Escape** (deletes typed text) |

Or use the menu bar dropdown.

## How It Works

Aqua Voice uses Deepgram's Nova-3 speech recognition model in "final results only" mode:

1. **Start recording** - Double-tap Right Option. Audio streams to Deepgram in real-time.
2. **Speak naturally** - Deepgram detects pauses (300ms silence) and sends finalized text.
3. **Text appears** - Each finalized chunk is typed at your cursor position.
4. **Stop recording** - Press Enter. Complete transcript is copied to clipboard.

This approach prioritizes reliability over real-time streaming, eliminating truncation issues that can occur with interim results.

## Cost

**Deepgram Nova-3 Pricing:**
- ~$0.0043/minute ($0.26/hour)
- Your $200 credit = ~775 hours of transcription
- Typical usage: 5-10 min/day = months of free use

The app only connects while recording, so you're charged only for actual transcription time.

## Project Structure

| File | Description |
|------|-------------|
| `aqua_voice_app.py` | Main application |
| `setup.py` | py2app build configuration |
| `.env` | API key (not in git) |
| `requirements.txt` | Python dependencies |
| `ROADMAP.md` | Product roadmap and backlog |
| `PRD.md` | Product Requirements Document |

## Logs

Debug log location: `~/aqua_voice.log`

## Troubleshooting

### Text not appearing
- Ensure the app has **Accessibility** permission
- Restart the app after granting permission

### Enter/Escape keys not working
- Ensure the app has **Input Monitoring** permission
- Check log for "CGEventTap for Enter/Escape keys started"
- If you see "Failed to create CGEventTap", re-add the app to both Accessibility and Input Monitoring

### Double-tap not working
- Taps must be within 350ms
- Ensure Accessibility permission is granted

### No audio / silent transcription
- Check **Microphone** permission
- Ensure no other app is using the mic

### Permissions reset after rebuild
- After rebuilding, remove the app from Accessibility and Input Monitoring
- Re-add the newly built app from `/Applications/Aqua Voice.app`
- Restart the app

## Tech Stack

- [Deepgram](https://deepgram.com) - Real-time speech-to-text (Nova-3 model)
- [rumps](https://github.com/jaredks/rumps) - macOS menu bar app framework
- [PyObjC](https://pyobjc.readthedocs.io) - Python-Objective-C bridge (Quartz CGEventTap)
- [pynput](https://pynput.readthedocs.io) - Keyboard controller for typing
- [PyAudio](https://people.csail.mit.edu/hubert/pyaudio/) - Audio capture
- [py2app](https://py2app.readthedocs.io) - macOS app bundler

## License

MIT License - see [LICENSE](LICENSE) for details.
