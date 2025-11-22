"""
FL Studio Fire Controller Interface Module for Fire MIDI Macro Runner
Author: Nelson F. Fernandez Jr.
Created on: 2025-Nov-21

This module provides low-level communication with the Akai FL Studio Fire MIDI controller,
specifically handling its RGB LED lighting capabilities. It includes functions for
initializing the MIDI connection, converting between color formats, and sending MIDI
SysEx messages to control the pad colors.

The module defines constants for the Fire controller's MIDI implementation, including:
- Valid pad range (54-117)
- SysEx message format and prefixes
- Message IDs for different types of commands

Functions:
- init_port: Initialize MIDI connection to the Fire controller
- send_midi_cc: Send Control Change messages
- RGB color conversion utilities (rgb_to_color, color_to_rgb, color_to_fire_color)
- SysEx message construction and transmission
- set_pad_color: Set RGB color for a specific pad

This module is used by fire-midi-macro-runner.py to provide visual feedback
on the controller when macros are active.
"""

import mido 
import mido.backends.rtmidi
import time
import math


# sysex state def
MSGID_SET_RGB_PAD_LED_STATE = 0x65

# Pads
SYSEX_PREFIX = [0x47, 0x7F, 0x43]
FIRE_PORT = None 
PADSTART = 54
PADEND = 117

def init_port(port_name):
    """
    Initialize the MIDI output port for communicating with the FL Studio Fire controller.
    
    Parameters:
        port_name (str): The name of the MIDI output port to open.
        
    Returns:
        None
    
    Side Effects:
        - Sets the global FIRE_PORT variable
        - Clears all pad LEDs by setting them to black (0x000000)
    """
    global FIRE_PORT
    FIRE_PORT = mido.open_output(port_name)
    #clear all pads
    send_midi_cc(FIRE_PORT, 0x7f, 0x00, channel=0)
    for pad in range(PADSTART, PADEND):
        set_pad_color(pad, 0x000000)

def send_midi_cc(port, control, value, channel=0):
    """
    Sends a MIDI CC message to the specified MIDI port.
    
    Parameters:
        port_name (str): The name of the MIDI output port.
        control (int): The control number (0-127).
        value (int): The control value (0-127).
        channel (int): The MIDI channel (0-15). Default is 0.
    
    Returns:
        None
    """
    # with mido.open_output(port_name) as outport:
    msg = mido.Message('control_change', channel=channel, control=control, value=value)
    port.send(msg)
    
def rgb_to_color(r, g, b):
    """
    Convert separate RGB component values to a single 24-bit color integer.
    
    Parameters:
        r (int): Red component (0-255)
        g (int): Green component (0-255)
        b (int): Blue component (0-255)
        
    Returns:
        int: 24-bit color value in 0xRRGGBB format
    """
    # Clamp values to range 0-255
    r = max(0, min(255, r))
    g = max(0, min(255, g))
    b = max(0, min(255, b))
    # Convert RGB values to 24-bit integer color
    color = (r << 16) | (g << 8) | b
    return color

def color_to_rgb(color):
    """
    Extract the RGB component values from a 24-bit color integer.
    
    Parameters:
        color (int): A 24-bit color value in 0xRRGGBB format
        
    Returns:
        tuple: A tuple containing (r, g, b) values as integers (0-255)
    """   
    # Extract the r, g, and b components from the hex value
    r = (color & 0xFF0000) >> 16
    g = (color & 0x00FF00) >> 8
    b = color & 0x0000FF

    return r, g, b

def color_to_fire_color(color):
    """
    Convert a standard 24-bit RGB color to Fire controller compatible color format.
    
    The Fire controller requires RGB values in a scaled range (0-127 instead of 0-255).
    This function extracts RGB components, scales them appropriately, and recombines
    them into a new color value suitable for the Fire controller.
    
    Parameters:
        color (int): A 24-bit color value in standard 0xRRGGBB format
        
    Returns:
        int: A 24-bit color value with components scaled for Fire controller compatibility
    """
    r, g, b = color_to_rgb(color)

    # Convert the components to values between 0 and 127
    r = int(r / 256 * 128)
    g = int(g / 256 * 128)
    b = int(b / 256 * 128)

    # Return the new color
    return rgb_to_color(r, g, b)

def get_hi_lo_vals(value):
    """
    Split a value into high and low bytes for MIDI SysEx compatibility.
    
    MIDI SysEx messages require data bytes to be 7-bit (max value 0x7F),
    so this function splits a larger value into two 7-bit bytes.
    
    Parameters:
        value (int): The value to split into high and low bytes
        
    Returns:
        tuple: A tuple containing (high_byte, low_byte), both 7-bit values (0-127)
    """
    high_byte = (value >> 7) & 0x7F
    low_byte = value & 0x7F
    return high_byte, low_byte

def send_msg_to_device(msgID, byteList):
    """
    Create and send a SysEx message to the Fire controller.
    
    This function formats the data according to the Fire controller's SysEx 
    message protocol, which includes a prefix, message ID, length (as high/low bytes),
    followed by the payload data.
    
    Parameters:
        msgID (int): The message ID that indicates the type of message being sent
        byteList (list): List of data bytes to send in the message
        
    Returns:
        None
        
    Requires:
        Global FIRE_PORT to be initialized with an open MIDI output port
    """
    hiHex, loHex = get_hi_lo_vals(len(byteList))
    dataOut = []
    dataOut.extend(SYSEX_PREFIX)
    dataOut.extend([msgID, hiHex, loHex])
    dataOut.extend(byteList)
    sysex_msg = mido.Message('sysex', data=bytes(dataOut))
    FIRE_PORT.send(sysex_msg)

def set_pad_color(padIdx, color):
    """
    Set the color of a specific pad on the Fire controller.
    
    Parameters:
        padIdx (int): The MIDI Control ID of the pad (54-117 for Fire controller)
        color (int): RGB color value in 0xRRGGBB format
        
    Returns:
        None
        
    Notes:
        - Only pads within the valid range (PADSTART to PADEND) will be affected
        - The color is automatically converted to the Fire controller's color format
    """
    if padIdx < PADSTART or padIdx > PADEND:
        return
    padIdx = padIdx - PADSTART
    padColor = color_to_fire_color(color)
    r,g,b = color_to_rgb(padColor)
    bytes = [padIdx, r, g, b]
    send_msg_to_device(MSGID_SET_RGB_PAD_LED_STATE, bytes)
