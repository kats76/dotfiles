#!/usr/bin/env python3
"""Indicador en pantalla (OSD) de volumen, micrófono y brillo. Lo lanzan las teclas de hyprland.lua.

Uso: osd.py volume up|down|mute · osd.py mic mute · osd.py brightness up|down

1. Hace el cambio con wpctl o brightnessctl, sin cargar GTK (rápido al mantener la tecla).
2. Si ya hay un indicador abierto, le avisa con SIGUSR1 para que se actualice y siga visible.
3. Si no, este mismo proceso lo abre: cajita abajo en el centro que desaparece a los 1,5 s.
"""

import fcntl
import os
import signal
import subprocess
import sys
import time

STEP = "5%"
TIMEOUT_MS = 1500
WIDTH = 320
BOTTOM_MARGIN = 80

RUNTIME = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
LOCK = os.path.join(RUNTIME, "osd.lock")
KIND = os.path.join(RUNTIME, "osd.kind")  # qué mostrar: volume, mic o brightness

ACTIONS = {
    ("volume", "up"): ["wpctl", "set-volume", "-l", "1", "@DEFAULT_AUDIO_SINK@", f"{STEP}+"],
    ("volume", "down"): ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{STEP}-"],
    ("volume", "mute"): ["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"],
    ("mic", "mute"): ["wpctl", "set-mute", "@DEFAULT_AUDIO_SOURCE@", "toggle"],
    ("brightness", "up"): ["brightnessctl", "-e4", "-n2", "set", f"{STEP}+"],
    ("brightness", "down"): ["brightnessctl", "-e4", "-n2", "set", f"{STEP}-"],
}


def run(*cmd):
    env = {**os.environ, "LC_ALL": "C"}
    return subprocess.run(cmd, capture_output=True, text=True, check=False, env=env).stdout


def level(kind):
    """(porcentaje, silenciado) del dispositivo."""
    if kind == "brightness":
        fields = run("brightnessctl", "-m").strip().split(",")
        return (int(fields[3].rstrip("%")) if len(fields) > 3 else 0), False
    target = "@DEFAULT_AUDIO_SOURCE@" if kind == "mic" else "@DEFAULT_AUDIO_SINK@"
    out = run("wpctl", "get-volume", target)  # "Volume: 0.55 [MUTED]"
    try:
        value = round(float(out.split()[1]) * 100)
    except (IndexError, ValueError):
        value = 0
    return value, "[MUTED]" in out


def icon(kind, value, muted):
    if kind == "brightness":
        return "󰃞" if value < 34 else "󰃟" if value < 67 else "󰃠"
    if kind == "mic":
        return "󰍭" if muted else "󰍬"
    if muted or value == 0:
        return "󰖁"
    return "󰕿" if value < 34 else "󰖀" if value < 67 else "󰕾"


def notify_running(fd):
    """Si otro proceso ya muestra el indicador, le pide que se actualice. True si lo había."""
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return False
    except BlockingIOError:
        for _ in range(10):  # el otro puede no haber escrito aún su pid
            os.lseek(fd, 0, os.SEEK_SET)
            pid = os.read(fd, 32).decode().strip()
            if pid.isdigit():
                try:
                    os.kill(int(pid), signal.SIGUSR1)
                except ProcessLookupError:
                    pass
                return True
            time.sleep(0.02)
        return True


