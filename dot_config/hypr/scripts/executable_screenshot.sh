#!/bin/sh
# Captura de un área con grim y slurp. La lanzan los atajos de hyprland.lua:
#   screenshot.sh clip   Impr Pant: al portapapeles
#   screenshot.sh save   Super + Impr Pant: al portapapeles y a SCREENSHOT_DIR
# Esc durante la selección cancela sin dejar ficheros ni avisos.
set -eu

mode="${1:-clip}"
dir="${SCREENSHOT_DIR:-$HOME/Img/Screenshots}"

# Recuadro de selección con la paleta: fondo bg oscurecido, borde y relleno en accent
geom=$(slurp -b 1e1e2e66 -c 8a63c7ff -s 8a63c722 -w 2) || exit 0

case "$mode" in
    clip)
        grim -g "$geom" - | wl-copy --type image/png
        notify-send -a Captura "Captura copiada al portapapeles"
        ;;
    save)
        mkdir -p "$dir"
        file="$dir/$(date +%Y-%m-%d_%H-%M-%S).png"
        grim -g "$geom" "$file"
        wl-copy --type image/png < "$file"
        notify-send -a Captura -i "$file" "Captura guardada" "$(basename "$file") · también en el portapapeles"
        ;;
    *)
        echo "Uso: $0 [clip|save]" >&2
        exit 2
        ;;
esac
