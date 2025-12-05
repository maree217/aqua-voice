#!/usr/bin/env python3
"""
Aqua Voice - macOS Menu Bar App
System-wide voice typing with Deepgram Nova-3

Controls:
  - Double-tap Right Option (⌥): Start recording
  - Single tap Right Option or Enter: Stop recording
  - Escape: Cancel and delete typed text

Uses batch transcription (interim_results=False) for reliable output.
Cost: Deepgram Nova-3 is ~$0.0043/minute ($0.26/hour)
"""

import os
import sys
import time
import threading
import subprocess
import logging
import queue
from pathlib import Path

# Setup logging - INFO level for normal use, DEBUG for troubleshooting
LOG_FILE = Path.home() / "aqua_voice.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(LOG_FILE)]
)
log = logging.getLogger(__name__)


def find_env():
    """Find .env file in multiple locations"""
    locations = [
        Path(__file__).parent / ".env",
        Path.home() / "Projects" / "aqua-voice" / ".env",
        Path(os.getcwd()) / ".env",
    ]
    if getattr(sys, 'frozen', False):
        bundle_dir = Path(sys.executable).parent.parent / "Resources"
        locations.insert(0, bundle_dir / ".env")

    for loc in locations:
        if loc.exists():
            return loc
    return None


def load_env():
    """Load environment variables from .env file"""
    env_path = find_env()
    if env_path:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        return True
    return False


load_env()

import rumps
import pyaudio
from pynput.keyboard import Key, Controller as KeyboardController
from AppKit import NSEvent, NSApplication
from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions
import ApplicationServices
import Quartz

# Audio settings
SAMPLE_RATE = 16000
CHUNK_SIZE = 1600  # 100ms chunks

# Key settings
DOUBLE_TAP_THRESHOLD = 0.35
RIGHT_OPTION_KEYCODE = 61
ENTER_KEYCODE = 36
ESCAPE_KEYCODE = 53


def check_accessibility():
    """Check if app has accessibility permissions and prompt if not"""
    # kAXTrustedCheckOptionPrompt = True will show the system dialog
    options = {ApplicationServices.kAXTrustedCheckOptionPrompt: True}
    trusted = ApplicationServices.AXIsProcessTrustedWithOptions(options)
    log.info(f"Accessibility trusted: {trusted}")
    return trusted


def copy_to_clipboard(text):
    """Copy text to macOS clipboard"""
    p = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
    p.communicate(text.encode('utf-8'))


