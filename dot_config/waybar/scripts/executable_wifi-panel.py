#!/usr/bin/env python3
"""Panel de Wi-Fi (clic en el módulo network de waybar).

Se abre al momento con las redes que el sistema ya conoce y escanea en segundo plano.
Interruptor para encender y apagar, la red conectada arriba con opción de desconectar,
y la contraseña de una red nueva se escribe dentro del panel. Usa nmcli; la base común está en panel.py.
"""

from panel import Gtk, Panel, clear, item, label, main, notify, run, run_async, run_ok

SIGNAL_ICONS = ((80, "󰤨"), (60, "󰤥"), (40, "󰤢"), (20, "󰤟"), (0, "󰤯"))


def split_terse(line):
    """Parte una línea de `nmcli -t` por ':' respetando sus escapes ('\\:' y '\\\\')."""
    fields, current, chars = [], "", iter(line)
    for char in chars:
        if char == "\\":
            current += next(chars, "")
        elif char == ":":
            fields.append(current)
            current = ""
        else:
            current += char
    fields.append(current)
    return fields


def wifi_device():
    for line in run("nmcli", "-t", "-f", "DEVICE,TYPE", "device").splitlines():
        device, kind = split_terse(line)[:2]
        if kind == "wifi":
            return device
    return None


def radio_on():
    return run("nmcli", "-t", "-f", "WIFI", "radio").strip() == "enabled"


def active_connection(device):
    """(nombre de la conexión, SSID) de la red conectada, o (None, None)."""
    if not device:
        return None, None
    name = run("nmcli", "-g", "GENERAL.CONNECTION", "device", "show", device).strip()
    if not name:
        return None, None
    ssid = split_terse(run("nmcli", "-g", "802-11-wireless.ssid", "connection", "show", name).strip())[0]
    return name, ssid


def saved_networks():
    names = set()
    for line in run("nmcli", "-t", "-f", "NAME,TYPE", "connection", "show").splitlines():
        name, kind = split_terse(line)[:2]
        if kind == "802-11-wireless":
            names.add(name)
    return names


def networks(rescan):
    """Redes visibles, sin repetir, de más a menos señal."""
    found = {}
    out = run("nmcli", "-t", "-f", "SIGNAL,SECURITY,SSID", "device", "wifi", "list",
              "--rescan", "yes" if rescan else "no")
    for line in out.splitlines():
        signal, security, ssid = split_terse(line)[:3]
        if ssid and int(signal or 0) > found.get(ssid, {}).get("signal", -1):
            found[ssid] = {"ssid": ssid, "signal": int(signal or 0),
                           "secured": security not in ("", "--")}
    return sorted(found.values(), key=lambda n: -n["signal"])


def signal_icon(strength):
    return next(icon for limit, icon in SIGNAL_ICONS if strength >= limit)


class WifiPanel(Panel):
    def __init__(self):
        super().__init__("Wi-Fi", "󰖩")
        self.device = wifi_device()
        self.switch = Gtk.Switch(active=radio_on(), valign=Gtk.Align.CENTER)
        self.switch.connect("notify::active", self.on_switch)
        self.header.pack_end(self.switch, False, False, 0)

        self.status = label("", "section")
        self.body.add(self.status)
        self.list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.scroll = self.scrolled(self.list)
        self.body.add(self.scroll)

        # Al momento con lo que ya se conoce; el escaneo llega después
        self.saved = saved_networks()
        self.show_networks(networks(rescan=False))
        self.scan()

    def scan(self):
        if self.switch.get_active():
            self.status.set_text("Redes · buscando…")
            run_async(lambda: networks(rescan=True), self.on_scan)

    def on_scan(self, nets):
        # Con una contraseña a medio escribir no se redibuja la lista (se perdería);
        # al terminar de conectar se vuelve a leer y ya incluye lo escaneado
        if self.typing:
            self.status.set_text("Redes")
        else:
            self.show_networks(nets)

    def show_networks(self, nets):
        clear(self.list)
        if not self.switch.get_active():
            self.status.set_text("Wi-Fi apagado")
            return
        self.status.set_text("Redes")
        connection, active = active_connection(self.device)
        nets = sorted(nets, key=lambda n: n["ssid"] != active)  # la conectada, la primera
        for net in nets:
            text = f"{signal_icon(net['signal'])}  {net['ssid']}" + ("  󰌾" if net["secured"] else "")
            if net["ssid"] == active:
                row = Gtk.Box(spacing=4)
                row.pack_start(item(text, True), True, True, 0)
                row.pack_end(item("Desconectar", False, self.on_disconnect, connection), False, False, 0)
                self.list.add(row)
            else:
                self.list.add(item(text, False, self.on_network, net))
        self.list.show_all()
        self.fit(self.scroll)

    def on_switch(self, switch, _param):
        state = "on" if switch.get_active() else "off"
        def done(_result):
            self.show_networks(networks(rescan=False))
            self.scan()
        run_async(lambda: run("nmcli", "radio", "wifi", state), done)

    def on_network(self, button, net):
        if net["ssid"] in self.saved or not net["secured"]:
            self.connect_to(net["ssid"], None, button)
        else:
            self.ask_password(button, net["ssid"])

    def ask_password(self, button, ssid):
        """Campo de contraseña justo debajo de la red elegida."""
        self.typing = True
        entry = Gtk.Entry(visibility=False, placeholder_text=f"Contraseña de {ssid}")
        go = item("Conectar", True)
        box = Gtk.Box(spacing=4)
        box.pack_start(entry, True, True, 0)
        box.pack_end(go, False, False, 0)
        position = self.list.get_children().index(button) + 1
        self.list.add(box)
        self.list.reorder_child(box, position)
        box.show_all()
        self.fit(self.scroll)
        entry.grab_focus()

        def submit(*_):
            if entry.get_text():
                self.connect_to(ssid, entry.get_text(), button)
        entry.connect("activate", submit)
        go.connect("clicked", submit)

    def connect_to(self, ssid, password, button):
        button.get_child().get_children()[0].set_text(f"󰤩  Conectando a {ssid}…")
        if ssid in self.saved:
            cmd = ("nmcli", "connection", "up", "id", ssid)
        elif password:
            cmd = ("nmcli", "device", "wifi", "connect", ssid, "password", password)
        else:
            cmd = ("nmcli", "device", "wifi", "connect", ssid)

        def done(result):
            ok, error = result
            self.typing = False
            if ok:
                notify("Wi-Fi", f"Conectado a {ssid}")
                self.saved = saved_networks()
            else:
                notify("Wi-Fi", f"No se pudo conectar a {ssid}", error, critical=True)
            self.show_networks(networks(rescan=False))
        run_async(lambda: run_ok(*cmd), done)

    def on_disconnect(self, button, connection):
        button.get_child().get_children()[0].set_text("Desconectando…")
        run_async(lambda: run_ok("nmcli", "connection", "down", "id", connection),
                  lambda _r: self.show_networks(networks(rescan=False)))


if __name__ == "__main__":
    main(WifiPanel, "wifi")
