"""
Fire MIDI Macro Runner
Author: Nelson F. Fernandez Jr. (modified by Cline)
Created on: 2025-Nov-21

A Python application that maps MIDI pad controllers (specifically the FL Studio FIRE)
to keyboard shortcuts, text input, and application launches, effectively creating
a customizable macro pad with visual RGB feedback.

This application connects to your MIDI controller and allows you to trigger
various actions by pressing pads. Each pad can be configured with:
- A keyboard shortcut (e.g., F3, Ctrl+S, Alt+Tab)
- A command to run an application or open a URL using the RUN| prefix
- A text string to type using the TYPE| prefix
- A sound to play using the SOUND| prefix
- A configuration file to load using the CONFIG| prefix
- A custom RGB color for visual feedback on the Fire controller

Key features:
- MIDI device auto-detection and configuration
- JSON-based macro definitions for easy customization
- RGB color feedback for active macros (Fire controller only)
- Support for both Fire-specific features and generic MIDI controllers 
- Keyboard shortcuts, program launching, and text typing capabilities
- Hot-swappable configurations via CONFIG| actions

Components:
- macros.py: Core functions for keyboard shortcuts and program execution
- fire_code.py: Fire controller-specific MIDI features (pad colors)
- gen_code.py: Generic MIDI controller compatibility layer
- macro_runner.py: MacroRunner class for configuration management
- macros_config.json: User-defined macro configurations

Usage:
1. Edit macros_config.json to define your MIDI pad mappings
2. Run this application
3. Press pads on your controller to trigger the configured actions
4. Use CONFIG| actions to switch between different configuration files
"""

import os
import re
import time
import mido
import macros
from macro_runner import MacroRunner

# this line import the fire specific code.
import fire_code as fc
# to make a generic device (non Fire) version, comment the line above and uncomment the line below
# import gen_code as fc

MIDI_CONFIG_FILE = "midi_config.json"
MACROS_CONFIG_FILE = "macros_config.json"
DEFAULT_CONFIG_FILE = "default_macros.json"  # Preferred configuration file if it exists


# ---------------------------
# LED Color Wrapper
# ---------------------------
def set_pad_color(midiId, color):
    """
    Wrapper for MIDI LED feedback to set pad colors.
    
    Parameters:
        midiId (int): MIDI Control ID number for the pad/control to set.
        color (int): RGB color value in 0xRRGGBB hex format.
        
    Returns:
        None
    """
    print(f"[LED INIT] set_pad_color({midiId}, 0x{color:06X})")
    fc.set_pad_color(midiId, color)


# ---------------------------
# MIDI Device Selection
# ---------------------------
def list_devices():
    """
    List all available MIDI input devices on the system.
    
    Returns:
        list: A list of available MIDI device names.
    """
    devices = mido.get_input_names()
    print("\nAvailable MIDI Input Devices:\n")
    for i, name in enumerate(devices):
        print(f"  [{i}] {name}")
    return devices

def select_device(devices):
    """
    Prompt the user to select a MIDI device from the provided list.
    
    Parameters:
        devices (list): List of available MIDI device names.
        
    Returns:
        str: The name of the selected MIDI device.
    """
    while True:
        try:
            num = int(input("\nSelect device number: "))
            if 0 <= num < len(devices):
                return devices[num]
        except ValueError:
            pass
        print("Invalid selection, try again.")






def initialize_pad_colors(control_colors):
    """
    Initialize all pad colors based on the configuration.
    
    Parameters:
        control_colors (dict): Mapping of MIDI Control IDs to color values (0xRRGGBB format).
    
    Returns:
        None
    """
    fc.clear_pads()
    for midiId, color in control_colors.items():
        if color is not None:
            set_pad_color(midiId, color)


def display_action_text(action_text):
    """
    Display macro action text on the Fire OLED (if supported by the active controller module).

    Parameters:
        action_text (str): Action text to display.

    Returns:
        None
    """
    try:
        if not hasattr(fc, "show_text"):
            return

        # Support literal "\\n" in macro text as an OLED newline.
        normalized_text = str(action_text).replace("\\n", "\n")

        # Use the same explicit rendering parameters as the working test app path.
        fc.show_text(
            normalized_text,
            font_path=getattr(fc, "DEFAULT_FONT", None),
            threshold=127,
            invert=False,
            include_font_name=False,
        )
    except Exception as e:
        print(f"[Display] Could not show action text: {e}")