class AquaVoiceApp(rumps.App):
    def __init__(self):
        super().__init__("Aqua Voice", icon=None, title="🎤", quit_button=None)

        self.status_item = rumps.MenuItem("Ready")
        self.status_item.set_callback(None)

        self.menu = [
            self.status_item,
            None,
            rumps.MenuItem("Start Recording (Double-tap ⌥)", callback=self.manual_start),
            rumps.MenuItem("Stop Recording", callback=self.manual_stop),
            None,
            rumps.MenuItem("Quit Aqua Voice", callback=self.quit_app),
        ]

        api_key = os.getenv("DEEPGRAM_API_KEY")
        if not api_key:
            rumps.alert("Error", "DEEPGRAM_API_KEY not found in .env file")
            rumps.quit_application()
            return

        self.deepgram = DeepgramClient(api_key=api_key)
        self.kb = KeyboardController()

        # State
        self.connection = None
        self.recording = False
        self.audio = None
        self.stream = None
        self.audio_thread = None
        self.lock = threading.Lock()

        # Text tracking
        self.final_text = []
        self.all_typed = ""

        # Transcript queue for sequential processing
        self.transcript_queue = queue.Queue()
        self.queue_processor_thread = None
        self.queue_running = False

        # Double-tap detection
        self.last_option_tap = 0
        self.option_tap_count = 0
        self.right_option_pressed = False

        self._setup_key_monitor()
        log.info("Aqua Voice initialized")

    def _setup_key_monitor(self):
        """Setup key monitoring using NSEvent for Option key and CGEventTap for Enter/Escape"""

        # Check accessibility permissions first
        if not check_accessibility():
            log.warning("Accessibility permission not granted - Enter/Escape keys won't work globally")
            rumps.notification(
                "Aqua Voice",
                "Accessibility Permission Needed",
                "Please add Aqua Voice to Accessibility in System Settings for Enter/Escape keys to work."
            )

        # Handler for modifier keys (Option) - NSEvent works for modifiers
        def handle_modifier_event(event):
            try:
                event_type = event.type()
                if event_type != 12:  # NSEventTypeFlagsChanged
                    return

                keycode = event.keyCode()
                if keycode == RIGHT_OPTION_KEYCODE:
                    flags = event.modifierFlags()
                    option_pressed = bool(flags & 0x80000)

                    if option_pressed and not self.right_option_pressed:
                        self.right_option_pressed = True
                    elif not option_pressed and self.right_option_pressed:
                        self.right_option_pressed = False
                        self._handle_option_tap()
            except Exception as e:
                log.exception(f"NSEvent modifier error: {e}")

        try:
            # NSEventMaskFlagsChanged = 1 << 12 = 0x1000
            mask_flags = 0x1000
            self.global_monitor_flags = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
                mask_flags, handle_modifier_event
            )
            log.info("Modifier key monitor started")
        except Exception as e:
            log.exception(f"Failed to create modifier key monitor: {e}")
            self.global_monitor_flags = None

        # Setup CGEventTap for Enter/Escape keys
        self._setup_cgeventtap()

    def _setup_cgeventtap(self):
        """Setup CGEventTap for capturing Enter and Escape keys globally"""

        def cg_event_callback(proxy, event_type, event, refcon):
            try:
                if event_type == Quartz.kCGEventKeyDown:
                    keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)

                    if self.recording:
                        if keycode == ENTER_KEYCODE:
                            log.info("CGEventTap: Enter key pressed - stopping recording")
                            self.stop_recording()
                        elif keycode == ESCAPE_KEYCODE:
                            log.info("CGEventTap: Escape key pressed - cancelling recording")
                            self.cancel_recording()
            except Exception as e:
                log.exception(f"CGEventTap callback error: {e}")

            return event

        try:
            # Create event tap for keyDown events
            event_mask = Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown)

            self.event_tap = Quartz.CGEventTapCreate(
                Quartz.kCGSessionEventTap,
                Quartz.kCGHeadInsertEventTap,
                Quartz.kCGEventTapOptionListenOnly,  # Listen only, don't block events
                event_mask,
                cg_event_callback,
                None
            )

            if self.event_tap is None:
                log.error("Failed to create CGEventTap - Accessibility permission required")
                return

            # Create run loop source and add to current run loop
            run_loop_source = Quartz.CFMachPortCreateRunLoopSource(None, self.event_tap, 0)
            Quartz.CFRunLoopAddSource(
                Quartz.CFRunLoopGetCurrent(),
                run_loop_source,
                Quartz.kCFRunLoopCommonModes
            )

            # Enable the tap
            Quartz.CGEventTapEnable(self.event_tap, True)
            log.info("CGEventTap for Enter/Escape keys started")

        except Exception as e:
            log.exception(f"Failed to create CGEventTap: {e}")
            self.event_tap = None

    def _handle_option_tap(self):
        """Handle Right Option key tap for start/stop"""
        now = time.time()

        if self.recording:
            self.stop_recording()
            self.option_tap_count = 0
        else:
            if now - self.last_option_tap < DOUBLE_TAP_THRESHOLD:
                self.option_tap_count += 1
                if self.option_tap_count >= 1:
                    self.start_recording()
                    self.option_tap_count = 0
            else:
                self.option_tap_count = 0

        self.last_option_tap = now

    def manual_start(self, _):
        if not self.recording:
            self.start_recording()

    def manual_stop(self, _):
        if self.recording:
            self.stop_recording()

    def quit_app(self, _):
        if self.recording:
            self.stop_recording()
        if hasattr(self, 'global_monitor_flags') and self.global_monitor_flags:
            NSEvent.removeMonitor_(self.global_monitor_flags)
        if hasattr(self, 'event_tap') and self.event_tap:
            Quartz.CGEventTapEnable(self.event_tap, False)
        rumps.quit_application()

    def start_recording(self):
        """Start recording and streaming to Deepgram"""
        with self.lock:
            if self.recording:
                return
            self.recording = True

        self.title = "🔴"
        self.status_item.title = "Recording..."
        self.final_text = []
        self.all_typed = ""

        # Clear and start transcript queue processor
        while not self.transcript_queue.empty():
            try:
                self.transcript_queue.get_nowait()
            except queue.Empty:
                break
        self.queue_running = True
        self.queue_processor_thread = threading.Thread(target=self._process_transcript_queue, daemon=True)
        self.queue_processor_thread.start()

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
                smart_format=False,  # No punctuation/capitalization changes
                interim_results=False,  # Only final results - no backtracking
                endpointing=300,
            )

            if not self.connection.start(options):
                self.recording = False
                self.title = "🎤"
                self.status_item.title = "Failed to connect"
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
            log.info("Recording started")

        except Exception as e:
            log.exception(f"Start recording error: {e}")
            self.recording = False
            self.title = "🎤"
            self.status_item.title = f"Error: {str(e)[:30]}"

    def stop_recording(self):
        """Stop recording and finalize text"""
        with self.lock:
            if not self.recording:
                return
            self.recording = False

        self.title = "🎤"

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

        # Wait for queue to finish processing remaining items
        self.queue_running = False
        if self.queue_processor_thread and self.queue_processor_thread.is_alive():
            self.queue_processor_thread.join(timeout=2.0)

        final = ' '.join(self.final_text).strip()
        if final:
            copy_to_clipboard(final)
            self.status_item.title = f"Copied: {final[:20]}..."
            log.info(f"Recording stopped, copied: {final[:50]}...")
        else:
            self.status_item.title = "Ready"
            log.info("Recording stopped, no text")

    def cancel_recording(self):
        """Cancel recording and delete typed text"""
        with self.lock:
            if not self.recording:
                return
            self.recording = False

        self.title = "🎤"

        # Stop queue processor immediately (don't wait for remaining items)
        self.queue_running = False
        # Clear the queue
        while not self.transcript_queue.empty():
            try:
                self.transcript_queue.get_nowait()
            except queue.Empty:
                break

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

        # Wait for queue processor to stop
        if self.queue_processor_thread and self.queue_processor_thread.is_alive():
            self.queue_processor_thread.join(timeout=1.0)

        # Delete all typed text
        if self.all_typed:
            for _ in range(len(self.all_typed)):
                self.kb.press(Key.backspace)
                self.kb.release(Key.backspace)
                time.sleep(0.003)

        self.status_item.title = "Cancelled"
        log.info("Recording cancelled")

    def _capture_audio(self):
        """Capture audio and send to Deepgram"""
        while self.recording and self.stream:
            try:
                data = self.stream.read(CHUNK_SIZE, exception_on_overflow=False)
                if self.connection and self.recording:
                    self.connection.send(data)
            except Exception as e:
                log.exception(f"Audio capture error: {e}")
                break

    def _on_transcript(self, *args, **kwargs):
        """Handle transcript from Deepgram - queue for sequential processing"""
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
            if not text:
                return

            # Queue the transcript for sequential processing
            self.transcript_queue.put(text)

        except Exception as e:
            log.exception(f"Transcript error: {e}")

    def _process_transcript_queue(self):
        """Process transcripts sequentially from the queue"""
        while self.queue_running or not self.transcript_queue.empty():
            try:
                # Use timeout to allow checking queue_running flag
                try:
                    text = self.transcript_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                to_type = text + " "
                self.kb.type(to_type)
                self.all_typed += to_type
                self.final_text.append(text)

                self.transcript_queue.task_done()

            except Exception as e:
                log.exception(f"Queue processor error: {e}")

    def _on_error(self, *args, **kwargs):
        """Handle Deepgram errors"""
        log.error(f"Deepgram error: {args}, {kwargs}")
        self.status_item.title = "Error"


if __name__ == "__main__":
    log.info("Starting Aqua Voice")
    app = AquaVoiceApp()
    app.run()
