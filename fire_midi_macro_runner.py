"""
Fire MIDI Macro Runner
Author: Nelson F. Fernandez Jr.
Created on: 2025-Nov-21

A Python application that maps MIDI pad controllers (specifically the FL Studio FIRE)
to keyboard shortcuts, text input, and application launches, effectively creating
a customizable macro pad with visual RGB feedback.

This application connects to your MIDI controller and allows you to trigger
various actions by pressing pads. Each pad can be configured with:
- A keyboard shortcut (e.g., F3, Ctrl+S, Alt+Tab)
- A command to run an application or open a URL using the RUN| prefix
- A text string to type using the TYPE| prefix
- A custom RGB color for visual feedback on the Fire controller

Key features:
- MIDI device auto-detection and configuration
- JSON-based macro definitions for easy customization
- RGB color feedback for active macros (Fire controller only)
- Support for both Fire-specific features and generic MIDI controllers 
- Keyboard shortcuts, program launching, and text typing capabilities

Components:
- macros.py: Core functions for keyboard shortcuts and program execution
- fire_code.py: Fire controller-specific MIDI features (pad colors)
- gen_code.py: Generic MIDI controller compatibility layer
- macros_config.json: User-defined macro configurations

Usage:
1. Edit macros_config.json to define your MIDI pad mappings
2. Run this application
3. Press pads on your controller to trigger the configured actions
"""

import time
import json
import os
import mido
import macros

# this line import the fire specific code.
import fire_code as fc
# to make a generic device (non Fire) version, comment the line above and uncomment the line below
# import gen_code as fc

MIDI_CONFIG_FILE = "midi_config.json"
MACROS_CONFIG_FILE = "macros_config.json"


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
# Config Helpers
# ---------------------------
def load_json(path):
    """
    Load and parse a JSON file from the specified path.
    
    Parameters:
        path (str): The path to the JSON file.
        
    Returns:
        dict: The parsed JSON content, or an empty dict if file doesn't exist or can't be read.
    """
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Config] Could not read {path}: {e}")
    return {}

def save_json(path, data):
    """
    Save data as JSON to the specified path.
    
    Parameters:
        path (str): The path where the JSON file will be saved.
        data (dict): The data to be serialized and saved.
        
    Returns:
        None
    """
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"[Config] Saved {path}")
    except Exception as e:
        print(f"[Config] Could not save {path}: {e}")


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


# ---------------------------
# Color Parsing
# ---------------------------
def parse_color(value):
    """
    Parse color values from various formats into a standard 0xRRGGBB integer format.
    
    Parameters:
        value: The color value to parse. Can be:
            - None: Returns None
            - int: Returns the integer value directly
            - str: Parses hex strings like "0xFF0000" or "#FF0000" to integers
    
    Returns:
        int: The parsed color as an integer in 0xRRGGBB format, or None if input was None.
    """
    if value is None:
        return None

    if isinstance(value, int):
        return value

    if isinstance(value, str):
        s = value.strip().lower()
        if s.startswith("0x"):
            return int(s, 16)
        if s.startswith("#"):
            return int(s[1:], 16)
        return int(s, 16)

    return None


