#!/bin/sh
# Menú de Wi-Fi (clic en el módulo network): lista las redes, conecta y enciende o apaga el Wi-Fi
set -u

# shellcheck source=/dev/null
. "${XDG_CONFIG_HOME:-$HOME/.config}/wofi/lib.sh"
menu_lock

menu() {
    "$WOFI_DIR/menu.sh" --dmenu --insensitive --cache-file /dev/null --prompt "$1" --width 480 --lines "${2:-10}"
}

if [ "$(nmcli -t -f WIFI radio)" != "enabled" ]; then
    choice=$(printf '󰖩  Encender Wi-Fi\n' | menu "Wi-Fi" 2) || exit 0
    [ -n "$choice" ] && nmcli radio wifi on && notify-send -a Wi-Fi "Wi-Fi encendido"
    exit 0
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# Red conectada: se pregunta a la tarjeta, porque la columna IN-USE de la lista puede salir vacía
dev=$(nmcli -t -f DEVICE,TYPE device | awk -F: '$2 == "wifi" { print $1; exit }')
conn=$(nmcli -g GENERAL.CONNECTION device show "$dev" 2>/dev/null)
active=""
[ -n "$conn" ] && active=$(nmcli -g 802-11-wireless.ssid connection show "$conn" 2>/dev/null)

# Campos SIGNAL:SECURITY:SSID. nmcli escapa los ':' del nombre como '\:'.
# Cada línea: texto del menú <TAB> SSID
nmcli -t -f SIGNAL,SECURITY,SSID device wifi list --rescan auto \
    | sed 's/\\:/\x01/g' \
    | awk -F: -v active="$active" '{ gsub("\001", ":", $3) } $3 != "" && !seen[$3]++ {
        s = $1 + 0
        icon = s >= 80 ? "󰤨" : s >= 60 ? "󰤥" : s >= 40 ? "󰤢" : s >= 20 ? "󰤟" : "󰤯"
        lock = ($2 == "" || $2 == "--") ? "" : "  󰌾"
        mark = ($3 == active) ? "  (conectada)" : ""
        printf "%s  %s%s%s\t%s\n", icon, $3, lock, mark, $3
    }' > "$tmp/list"

# Altura justa hasta 10 líneas; con más redes, el menú se desplaza
n=$(($(wc -l < "$tmp/list") + 1))
[ "$n" -gt 10 ] && n=10
choice=$({ cut -f1 "$tmp/list"; printf '󰖪  Apagar Wi-Fi\n'; } | menu "Wi-Fi" "$n") || exit 0
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
    pass=$("$WOFI_DIR/menu.sh" --dmenu --password --cache-file /dev/null --prompt "Contraseña de $ssid" --width 480 --lines 1 < /dev/null) || exit 0
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
