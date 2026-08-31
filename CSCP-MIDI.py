# CSCP-MIDI
# Provides two-way connection and communications between CSCP and MIDI devices.
# Copyright Peter Walker 2020.
# Feedback/Requests - peter.allan.walker@gmail.com

# See Readme.txt for info on how to use this app.
# See Project_Notes.txt for info on the implementation - how the app works.

import json

# My local files
import CSCP_MIDI_settings as config
import MIDI_connection
import CSCP_connection
import MIDI_to_CSCP
import CSCP_to_MIDI

# mido uses rtmidi backend
# For some reason I have to ensure I have rtmidi installed in order for mido to work
#    'pip install python-rtmidi'
# Then it will work fine as a python script, but when run as an exe built by pyinstaller, it will fail when it
# attempts midi comms.
# The following import fixes this, this import is included purely for pyinstaller to build a functioning exe...
import mido.backends.rtmidi  # DO NOT DELETE THIS EVEN THOUGH PYCHARM THINKS IT IS NOT REQUIRED


def main():
    print("\n", 27 * "-", "\n", 8 * " ", "CSCP-MIDI\n", 27 * "-")  # Formatted title/heading

    print('\nMIDI Outputs:')
    print(*mido.get_output_names(), sep='\n')
    print('\nMIDI Inputs:')
    print(*mido.get_input_names(), sep='\n')
    print() 

    # Load config settings with user confirm/edit
    settings = config.get_settings()

    # Load the chosen control mapping json file
    try:
        with open(settings["Mode/Mapping"][1], "r") as control_map:
            control_map = json.load(control_map)
    except FileNotFoundError:
        print("'{}' file not found!".format(settings["Mode/Mapping"][1]))
        return False
    except json.decoder.JSONDecodeError:
        print("'{}' file is invalid!".format(settings["Mode/Mapping"][1]))
        return False
    except TypeError:
        print("** Need to select a control mode/mapping file! **")
        return False

    # Open MIDI ports and start thread receiving incoming MIDI messages
    midi_list = [
        MIDI_connection.Connection(settings["MIDI Devices"][0]["MIDI -> CSCP port"], settings["MIDI Devices"][0]["CSCP -> MIDI port"]),
        MIDI_connection.Connection(settings["MIDI Devices"][1]["MIDI -> CSCP port"], settings["MIDI Devices"][1]["CSCP -> MIDI port"])
    ]

    # Open CSCP connection and start thread receiving incoming CSCP messages
    cscp = CSCP_connection.Connection(settings["Mixer IP Address"], settings["Mixer CSCP Port"])

    # Store current settings for next start up
    config.save_settings(settings)

    while True:
        # Get the oldest received MIDI message if there are any and send it to the CSCP device
        for i,midi in enumerate(midi_list):
            midi_in = midi.get_message()
            if midi_in:
                #print(20*"-", "\nMIDI RECEIVED: {} [MIDI messages remaining in connection buffer:{}"
                #      .format(midi_in, len(midi.messages)))
                midi_in.channel = midi_in.channel +  settings["MIDI Devices"][i]["Channel Offset"]
                print('MIDI IN')
                # Convert MIDI to CSCP Message object
                cscp_message = MIDI_to_CSCP.convert_message(midi_in, control_map)
                
                if cscp_message:
                    print('CSCP')
                    print(20*"-", "\nMIDI RECEIVED", midi_in)
                    print("converted to CSCP Message object:", cscp_message)

                if cscp_message and cscp.status == "Connected":
                    # Send CSCP message bytes to mixer
                    # print("DEBUG MAIN", cscp_message)
                    cscp.send(cscp_message.encoded)

        # Get the oldest received CSCP message if there are any and send it to the MIDI device
        # cscp_in = cscp.get_message()
        cscp_in = None
        if cscp_in:
            print(20 * "-", "\nCSCP RECEIVED:", cscp_in, ". CSCP messages remaining in connection buffer:",
                  len(cscp.messages))
            midi_msg = CSCP_to_MIDI.convert_message(cscp_in, control_map)
            print("Translated to MIDI:", midi_msg)
            if midi_msg:
                midi.send_message(midi_msg)


if __name__ == '__main__':
    main()
