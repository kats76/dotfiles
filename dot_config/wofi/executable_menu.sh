#!/usr/bin/env bash
# Única forma de abrir wofi: el lanzador (Super + Space) y los menús de waybar pasan por aquí.
# Uso: menu.sh [opciones de wofi]
# - Un solo menú a la vez (menu_lock en lib.sh).
# - Con ventanas en el escritorio activo, añade el panel de la ilustración (style.css + style-panel.css).
#   En un escritorio vacío ya se ve el wallpaper, así que se abre sin él.
set -u

# shellcheck source=/dev/null
. "${XDG_CONFIG_HOME:-$HOME/.config}/wofi/lib.sh"
menu_lock

style="$WOFI_DIR/style.css"
extra=0
windows=$(hyprctl -j activeworkspace 2> /dev/null | jq -r '.windows // 0')
if [ "${windows:-0}" -gt 0 ] && panel_ready; then
    # wofi admite un solo fichero de estilo: se junta el base con lo que añade el panel
    style="${XDG_RUNTIME_DIR:-/tmp}/wofi-style-panel.css"
    cat "$WOFI_DIR/style.css" "$WOFI_DIR/style-panel.css" > "$style"
    extra=$PANEL_WIDTH
fi

# El panel ocupa sitio a la izquierda: se ensancha la ventana para que la lista mida lo mismo
args=()
width=""
while [ $# -gt 0 ]; do
    case "$1" in
        -W | --width) width="$2"; shift 2 ;;
        --width=*) width="${1#*=}"; shift ;;
        *) args+=("$1"); shift ;;
    esac
done
[ -z "$width" ] && width=$(awk -F= '$1 == "width" { print $2 }' "$WOFI_DIR/config")

exec wofi --style "$style" --width "$((${width:-560} + extra))" "${args[@]}"
