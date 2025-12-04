#!/usr/bin/env python3
"""
Aqua Voice - macOS System-Wide Voice Typing

Controls:
- Double-tap Right Option (⌥): Start recording
- Single tap Right Option: Stop recording (text already typed live)
- Escape: Cancel (deletes what was typed, saves to clipboard)

Text is typed LIVE at cursor as you speak.
Deepgram connection closes when not recording to save costs.
"""

import os
import time
import threading
import subprocess
from dotenv import load_dotenv

import pyaudio
from pynput import keyboard
from pynput.keyboard import Key, Controller as KeyboardController

from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions

load_dotenv()

SAMPLE_RATE = 16000
CHUNK_SIZE = 1600
DOUBLE_TAP_THRESHOLD = 0.35


def copy_to_clipboard(text):
    """Copy text to macOS clipboard"""
    p = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
    p.communicate(text.encode('utf-8'))


class AquaVoice:
    def __init__(self):
        self.deepgram = DeepgramClient(api_key=os.getenv("DEEPGRAM_API_KEY"))
        self.kb = KeyboardController()
        self.connection = None
        self.recording = False
        self.audio = None
        self.stream = None
        self.audio_thread = None

        # Transcript tracking
        self.final_text = []
        self.last_interim = ""
        self.all_typed = ""  # Track everything typed for cancel/clipboard

        # Double-tap detection
        self.last_option_tap = 0
        self.option_tap_count = 0

        self.lock = threading.Lock()

        print("\n" + "="*50)
        print("  Aqua Voice - Live Voice Typing")
        print("="*50)
        print("\n  Double-tap Right Option (⌥): Start")
        print("  Single tap Right Option: Stop")
        print("  Escape: Cancel & delete typed text")
        print("\n  Ctrl+C to quit app")
        print("="*50 + "\n")
        print("Ready. Double-tap Right Option to start...")

    def start_recording(self):
        """Start recording and transcription"""
        with self.lock:
            if self.recording:
                return
            self.recording = True

        print("\n🎙️  RECORDING - speak now...")
        self.final_text = []
        self.last_interim = ""
        self.all_typed = ""

        try:
            self.connection = self.deepgram.listen.websocket.v("1")
            self.connection.on(LiveTranscriptionEvents.Transcript, self._on_transcript)
            self.connection.on(LiveTranscriptionEvents.Error, self._on_error)

            options = LiveOptions(
                model="nova-3",
                language="en",
                encoding="linear16",
                sample_rate=SAMPLE_RATE,
                channels=1,
                smart_format=True,
                interim_results=True,
                endpointing=300,
            )

            if not self.connection.start(options):
                print("❌ Failed to connect to Deepgram")
                self.recording = False
                return

            self.audio = pyaudio.PyAudio()
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE,
            )

            self.audio_thread = threading.Thread(target=self._capture_audio, daemon=True)
            self.audio_thread.start()

        except Exception as e:
            print(f"❌ Error: {e}")
            self.recording = False

    def stop_recording(self):
        """Stop recording - text is already typed live"""
        with self.lock:
            if not self.recording:
                return
            self.recording = False

        # Close Deepgram immediately to stop billing
        if self.connection:
            try:
                self.connection.finish()
            except:
                pass
            self.connection = None

        # Stop audio
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except:
                pass
            self.stream = None

        if self.audio:
            try:
                self.audio.terminate()
            except:
                pass
            self.audio = None

        # Copy final text to clipboard
        final = ' '.join(self.final_text).strip()
        if final:
            copy_to_clipboard(final)
            print(f"\n📋 Saved to clipboard: {final[:50]}{'...' if len(final) > 50 else ''}")

        print("\n⏹️  STOPPED")
        print("Double-tap Right Option to start...")

    def cancel_recording(self):
        """Cancel - delete typed text, save to clipboard"""
        with self.lock:
            if not self.recording:
                return
            self.recording = False

        print("\n🚫 CANCELLING...")

        # Close connections first
        if self.connection:
            try:
                self.connection.finish()
            except:
                pass
            self.connection = None

        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except:
                pass
            self.stream = None

        if self.audio:
            try:
                self.audio.terminate()
            except:
                pass
            self.audio = None

        # Delete what was typed
        if self.all_typed:
            copy_to_clipboard(self.all_typed)  # Save before deleting
            for _ in range(len(self.all_typed)):
                self.kb.press(Key.backspace)
                self.kb.release(Key.backspace)
                time.sleep(0.003)
            print(f"🗑️  Deleted text (saved to clipboard)")

        print("\n⏹️  CANCELLED")
        print("Double-tap Right Option to start...")

    def _capture_audio(self):
        """Audio capture loop"""
        while self.recording and self.stream:
            try:
                data = self.stream.read(CHUNK_SIZE, exception_on_overflow=False)
                if self.connection and self.recording:
                    self.connection.send(data)
            except:
                break

    def _on_transcript(self, *args, **kwargs):
        """Handle transcript - TYPE LIVE at cursor"""
        if not self.recording:
            return

        try:
            result = kwargs.get('result') or (args[1] if len(args) > 1 else args[0] if args else None)
            if not result:
                return

            channel = getattr(result, 'channel', None)
            if not channel:
                return

            alts = getattr(channel, 'alternatives', None)
            if not alts or len(alts) == 0:
                return

            text = alts[0].transcript
            is_final = getattr(result, 'is_final', False)

            if not text:
                return

            # Delete previous interim text
            if self.last_interim:
                for _ in range(len(self.last_interim)):
                    self.kb.press(Key.backspace)
                    self.kb.release(Key.backspace)
                    time.sleep(0.003)
                # Update all_typed by removing interim
                self.all_typed = self.all_typed[:-len(self.last_interim)]

            if is_final:
                # Type final with space
                to_type = text + " "
                self.kb.type(to_type)
                self.all_typed += to_type
                self.final_text.append(text)
                self.last_interim = ""
                print(f"  ✓ {text}")
            else:
                # Type interim (will be replaced)
                self.kb.type(text)
                self.all_typed += text
                self.last_interim = text

        except Exception as e:
            print(f"Transcript error: {e}")

    def _on_error(self, *args, **kwargs):
        error = kwargs.get('error') or (args[1] if len(args) > 1 else 'Unknown')
        print(f"❌ Deepgram error: {error}")

    def _handle_option_tap(self):
        """Handle Right Option key tap"""
        now = time.time()

        if self.recording:
            # If recording, single tap stops
            self.stop_recording()
            self.option_tap_count = 0
        else:
            # If not recording, check for double tap
            if now - self.last_option_tap < DOUBLE_TAP_THRESHOLD:
                self.option_tap_count += 1
                if self.option_tap_count >= 1:
                    self.start_recording()
                    self.option_tap_count = 0
            else:
                self.option_tap_count = 0

        self.last_option_tap = now

    def run(self):
        """Main loop"""
        def on_release(key):
            if key == Key.alt_r:  # Right Option
                self._handle_option_tap()
            elif key == Key.esc:
                if self.recording:
                    self.cancel_recording()

        with keyboard.Listener(on_release=on_release) as listener:
            try:
                listener.join()
            except KeyboardInterrupt:
                print("\nQuitting...")
                if self.recording:
                    self.stop_recording()


def main():
    if not os.getenv("DEEPGRAM_API_KEY"):
        print("❌ DEEPGRAM_API_KEY not set")
        return

    app = AquaVoice()
    app.run()


if __name__ == "__main__":
    main()
