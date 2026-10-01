# CSCP_MIDI_settings
# Used by the CSCP-MIDI application.
# Handles loading and saving of connection configuration settings to/from json file
# Gets user confirmation and allows user to edit the settings.
# Copyright Peter Walker 2020.
# Feedback - peter.allan.walker@gmail.com

# See Readme.txt for info on how to use this app.
# See Project_Notes.txt for info on the implementation - how the app works.

import json
import mido  # MIDI library (used to get the available MIDI ports)

CONFIG_FILE = "settings.json"
MODES = (("CC", "korg_default_cc.json"),
         ("Sonar/Reaper", "korg_sonar_reaper.json"))
DEBUG_LOGGING = False


def set_debug_logging(enabled):
    global DEBUG_LOGGING
    DEBUG_LOGGING = bool(enabled)


def debug_log(message):
    if DEBUG_LOGGING:
        print(message, flush=True)


# THESE FIRST FUNCTIONS ARE INTENDED FOR PRIVATE USE,
# THEY ARE CALLED BY THE PUBLIC FUNCTIONS FURTHER BELOW
def _yes_or_no(string, enter=False, edit=False):
    """
    For parsing cmd line input from user - yes/no prompts
    if string is 'y' or 'yes', case-insensitive, returns 'y'
    if string is 'n' or 'no', case-insensitive, returns 'n'
    else, returns False
    :param string: typically, user input('y/n?')
    :param enter: optional, if enter=True, when string is empty (Enter key alone), returns 'y'
    :param edit: optional, if edit=True, when string is 'e'/'E', return 'n'
    :return: 'y' for affirmative response/acceptance, 'n' for negative response or edit, False for invalid response
    """
    string = string.lower().strip()

    if string in ("y", "yes") or (string == "" and enter):
        return "y"
    elif string in ("n", "no") or (string == "e" and edit):
        return "n"
    else:
        return False


def _validate_ip_address(address):
    """
    Checks if input is a valid IPv4 address
    :param address: string
    :return: True if valid IPv4 address, else False
    """
    address = address.split(".")

    if len(address) != 4:
        return False

    for segment in address:
        try:
            segment = int(segment)
        except ValueError:
            return False

        if segment not in range(255):
            return False

    return True


def _load_settings():
    """
    Check if configuration file exists
    :return: Dict of settings (returns defaults if none saved)
    """
    try:
        with open(CONFIG_FILE, "r") as config:
            r = json.load(config)

    except FileNotFoundError:
        print("'{}' file not found. Enter a few details to get started...".format(CONFIG_FILE))
        r = False

    except json.decoder.JSONDecodeError:
        print("'{}' file is invalid. Enter a few details to get started...".format(CONFIG_FILE))
        r = False

    if not r:
        r = {"Mixer Name": "Unknown",
             "Mixer IP Address": None,
             "Mixer CSCP Port": None,
             "CSCP -> MIDI port": None,
             "MIDI -> CSCP port": None,
             "Mode/Mapping": None}
    return r


def _ask_ip_address():
    """
    Asks user to input an IP address
    Checks input is a valid IP address, keeps asking until it is
    :return: string - user inputted IP address
    """
    valid = False
    while not valid:
        ip_address = input("Enter mixer's IP address: ")
        if _validate_ip_address(ip_address):
            return ip_address


def _ask_port():
    """
    Asks user for a TCP port value,
    Keeps asking until they input a number in range 0 - 65,000
    :return:
    """
    valid = False
    while not valid:
        port = input("Enter mixer's CSCP port: ")
        try:
            port = int(port)
            if port in range(65000):
                return port
        except ValueError:
            pass


def _confirm_settings(config):
    """
    Ask user if they want to keep the last used settings or enter new ones
    :return: Dict of user confirmed settings
    """
    use_settings = False

    # Present last used settings and ask to confirm or update
    while not use_settings:
        print("  Current Connection Settings...")
        for heading in config:
            print("\t", heading, ":", config[heading])

        use_settings = _yes_or_no(input("\nUse these settings? (y/n): "), enter=True)

    if use_settings == "n":
        # User does not want to keep last used settings, so get their input for new settings
        config["Mixer IP Address"] = _ask_ip_address()
        config["Mixer CSCP Port"] = _ask_port()

        # Select midi connection from this app's output to midi device's input
        available_midi_outputs = mido.get_output_names()
        selected_port = -1
        while selected_port not in range(len(available_midi_outputs)):
            print(27*"-", "\nAvailable MIDI ports for output to DAW/controller:")
            for i, port in enumerate(available_midi_outputs):
                print("{} : {}".format(port[:-1], i))
            try:
                selected_port = int(input("\nSelect DAW/Controller MIDI input port: "))
            except ValueError:
                pass
        config["CSCP -> MIDI port"] = available_midi_outputs[selected_port]

        # Select midi connection from midi device's output to this app's input
        available_midi_inputs = mido.get_input_names()
        selected_port = -1
        while selected_port not in range(len(available_midi_inputs)):
            print(27*"-", "\nAvailable MIDI ports for input from DAW/controller:")
            for i, port in enumerate(available_midi_inputs):
                print("{} : {}".format(port[:-1], i))
            try:
                selected_port = int(input("\nSelect DAW/Controller MIDI output port: "))
            except ValueError:
                pass
        config["MIDI -> CSCP port"] = available_midi_inputs[selected_port]

        # Select mode / mapping file
        selected_mode = -1
        while selected_mode not in range(len(MODES)):
            print("\nAvailable modes:")
            for i, mode in enumerate(MODES):
                print("{} ({}) : {}".format(mode[0], mode[1], i))

            try:
                selected_mode = int(input("\nSelect MIDI mode: "))
            except ValueError:
                pass

        config["Mode/Mapping"] = MODES[selected_mode]

    return config


# THE FOLLOWING FUNCTIONS ARE INTENDED AS PUBLIC / TO BE CALLED FROM OTHER APPLICATION
def get_settings():
    """
    Loads CSCP-MIDI settings & gets user to confirm or edit
    :return: dict of user confirmed settings
    """
    r = _load_settings()
    r = _confirm_settings(r)
    return r


def save_settings(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)


def get_mixer(settings):
    """Return the selected mixer profile from settings."""
    for mixer in settings.get("Mixers", []):
        if mixer.get("Name") == settings.get("Mixer Name"):
            return mixer
    raise ValueError("Selected mixer profile was not found.")


if __name__ == '__main__':
    print("\n", 23 * "-", "\n   CSCP-MIDI Settings   \n", 23 * "-")
    settings = get_settings()
    save_settings(settings)

    for setting in settings:
        print(setting, ":", settings[setting])
