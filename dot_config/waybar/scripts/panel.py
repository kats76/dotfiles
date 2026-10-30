"""Base común de los paneles de waybar (volumen, Wi-Fi, Bluetooth y batería).

Cada panel hereda de Panel y solo rellena su contenido. Esta base se encarga de:
- Salir bajo el botón pulsado, en el monitor con el foco, con un ancho que cabe en él.
- Un solo panel a la vez: otro clic en el mismo botón lo cierra; en otro botón, cambia de panel.
- Cerrarse con Esc o al sacar el ratón (salvo mientras se escribe, p. ej. una contraseña).
- La paleta de Hyprland y la fuente JetBrainsMono.
- Ejecutar comandos en segundo plano (run_async) para que la interfaz no se congele.
"""

import fcntl
import json
import os
import signal
import subprocess
import sys
import threading
import time

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
.waybar-panel { background-color: transparent; }
#panel {
    background-color: rgba(30, 30, 46, 0.96);
    border: 1px solid #8a63c7;
    border-radius: 18px;
    padding: 14px;
}
#panel * { font-family: "JetBrainsMono Nerd Font"; font-size: 13px; color: #cdd6f4; }
#panel .title { font-weight: bold; }
#panel .value { color: #6f9f98; }
#panel .section { color: #a08f95; font-size: 11px; margin-top: 6px; }
#panel .hint { color: #a08f95; }
#panel scrolledwindow, #panel viewport { background: transparent; border: none; }
#panel scale trough { background-color: #313244; border: none; border-radius: 6px; min-height: 6px; }
#panel scale highlight { background-color: #8a63c7; border-radius: 6px; }
#panel scale slider {
    background-color: #cdd6f4; border: none; box-shadow: none;
    min-width: 16px; min-height: 16px; border-radius: 8px;
}
#panel switch { background-color: #313244; border: none; border-radius: 12px; }
#panel switch:checked { background-color: #8a63c7; }
#panel switch slider { background-color: #cdd6f4; border: none; box-shadow: none; border-radius: 10px; }
#panel button { background: transparent; border: none; box-shadow: none; border-radius: 10px; padding: 8px 10px; }
#panel button:hover { background-color: alpha(#6f9f98, 0.35); }
#panel button.active { background-color: #8a63c7; }
#panel button.active label { color: #c7ced6; }
#panel button.muted label, #panel .error { color: #c44532; }
#panel entry {
    background-color: #252536; color: #cdd6f4; caret-color: #cdd6f4;
    border: 1px solid alpha(#a08f95, 0.35); border-radius: 10px; padding: 6px 10px;
}
#panel entry:focus { border-color: #6f9f98; }
"""

LOCK = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "waybar-panel.lock")

# Salida en inglés fijo: algunas herramientas traducen sus respuestas
ENV = {**os.environ, "LC_ALL": "C"}


def run(*cmd):
    """Ejecuta un comando y devuelve su salida (vacía si falla)."""
    return subprocess.run(cmd, capture_output=True, text=True, check=False, env=ENV).stdout


def run_ok(*cmd):
    """Ejecuta un comando y devuelve (correcto, mensaje de error)."""
    p = subprocess.run(cmd, capture_output=True, text=True, check=False, env=ENV)
    return p.returncode == 0, (p.stderr or p.stdout).strip()


def run_async(func, callback=None):
    """Ejecuta func() en otro hilo y llama a callback(resultado) en el de la interfaz."""
    def worker():
        result = func()
        if callback:
            GLib.idle_add(callback, result)
    threading.Thread(target=worker, daemon=True).start()


def notify(app, title, body="", critical=False):
    """Aviso con mako; las críticas no se cierran solas."""
    cmd = ["notify-send", "-a", app] + (["-u", "critical"] if critical else [])
    subprocess.Popen(cmd + [title, body])


def clear(box):
    for child in box.get_children():
        box.remove(child)


def item(text, active=False, on_click=None, *args, extra=None):
    """Botón de una fila de la lista: texto a la izquierda (se recorta si no cabe)
    y, si se da, un dato corto a la derecha que nunca se recorta (p. ej. la batería)."""
    button = Gtk.Button()
    row = Gtk.Box(spacing=8)
    main_label = Gtk.Label(label=text, xalign=0)
    main_label.set_ellipsize(3)  # Pango.EllipsizeMode.END
    row.pack_start(main_label, True, True, 0)
    if extra:
        row.pack_end(Gtk.Label(label=extra), False, False, 0)
    button.add(row)
    if active:
        button.get_style_context().add_class("active")
    if on_click:
        button.connect("clicked", on_click, *args)
    return button


def label(text, css_class=None, xalign=0):
    widget = Gtk.Label(label=text, xalign=xalign)
    if css_class:
        widget.get_style_context().add_class(css_class)
    return widget


def focused_monitor():
    try:
        cursor = json.loads(run("hyprctl", "-j", "cursorpos"))
        mon = next(m for m in json.loads(run("hyprctl", "-j", "monitors")) if m["focused"])
    except (ValueError, StopIteration):
        return None, None
    rotated = mon.get("transform", 0) % 2 == 1
    mon["lw"] = (mon["height"] if rotated else mon["width"]) / mon["scale"]  # tamaño lógico
    mon["lh"] = (mon["width"] if rotated else mon["height"]) / mon["scale"]
    return cursor, mon


class Panel(Gtk.Window):
    """Panel bajo el botón pulsado. Las subclases añaden su contenido a self.body."""

    def __init__(self, title, icon):
        super().__init__(title=title)
        self.get_style_context().add_class("waybar-panel")
        self.typing = False  # mientras se escribe no se cierra al sacar el ratón

        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_namespace(self, "waybar-panel")
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.TOP)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, True)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 6)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.ON_DEMAND)
        self.max_height = self.place()

        self.close_timer = GLib.timeout_add(IDLE_CLOSE_MS, Gtk.main_quit)
        self.connect("enter-notify-event", self.on_enter)
        self.connect("leave-notify-event", self.on_leave)
        self.connect("key-press-event", self.on_key)

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, name="panel")
        self.add(self.box)
        self.header = Gtk.Box(spacing=8)
        self.header.pack_start(label(f"{icon}  {title}", "title"), True, True, 0)
        self.box.add(self.header)
        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.box.add(self.body)

    def place(self):
        """Centra el panel bajo el cursor sin salirse del monitor. Devuelve el alto máximo."""
        cursor, mon = focused_monitor()
        if not mon:
            self.set_size_request(WIDTH, -1)
            return 480
        width = int(min(WIDTH, mon["lw"] - 2 * MARGIN))
        self.set_size_request(width, -1)
        left = cursor["x"] - mon["x"] - width / 2
        left = max(MARGIN, min(left, mon["lw"] - width - MARGIN))
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.LEFT, int(left))

        display = Gdk.Display.get_default()
        for i in range(display.get_n_monitors()):
            geo = display.get_monitor(i).get_geometry()
            if (geo.x, geo.y) == (mon["x"], mon["y"]):
                GtkLayerShell.set_monitor(self, display.get_monitor(i))
                break
        return int(min(480, mon["lh"] * 0.6))

    def scrolled(self, child):
        """Lista con scroll que no pasa del alto máximo del monitor. Tras cambiar su
        contenido hay que llamar a fit(): en una capa, GTK no la deja crecer sola."""
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(child)
        return scroll

    def fit(self, scroll):
        """Ajusta la lista a su contenido, sin pasar del alto máximo."""
        natural = scroll.get_child().get_preferred_height()[1]
        scroll.set_min_content_height(min(natural, self.max_height))

    def on_key(self, _widget, event):
        if event.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()

    def on_enter(self, _widget, event):
        if event.detail != Gdk.NotifyType.INFERIOR and self.close_timer:
            GLib.source_remove(self.close_timer)
            self.close_timer = None

    def on_leave(self, _widget, event):
        if event.detail != Gdk.NotifyType.INFERIOR and not self.close_timer and not self.typing:
            self.close_timer = GLib.timeout_add(CLOSE_DELAY_MS, Gtk.main_quit)


def single_instance(name):
    """Un solo panel abierto. El mismo botón lo cierra; otro botón cambia de panel."""
    fd = os.open(LOCK, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        pid, _, other = os.read(fd, 128).decode().partition(" ")
        if pid.isdigit():
            os.kill(int(pid), signal.SIGTERM)
        if other.strip() == name:
            sys.exit(0)
        for _ in range(20):  # espera a que el otro panel se cierre (máx. 1 s)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                time.sleep(0.05)
        else:
            sys.exit(0)
    os.ftruncate(fd, 0)
    os.lseek(fd, 0, os.SEEK_SET)
    os.write(fd, f"{os.getpid()} {name}".encode())
    return fd  # el candado dura mientras el descriptor siga abierto


def main(panel_class, name, extra_css=b""):
    """Arranca un panel: candado, estilo (CSS común más el propio del panel) y bucle de GTK."""
    _lock = single_instance(name)  # noqa: F841 (el candado vive mientras el proceso)
    # Otro clic manda SIGTERM: se cierra desde el bucle de GTK
    try:
        gi.require_version("GLibUnix", "2.0")
        from gi.repository import GLibUnix

        GLibUnix.signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, Gtk.main_quit)
    except (ValueError, ImportError):  # PyGObject antiguo
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, Gtk.main_quit)

    provider = Gtk.CssProvider()
    provider.load_from_data(CSS + extra_css)
    # Por encima de gtk-3.0/gtk.css (prioridad USER), que pinta el fondo de todas las ventanas
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)

    panel = panel_class()
    panel.connect("destroy", Gtk.main_quit)
    panel.show_all()
    Gtk.main()
