# MIDI_to_CSCP
# Provides convert_message() function to convert a mido midi message to a CSCP_encode Message object
# using dict from json control mapping file.
# Copyright Peter Walker 2020.
# Feedback/Requests - peter.allan.walker@gmail.com

# See Readme.txt for info on how to use this app.
# See Project_Notes.txt for info on the implementation - how the app works.


import CSCP_encode
import CSCP_MIDI_settings as config


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


def convert_message(message, mapping, channel_mapping=None):
    """
    :param message: MIDI message from mido
    :param mapping: dict loaded from json control mapping file
    :returns CSCP_encode message object
    """
    # TODO - figure out how to structure json mapping file to allow fewer conditionals in the following
    # (not too bad at the moment, but as I add more controls and different mappings/modes it will get cumbersome
    # TODO - passing the control mapping dict for each message feels inefficient
    if message.type == "pitchwheel":
        config.debug_log("[MIDI->CSCP] Pitchwheel channel {} received; channel mapping: {}".format(message.channel, channel_mapping))
        try:
            command = mapping["control_map"]["pitchwheel"]["command"]
            if channel_mapping is None:
                strip = mapping["control_map"]["pitchwheel"]["ch_to_strip"][str(message.channel)]
            else:
                strip = channel_mapping[message.channel] - 1
            value = _adjust_scale(message.pitch)
        except (IndexError, KeyError, TypeError) as error:
            config.debug_log("[MIDI->CSCP] Pitchwheel mapping failed for channel {}: {}".format(message.channel, error))
            return False

        mapped_strip = strip + 1 if channel_mapping is not None else strip
        config.debug_log("[MIDI->CSCP] Pitchwheel channel {} mapped to mixer strip {} (CSCP strip {}); command={}, value={}.".format(message.channel, mapped_strip, strip, command, value))
        try:
            cscp_message = CSCP_encode.Message(command, strip, value)
        except Exception as error:
            config.debug_log("[MIDI->CSCP] Failed to encode fader event for mixer strip {}: {}".format(mapped_strip, error))
            return False
        config.debug_log("[MIDI->CSCP] CSCP message created: operation={}, strip={}, value={}, bytes={}.".format(command, strip, value, cscp_message.encoded.hex(" ")))
        return cscp_message

    elif message.type == "note_on":
        config.debug_log("[MIDI->CSCP] Note {} velocity {} received; channel mapping: {}".format(message.note, message.velocity, channel_mapping))
        try:
            note_mapping = mapping["control_map"]["note_on"][str(message.note)]
            command = note_mapping["command"]
            local_strip = note_mapping["strip"]
        except (KeyError, TypeError) as error:
            config.debug_log("[MIDI->CSCP] Note {} is not configured in the control map: {}".format(message.note, error))
            return False

        strip = local_strip
        if channel_mapping is not None:
            try:
                strip = channel_mapping[local_strip] - 1
            except (IndexError, TypeError) as error:
                config.debug_log("[MIDI->CSCP] Note {} maps to local slot {}, but that slot is missing from channel mapping {}: {}".format(message.note, local_strip, channel_mapping, error))
                return False

        try:
            value = note_mapping["velocity"][str(message.velocity)]
        except (KeyError, TypeError) as error:
            config.debug_log("[MIDI->CSCP] Note {} has no configured value for velocity {}: {}".format(message.note, message.velocity, error))
            return False

        # TODO - need to figure out how to handle actual state to allow toggle of function!
        mapped_strip = strip + 1 if channel_mapping is not None else strip
        config.debug_log("[MIDI->CSCP] Note {} local slot {} mapped to mixer strip {} (CSCP strip {}, command={}, value={}).".format(message.note, local_strip, mapped_strip, strip, command, value))
        try:
            cscp_message = CSCP_encode.Message(command, strip, value)
        except Exception as error:
            config.debug_log("[MIDI->CSCP] Failed to encode note event for mixer strip {}: {}".format(mapped_strip, error))
            return False
        config.debug_log("[MIDI->CSCP] CSCP message created: operation={}, strip={}, value={}, bytes={}.".format(command, strip, value, cscp_message.encoded.hex(" ")))
        return cscp_message

    config.debug_log("[MIDI->CSCP] Ignored unsupported MIDI message type '{}': {}".format(message.type, message))


if __name__ == '__main__':
    # Load the chosen control mapping json file
    import json
    with open("korg_sonar_reaper.json", "r") as control_map:
        control_map = json.load(control_map)
        #print(control_map)

