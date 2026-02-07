"""
MacroRunner Module for Fire MIDI Macro Runner
Author: Nelson F. Fernandez Jr. (modified by Cline)
Created on: 2025-Nov-23

This module provides a MacroRunner class that encapsulates configuration management
and macro execution for the Fire MIDI Macro Runner. It handles loading, reloading, 
and applying macro configurations that map MIDI controls to specific actions.

The class manages:
- Loading configuration from JSON files
- Mapping MIDI Control IDs to actions and colors
- Processing MIDI messages and triggering appropriate actions
- Handling configuration reload requests

This module works together with:
- fire_midi_macro_runner.py: Manages MIDI device connections and message routing
- macros.py: Provides the core action functionality
- fire_code.py/gen_code.py: Handles MIDI-specific functionality
"""

import json
import os
import time
import macros
from typing import Dict, Tuple, Callable, Any, Optional

class MacroRunner:
    """
    Core class that manages macro configuration and execution.
    Handles configuration loading/reloading and mapping of MIDI controls to actions.
    """

    def __init__(self, midi_config_path="midi_config.json", macros_config_path="macros_config.json", 
                 preferred_config_path="default_macros.json"):
        """
        Initialize the MacroRunner with paths to configuration files.
        
        Parameters:
            midi_config_path (str): Path to the MIDI device configuration file.
            macros_config_path (str): Path to the fallback macro definitions configuration file.
            preferred_config_path (str): Path to the preferred macro definitions configuration file.
                                         If this file exists, it will be used instead of macros_config_path.
        """
        # Configuration paths
        self.midi_config_path = midi_config_path
        self.macros_config_path = macros_config_path
        self.preferred_config_path = preferred_config_path
        
        # Internal state
        self.midi_cfg = {}
        self.macro_cfg = {}
        self.control_macros = {}  # Maps MIDI Control IDs to callable functions
        self.control_colors = {}  # Maps MIDI Control IDs to RGB color values
        self.control_actions = {}  # Maps MIDI Control IDs to human-readable action descriptions
        self.control_hold_enabled = {}  # Maps MIDI Control IDs to boolean (whether hold is enabled)
        self.currently_held_keys = {}  # Maps MIDI Control IDs to the keys currently being held
        self.debug_midi_messages = False  # If True, print raw MIDI messages for troubleshooting
        self.note_on_debounce_ms = 0  # Optional debounce window for note_on events (milliseconds)
        self.last_note_on_time = {}  # Maps MIDI Control IDs to last accepted note_on timestamp

    def load_json(self, path: str) -> dict:
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

    def save_json(self, path: str, data: dict) -> None:
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

    def parse_color(self, value) -> Optional[int]:
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

    def build_control_macros(self, cfg: dict) -> Tuple[Dict[int, Callable], Dict[int, int], Dict[int, str]]:
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
        self.control_hold_enabled = {}  # Clear and rebuild hold settings

        # Load global default color
        default_color = self.parse_color(cfg.get("default_color", "0xFFFFFF"))

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
                hold_enabled = False

            # New style
            elif isinstance(entry, dict):
                action = entry.get("action")
                if not isinstance(action, str):
                    print(f"[Config] Missing/invalid 'action' for note {control_str}")
                    continue
                color_value = entry.get("color")
                color_int = self.parse_color(color_value) if color_value else default_color
                hold_enabled = entry.get("hold", False)  # Default to False if not specified

            else:
                print(f"[Config] Invalid mapping for note {control_str}")
                continue

            # Store macro callable
            control_macros[note] = (lambda kc=action: macros.sendkey(kc))

            # Store actual action text for display
            control_actions[note] = action

            # Store color
            control_colors[note] = color_int

            # Store hold setting
            self.control_hold_enabled[note] = hold_enabled

        return control_macros, control_colors, control_actions

    def load_configuration(self, config_path: str = None) -> bool:
        """
        Load and apply a configuration file.
        
        Parameters:
            config_path (str, optional): Path to the configuration file to load.
                                        If None, tries to use preferred_config_path first,
                                        then falls back to macros_config_path.
        
        Returns:
            bool: True if configuration was loaded successfully, False otherwise.
        """
        # Load MIDI device configuration
        self.midi_cfg = self.load_json(self.midi_config_path)
        
        # Determine which config file to load
        if config_path:
            # If a specific path is provided, use it
            macro_config_path = config_path
        else:
            # Check if preferred config exists, otherwise use fallback
            if os.path.exists(self.preferred_config_path):
                macro_config_path = self.preferred_config_path
                print(f"[Config] Using preferred configuration: {self.preferred_config_path}")
            else:
                macro_config_path = self.macros_config_path
                print(f"[Config] Preferred configuration not found, using: {self.macros_config_path}")
        
        # Load the selected configuration
        self.macro_cfg = self.load_json(macro_config_path)
        
        if not self.macro_cfg:
            print(f"[Config] Failed to load configuration from {macro_config_path}")
            return False

        # Optional global runtime settings
        self.debug_midi_messages = bool(self.macro_cfg.get("debug_midi_messages", False))
        debounce_val = self.macro_cfg.get("note_on_debounce_ms", 0)
        try:
            self.note_on_debounce_ms = max(0, int(debounce_val))
        except (TypeError, ValueError):
            print(f"[Config] Invalid note_on_debounce_ms value '{debounce_val}', defaulting to 0")
            self.note_on_debounce_ms = 0
        self.last_note_on_time.clear()
            
        # If we successfully loaded the config, update our current config path
        self.macros_config_path = macro_config_path
            
        # Build mappings
        self.control_macros, self.control_colors, self.control_actions = self.build_control_macros(self.macro_cfg)
        return True

    def reload_configuration(self, config_path: str) -> Tuple[bool, Dict[int, int]]:
        """
        Reload configuration from a different file.
        Releases any currently held keys before reloading to prevent stuck keys.
        
        Parameters:
            config_path (str): Path to the new configuration file.
            
        Returns:
            tuple: (success, color_map)
                - success (bool): True if reload was successful
                - color_map (dict): Updated mapping of MIDI Control IDs to colors
        """
        # Release all currently held keys before reloading to prevent stuck keys
        if self.currently_held_keys:
            print(f"[Config] Releasing {len(self.currently_held_keys)} held key(s) before reload")
            for control_id, action in list(self.currently_held_keys.items()):
                macros.sendkey(action, mode="release")
            self.currently_held_keys.clear()
        
        # Store current configuration for fallback
        old_macro_cfg = self.macro_cfg
        old_control_macros = self.control_macros
        old_control_colors = self.control_colors
        old_control_actions = self.control_actions
        
        # Try loading the new configuration
        print(f"[Config] Attempting to load configuration from {config_path}")
        success = self.load_configuration(config_path)
        
        if not success:
            # Restore old configuration on failure
            self.macro_cfg = old_macro_cfg
            self.control_macros = old_control_macros
            self.control_colors = old_control_colors
            self.control_actions = old_control_actions
            return False, old_control_colors
            
        # Update the default config path to the new one if successful
        self.macros_config_path = config_path
        return True, self.control_colors

    def get_color_map(self) -> Dict[int, int]:
        """
        Return the current color mapping for initializing pad colors.
        
        Returns:
            dict: Current mapping of MIDI Control IDs to color values.
        """
        return self.control_colors

    def handle_message(self, msg: Any) -> None:
        """
        Process incoming MIDI messages and trigger the associated actions.
        Handles both button press (note_on) and button release (note_off) events.
        
        Parameters:
            msg: The MIDI message to handle (from mido library).
            
        Returns:
            None
        """
        if self.debug_midi_messages:
            print(f"[MIDI DEBUG] {msg}")

        # We only process note messages for macro triggering.
        if not hasattr(msg, "note"):
            return

        control_id = msg.note
        
        # Button Press: note_on with velocity > 0
        if msg.type == "note_on" and msg.velocity > 0:
            # Optional debounce to reduce accidental double-triggers/noise
            if self.note_on_debounce_ms > 0:
                now = time.monotonic()
                last = self.last_note_on_time.get(control_id)
                if last is not None and (now - last) * 1000 < self.note_on_debounce_ms:
                    if self.debug_midi_messages:
                        print(f"[MIDI DEBUG] Debounced note_on for control {control_id}")
                    return
                self.last_note_on_time[control_id] = now

            if control_id not in self.control_macros:
                print(f"Trigger: MIDI Control ID# {control_id} -> * UNUSED *")
                return
                
            action = self.control_actions[control_id]
            hold_enabled = self.control_hold_enabled.get(control_id, False)
            
            # Check if this is a special command (RUN|, TYPE|, SOUND|, CONFIG|)
            is_special_command = action.startswith(("RUN|", "TYPE|", "SOUND|", "CONFIG|"))
            
            if is_special_command:
                # Special commands always fire on press only, ignore hold setting
                print(f"Trigger: MIDI Control ID# {control_id} -> {action}")
                self.control_macros[control_id]()
            elif hold_enabled:
                # Ignore duplicate note_on events while the same hold key is already active
                if control_id in self.currently_held_keys:
                    if self.debug_midi_messages:
                        print(f"[MIDI DEBUG] Ignoring duplicate hold press for control {control_id}")
                    return
                # Hold mode: press the key down and keep it held
                print(f"Hold Press: MIDI Control ID# {control_id} -> {action}")
                macros.sendkey(action, mode="press")
                self.currently_held_keys[control_id] = action
            else:
                # Normal mode: send the key (press + release)
                print(f"Trigger: MIDI Control ID# {control_id} -> {action}")
                self.control_macros[control_id]()
        
        # Button Release: note_off OR note_on with velocity == 0
        elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
            if control_id in self.currently_held_keys:
                action = self.currently_held_keys[control_id]
                print(f"Hold Release: MIDI Control ID# {control_id} -> {action}")
                macros.sendkey(action, mode="release")
                del self.currently_held_keys[control_id]
