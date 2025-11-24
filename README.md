# Fire MIDI Macro Runner

A Python utility for mapping the Akai FL Studio Fire MIDI controller to keyboard shortcuts. This allows you to create a custom macro pad with colorful RGB buttons.

With minimal code changes you can use this for any MIDI device. Non-Fire devices will not have color capabilities without custom programming.

## Overview

"fire_midi_macro_runner" connects to your Akai FL Studio Fire MIDI controller and allows you to trigger keyboard shortcuts by pressing pads on the controller. Each pad can be configured with:
- A specific keyboard shortcut (e.g., `F3`, `Ctrl+S`, `Alt+Tab`)
- Start a process (e.g. open a program or web site)
- Type a text string.
- A custom RGB color for visual recognition
- Ability to load different macro sets

This is particularly useful for:
- Audio/video editing workflows
- Productivity enhancements
- Application shortcuts
- Gaming macros

> [!IMPORTANT]
> When this app is running the MIDI device will not be usable in FL Studio or other apps. Remember to exit this app before starting your DAW.

## Requirements

- Python 3.12 or greater
- An AKAI Fire MIDI controller
- Required Python packages:
  - `mido`
  - `keyboard`
  - `python-rtmidi`
  - `playsound3`

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
4. Run `python fire_midi_macro_runner.py`

## Configuration

### MIDI Device Selection

The first time you run the application, it will prompt you to select your MIDI device from a list of available devices. This selection is saved in `midi_config.json` for future use. Delete this file to be prompted again.

If you do not select an Akai Fire, you should replace the `import fire_code as fc` line to `import gen_code as fc` inside fire_midi_macro_runner.py and remove the existing defined actions from `macros_config.json` and build your own based off the MIDI controller IDs from your device.

### Configuration Files

The application supports multiple configuration files:

- `default_macros.json`: This is the primary configuration file. When you run the application for the first time using `start_windows.bat`, it will automatically create this file by copying `macros_config.json` if it doesn't already exist. This file willnot be overwritten by updates.

- `macros_config.json`: This is the fallback configuration that's included with the application. This file may be overwritten by updates.

- `gaming_macros.json`: This is another sample for demo purposes. It may be overwritten by future updates.

- Custom config files (e.g., `gaming_macros.json`): You can create additional configuration files for different uses and switch between them using the CONFIG action (see below).

### Macro Configuration

Edit `macros_config.json` to customize your pad mappings. Sample:

```json
{
  "default_color": "0xFFFFFF",  // Default color for all pads (white)
  "control_macros": {

    "44": { "action": "CONFIG|macros_config.json", "color": "0x03" },   // load a macro set
    "45": { "action": "CONFIG|gaming_macros.json", "color": "0x02" },   // load a macro set
    
    "56": { "action": "f3", "color": "0xFF0000" },  // Red pad that sends F3 key
    "57": "ctrl+s",                                 // Default color pad that sends Ctrl+S
    "60": "alt+tab"                                 // Default color pad that sends Alt+Tab

    "70": { "action": "RUN|C:/Program Files/VideoLAN/VLC/vlc.exe", "color": "0x00FFFF" },  // Launch VLC media player
    "71": { "action": "RUN|notepad", "color": "0xFF00FF" },                                // Open Notepad
    "72": { "action": "RUN|https://warbeats.com", "color": "0x00FF00" },                   // Open URL in browser

    "109": { "action": "SOUND|./sounds/air_horn.wav", "color": "0xFF0000" },               // play a sound

    "105": { "action": "TYPE|you@youremail.com", "color": "0xFFFF00" }                     // type a text string
  }
}
```

#### Configuration Format

- `default_color`: Sets the default color for all pads with a defined macro (hex format)
- `control_macros`: Maps MIDI Control ID#s to keyboard shortcuts
  - Simple format: `"MIDI Control ID#": "key_combination"`
  - Extended format: `"MIDI Control ID#": { "action": "key_combination", "color": "hex_color" }`

#### Action Types

The `action` field supports several types of commands:

- **Keyboard shortcuts**: `"f1"`, `"ctrl+s"`, `"alt+tab"`
- **Running programs**: Use `"RUN|"` prefix, e.g., `"RUN|notepad"` or `"RUN|https://warbeats.com"`
- **Typing text**: Use `"TYPE|"` prefix, e.g., `"TYPE|you@youremail.com"`
- **Playing sounds**: Use `"SOUND|"` prefix, e.g., `"SOUND|./sounds/air_horn.wav"`
- **Loading configurations**: Use `"CONFIG|"` prefix, e.g., `"CONFIG|gaming_macros.json"` to load a different configuration file on-the-fly

#### Color Formats

