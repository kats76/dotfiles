#!/bin/sh
# Menú de Bluetooth (clic en el módulo bluetooth): conecta o desconecta los dispositivos emparejados
set -u

# shellcheck source=/dev/null
. "${XDG_CONFIG_HOME:-$HOME/.config}/wofi/lib.sh"
menu_lock

menu() {
    "$WOFI_DIR/menu.sh" --dmenu --insensitive --cache-file /dev/null --prompt "$1" --width 480 --lines "${2:-8}"
}

if [ "$(bluetoothctl show | awk '/Powered:/ { print $2 }')" != "yes" ]; then
    choice=$(printf '󰂯  Encender Bluetooth\n' | menu "Bluetooth" 2) || exit 0
    [ -n "$choice" ] && bluetoothctl power on > /dev/null && notify-send -a Bluetooth "Bluetooth encendido"
    exit 0
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# Cada línea: texto del menú <TAB> MAC <TAB> acción <TAB> nombre
bluetoothctl devices Paired | while read -r _ mac name; do
    if bluetoothctl info "$mac" | grep -q 'Connected: yes'; then
        printf '󰂱  %s  (conectado)\t%s\tdisconnect\t%s\n' "$name" "$mac" "$name"
    else
        printf '󰂯  %s\t%s\tconnect\t%s\n' "$name" "$mac" "$name"
    fi
done > "$tmp/list"

# Altura justa: los dispositivos más las dos opciones fijas
n=$(($(wc -l < "$tmp/list") + 2))
choice=$({ cut -f1 "$tmp/list"; printf '󰂳  Emparejar un dispositivo nuevo\n󰂲  Apagar Bluetooth\n'; } | menu "Bluetooth" "$n") || exit 0
[ -z "$choice" ] && exit 0

case "$choice" in
    "󰂳  Emparejar un dispositivo nuevo")
        # 9>&-: blueman no hereda el candado; si no, ningún menú se abriría mientras siga abierto
        setsid -f blueman-manager > /dev/null 2>&1 9>&-
        exit 0
        ;;
    "󰂲  Apagar Bluetooth")
        bluetoothctl power off > /dev/null && notify-send -a Bluetooth "Bluetooth apagado"
        exit 0
        ;;
esac

# La elección va por el entorno: awk -v interpretaría las '\' del nombre
line=$(c="$choice" awk -F'\t' '$1 == ENVIRON["c"] { print; exit }' "$tmp/list")
[ -z "$line" ] && exit 0
mac=$(printf '%s' "$line" | cut -f2)
action=$(printf '%s' "$line" | cut -f3)
name=$(printf '%s' "$line" | cut -f4)

if [ "$action" = "connect" ]; then
    notify-send -a Bluetooth "Conectando a $name…"
    if bluetoothctl connect "$mac" > /dev/null 2>&1; then
        notify-send -a Bluetooth "Conectado a $name"
    else
        notify-send -u critical -a Bluetooth "No se pudo conectar a $name" "¿Está encendido y cerca?"
    fi
else
    bluetoothctl disconnect "$mac" > /dev/null 2>&1 && notify-send -a Bluetooth "Desconectado de $name"
fi