def show(kind, fd):
    """Abre el indicador y lo mantiene mientras lleguen avisos. Aquí se carga GTK."""
    # Un aviso puede llegar mientras GTK carga: ignorado no mata el proceso, y al
    # arrancar se lee el último cambio de todos modos (on_update)
    signal.signal(signal.SIGUSR1, signal.SIG_IGN)
    os.ftruncate(fd, 0)
    os.lseek(fd, 0, os.SEEK_SET)
    os.write(fd, str(os.getpid()).encode())

    import cairo
    import gi

    gi.require_version("Gdk", "3.0")
    gi.require_version("Gtk", "3.0")
    gi.require_version("GtkLayerShell", "0.1")
    from gi.repository import Gdk, GLib, Gtk, GtkLayerShell

    # Paleta: bg #1e1e2e, fg #cdd6f4, accent #8a63c7, red #c44532
    css = b"""
    .osd { background-color: transparent; }
    #osd {
        background-color: rgba(30, 30, 46, 0.94);
        border: 1px solid #8a63c7;
        border-radius: 18px;
        padding: 12px 16px;
    }
    #osd * { font-family: "JetBrainsMono Nerd Font"; color: #cdd6f4; }
    #osd .icon { font-size: 20px; }
    #osd .icon.muted { color: #c44532; }
    #osd .value { font-size: 13px; min-width: 44px; }
    #osd levelbar trough { background-color: #313244; border: none; border-radius: 6px; min-height: 8px; }
    #osd levelbar block.filled { background-color: #8a63c7; border-radius: 6px; }
    #osd levelbar.muted block.filled { background-color: #a08f95; }
    #osd levelbar block.empty { background-color: transparent; }
    """
    provider = Gtk.CssProvider()
    provider.load_from_data(css)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)

    window = Gtk.Window()
    window.get_style_context().add_class("osd")
    window.set_size_request(WIDTH, -1)
    GtkLayerShell.init_for_window(window)
    GtkLayerShell.set_namespace(window, "osd")
    GtkLayerShell.set_layer(window, GtkLayerShell.Layer.OVERLAY)
    GtkLayerShell.set_anchor(window, GtkLayerShell.Edge.BOTTOM, True)  # sin LEFT/RIGHT: centrado
    GtkLayerShell.set_margin(window, GtkLayerShell.Edge.BOTTOM, BOTTOM_MARGIN)
    GtkLayerShell.set_keyboard_mode(window, GtkLayerShell.KeyboardMode.NONE)

    box = Gtk.Box(spacing=12, name="osd")
    glyph = Gtk.Label()
    glyph.get_style_context().add_class("icon")
    bar = Gtk.LevelBar(min_value=0, max_value=100, hexpand=True, valign=Gtk.Align.CENTER)
    for offset in ("low", "high", "full"):  # sin los colores por defecto de GTK
        bar.remove_offset_value(offset)
    value_label = Gtk.Label(xalign=1)
    value_label.get_style_context().add_class("value")
    box.pack_start(glyph, False, False, 0)
    box.pack_start(bar, True, True, 0)
    box.pack_end(value_label, False, False, 0)
    window.add(box)

    state = {"timer": None}

    def refresh(current):
        value, muted = level(current)
        glyph.set_text(icon(current, value, muted))
        bar.set_value(value)
        value_label.set_text("silencio" if muted else f"{value} %")
        for widget in (glyph, bar):
            context = widget.get_style_context()
            (context.add_class if muted else context.remove_class)("muted")
        if state["timer"]:
            GLib.source_remove(state["timer"])
        state["timer"] = GLib.timeout_add(TIMEOUT_MS, Gtk.main_quit)

    def on_update():
        try:
            with open(KIND) as f:
                refresh(f.read().strip())
        except OSError:
            refresh(kind)
        return True

    try:
        gi.require_version("GLibUnix", "2.0")
        from gi.repository import GLibUnix

        GLibUnix.signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, on_update)
    except (ValueError, ImportError):  # PyGObject antiguo
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, on_update)

    on_update()
    window.show_all()
    # Sin región de entrada: los clics pasan a lo que haya debajo
    window.input_shape_combine_region(cairo.Region())
    Gtk.main()


def main():
    if len(sys.argv) != 3 or (sys.argv[1], sys.argv[2]) not in ACTIONS:
        sys.exit("Uso: osd.py volume up|down|mute · osd.py mic mute · osd.py brightness up|down")
    kind, action = sys.argv[1], sys.argv[2]
    subprocess.run(ACTIONS[(kind, action)], check=False, capture_output=True)

    with open(KIND, "w") as f:
        f.write(kind)
    fd = os.open(LOCK, os.O_RDWR | os.O_CREAT, 0o600)
    if not notify_running(fd):
        show(kind, fd)


if __name__ == "__main__":
    main()