RGB Colors can be specified in any of these formats:
- Hexadecimal: `"0xFF0000"` or `"#FF0000"` (red)
- Integer: `16711680` (equivalent to 0xFF0000)

> [!NOTE]
> RGB colors are used for the Akai Fire Pads ONLY which start at MIDI Control ID#54 (top left pad) and end at MIDI Control ID#117 (bottom right pad). Any color definition for controls outside this range use the table below

##### Non RGB Pad Color Support
| ID | Fire Label | Supported Colors |
| :--| :--------  | :--------------- |
| 31 | PATTERN UP   | 0x00=Off, 0x01=Dim Red, 0x02=Red |
| 32 | PATTERN DOWN | 0x00=Off, 0x01=Dim Red, 0x02=Red |
| 33 | BROWSER      | 0x00=Off, 0x01=Dim Red, 0x02=Red |
| 34 | GRID LEFT    | 0x00=Off, 0x01=Dim Red, 0x02=Red |
| 35 | GRID RIGHT   | 0x00=Off, 0x01=Dim Red, 0x02=Red |
| 36 | MUTE 1       | 0x00=Off, 0x01=Dim Green, 0x02=Green |
| 37 | MUTE 2       | 0x00=Off, 0x01=Dim Green, 0x02=Green |
| 38 | MUTE 3       | 0x00=Off, 0x01=Dim Green, 0x02=Green |
| 39 | MUTE 4       | 0x00=Off, 0x01=Dim Green, 0x02=Green |
| 44 | STEP         | 0x00=Off, 0x01=Dim Red, 0x02=Dim Yellow, 0x03=Red, 0x04=Yellow |
| 45 | NOTE         | 0x00=Off, 0x01=Dim Red, 0x02=Dim Yellow, 0x03=Red, 0x04=Yellow |
| 46 | DRUM         | 0x00=Off, 0x01=Dim Red, 0x02=Dim Yellow, 0x03=Red, 0x04=Yellow |
| 47 | PERFORM      | 0x00=Off, 0x01=Dim Red, 0x02=Dim Yellow, 0x03=Red, 0x04=Yellow |
| 48 | SHIFT        | 0x00=Off, 0x01=Dim Red, 0x02=Dim Yellow, 0x03=Red, 0x04=Yellow |
| 49 | ALT          | 0x00=Off, 0x01=Dim Yellow, 0x02=Yellow |
| 50 | PATT/SONG    | 0x00=Off, 0x01=Dim Green, 0x02=Dim Yellow, 0x03=Green, 0x04=Yellow |
| 51 | PLAY         | 0x00=Off, 0x01=Dim Green, 0x02=Dim Yellow, 0x03=Green, 0x04=Yellow |
| 52 | STOP         | 0x00=Off, 0x01=Dim Yellow, 0x02=Bright Yellow |
| 53 | RECORD       | 0x00=Off, 0x01=Dim Red, 0x02=Dim Yellow, 0x03=Red, 0x04=Yellow |

##### Unsupported LEDS

The knob mode LEDs (CHANNEL, MIXER, USER 1, USER 2) are not supported at this time.


## Usage

1. Run the application:

Windows (Easy):
```
start_windows.bat
```

Manual:
```
python fire_midi_macro_runner.py
```

2. If this is your first time running it, you'll be prompted to select your MIDI device. A `midi_config.json` will be created. Delete this file if you want to reset the device.
3. Press pads/buttons on your controller to trigger the configured keyboard shortcuts
4. A message will appear in the console showing the MIDI Control ID that was pressed so you can easily know what MIDI Control ID is available to use. If the control is already defined, it will show you the defined action otherwise it will say `* UNUSED *` 
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

You can also specify playback of a sound (MP3 or WAV files only) using the `SOUND|` prefix followed by the file path to the sound. For example:

- Sound playback: `"SOUND|./sounds/air_horn.wav"`

> [!IMPORTANT]
> When specifying file paths, it is recommended to use forward slashes (`/`) instead of backslashes, even on Windows. This helps prevent issues with path parsing and ensures compatibility.

You can enter a string of text characters using `TEXT|` prefix. For example:

- Type text: `"TYPE|yourname@youremail.com"`

Finally you can specify a pad to load another config file. This would be useful if you wanted one layout for general use and another specific layout for an application or purpose. To make a button load another set of macros use the `CONFIG|` prefix. For example:

- Load a config: `""CONFIG|gaming_macros.json""` 

## Troubleshooting

- If no MIDI devices are detected, ensure your controller is properly connected. Delete the `midi_config.json` file to reconfigure the device to use.
- If a specific pad doesn't trigger, check the MIDI Control ID# in `macros_config.json`
- For color issues, verify your color values are in the correct format

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
