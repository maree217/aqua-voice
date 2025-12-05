"""
py2app setup for Aqua Voice

Run: python setup.py py2app
"""

from setuptools import setup

APP = ['aqua_voice_app.py']
DATA_FILES = ['.env']

OPTIONS = {
    'argv_emulation': False,
    'iconfile': None,
    'plist': {
        'CFBundleName': 'Aqua Voice',
        'CFBundleDisplayName': 'Aqua Voice',
        'CFBundleIdentifier': 'com.aquavoice.app',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'LSUIElement': True,  # Hide from Dock - menu bar only!
        'NSMicrophoneUsageDescription': 'Aqua Voice needs microphone access to transcribe your speech.',
        'NSAppleEventsUsageDescription': 'Aqua Voice needs accessibility to type text for you.',
    },
    'packages': [
        'rumps',
        'pynput',
        'pyaudio',
        'deepgram',
        'httpx',
        'httpcore',
        'anyio',
        'certifi',
        'idna',
        'sniffio',
        'h11',
        'websockets',
        'typing_extensions',
    ],
    'includes': [
        'pynput.keyboard._darwin',
        'pynput._util.darwin',
    ],
}

setup(
    app=APP,
    name='Aqua Voice',
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
