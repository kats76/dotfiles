# dotfiles

[![Check configs](https://github.com/kats76/dotfiles/actions/workflows/check.yml/badge.svg)](https://github.com/kats76/dotfiles/actions/workflows/check.yml)

[Read in English](README.md)

Mi configuración personal, gestionada con [chezmoi](https://www.chezmoi.io/): un solo repo y la misma configuración en cualquier máquina con un comando.

- **Escritorio:** Arch Linux + Hyprland con una sola paleta y una sola fuente en todo: el gestor de ventanas, la barra, el lanzador, la terminal, el menú de salida y la pantalla de login.
- **Editor:** Neovim (LazyVim).

## Qué hay aquí

| Ruta en el repo | Destino en la máquina | Qué es |
| --- | --- | --- |
| `dot_config/hypr/` | `~/.config/hypr/` | Hyprland 0.57+ en Lua, wallpaper y el script de la tapa |
| `dot_config/waybar/` | `~/.config/waybar/` | Barra superior |
| `dot_config/sddm-silent/` | `~/.config/sddm-silent/` | Pantalla de login (tema SilentSDDM) y su instalador |
| `dot_config/kitty`, `wofi`, `wlogout`, `cava` | `~/.config/…` | Terminal, lanzador de apps, menú de salida, visualizador de audio |
| `dot_config/fontconfig`, `gtk-3.0`, `gtk-4.0`, `qt6ct` | `~/.config/…` | Para que las apps GTK y Qt sigan el mismo estilo |
| `dot_local/share/color-schemes/` | `~/.local/share/color-schemes/` | Esquema de color de Qt con la paleta |
| `dot_zshrc`, `dot_bashrc` | `~/.zshrc`, `~/.bashrc` | Shell |
| `dot_config/nvim/` | `~/.config/nvim/` | Neovim (LazyVim) |

> Nomenclatura de chezmoi: `dot_` = `.`, `private_` = sin permisos para otros, `executable_` = ejecutable, `.tmpl` = plantilla.

## Paleta

| Nombre | Color | Para qué |
| --- | --- | --- |
| bg | `#1e1e2e` | Fondos |
| fg | `#cdd6f4` | Texto |
| accent | `#8a63c7` | Borde activo, selección, botones con foco |
| accent2 | `#6f9f98` | Segundo acento, hover |
| red | `#c44532` | Urgente, errores |
| gray | `#a08f95` | Elementos inactivos |
| light | `#c7ced6` | Texto secundario |

Fuente: **JetBrainsMono Nerd Font**, con Noto Color Emoji y Source Han Sans JP (japonés) de respaldo. Sin una fuente japonesa, el texto en japonés sale en cuadros vacíos en la terminal, el navegador y el título de la ventana en waybar.

## Instalar el escritorio (Arch Linux)

Haz antes un `sudo pacman -Syu` completo: instalar un paquete de Qt con el sistema a medio actualizar rompe SDDM.

```bash
sudo pacman -S chezmoi hyprland hyprpaper waybar kitty wofi cava brightnessctl playerctl \
  ttf-jetbrains-mono-nerd noto-fonts-emoji adobe-source-han-sans-jp-fonts qt6ct thunar starship \
  zsh-autosuggestions sddm qt6-virtualkeyboard
yay -S wlogout sddm-silent-theme python-pywal
chezmoi init --apply kats76
```

`chezmoi diff` enseña qué cambiaría antes de aplicar. Las rutas del home son plantillas (`{{ .chezmoi.homeDir }}`), así que funciona con otro nombre de usuario.

### Wallpaper

El wallpaper no está en el repo. Descárgalo de [wallhaven 9oo8k1](https://wallhaven.cc/w/9oo8k1) en `~/Img/wallhaven-9oo8k1.jpg`, o cambia la ruta en `hyprpaper.conf`, `hyprland.lua` y `sddm-silent/install.sh` por la tuya.

### Pantalla de login

SDDM corre con su propio usuario, así que su tema no puede vivir en tu home. `install.sh` lo copia a su sitio con `sudo`:

```bash
~/.config/sddm-silent/install.sh
cd /usr/share/sddm/themes/silent && ./test.sh   # vista previa sin cerrar sesión
```

Vuelve a ejecutarlo tras actualizar `sddm-silent-theme` o cambiar el wallpaper. `Xsetup` deja el login en una sola pantalla: con la tapa cerrada ignora la del portátil y elige el monitor de mayor resolución.

### Atajos

`Super` es el modificador principal.

| Teclas | Acción |
| --- | --- |
| `Super + Return` | Terminal (kitty) |
| `Super + Space` | Lanzador de apps (wofi) |
| `Super + F` | Firefox |
| `Super + E` | Gestor de archivos (Thunar) |
| `Super + Backspace` | Menú de salida (wlogout) |
| `Super + Q` | Cerrar ventana |
| `Super + V` | Alternar flotante |
| `Super + H/J/K/L` | Mover el foco |
| `Super + Shift + H/J/K/L` | Mover ventana |
| `Super + Ctrl + H/J/K/L` | Redimensionar ventana |
| `Super + Tab`, luego `Super + H/J/K/L` | Intercambiar ventanas (`Esc` para salir) |
| `Super + 1…0` | Ir al escritorio |
| `Super + Shift + 1…0` | Mandar la ventana al escritorio |
| `Super + S` / `Super + Shift + S` | Scratchpad: mostrar / mandar ventana |
| `Super + M` | Salir de Hyprland |

Las teclas de medios, volumen y brillo también funcionan, incluso con la sesión bloqueada.

### Hyprland 0.57 y Lua

Desde la 0.57, Hyprland solo lee `hyprland.lua` y se ignora `hyprland.conf`. Para comprobar la config antes de recargar:

```bash
Hyprland --verify-config -c ~/.config/hypr/hyprland.lua
```

El CI ejecuta la misma comprobación en cada pull request. Los stubs de la API están en `/usr/share/hypr/stubs/hl.meta.lua`. El autoarranque va en `hl.on("hyprland.start", ...)` y no se vuelve a ejecutar con `hyprctl reload`.

## Flujo de trabajo

El mismo flujo que en mis otros repos: **`dev` es para probar y `main` es lo publicado.**

1. Cada cambio empieza como una [issue](../../issues) con una propuesta y criterios de aceptación.
2. Una rama desde `dev` (`feat/…`, `fix/…`, `docs/…`, `ci/…`) y una pull request a `dev`. Conventional Commits y squash merge.
3. El workflow **Check configs** renderiza el repo con chezmoi en un home vacío y lo valida: `Hyprland --verify-config`, sintaxis Lua, shellcheck y JSON. `dev` y `main` solo aceptan cambios con el check en verde.
4. Una vez probado en la máquina real, `main` avanza hasta `dev` con fast-forward.

```bash
chezmoi cd
git switch dev && git pull
git switch -c feat/mi-cambio

# Editar, o traer cambios hechos directamente en ~
chezmoi re-add
chezmoi diff && chezmoi apply      # probar en esta máquina

git commit -am "feat: ..." && git push -u origin feat/mi-cambio
gh pr create --base dev            # "Closes #N" en la descripción

# Publicar (después de fusionar la PR en dev)
git switch main && git pull && git merge --ff-only dev && git push
git switch dev && git pull
```

Para añadir un archivo nuevo: `chezmoi add ~/.config/algo/config.toml`.

## Nunca va al repo 🔒

Credenciales y estado local. **Nunca** `chezmoi add` sobre:

- `~/.codex/auth.json`, `~/.codex/config.toml`, `~/.codex/*.sqlite*`
- `~/.claude.json`, `~/.claude/.credentials.json`, historiales y sesiones
- `~/.config/gh/`, perfiles del navegador, Slack
- `node_modules/`, logs, cachés
- Imágenes sin licencia para redistribuirlas (como el wallpaper)

Si algún día hace falta una config con secretos, se usa una plantilla de chezmoi que lea el secreto de un gestor (1Password, Bitwarden, `pass`), nunca el secreto en texto plano.

---

## Otras máquinas

El escritorio necesita Arch Linux, pero la config de la shell y de Neovim funciona en cualquier Linux o macOS:

```bash
brew install chezmoi gh neovim     # o el gestor de paquetes de tu distro
gh auth login
chezmoi init kats76
chezmoi diff                       # revisar qué cambiaría
chezmoi apply ~/.config/nvim ~/.zshrc
```

`chezmoi apply` con rutas solo aplica esos ficheros, así la config de Hyprland no llega a una máquina que no la usa. En Windows, usa WSL2 (`wsl --install`) y sigue los mismos pasos dentro.

## Licencia

[MIT](LICENSE)
