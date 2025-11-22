"""
Generic MIDI Controller Compatibility Module for Fire MIDI Macro Runner
Author: Nelson F. Fernandez Jr.
Created on: 2025-Nov-21

This module provides stub implementations of the functions in fire_code.py
for use with MIDI controllers that don't support the RGB LED color features 
of the FL Studio Fire controller.

The module enables code that was written for the Fire controller to work with
other MIDI controllers without modification, by implementing the same API but
with non-functional color-related calls that simply do nothing.

When a user wants to use a non-Fire MIDI controller, they can change the import
in fire-midi-macro-runner.py to use this module instead of fire_code.py.

Functions:
- init_port: Empty stub that mimics initializing a MIDI port
- set_pad_color: Empty stub that mimics setting pad colors

All functions maintain API compatibility with fire_code.py but perform no actions.
"""

def init_port(port_name):
    """
    Initialize the MIDI output port for a generic MIDI device.
    
    This is a stub implementation for non-Fire MIDI controllers that don't 
    support RGB pad colors. It provides API compatibility with fire_code.py 
    but performs no actual initialization.
    
    Parameters:
        port_name (str): The name of the MIDI output port to open.
        
    Returns:
        None
    """
    pass

def set_pad_color(padIdx, color):
    """
    Set the color of a specific pad (stub implementation).
    
    This is a stub implementation for non-Fire MIDI controllers that don't
    support RGB pad colors. It provides API compatibility with fire_code.py
    but performs no actual color setting.
    
    Parameters:
        padIdx (int): The MIDI Control ID of the pad
        color (int): RGB color value in 0xRRGGBB format
        
    Returns:
        None
    """
    pass