def get_display_text(action):
    """
    Build display-friendly text from a macro action string.

    Examples:
      RUN|C:\\Program Files\\VideoLAN\\VLC\\vlc.exe -> RUN vlc.exe
      RUN|"C:\\Program Files\\VideoLAN\\VLC\\vlc.exe" --arg -> RUN vlc.exe
      SOUND|sounds\\air_horn.wav -> SOUND air_horn.wav
      CONFIG|gaming_macros.json -> CONFIG gaming_macros.json
      TYPE|hello world -> TYPE hello world
    """
    if not isinstance(action, str):
        return str(action)

    action = action.strip()

    def _first_token(command_text):
        s = command_text.strip()
        if not s:
            return ""
        if s[0] == '"':
            end_quote = s.find('"', 1)
            if end_quote > 0:
                return s[1:end_quote]
        return s.split()[0]

    def _extract_run_target(command_text):
        """
        Extract command target path from RUN payload.

        Supports:
        - Quoted commands: "C:\\Path With Spaces\\app.exe" --args
        - Unquoted paths with spaces that include known executable extensions
          e.g. C:\\Program Files\\VideoLAN\\VLC\\vlc.exe --arg
        """
        s = command_text.strip()
        if not s:
            return ""

        if s[0] == '"':
            end_quote = s.find('"', 1)
            if end_quote > 0:
                return s[1:end_quote]

        ext_match = re.match(
            r"(?i)^(.+?\.(?:exe|bat|cmd|com|ps1|py|lnk|msc))(?:\s|$)",
            s,
        )
        if ext_match:
            return ext_match.group(1)

        return "" + _first_token(s)

    if action.startswith("RUN|"):
        payload = action[4:]
        cmd = _extract_run_target(payload)
        name = os.path.basename(cmd.replace("\\", "/")) if cmd else ""
        return f"RUN\n{name}".strip()

    if action.startswith("SOUND|"):
        payload = action[6:].strip()
        name = os.path.basename(payload.replace("\\", "/")) if payload else ""
        return f"SOUND\n{name}".strip()

    if action.startswith("CONFIG|"):
        payload = action[7:].strip()
        name = os.path.basename(payload.replace("\\", "/")) if payload else ""
        return f"CONFIG\n{name}".strip()

    if action.startswith("TYPE|"):
        return f"TYPE\n{action[5:].strip()}".strip()

    return f"PRESS\n{action}".strip()



def monitor_device(port_name, runner):
    """
    Continuously monitor a MIDI device and handle incoming messages.
    
    Parameters:
        port_name (str): Name of the MIDI input device to monitor.
        runner (MacroRunner): The MacroRunner instance to handle messages.
        
    Returns:
        None
    """
    print(f"\nListening on: {port_name}")
    print("Press Ctrl+C to quit.\n")

    with mido.open_input(port_name) as port:  # This is correct despite linting error
        while True:
            for msg in port.iter_pending():
                if msg.type == "note_on" and msg.velocity > 0 and hasattr(msg, "note"):
                    action = runner.control_actions.get(msg.note)
                    if action:
                        display_action_text(get_display_text(action))
                runner.handle_message(msg)
            time.sleep(0.01)


# ---------------------------
# Main
# ---------------------------
def main():
    """
    Main entry point for the application.
    
    Loads configurations, initializes the MIDI device connection,
    sets up pad colors according to configuration, and starts
    monitoring for incoming MIDI messages.
    """
    # Create and initialize the MacroRunner with preferred configuration
    runner = MacroRunner(MIDI_CONFIG_FILE, MACROS_CONFIG_FILE, DEFAULT_CONFIG_FILE)
    runner.load_configuration()

    # Set up the CONFIG| action callback
    def handle_config_reload(config_path):
        """Handle a configuration reload request from a macro action"""
        success, new_colors = runner.reload_configuration(config_path)
        if success:
            initialize_pad_colors(new_colors)
            print(f"[Config] Loaded configuration from {config_path}")
            return True
        else:
            print(f"[Config] Failed to load configuration from {config_path}")
            return False
    
    macros.set_config_reload_callback(handle_config_reload)

    # Inspect available devices
    devices = list_devices()
    if not devices:
        print("No MIDI devices found.")
        return

    # Find or prompt device
    stored_name = runner.midi_cfg.get("device_name")
    if stored_name and stored_name in devices:
        port_name = stored_name
        print(f"\n[Config] Using saved device: {port_name}")
    else:
        if stored_name:
            print(f"\n[Config] Saved device not found: {stored_name}")
        port_name = select_device(devices)
        runner.midi_cfg["device_name"] = port_name
        runner.save_json(MIDI_CONFIG_FILE, runner.midi_cfg)

    # Run
    try:
        fc.init_port(port_name)
        initialize_pad_colors(runner.get_color_map())
        monitor_device(port_name, runner)

    except KeyboardInterrupt:
        print("\nExiting cleanly...")
        fc.clear_pads()

    finally:
        if hasattr(fc, "close_port"):
            fc.close_port()


if __name__ == "__main__":
    main()
