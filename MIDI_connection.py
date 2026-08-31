# MIDI_connection
# Used by the CSCP-MIDI application.
# Handles MIDI input and output using the mido library
# Runs a thread receiving MIDI messages
# Provides public methods to send messages and to get received messages
# Copyright Peter Walker 2020.
# Feedback - peter.allan.walker@gmail.com

import mido
import threading


class Connection:

    def __init__(self, midi_input, midi_output):
        self.input = midi_input
        self.output = midi_output
        self.messages = []

        self.receiver = threading.Thread(target=self._run)  # target is the method called when thread starts
        self.receiver.daemon = True  # Important - without this, cannot kill with control+c
        self.receiver.start()  # calls target - self.run()

        self.transmitter = mido.open_output(self.output)

    def _run(self):
        """
        Start listening for messages on the MIDI input
        """
        with mido.open_input(self.input) as input_port:
            print("{} - MIDI input port is listening for control messages".format(input_port))
            # Handle incoming MIDI messages
            for msg in input_port:
                print("MIDI input message received: ", msg)
                self.messages.append(msg)

    # The following are intended to be externally accessed/public methods
    def get_message(self):
        """
        Returns and removes first message from self.messages
        :return:
        """
        r = False
        if self.messages:
            r = self.messages[0]
            self.messages = self.messages[1:]
        return r

    def send_message(self, msg):
        # print("DEBUG CSCP SEND", msg)
        self.transmitter.send(msg)


# TODO - Check the following
#  - Am I actually calling it and if so is it doing the right things?
# ... in cscp_connection, close is a method of the class! (not sure either are correct)
def close(self):
    self.input.close()
    self.output.close()
    self.receiver.stop()
    self.transmitter.close()
    # print(self.receiver.getName())


if __name__ == '__main__':

    print(20*'#'+' MIDI_connection ' + 20*'#')

    # Check what MIDI inputs are available
    inputs = mido.get_input_names()
    print('\nMIDI inputs available:')
    for i, source in enumerate(inputs):
        print('\t', source[:-2], '\t:', i)

    chosen_input = int(input("Select MIDI input: "))

    outputs = mido.get_output_names()
    print('\nMIDI outputs available:')
    for i, source in enumerate(outputs):
        print('\t', source[:-2], '\t:', i)

    chosen_output = int(input("Select MIDI output: "))
    midi_connection = Connection(inputs[chosen_input], outputs[chosen_output])

    # params for outgoing test message:
    strip = 1
    value = -8000

    count = 0
    button_strip = 8
    button_state = True

    midi_msg = mido.Message('note_on', channel=0, note=0, velocity=127)
    midi_connection.send_message(midi_msg)

    """
    while True:
        # Check for received midi message
        message = midi_connection.get_message()
        #if message and message.type != "control_change":
        if message:
            #print("RECEIVED", message, ", messages remaining: ", len(midi_connection.messages))
            pass
        
        
        if count % 100 == 0:
            # Send test fader move message
            midi_msg = mido.Message('pitchwheel', channel=0, pitch=value)
            # print("SENDING", midi_msg)
            midi_connection.send_message(midi_msg)
            value += 1
            if value > 8000:
                value = -8000
        
        
        # Send test button press messages - toggle button on and off:
        if count % 10000 == 0:
            if button_state:
                button_value = 127
                button_state = False
            else:
                button_value = 0
                button_state = True

            midi_msg = mido.Message('note_on', channel=0, note=button_strip, velocity=button_value)
            midi_connection.send_message(midi_msg)

        count += 1
    """