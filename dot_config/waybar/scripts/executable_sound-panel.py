#!/usr/bin/env python3
"""Panel de sonido (clic en el módulo de volumen de waybar).

Barra de volumen, silencio y salidas de audio con la paleta de Hyprland.
Sale bajo el icono como capa de Wayland (gtk-layer-shell), igual que las notificaciones.
Se cierra con Esc, al sacar el ratón de encima o con otro clic en el icono: nunca hay dos.
Lee y cambia el audio con pactl (pipewire-pulse).
"""

import fcntl
import json
import os
import signal
import subprocess
import sys

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gdk, GLib, Gtk, GtkLayerShell  # noqa: E402

WIDTH = 360
MARGIN = 8  # distancia mínima al borde del monitor
CLOSE_DELAY_MS = 600  # margen tras sacar el ratón antes de cerrar
IDLE_CLOSE_MS = 5000  # si nunca se pasa el ratón por encima, se cierra solo

# Paleta: bg #1e1e2e, fg #cdd6f4, accent #8a63c7, accent2 #6f9f98, red #c44532, gray #a08f95, light #c7ced6
CSS = b"""
#sound-panel { background-color: transparent; }
#panel {
    background-color: rgba(30, 30, 46, 0.96);
    border: 1px solid #8a63c7;
    border-radius: 18px;
    padding: 14px;
}
#panel * { font-family: "JetBrainsMono Nerd Font"; font-size: 13px; color: #cdd6f4; }
#panel .title { font-weight: bold; }
#panel .pct { color: #6f9f98; }
#panel .section { color: #a08f95; font-size: 11px; margin-top: 6px; }
#panel scale trough { background-color: #313244; border: none; border-radius: 6px; min-height: 6px; }
#panel scale highlight { background-color: #8a63c7; border-radius: 6px; }
#panel scale slider {
    background-color: #cdd6f4; border: none; box-shadow: none;
    min-width: 16px; min-height: 16px; border-radius: 8px;
}
#panel button { background: transparent; border: none; box-shadow: none; border-radius: 10px; padding: 8px 10px; }
#panel button:hover { background-color: alpha(#6f9f98, 0.35); }
#panel button.active { background-color: #8a63c7; }
#panel button.active label { color: #c7ced6; }
#panel button.muted label { color: #c44532; }
"""

LOCK = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "sound-panel.lock")


def run(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=False).stdout


