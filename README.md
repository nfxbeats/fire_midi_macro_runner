# Fire MIDI Macro Runner

A Python utility for mapping the Akai FL Studio Fire MIDI controller to keyboard shortcuts. This allows you to create a custom macro pad with colorful RGB buttons.

With minimal code changes you can use this for any MIDI device. Non-Fire devices will not have color capabilities without custom programming.

## Overview

"fire_midi_macro_runner" connects to your Akai FL Studio Fire MIDI controller and allows you to trigger keyboard shortcuts by pressing pads on the controller. Each pad can be configured with:
- A specific keyboard shortcut (e.g., `F3`, `Ctrl+S`, `Alt+Tab`)
- Start a process (e.g. open a program or web site)
- Type a text string.
- A custom RGB color for visual recognition

This is particularly useful for:
- Audio/video editing workflows
- Productivity enhancements
- Application shortcuts
- Gaming macros

## Requirements

- Python 3.12 or greater
- An AKAI Fire MIDI controller
- Required Python packages:
  - `mido`
  - `keyboard`
  - `python-rtmidi`

## Installation

### Easy Windows Installation
1. Download the main zip file from: [Fire MIDI Macro Runner Main ZIP file](https://github.com/nfxbeats/fire_midi_macro_runner/archive/refs/heads/main.zip)
2. Unzip the files into a folder of your choice.
3. Run `setup_windows.bat` to set up the libraries the first time (only needs to run once)
4. Run `start_windows.bat` to start the program after the libraries are installed.

### Manual Installation

1. Clone or download this repository
2. Optional - Set up a new virtual environment
3. Install required packages:

```
pip install -r requirements.txt
```
4. run `python fire_midi_macro_runner.py`

## Configuration

### MIDI Device Selection

The first time you run the application, it will prompt you to select your MIDI device from a list of available devices. This selection is saved in `midi_config.json` for future use. Delete this file to be prompted again.

If you do not select an Akai Fire, you should replace the `import fire_code as fc` line to `import gen_code as fc` inside fire_midi_macro_runner.py 

### Macro Configuration

Edit `macros_config.json` to customize your pad mappings:

```json
{
  "default_color": "0xFFFFFF",  // Default color for all pads (white)
  "control_macros": {
    
    "56": { "action": "f3", "color": "0xFF0000" },  // Red pad that sends F3 key
    "57": "ctrl+s",                                 // Default color pad that sends Ctrl+S
    "60": "alt+tab"                                 // Default color pad that sends Alt+Tab

    "70": { "action": "RUN|C:/Program Files/VideoLAN/VLC/vlc.exe", "color": "0x00FFFF" },  // Launch VLC media player
    "71": { "action": "RUN|notepad", "color": "0xFF00FF" },                                // Open Notepad
    "72": { "action": "RUN|https://warbeats.com", "color": "0x00FF00" },                   // Open URL in browser

    "105": { "action": "TYPE|you@youremail.com", "color": "0xFFFF00" }                     // type a text string
  }
}
```

#### Configuration Format

- `default_color`: Sets the default color for all pads with a defined macro (hex format)
- `control_macros`: Maps MIDI Control ID#s to keyboard shortcuts
  - Simple format: `"MIDI Control ID#": "key_combination"`
  - Extended format: `"MIDI Control ID#": { "action": "key_combination", "color": "hex_color" }`

#### Color Formats

Colors can be specified in any of these formats:
- Hexadecimal: `"0xFF0000"` or `"#FF0000"` (red)
- Integer: `16711680` (equivalent to 0xFF0000)

> [!NOTE]
> Colors are used for the Akai Fire Pads ONLY which start at MIDI Control ID#54 (top left pad) and end at MIDI Control ID#117 (bottom right pad). Any color definition for controls outside this range or for nonFire devices will be ignored.

## Usage

1. Run the application:

```
python fire_midi_macro_runner.py
```

2. If this is your first time running it, you'll be prompted to select your MIDI device. A `midi_config.json` will be created.
3. Press pads/buttons on your controller to trigger the configured keyboard shortcuts
4. A message will appear in the console showing the MIDI Control ID that was pressed so you can easily know what MIDI Control ID is available to use. If the control is already defined, it will show you the defined text otherwise it will say `* UNUSED *` 
5. Press Ctrl+C in the terminal to exit the application

## Customizing Macros

By editing the `macros_config.json` you can edit the actions to be run when certain MIDI controls are pressed. You can do things like:
- Function keys: `"f1"`, `"f2"`,  etc.
- Modifier combinations: `"ctrl+s"`, `"alt+tab"`, `"shift+f5"`, `"ctrl+alt+delete"`
- Regular keys: `"a"`, `"b"`, etc.
- Multimedia keys: `"play/pause"`, `"stop"`, `"next track"`, `"previous track"`, `"volume up"`, `"volume down"`, `"volume mute"`
- Special keys: `"esc"`, `"print screen"`, `"scroll lock"`, `"up arrow"`, `"insert"`, etc.

An mostly complete list of available key presses can be found here:  [Keyboard Canonical Names](https://github.com/boppreh/keyboard/blob/master/keyboard/_canonical_names.py)

You can also launch applications or open URLs by prefixing your command with `RUN|` prefix. For example:

- File path to executable: `"RUN|C:/Program Files/VideoLAN/VLC/vlc.exe"`
- Built-in apps: `"RUN|notepad"`
- Launch URLS: `"RUN|https://warbeats.com"`

Finally you can enter a string of text characters using `TEXT|` prefix. For example:

- Type text: `"TYPE|yourname@youremail.com"`

> [!IMPORTANT]
> When specifying file paths, it is recommended to use forward slashes (`/`) instead of backslashes, even on Windows. This helps prevent issues with path parsing and ensures compatibility.

## Troubleshooting

- If no MIDI devices are detected, ensure your controller is properly connected. Delete the `midi_config.json` file to reconfigure the device to use.
- If a specific pad doesn't trigger, check the MIDI Control ID# in `macros_config.json`
- For color issues, verify your color values are in the correct format

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
