# Converts CSCP_decode message object and converts to mido MIDI message object ready to send

import mido

# TODO - fix fader jitter - noticed MIDI returns value-1 everytime?
# - check this hypothesis, there could be a simple fix


def adjust_scale(value):
    # Convert CSCP fader value to MIDI pitchwheel value in range -8192 to 8192
    # take a "pitch" value in range -8192 to +8192 and convert to a CSCP fader level
    # TODO - Handle Alt MIDI mode - CC values 0-127
    midi_min = -8192
    midi_max = 8191

    cscp_min = 0  # TODO - Check if this OK with PFL over-press,
    # mixer will probably open Reaper's level control a bit
    cscp_max = 1024  # TODO - Check this

    midi_range = midi_max - midi_min
    cscp_range = cscp_max - cscp_min

    scale_factor = midi_range / cscp_range
    level = int(scale_factor * value)
    level = level + midi_min  # Offset to handle negative min values

    return level


def convert_message(msg, mapping):
    # message = CSCP_decode.Message(message)
    print(msg)
    if msg.operation == "fader_move":
        mtype = "pitchwheel"
        try:
            strip = mapping["CSCP to MIDI"]["strip_to_ch"][str(msg.strip)]
        except KeyError:
            return False
        value = adjust_scale(msg.value)
        midi = mido.Message(mtype, channel=strip, pitch=value)
        return midi

    if msg.operation == "pfl_toggle":
        mtype = "note_on"
        try:
            note = mapping["CSCP to MIDI"]["pfl_strip_to_note"][str(msg.strip)]
        except KeyError:
            return False
        # TODO - handle two-way toggling of controls properly!
        # Reaper in current mod only allows toggle with velocity of 127
        #   it is ignoring velocity of 0, cannot explicitlu set on or off, just toggle
        """
        if msg.value:
            velocity = 127
        else:
            velocity = 0
        """
        velocity = 127
        midi = mido.Message(mtype, note=note, velocity=velocity)
        return midi

    if msg.operation == "cut_toggle":
        mtype = "note_on"
        try:
            note = mapping["CSCP to MIDI"]["cut_strip_to_note"][str(msg.strip)]
        except KeyError:
            return False
        # CSCP's Cut state logic is reversed, true/1 = uncut/passing audio, false/0 = cut

        # Reaper in this mode only seems to accept velocity of 127 and that toggles rather than sets on
        # So this rough hack will attempt to bodge a fix - TODO - properly design this functionality
        """
        if msg.value:
            velocity = 0
        else:
            velocity = 127
        """
        velocity = 127
        midi = mido.Message(mtype, note=note, velocity=velocity)
        return midi

    return False


if __name__ == '__main__':

    # Load the chosen control mapping json file
    import json

    with open("korg_sonar_reaper.json", "r") as control_map:
        control_map = json.load(control_map)
        # print(control_map)

    import CSCP_encode
    test_messages = (CSCP_encode.Message("fader_move", strip=0, value=0),
                     CSCP_encode.Message("fader_move", strip=0, value=1024),
                     CSCP_encode.Message("fader_move", strip=0, value=744),
                     CSCP_encode.Message("cut_toggle", strip=0, value=0))

    for message in test_messages:
        print(convert_message(message, control_map))
