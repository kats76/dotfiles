#!/bin/sh
# Apaga la pantalla del portátil con la tapa cerrada (si hay monitores externos)
LAPTOP='hl.monitor({ output = "eDP-1", mode = "1920x1200@60", position = "360x1920", scale = 1.333333, disabled = false })'
state=$(grep -o 'closed\|open' /proc/acpi/button/lid/*/state | head -1)
externals=$(hyprctl monitors -j | grep -c '"name": "DP-\|"name": "HDMI-')
if [ "$state" = "closed" ] && [ "$externals" -gt 0 ]; then
    hyprctl eval 'hl.monitor({ output = "eDP-1", disabled = true })'
else
    hyprctl eval "$LAPTOP"
fi