def single_instance():
    """Un solo panel: si ya hay uno, el segundo clic lo cierra y sale."""
    fd = os.open(LOCK, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        pid = os.read(fd, 32).decode().strip()
        if pid.isdigit():
            os.kill(int(pid), signal.SIGTERM)
        sys.exit(0)
    os.ftruncate(fd, 0)
    os.write(fd, str(os.getpid()).encode())
    return fd  # el candado dura mientras el descriptor siga abierto


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
        label = output_label(s.get("description", s["name"]), s["name"])
        if label is None and s["name"] != default:
            continue
        icon, text = label or ("󰓃", s.get("description", s["name"]))
        channel = next(iter(s.get("volume", {}).values()), {})
        volume = int(channel.get("value_percent", "0%").rstrip("%"))
        sinks.append({"name": s["name"], "icon": icon, "text": text, "volume": volume,
                      "mute": s.get("mute", False), "default": s["name"] == default})
    return sinks


def place(window):
    """Bajo el cursor (el icono que se ha pulsado), en el monitor que tiene el foco."""
    try:
        cursor = json.loads(run("hyprctl", "-j", "cursorpos"))
        mon = next(m for m in json.loads(run("hyprctl", "-j", "monitors")) if m["focused"])
    except (ValueError, StopIteration):
        return
    rotated = mon.get("transform", 0) % 2 == 1
    width = (mon["height"] if rotated else mon["width"]) / mon["scale"]
    left = cursor["x"] - mon["x"] - WIDTH / 2
    left = max(MARGIN, min(left, width - WIDTH - MARGIN))
    GtkLayerShell.set_margin(window, GtkLayerShell.Edge.LEFT, int(left))

    display = Gdk.Display.get_default()
    for i in range(display.get_n_monitors()):
        geo = display.get_monitor(i).get_geometry()
        if (geo.x, geo.y) == (mon["x"], mon["y"]):
            GtkLayerShell.set_monitor(window, display.get_monitor(i))
            break


class SoundPanel(Gtk.Window):
    def __init__(self):
        super().__init__(title="Sonido")
        self.set_name("sound-panel")
        self.set_size_request(WIDTH, -1)  # en una capa, GTK ignora set_default_size

        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_namespace(self, "sound-panel")
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.TOP)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, True)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 6)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.ON_DEMAND)
        place(self)

        self.close_timer = GLib.timeout_add(IDLE_CLOSE_MS, Gtk.main_quit)
        self.connect("enter-notify-event", self.on_enter)
        self.connect("leave-notify-event", self.on_leave)
        self.connect("key-press-event", lambda _w, e: e.keyval == Gdk.KEY_Escape and Gtk.main_quit())

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, name="panel")
        self.add(self.box)

        header = Gtk.Box(spacing=8)
        title = Gtk.Label(label="󰕾  Volumen", xalign=0)
        title.get_style_context().add_class("title")
        self.pct = Gtk.Label(xalign=1)
        self.pct.get_style_context().add_class("pct")
        header.pack_start(title, True, True, 0)
        header.pack_end(self.pct, False, False, 0)
        self.box.add(header)

        row = Gtk.Box(spacing=8)
        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.scale.set_draw_value(False)
        self.scale_handler = self.scale.connect("value-changed", self.on_volume)
        self.mute = Gtk.Button()
        self.mute.connect("clicked", self.on_mute)
        row.pack_start(self.scale, True, True, 0)
        row.pack_end(self.mute, False, False, 0)
        self.box.add(row)

        section = Gtk.Label(label="Salida", xalign=0)
        section.get_style_context().add_class("section")
        self.box.add(section)

        self.outputs = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.box.add(self.outputs)
        self.refresh()

    # Cierre al sacar el ratón, con un pequeño margen por si vuelve
    def on_enter(self, _w, event):
        if event.detail != Gdk.NotifyType.INFERIOR and self.close_timer:
            GLib.source_remove(self.close_timer)
            self.close_timer = None

    def on_leave(self, _w, event):
        if event.detail != Gdk.NotifyType.INFERIOR and not self.close_timer:
            self.close_timer = GLib.timeout_add(CLOSE_DELAY_MS, Gtk.main_quit)

    def refresh(self):
        self.sinks = read_sinks()
        current = next((s for s in self.sinks if s["default"]), None)
        if current:
            with self.scale.handler_block(self.scale_handler):
                self.scale.set_value(current["volume"])
            self.show_volume(current["volume"], current["mute"])

        for child in self.outputs.get_children():
            self.outputs.remove(child)
        for sink in self.sinks:
            button = Gtk.Button(label=f"{sink['icon']}  {sink['text']}")
            button.get_child().set_xalign(0)
            if sink["default"]:
                button.get_style_context().add_class("active")
            button.connect("clicked", self.on_output, sink["name"])
            self.outputs.add(button)
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


def main():
    _lock = single_instance()  # noqa: F841 (el candado vive mientras el proceso)
    # El segundo clic manda SIGTERM: se cierra desde el bucle de GTK
    try:
        gi.require_version("GLibUnix", "2.0")
        from gi.repository import GLibUnix

        GLibUnix.signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, Gtk.main_quit)
    except (ValueError, ImportError):  # PyGObject antiguo
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, Gtk.main_quit)

    provider = Gtk.CssProvider()
    provider.load_from_data(CSS)
    # Por encima de gtk-3.0/gtk.css (prioridad USER), que pinta el fondo de todas las ventanas
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)

    panel = SoundPanel()
    panel.connect("destroy", Gtk.main_quit)
    panel.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
