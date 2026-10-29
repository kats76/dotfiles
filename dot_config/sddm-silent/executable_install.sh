#!/usr/bin/env bash
# Aplica la config de SilentSDDM con la identidad de Hyprland.
# Fuente de verdad: ~/.config/sddm-silent/  ->  /usr/share/sddm/themes/silent/
# Volver a ejecutar tras actualizar sddm-silent-theme (AUR) o cambiar el wallpaper.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
THEME=/usr/share/sddm/themes/silent
WALLPAPER="$HOME/Img/wallhaven-9oo8k1.jpg"

[[ -d $THEME ]] || { echo "Falta el tema: yay -S sddm-silent-theme"; exit 1; }

sudo install -m644 "$HERE/hypr.conf" "$THEME/configs/hypr.conf"
sudo install -m644 "$WALLPAPER" "$THEME/backgrounds/hypr-wallpaper.jpg"
sudo sed -i 's|^ConfigFile=.*|ConfigFile=configs/hypr.conf|' "$THEME/metadata.desktop"
sudo install -Dm755 "$HERE/Xsetup" /usr/local/share/sddm/Xsetup
sudo install -Dm644 "$HERE/10-silent.conf" /etc/sddm.conf.d/10-silent.conf
sudo sed -i "s/^Current=.*/Current=silent/" /etc/sddm.conf  # sddm.conf gana sobre conf.d

echo "Listo. Prueba sin cerrar sesión con: cd $THEME && ./test.sh"
