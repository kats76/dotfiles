#!/bin/sh
# Modos de energía (clic en el módulo battery): rendimiento, equilibrado y ahorro de power-profiles-daemon
set -u

current=$(powerprofilesctl get)

# Cada línea: texto del menú <TAB> perfil
lines=$(printf '%s\t%s\n' \
        "󰓅  Rendimiento" performance \
        "󰾅  Equilibrado" balanced \
        "󰾆  Ahorro" power-saver \
    | awk -F'\t' -v c="$current" '{ print $1 ($2 == c ? "  (actual)" : "") "\t" $2 }')

choice=$(printf '%s\n' "$lines" | cut -f1 \
    | wofi --dmenu --cache-file /dev/null --prompt "Modo de energía" --width 360 --lines 4) || exit 0
[ -z "$choice" ] && exit 0

profile=$(printf '%s\n' "$lines" | awk -F'\t' -v c="$choice" '$1 == c { print $2 }')
[ -z "$profile" ] || [ "$profile" = "$current" ] && exit 0

if powerprofilesctl set "$profile"; then
    notify-send -a Energía "Modo de energía: ${choice#*  }"
else
    notify-send -u critical -a Energía "No se pudo cambiar el modo de energía"
fi
