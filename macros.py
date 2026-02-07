"""
Macros Module for Fire MIDI Macro Runner
Author: Nelson F. Fernandez Jr. (modified by Cline)
Created on: 2025-Nov-21

This module provides the core functionality for executing user-defined macros
when MIDI control events are triggered. It handles sending keyboard shortcuts,
running applications, opening URLs, typing text strings, and loading configurations.

The module is designed to work with the fire-midi-macro-runner.py main application,
which maps MIDI control IDs to specific macro actions defined in this module.

Functions:
    sendkey(key): Send keyboard shortcuts or execute special commands (RUN|, TYPE|, etc.)
    type_text(text): Type a string of text character by character
    run_program(path_or_name, args, cwd): Start an application, open a file, or load a URL
    reload_config(config_path): Reload configuration from a specified file
    set_config_reload_callback(callback): Register a callback for CONFIG| actions

Usage examples:
    sendkey("ctrl+s")                           # Send Ctrl+S shortcut
    sendkey("RUN|notepad")                      # Launch Notepad
    sendkey("RUN|https://example.com")          # Open URL in browser
    sendkey("TYPE|Hello, world!")               # Type the provided text
    sendkey("SOUND|./sounds/alert.wav")         # Play a sound file
    sendkey("CONFIG|gaming_macros.json")        # Load a different configuration file
"""

import keyboard
import os
import subprocess
from pathlib import Path
from playsound3 import playsound

# Callback for CONFIG| actions
_config_reload_callback = None

def set_config_reload_callback(callback):
    """
    Register a callback function to be called when a CONFIG action is triggered.
    
    Parameters:
        callback: A function that takes a config path string and returns a boolean
                 indicating success or failure.
    """
    global _config_reload_callback
    _config_reload_callback = callback

def reload_config(config_path: str):
    """
    Handle a CONFIG| action to reload a configuration file.
    
    Parameters:
        config_path (str): Path to the configuration file to load.
        
    Returns:
        bool: True if reload was successful, False otherwise.
    """
    if _config_reload_callback:
        return _config_reload_callback(config_path)
    print(f"[Macro Error] No callback registered for CONFIG actions.")
    return False

def sendkey(key: str, mode: str = "send"):
    """
    Send any key combination to the currently-focused window or execute special commands.
    
    Parameters:
        key (str): The key combination or command to execute.
        mode (str): The mode of operation:
            - "send" (default): Press and release the key immediately (normal behavior)
            - "press": Press the key down and hold it
            - "release": Release a previously pressed key
    
    Examples:
        sendkey("f3")                         # Send F3 key
        sendkey("ctrl+s")                     # Send Ctrl+S shortcut
        sendkey("ctrl+shift+p")               # Send Ctrl+Shift+P shortcut
        sendkey("alt+tab")                    # Send Alt+Tab shortcut
        sendkey("w", mode="press")            # Press and hold W key
        sendkey("w", mode="release")          # Release W key
        sendkey("RUN|notepad")                # Launch Notepad
        sendkey("TYPE|Hello")                 # Type "Hello"
        sendkey("SOUND|./sounds/beep.wav")    # Play a sound
        sendkey("CONFIG|editing_macros.json") # Load a configuration
    """
    try:
        # Special commands always execute immediately, ignoring mode
        if key.startswith("RUN|"):
            run_program(key[4:])
        elif key.startswith("TYPE|"):
            type_text(key[5:])
        elif key.startswith("SOUND|"):
            play_sound(key[6:])
        elif key.startswith("CONFIG|"):
            reload_config(key[7:])
        else:
            # Handle keyboard key operations based on mode
            if mode == "press":
                # Press key(s) down and hold
                _press_keys(key)
            elif mode == "release":
                # Release previously pressed key(s)
                _release_keys(key)
            else:  # mode == "send" or any other value
                # Normal behavior: press and release immediately
                keyboard.send(key)
    except Exception as e:
        print(f"[Macro Error] Could not send key '{key}' in mode '{mode}': {e}")