# ---------------------------
# Macro Mapping + Color Assignment
# ---------------------------
def build_control_macros(cfg):
    """
    Build mappings between MIDI Control IDs and their associated actions and colors.
    
    Parameters:
        cfg (dict): Configuration dictionary loaded from macros_config.json.
        
    Returns:
        tuple: A tuple containing three dictionaries:
            - control_macros (dict): Maps MIDI Control IDs to callable functions.
            - control_colors (dict): Maps MIDI Control IDs to RGB color values.
            - control_actions (dict): Maps MIDI Control IDs to human-readable action descriptions.
    """
    control_macros = {}
    control_colors = {}
    control_actions = {}

    # Load global default color
    default_color = parse_color(cfg.get("default_color", "0xFFFFFF"))

    raw = cfg.get("control_macros", {})
    for control_str, entry in raw.items():
        try:
            note = int(control_str)
        except ValueError:
            print(f"[Config] Invalid note value: {control_str}")
            continue

        # Old style: just a action string
        if isinstance(entry, str):
            action = entry
            color_int = default_color

        # New style
        elif isinstance(entry, dict):
            action = entry.get("action")
            if not isinstance(action, str):
                print(f"[Config] Missing/invalid 'action' for note {control_str}")
                continue
            color_value = entry.get("color")
            color_int = parse_color(color_value) if color_value else default_color

        else:
            print(f"[Config] Invalid mapping for note {control_str}")
            continue

        # Store macro callable
        control_macros[note] = (lambda kc=action: macros.sendkey(kc))

        # Store actual action text for display
        control_actions[note] = action

        # Store color
        control_colors[note] = color_int

    return control_macros, control_colors, control_actions


def initialize_pad_colors(control_colors):
    """
    Initialize all pad colors based on the configuration.
    
    Parameters:
        control_colors (dict): Mapping of MIDI Control IDs to color values (0xRRGGBB format).
    
    Returns:
        None
    """
    for midiId, color in control_colors.items():
        if color is not None:
            set_pad_color(midiId, color)


# ---------------------------
# MIDI Handling
# ---------------------------
def handle_message(msg, control_macros, control_actions):
    """
    Process incoming MIDI messages and trigger the associated actions.
    
    Parameters:
        msg (mido.Message): The MIDI message to handle.
        control_macros (dict): Mapping of MIDI Control IDs to callable functions.
        control_actions (dict): Mapping of MIDI Control IDs to action descriptions.
        
    Returns:
        None
    """
    if msg.type == "note_on" and msg.velocity > 0:
        control_id = msg.note
        if control_id in control_macros:
            print(f"Trigger: MIDI Control ID# {control_id} -> {control_actions[control_id]}")
            control_macros[control_id]()
        else:
            print(f"Trigger: MIDI Control ID# {control_id} -> * UNUSED *")


def monitor_device(port_name, control_macros, control_actions):
    """
    Continuously monitor a MIDI device and handle incoming messages.
    
    Parameters:
        port_name (str): Name of the MIDI input device to monitor.
        control_macros (dict): Mapping of MIDI Control IDs to callable functions.
        control_actions (dict): Mapping of MIDI Control IDs to action descriptions.
        
    Returns:
        None
    """
    print(f"\nListening on: {port_name}")
    print("Press Ctrl+C to quit.\n")

    with mido.open_input(port_name) as port:
        while True:
            for msg in port.iter_pending():
                handle_message(msg, control_macros, control_actions)
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
    midi_cfg = load_json(MIDI_CONFIG_FILE)
    macro_cfg = load_json(MACROS_CONFIG_FILE)

    # Build macros + colors from macros_config.json
    control_macros, control_colors, control_actions = build_control_macros(macro_cfg)

    # Inspect available devices
    devices = list_devices()
    if not devices:
        print("No MIDI devices found.")
        return

    # Find or prompt device
    stored_name = midi_cfg.get("device_name")
    if stored_name and stored_name in devices:
        port_name = stored_name
        print(f"\n[Config] Using saved device: {port_name}")
    else:
        if stored_name:
            print(f"\n[Config] Saved device not found: {stored_name}")
        port_name = select_device(devices)
        midi_cfg["device_name"] = port_name
        save_json(MIDI_CONFIG_FILE, midi_cfg)

    # Run
    try:
        fc.init_port(port_name)
        initialize_pad_colors(control_colors)
        monitor_device(port_name, control_macros, control_actions)

    except KeyboardInterrupt:
        print("\nExiting cleanly...")

    finally:
        if hasattr(fc, "close_port"):
            fc.close_port()


if __name__ == "__main__":
    main()
