# Aqua Voice

**System-wide voice typing for macOS** - Type anywhere with your voice using Deepgram's real-time transcription.

## Features

- **Live transcription** - Text appears as you speak, with real-time corrections
- **Works everywhere** - Types directly wherever your cursor is (any app)
- **Global hotkey** - Double-tap Right Option to start, tap again to stop
- **Cost-efficient** - Uses Deepgram Nova-3 (~$0.0065/min), connection closes when not recording
- **Cancel support** - Press Escape to delete what was typed and start over

## Installation

### Prerequisites

- macOS 10.15+
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

### Grant Permissions

On first run, macOS will ask for:
1. **Accessibility** - Required to type text (System Preferences > Privacy & Security > Accessibility)
2. **Microphone** - Required to record audio

## Usage

```bash
# Activate virtual environment
source venv/bin/activate

# Run the app
python aqua_voice.py
```

### Controls

| Action | Key |
|--------|-----|
| **Start recording** | Double-tap **Right Option** (⌥) |
| **Stop recording** | Single tap **Right Option** |
| **Cancel** (delete typed text) | **Escape** |

### Workflow

1. Place your cursor where you want to type
2. Double-tap Right Option - you'll see "RECORDING" in terminal
3. Speak naturally - text appears live as you talk
4. Tap Right Option once to stop - text stays, copied to clipboard
5. Or press Escape to cancel - deletes typed text (still saved to clipboard)

## Cost

Deepgram provides **$200 free credit** (~30,000 minutes of transcription).

- Nova-3 streaming: ~$0.0065/min
- Billed per second, only while recording
- Connection closes immediately when you stop

## Troubleshooting

### "Accessibility access denied"
Go to System Preferences > Privacy & Security > Accessibility and add Terminal (or your terminal app).

### "Microphone access denied"
Go to System Preferences > Privacy & Security > Microphone and allow access.

### Text not appearing
Make sure your cursor is in a text field before starting recording.

### Double-tap not working
Try adjusting your tap speed - taps must be within 350ms of each other.

## Tech Stack

- [Deepgram](https://deepgram.com) - Real-time speech-to-text (Nova-3 model)
- [pynput](https://pynput.readthedocs.io) - Global keyboard monitoring and text input
- [PyAudio](https://people.csail.mit.edu/hubert/pyaudio/) - Audio capture

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

Built with Deepgram's excellent real-time transcription API.
