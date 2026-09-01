# MIDI_to_CSCP
# Provides convert_message() function to convert a mido midi message to a CSCP_encode Message object
# using dict from json control mapping file.
# Copyright Peter Walker 2020.
# Feedback/Requests - peter.allan.walker@gmail.com

# See Readme.txt for info on how to use this app.
# See Project_Notes.txt for info on the implementation - how the app works.


import CSCP_encode


def _adjust_scale(level):
    # take a "pitch" value in range -8192 to +8192 and convert to a CSCP fader level
    # TODO - Handle Alt MIDI mode - CC values 0-127
    midi_min = -8192
    midi_max = 8192
    cscp_min = 0  # TODO - Check if this OK with PFL over-press
    cscp_max = 1024  # TODO - Check this

    midi_range = midi_max - midi_min
    cscp_range = cscp_max - cscp_min

    scale_factor = cscp_range / midi_range

    level = level - midi_min  # Offset to handle negative min values
    converted_level = int(scale_factor * level)
    #print("DEBUG:", converted_level)
    return converted_level


def convert_message(message, mapping):
    """
    :param message: MIDI message from mido
    :param mapping: dict loaded from json control mapping file
    :returns CSCP_encode message object
    """
    # TODO - figure out how to structure json mapping file to allow fewer conditionals in the following
    # (not too bad at the moment, but as I add more controls and different mappings/modes it will get cumbersome
    # TODO - passing the control mapping dict for each message feels inefficient
    if message.type == "pitchwheel":
        try:
            command = mapping["control_map"]["pitchwheel"]["command"]
            strip = mapping["control_map"]["pitchwheel"]["ch_to_strip"][str(message.channel)]
            # strip = str(message.channel)
            value = _adjust_scale(message.pitch)
        except KeyError:
            return False

        return CSCP_encode.Message(command, strip, value)

    elif message.type == "note_on":
        try:
            command = mapping["control_map"]["note_on"][str(message.note)]["command"]
            strip = mapping["control_map"]["note_on"][str(message.note)]["strip"]
            value = mapping["control_map"]["note_on"][str(message.note)]["velocity"][str(message.velocity)]
        except KeyError:
            return False

        # TODO - need to figure out how to handle actual state to allow toggle of function!
        return CSCP_encode.Message(command, strip, value)


if __name__ == '__main__':
    # Load the chosen control mapping json file
    import json
    with open("korg_sonar_reaper.json", "r") as control_map:
        control_map = json.load(control_map)
        #print(control_map)

