# shellcheck shell=sh
# Funciones comunes del lanzador y de los menús de waybar. Se carga con:
#   . "${XDG_CONFIG_HOME:-$HOME/.config}/wofi/lib.sh"

WOFI_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/wofi"

# Ancho que ocupa el panel de la ilustración: 220 px de imagen + 14 de separación.
# Debe coincidir con padding-left en style-panel.css.
# shellcheck disable=SC2034 # se usa en menu.sh
PANEL_WIDTH=234

# Un solo menú a la vez: si ya hay uno abierto (o cargándose, como el escaneo de redes),
# sale sin abrir otro. El candado dura hasta que termina el script que lo pidió.
menu_lock() {
    [ -n "${WOFI_MENU_LOCKED:-}" ] && return 0
    exec 9> "${XDG_RUNTIME_DIR:-/tmp}/wofi-menu.lock"
    flock -n 9 || exit 0
    export WOFI_MENU_LOCKED=1
}

# El panel existe o se puede generar (make-panel.sh necesita la imagen de origen)
panel_ready() {
    [ -f "$WOFI_DIR/panel.png" ] || "$WOFI_DIR/make-panel.sh" > /dev/null 2>&1
}
