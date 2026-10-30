#!/usr/bin/env python3
"""Panel de Bluetooth (clic en el módulo bluetooth de waybar).

Interruptor de encendido, dispositivos emparejados con su estado y su batería,
conectar o desconectar con un clic, y emparejar uno nuevo con blueman.
Usa bluetoothctl; la base común está en panel.py.
"""

import subprocess

from panel import Gtk, Panel, clear, item, label, main, notify, run, run_async, run_ok

# Icono según el tipo de dispositivo que anuncia bluetoothctl (campo Icon)
DEVICE_ICONS = {"audio-headphones": "󰋋", "audio-headset": "󰋎", "audio-card": "󰓃",
                "input-mouse": "󰍽", "input-keyboard": "󰌌", "input-gaming": "󰊴", "phone": "󰏲"}


def powered():
    return "Powered: yes" in run("bluetoothctl", "show")


def devices():
    """Dispositivos emparejados: los conectados primero."""
    found = []
    for line in run("bluetoothctl", "devices", "Paired").splitlines():
        parts = line.split(" ", 2)
        if len(parts) < 3:
            continue
        mac, name = parts[1], parts[2]
        info = run("bluetoothctl", "info", mac)
        battery = None
        for row in info.splitlines():
            if "Battery Percentage" in row and "(" in row:
                battery = row.rsplit("(", 1)[1].rstrip(")")
        icon = next((DEVICE_ICONS[k] for k in DEVICE_ICONS if f"Icon: {k}" in info), "󰂯")
        found.append({"mac": mac, "name": name, "icon": icon, "battery": battery,
                      "connected": "Connected: yes" in info})
    return sorted(found, key=lambda d: not d["connected"])


class BluetoothPanel(Panel):
    def __init__(self):
        super().__init__("Bluetooth", "󰂯")
        self.switch = Gtk.Switch(active=powered(), valign=Gtk.Align.CENTER)
        self.switch.connect("notify::active", self.on_switch)
        self.header.pack_end(self.switch, False, False, 0)

        self.status = label("Dispositivos · cargando…", "section")
        self.body.add(self.status)
        self.list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.scroll = self.scrolled(self.list)
        self.body.add(self.scroll)
        self.body.add(item("󰂳  Emparejar un dispositivo nuevo", False, self.on_pair))
        self.load()

    def load(self):
        run_async(devices, self.show_devices)

    def show_devices(self, devs):
        clear(self.list)
        if not self.switch.get_active():
            self.status.set_text("Bluetooth apagado")
            return
        self.status.set_text("Dispositivos" if devs else "Sin dispositivos emparejados")
        for dev in devs:
            battery = f"󰁹 {dev['battery']} %" if dev["connected"] and dev["battery"] else None
            self.list.add(item(f"{dev['icon']}  {dev['name']}", dev["connected"], self.on_device, dev,
                               extra=battery))
        self.list.show_all()
        self.fit(self.scroll)

    def on_switch(self, switch, _param):
        state = "on" if switch.get_active() else "off"
        run_async(lambda: run("bluetoothctl", "power", state), lambda _r: self.load())

    def on_device(self, button, dev):
        action = "disconnect" if dev["connected"] else "connect"
        state = "Desconectando" if dev["connected"] else "Conectando"
        button.get_child().get_children()[0].set_text(f"{dev['icon']}  {state}…")

        def done(result):
            ok, _error = result
            if not ok:
                notify("Bluetooth", f"No se pudo conectar a {dev['name']}",
                       "¿Está encendido y cerca?", critical=True)
            self.load()
        run_async(lambda: run_ok("bluetoothctl", action, dev["mac"]), done)

    def on_pair(self, _button):
        subprocess.Popen(["setsid", "-f", "blueman-manager"], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
        Gtk.main_quit()


if __name__ == "__main__":
    main(BluetoothPanel, "bluetooth")
