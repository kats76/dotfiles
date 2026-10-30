#!/bin/sh
# Menú de Wi-Fi (clic en el módulo network): lista las redes, conecta y enciende o apaga el Wi-Fi
set -u

menu() {
    wofi --dmenu --insensitive --cache-file /dev/null --prompt "$1" --width 480 --lines "${2:-10}"
}

if [ "$(nmcli -t -f WIFI radio)" != "enabled" ]; then
    choice=$(printf '󰖩  Encender Wi-Fi\n' | menu "Wi-Fi" 2) || exit 0
    [ -n "$choice" ] && nmcli radio wifi on && notify-send -a Wi-Fi "Wi-Fi encendido"
    exit 0
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# Campos IN-USE:SIGNAL:SECURITY:SSID. nmcli escapa los ':' del nombre como '\:'.
# Cada línea: texto del menú <TAB> SSID
nmcli -t -f IN-USE,SIGNAL,SECURITY,SSID device wifi list --rescan auto \
    | sed 's/\\:/\x01/g' \
    | awk -F: '$4 != "" && !seen[$4]++ {
        s = $2 + 0
        icon = s >= 80 ? "󰤨" : s >= 60 ? "󰤥" : s >= 40 ? "󰤢" : s >= 20 ? "󰤟" : "󰤯"
        lock = ($3 == "" || $3 == "--") ? "" : "  󰌾"
        mark = ($1 == "*") ? "  (conectada)" : ""
        gsub("\001", ":", $4)
        printf "%s  %s%s%s\t%s\n", icon, $4, lock, mark, $4
    }' > "$tmp/list"

choice=$({ cut -f1 "$tmp/list"; printf '󰖪  Apagar Wi-Fi\n'; } | menu "Wi-Fi") || exit 0
[ -z "$choice" ] && exit 0

if [ "$choice" = "󰖪  Apagar Wi-Fi" ]; then
    nmcli radio wifi off && notify-send -a Wi-Fi "Wi-Fi apagado"
    exit 0
fi

line=$(awk -F'\t' -v c="$choice" '$1 == c { print; exit }' "$tmp/list")
[ -z "$line" ] && exit 0
ssid=$(printf '%s' "$line" | cut -f2)

case "$choice" in
    *"(conectada)")
        notify-send -a Wi-Fi "Ya estás conectado a $ssid"
        exit 0
        ;;
esac

# Red guardada: se reutiliza su conexión. Nueva: contraseña si tiene candado.
if nmcli -t -f NAME connection show | grep -qxF "$ssid"; then
    out=$(nmcli connection up id "$ssid" 2>&1); rc=$?
elif printf '%s' "$choice" | grep -q '󰌾'; then
    pass=$(wofi --dmenu --password --cache-file /dev/null --prompt "Contraseña de $ssid" --width 480 --lines 1 < /dev/null) || exit 0
    [ -z "$pass" ] && exit 0
    out=$(nmcli device wifi connect "$ssid" password "$pass" 2>&1); rc=$?
else
    out=$(nmcli device wifi connect "$ssid" 2>&1); rc=$?
fi

if [ "$rc" -eq 0 ]; then
    notify-send -a Wi-Fi "Conectado a $ssid"
else
    notify-send -u critical -a Wi-Fi "No se pudo conectar a $ssid" "$out"
fi
