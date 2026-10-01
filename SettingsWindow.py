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
        self._set_fields(self.settings)
        self.refresh_midi_ports()
        self._apply_settings(show_error=False)

    def _load_settings(self):
        try:
            with open(config.CONFIG_FILE, "r") as settings_file:
                settings = json.load(settings_file)
        except (FileNotFoundError, json.JSONDecodeError):
            settings = {}
        mixers = settings.setdefault("Mixers", [])
        if not mixers and settings.get("Mixer IP Address"):
            mixers.append({
                "Name": settings.get("Mixer Name", "Unknown"),
                "IP Address": settings["Mixer IP Address"],
                "Port": settings.get("Mixer CSCP Port", 49202),
            })
        selected_name = settings.get("Mixer Name")
        if not any(mixer.get("Name") == selected_name for mixer in mixers) and mixers:
            settings["Mixer Name"] = mixers[0].get("Name", "")
        settings.pop("Mixer IP Address", None)
        settings.pop("Mixer CSCP Port", None)
        settings.setdefault("Debug Logging", False)
        settings.setdefault("Mode/Mapping", ["Sonar/Reaper", "korg_sonar_reaper.json"])
        devices = settings.setdefault("MIDI Devices", [])
        mapping_version = settings.get("Channel Mapping Version", 0)
        defaults = ("iCON V1-M (9 Faders)", "iCON V1-X (8 Faders)")
        while len(devices) < 2:
            devices.append({"Name": defaults[len(devices)], "Enabled": True, "CSCP -> MIDI port": "", "MIDI -> CSCP port": "", "Channel Mapping": []})
        for device in devices:
            device.setdefault("Name", "MIDI Device")
            device.setdefault("Enabled", True)
            count = self._fader_count(device)
            if not device.get("Channel Mapping"):
                offset = device.pop("Channel Offset", 0)
                channel_mapping = list(range(offset + 1, offset + count + 1))
            else:
                channel_mapping = [int(strip) for strip in device["Channel Mapping"]]
                if mapping_version < 2:
                    channel_mapping = [strip + 1 for strip in channel_mapping]
            if len(channel_mapping) < count:
                first_new_strip = max(channel_mapping, default=0) + 1
                channel_mapping.extend(range(first_new_strip, first_new_strip + count - len(channel_mapping)))
            device["Channel Mapping"] = channel_mapping
            device.pop("Channel Offset", None)
        settings["Channel Mapping Version"] = 2
        return settings

    @staticmethod
    def _fader_count(device):
        name = device.get("Name", "")
        if "V1-M" in name:
            return 9
        if "V1-X" in name:
            return 8
        return len(device.get("Channel Mapping", [])) or 8

    def _build_ui(self):
        content = ttk.Frame(self.window, padding=12)
        content.grid(sticky="nsew")
        self.window.columnconfigure(0, weight=1)
        mixer_group = ttk.LabelFrame(content, text="Mixer", padding=8)
        mixer_group.grid(row=0, column=0, sticky="ew")
        self.mixer_names = [mixer.get("Name", "") for mixer in self.settings.get("Mixers", [])]
        self.mixer_choice = ttk.Combobox(mixer_group, state="readonly", values=self.mixer_names, width=32)
        self.mixer_choice.grid(row=0, column=0, sticky="ew")
        self.mixer_choice.bind("<<ComboboxSelected>>", self._update_mixer_details)
        self.mixer_details = ttk.Label(mixer_group)
        self.mixer_details.grid(row=1, column=0, sticky="w", pady=(4, 0))
        mixer_group.columnconfigure(0, weight=1)

        self.device_fields = []
        devices_layout = ttk.Frame(content)
        devices_layout.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        for index in range(2):
            device = self.settings["MIDI Devices"][index]
            group = ttk.LabelFrame(devices_layout, text=device["Name"], padding=8)
            group.grid(row=0, column=index, sticky="nsew", padx=(0, 8) if index == 0 else (0, 0))
            enabled = tk.BooleanVar(value=bool(device["Enabled"]))
            ttk.Checkbutton(group, text="Enabled", variable=enabled).grid(row=0, column=0, columnspan=5, sticky="w")
            ttk.Label(group, text="CSCP to MIDI").grid(row=1, column=0, sticky="w")
            output_port = ttk.Combobox(group, state="readonly", width=30)
            output_port.grid(row=2, column=0, columnspan=5, sticky="ew", pady=(2, 6))
            ttk.Label(group, text="MIDI to CSCP").grid(row=3, column=0, sticky="w")
            input_port = ttk.Combobox(group, state="readonly", width=30)
            input_port.grid(row=4, column=0, columnspan=5, sticky="ew", pady=(2, 6))
            ttk.Label(group, text="Fader mapping (mixer strip)").grid(row=5, column=0, columnspan=5, sticky="w")
            mapping_fields = []
            for fader in range(self._fader_count(device)):
                grid_row = 6 + fader // 3
                grid_column = (fader % 3) * 2
                ttk.Label(group, text="F{}".format(fader + 1)).grid(row=grid_row, column=grid_column, sticky="w", padx=(0, 3), pady=(3, 0))
                mapping_entry = ttk.Entry(group, width=7)
                mapping_entry.grid(row=grid_row, column=grid_column + 1, sticky="w", pady=(3, 0))
                mapping_fields.append(mapping_entry)
            self.device_fields.append((enabled, output_port, input_port, mapping_fields))
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
        missing_ports = []
        for device, (_, output_port, input_port, _) in zip(self.settings["MIDI Devices"], self.device_fields):
            output_value = output_port.get()
            input_value = input_port.get()
            output_port["values"] = outputs
            input_port["values"] = inputs
            if output_value not in outputs:
                output_port.set("")
                if output_value:
                    missing_ports.append("{} output '{}'".format(device["Name"], output_value))
            else:
                output_port.set(output_value)
            if input_value not in inputs:
                input_port.set("")
                if input_value:
                    missing_ports.append("{} input '{}'".format(device["Name"], input_value))
            else:
                input_port.set(input_value)
        if missing_ports:
            self.status.config(text="Unavailable MIDI port(s) cleared: {}. Select current ports.".format(", ".join(missing_ports)))

    def _set_fields(self, settings):
        self.mixer_choice.set(settings.get("Mixer Name", ""))
        self._update_mixer_details()
        for device, fields in zip(settings["MIDI Devices"], self.device_fields):
            enabled, output_port, input_port, mapping_fields = fields
            enabled.set(bool(device.get("Enabled", True)))
            output_port.set(device["CSCP -> MIDI port"])
            input_port.set(device["MIDI -> CSCP port"])
            for mapping_entry, strip in zip(mapping_fields, device["Channel Mapping"]):
                mapping_entry.delete(0, tk.END)
                mapping_entry.insert(0, strip)

    def _update_mixer_details(self, _event=None):
        mixer = next((mixer for mixer in self.settings.get("Mixers", []) if mixer.get("Name") == self.mixer_choice.get()), None)
        if mixer:
            self.mixer_details.config(text="{} : {}".format(mixer.get("IP Address", ""), mixer.get("Port", "")))
        else:
            self.mixer_details.config(text="No mixer profiles configured.")

    def _collect_settings(self):
        settings = dict(self.settings)
        settings["Mixer Name"] = self.mixer_choice.get()
        settings["MIDI Devices"] = [
            {
                **device,
                "Enabled": enabled.get(),
                "CSCP -> MIDI port": output_port.get(),
                "MIDI -> CSCP port": input_port.get(),
                "Channel Mapping": [int(field.get()) for field in mapping_fields],
            }
            for device, (enabled, output_port, input_port, mapping_fields) in zip(settings["MIDI Devices"], self.device_fields)
        ]
        return settings

    def _apply_settings(self, show_error=True):
        try:
            settings = self._collect_settings()
        except ValueError:
            self.status.config(text="Every fader mapping must be a whole positive mixer strip number.")
            return
        if not settings["Mixer Name"]:
            self.status.config(text="Select a mixer before applying.")
            return
        missing_ports = [device["Name"] for device in settings["MIDI Devices"] if device["Enabled"] and (not device["CSCP -> MIDI port"] or not device["MIDI -> CSCP port"])]
        if missing_ports:
            self.status.config(text="Select available MIDI input and output ports for: {}.".format(", ".join(missing_ports)))
            return
        if any(strip < 1 or strip > 65536 for device in settings["MIDI Devices"] if device["Enabled"] for strip in device["Channel Mapping"]):
            self.status.config(text="Fader mappings must be from 1 to 65536 (the CSCP strip range).")
            return
        config.set_debug_logging(settings["Debug Logging"])
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