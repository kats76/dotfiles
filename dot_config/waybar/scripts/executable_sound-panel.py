#!/usr/bin/env python3
"""Panel de sonido (clic en el módulo de volumen de waybar).

Barra de volumen, silencio y salidas de audio. Al elegir una salida, lo que ya suena pasa a ella.
Lee y cambia el audio con pactl (pipewire-pulse). La base común está en panel.py.
"""

import json

from panel import Gtk, Panel, clear, item, label, main, run


def output_label(description, name):
    """Nombre corto y su icono. None para las salidas HDMI sin pantalla conectada."""
    if name.startswith("bluez_output"):
        return "󰋋", description
    if "HDMI" in description or "DisplayPort" in description:
        if "[" not in description:
            return None
        return "󰍹", description[description.index("[") + 1 : description.index("]")] + " (HDMI)"
    if "Speaker" in description:
        return "󰓃", "Altavoces"
    if "Headphones" in description:
        return "󰋋", "Auriculares"
    return "󰓃", description


def read_sinks():
    default = run("pactl", "get-default-sink").strip()
    sinks = []
    for s in json.loads(run("pactl", "-f", "json", "list", "sinks") or "[]"):
        name = s["name"]
        shown = output_label(s.get("description", name), name)
        if shown is None and name != default:
            continue
        icon, text = shown or ("󰓃", s.get("description", name))
        channel = next(iter(s.get("volume", {}).values()), {})
        volume = int(channel.get("value_percent", "0%").rstrip("%"))
        sinks.append({"name": name, "icon": icon, "text": text, "volume": volume,
                      "mute": s.get("mute", False), "default": name == default})
    return sinks


class SoundPanel(Panel):
    def __init__(self):
        super().__init__("Volumen", "󰕾")
        self.pct = label("", "value", xalign=1)
        self.header.pack_end(self.pct, False, False, 0)

        row = Gtk.Box(spacing=8)
        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.scale.set_draw_value(False)
        self.scale_handler = self.scale.connect("value-changed", self.on_volume)
        self.mute = Gtk.Button()
        self.mute.connect("clicked", self.on_mute)
        row.pack_start(self.scale, True, True, 0)
        row.pack_end(self.mute, False, False, 0)
        self.body.add(row)

        self.body.add(label("Salida", "section"))
        self.outputs = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.body.add(self.outputs)
        self.refresh()

    def refresh(self):
        sinks = read_sinks()
        current = next((s for s in sinks if s["default"]), None)
        if current:
            with self.scale.handler_block(self.scale_handler):
                self.scale.set_value(current["volume"])
            self.show_volume(current["volume"], current["mute"])

        clear(self.outputs)
        for sink in sinks:
            self.outputs.add(item(f"{sink['icon']}  {sink['text']}", sink["default"],
                                  self.on_output, sink["name"]))
        self.outputs.show_all()

    def show_volume(self, volume, muted):
        self.pct.set_text("silencio" if muted else f"{volume} %")
        self.mute.set_label("󰖁" if muted else "󰕾")
        context = self.mute.get_style_context()
        (context.add_class if muted else context.remove_class)("muted")

    def on_volume(self, scale):
        volume = int(scale.get_value())
        run("pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{volume}%")
        muted = run("pactl", "get-sink-mute", "@DEFAULT_SINK@").strip().endswith("yes")
        self.show_volume(volume, muted)

    def on_mute(self, _button):
        run("pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle")
        self.refresh()

    def on_output(self, _button, name):
        run("pactl", "set-default-sink", name)
        # Lo que ya está sonando se mueve a la salida nueva
        for line in run("pactl", "list", "short", "sink-inputs").splitlines():
            run("pactl", "move-sink-input", line.split()[0], name)
        self.refresh()


if __name__ == "__main__":
    main(SoundPanel, "sound")
