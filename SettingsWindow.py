import json
import tkinter as tk
from tkinter import messagebox, ttk

import mido

import CSCP_MIDI_settings as config


class SettingsWindow:
    def __init__(self, controller, on_close):
        self.controller = controller
        self.on_close = on_close
        self.closed = False
        self.settings = self._load_settings()
        self.window = tk.Tk()
        self.window.title("CSCP-MIDI Settings")
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self._build_ui()
        self.refresh_midi_ports()
        self._set_fields(self.settings)
        self._apply_settings(show_error=False)

    def _load_settings(self):
        try:
            with open(config.CONFIG_FILE, "r") as settings_file:
                settings = json.load(settings_file)
        except (FileNotFoundError, json.JSONDecodeError):
            settings = {}
        settings.setdefault("Mixer Name", "Unknown")
        settings.setdefault("Mixer IP Address", "")
        settings.setdefault("Mixer CSCP Port", 49202)
        settings.setdefault("Mode/Mapping", ["Sonar/Reaper", "korg_sonar_reaper.json"])
        devices = settings.setdefault("MIDI Devices", [])
        while len(devices) < 2:
            devices.append({"CSCP -> MIDI port": "", "MIDI -> CSCP port": "", "Channel Offset": 0})
        return settings

    def _build_ui(self):
        content = ttk.Frame(self.window, padding=12)
        content.grid(sticky="nsew")
        self.window.columnconfigure(0, weight=1)
        mixer_group = ttk.LabelFrame(content, text="Mixer", padding=8)
        mixer_group.grid(row=0, column=0, sticky="ew")
        ttk.Label(mixer_group, text="IP address").grid(row=0, column=0, sticky="w")
        self.mixer_ip = ttk.Entry(mixer_group, width=32)
        self.mixer_ip.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ttk.Label(mixer_group, text="CSCP port").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.mixer_port = tk.Spinbox(mixer_group, from_=1, to=65535, width=10)
        self.mixer_port.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(6, 0))
        mixer_group.columnconfigure(1, weight=1)

        self.device_fields = []
        devices_layout = ttk.Frame(content)
        devices_layout.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        for index in range(2):
            group = ttk.LabelFrame(devices_layout, text="MIDI Device {}".format(index + 1), padding=8)
            group.grid(row=0, column=index, sticky="nsew", padx=(0, 8) if index == 0 else (0, 0))
            ttk.Label(group, text="CSCP to MIDI").grid(row=0, column=0, sticky="w")
            output_port = ttk.Combobox(group, state="readonly", width=30)
            output_port.grid(row=1, column=0, sticky="ew", pady=(2, 6))
            ttk.Label(group, text="MIDI to CSCP").grid(row=2, column=0, sticky="w")
            input_port = ttk.Combobox(group, state="readonly", width=30)
            input_port.grid(row=3, column=0, sticky="ew", pady=(2, 6))
            ttk.Label(group, text="Channel offset").grid(row=4, column=0, sticky="w")
            offset = tk.Spinbox(group, from_=0, to=15, width=5)
            offset.grid(row=5, column=0, sticky="w", pady=(2, 0))
            self.device_fields.append((output_port, input_port, offset))
            devices_layout.columnconfigure(index, weight=1)

        buttons = ttk.Frame(content)
        buttons.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        ttk.Button(buttons, text="Refresh MIDI Devices", command=self.refresh_midi_ports).grid(row=0, column=0, sticky="w")
        ttk.Button(buttons, text="Apply", command=self._apply_settings).grid(row=0, column=1, sticky="e")
        buttons.columnconfigure(1, weight=1)
        self.status = ttk.Label(content)
        self.status.grid(row=3, column=0, sticky="w", pady=(8, 0))

    def refresh_midi_ports(self):
        outputs = mido.get_output_names()
        inputs = mido.get_input_names()
        for output_port, input_port, _ in self.device_fields:
            output_value = output_port.get()
            input_value = input_port.get()
            output_port["values"] = outputs
            input_port["values"] = inputs
            if output_value:
                output_port.set(output_value)
            if input_value:
                input_port.set(input_value)

    def _set_fields(self, settings):
        self.mixer_ip.insert(0, settings["Mixer IP Address"])
        self.mixer_port.delete(0, tk.END)
        self.mixer_port.insert(0, settings["Mixer CSCP Port"])
        for device, fields in zip(settings["MIDI Devices"], self.device_fields):
            output_port, input_port, offset = fields
            output_port.set(device["CSCP -> MIDI port"])
            input_port.set(device["MIDI -> CSCP port"])
            offset.delete(0, tk.END)
            offset.insert(0, device["Channel Offset"])

    def _collect_settings(self):
        settings = dict(self.settings)
        settings["Mixer IP Address"] = self.mixer_ip.get().strip()
        settings["Mixer CSCP Port"] = int(self.mixer_port.get())
        settings["MIDI Devices"] = [
            {"CSCP -> MIDI port": output_port.get(), "MIDI -> CSCP port": input_port.get(), "Channel Offset": int(offset.get())}
            for output_port, input_port, offset in self.device_fields
        ]
        return settings

    def _apply_settings(self, show_error=True):
        try:
            settings = self._collect_settings()
        except ValueError:
            self.status.config(text="CSCP port and channel offsets must be whole numbers.")
            return
        if not settings["Mixer IP Address"] or any(not device["CSCP -> MIDI port"] or not device["MIDI -> CSCP port"] for device in settings["MIDI Devices"]):
            self.status.config(text="Select a mixer IP address and all MIDI ports before applying.")
            return
        try:
            self.controller.start(settings)
        except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError) as error:
            self.status.config(text="Unable to apply settings: {}".format(error))
            if show_error:
                messagebox.showwarning("CSCP-MIDI", self.status.cget("text"))
            return
        config.save_settings(settings)
        self.settings = settings
        print("[APP] Settings saved and connections restarted")
        self.status.config(text="Settings applied. Connections restarted.")

    def close(self):
        self.closed = True
        self.on_close()
        self.window.destroy()

    def run(self):
        self.window.mainloop()