def _press_keys(key: str):
    """
    Press down key(s) and hold them.
    Handles both single keys and combinations like 'ctrl+s'.
    
    Parameters:
        key (str): The key or key combination to press.
    
    Notes:
        keyboard.parse_hotkey() returns a nested tuple structure:
        - (step, step, ...) for key sequences
        - Each step is (key_alternatives, key_alternatives, ...) for keys pressed together
        - Each key_alternatives is (scancode, scancode_alt, ...) for the same key on different layouts
        
        Example: parse_hotkey("ctrl+s") returns (((29,), (31,)),)
        - One step: ((29,), (31,))
        - Two keys pressed together: (29,) for ctrl, (31,) for s
        - We use [0] to get the primary scancode from each key_alternatives tuple
    """
    try:
        parsed = keyboard.parse_hotkey(key)
        
        for step in parsed:
            for key_alternatives in step:
                # key_alternatives is a tuple like (scancode,) or (scancode1, scancode2_alt)
                # Extract the first (primary) scancode to press
                scancode = key_alternatives[0]
                keyboard.press(scancode)
    except Exception as e:
        print(f"[Macro Error] Could not press key '{key}': {e}")


def _release_keys(key: str):
    """
    Release previously pressed key(s).
    Handles both single keys and combinations like 'ctrl+s'.
    Releases keys in reverse order to maintain proper modifier handling.
    
    Parameters:
        key (str): The key or key combination to release.
    
    Notes:
        See _press_keys for details on the parse_hotkey return structure.
        Keys are released in reverse order so modifiers (ctrl, shift, etc.) 
        are released after the main keys.
    """
    try:
        parsed = keyboard.parse_hotkey(key)
        
        # Release keys in reverse order (modifiers last)
        for step in reversed(parsed):
            for key_alternatives in reversed(step):
                # Extract the first (primary) scancode to release
                scancode = key_alternatives[0]
                keyboard.release(scancode)
    except Exception as e:
        print(f"[Macro Error] Could not release key '{key}': {e}")

def type_text(text: str):
    """
    Type a plaintext string character-by-character.
    Good for inserting text like usernames, emails, commands.
    """
    try:
        keyboard.write(text)
    except Exception as e:
        print(f"[Macro Error] Could not type text '{text}': {e}")
        
def run_program(path_or_name: str, args=None, cwd=None):
    """
    Start a program or open a file/URL.
    
    path_or_name:
      - full exe path: r"C:\\Program Files\\App\\app.exe"
      - shortcut / file / folder: r"C:\\Users\\you\\Desktop\\App.lnk"
      - URL: "https://example.com"
      - app name if on PATH: "notepad", "calc", etc.
    
    args: list of strings, optional
      e.g. ["--flag", "value"]
    
    cwd: working directory, optional
    """
    args = args or []

    # Expand ~ and env vars, normalize
    target = os.path.expandvars(os.path.expanduser(path_or_name))
    target_path = Path(target)

    try:
        # If it looks like an existing file/folder/shortcut, let Windows open it
        if target_path.exists():
            os.startfile(str(target_path))
            return

        # If it's a URL, let Windows open default browser
        if target.lower().startswith(("http://", "https://")):
            os.startfile(target)
            return

        # Otherwise treat as command on PATH or exe name
        subprocess.Popen([target] + args, cwd=cwd or None)
    except Exception as e:
        print(f"[Macro Error] Could not start '{path_or_name}': {e}")

# ---------------------------
# Sound macros (playsound3)
# ---------------------------
def play_sound(path: str, block: bool = False):
    """
    Play a sound file.
    - block=False (default) = non-blocking background playback
    - block=True = wait until finished

    Returns a Sound object (playsound3), which you could store
    and later call .stop() on if you add that feature.
    """
    try:
        return playsound(path, block=block)  # playsound3 supports block arg
    except Exception as e:
        print(f"[Macro Error] Could not play sound '{path}': {e}")
        return None
