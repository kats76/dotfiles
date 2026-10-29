# dotfiles

[![Check configs](https://github.com/kats76/dotfiles/actions/workflows/check.yml/badge.svg)](https://github.com/kats76/dotfiles/actions/workflows/check.yml)

[Leer en español](README.es.md)

My personal setup, managed with [chezmoi](https://www.chezmoi.io/): one repo, the same configuration on any machine with one command.

- **Desktop:** Arch Linux + Hyprland with one palette and one font everywhere: the window manager, the bar, the launcher, the terminal, the logout menu and the login screen.
- **Editor:** Neovim (LazyVim).

## What's inside

| Repo path | Target on the machine | What it is |
| --- | --- | --- |
| `dot_config/hypr/` | `~/.config/hypr/` | Hyprland 0.57+ in Lua, wallpaper and the lid script |
| `dot_config/waybar/` | `~/.config/waybar/` | Top bar |
| `dot_config/sddm-silent/` | `~/.config/sddm-silent/` | Login screen (SilentSDDM theme) and its installer |
| `dot_config/kitty`, `wofi`, `wlogout`, `cava` | `~/.config/…` | Terminal, app launcher, logout menu, audio visualizer |
| `dot_config/fontconfig`, `gtk-3.0`, `gtk-4.0`, `qt6ct` | `~/.config/…` | Make GTK and Qt apps follow the same look |
| `dot_local/share/color-schemes/` | `~/.local/share/color-schemes/` | Qt color scheme with the palette |
| `dot_zshrc`, `dot_bashrc` | `~/.zshrc`, `~/.bashrc` | Shell |
| `dot_config/nvim/` | `~/.config/nvim/` | Neovim (LazyVim) |

> chezmoi naming: `dot_` = `.`, `private_` = no permissions for others, `executable_` = executable bit, `.tmpl` = template.

## Palette

| Name | Color | Used for |
| --- | --- | --- |
| bg | `#1e1e2e` | Backgrounds |
| fg | `#cdd6f4` | Text |
| accent | `#8a63c7` | Active border, selection, focused buttons |
| accent2 | `#6f9f98` | Second accent, hover |
| red | `#c44532` | Urgent, errors |
| gray | `#a08f95` | Inactive elements |
| light | `#c7ced6` | Secondary text |

Font: **JetBrainsMono Nerd Font**, with Noto Color Emoji and Source Han Sans JP (Japanese) as fallbacks. Without a Japanese font, Japanese text shows as empty squares in the terminal, the browser and the window title in waybar.

## Install the desktop (Arch Linux)

Do a full `sudo pacman -Syu` first: installing a Qt package on a partially upgraded system breaks SDDM.

```bash
sudo pacman -S chezmoi hyprland hyprpaper waybar kitty wofi cava brightnessctl playerctl \
  ttf-jetbrains-mono-nerd noto-fonts-emoji adobe-source-han-sans-jp-fonts qt6ct thunar starship \
  zsh-autosuggestions sddm qt6-virtualkeyboard
yay -S wlogout sddm-silent-theme python-pywal
chezmoi init --apply kats76
```

`chezmoi diff` shows what would change before you apply. Home paths are templates (`{{ .chezmoi.homeDir }}`), so another username works.

### Wallpaper

The wallpaper is not in this repo. Download it from [wallhaven 9oo8k1](https://wallhaven.cc/w/9oo8k1) to `~/Img/wallhaven-9oo8k1.jpg`, or point `hyprpaper.conf`, `hyprland.lua` and `sddm-silent/install.sh` to your own.

### Login screen

SDDM runs as its own user, so its theme cannot live in your home. `install.sh` copies it into place with `sudo`:

```bash
~/.config/sddm-silent/install.sh
cd /usr/share/sddm/themes/silent && ./test.sh   # preview without logging out
```

Run it again after updating `sddm-silent-theme` or changing the wallpaper. `Xsetup` keeps the login on a single screen: with the lid closed it ignores the laptop panel and picks the highest resolution monitor.

### Keybindings

`Super` is the main modifier.

| Keys | Action |
| --- | --- |
| `Super + Return` | Terminal (kitty) |
| `Super + Space` | App launcher (wofi) |
| `Super + F` | Firefox |
| `Super + E` | File manager (Thunar) |
| `Super + Backspace` | Logout menu (wlogout) |
| `Super + Q` | Close window |
| `Super + V` | Toggle floating |
| `Super + H/J/K/L` | Move focus |
| `Super + Shift + H/J/K/L` | Move window |
| `Super + Ctrl + H/J/K/L` | Resize window |
| `Super + Tab`, then `Super + H/J/K/L` | Swap windows (`Esc` to leave) |
| `Super + 1…0` | Go to workspace |
| `Super + Shift + 1…0` | Send window to workspace |
| `Super + S` / `Super + Shift + S` | Scratchpad: show / send window |
| `Super + M` | Exit Hyprland |

Media, volume and brightness keys work too, even on the lock screen.

### Hyprland 0.57 and Lua

Since 0.57, Hyprland only reads `hyprland.lua`, and `hyprland.conf` is ignored. To check the config before reloading:

```bash
Hyprland --verify-config -c ~/.config/hypr/hyprland.lua
```

CI runs the same check on every pull request. API stubs live in `/usr/share/hypr/stubs/hl.meta.lua`. Autostart goes in `hl.on("hyprland.start", ...)` and does not run again on `hyprctl reload`.

## Workflow

Same flow as my other repos: **`dev` is for testing, `main` is what gets published.**

1. Every change starts as an [issue](../../issues) with a proposal and acceptance criteria.
2. A branch off `dev` (`feat/…`, `fix/…`, `docs/…`, `ci/…`) and a pull request to `dev`. Conventional Commits, squash merge.
3. The **Check configs** workflow renders the repo with chezmoi into an empty home and validates it: `Hyprland --verify-config`, Lua syntax, shellcheck and JSON. `dev` and `main` only accept changes with the check green.
4. Once tested on the real machine, `main` is fast-forwarded to `dev`.

```bash
chezmoi cd
git switch dev && git pull
git switch -c feat/my-change

# Edit, or bring in changes made directly in ~
chezmoi re-add
chezmoi diff && chezmoi apply      # test on this machine

git commit -am "feat: ..." && git push -u origin feat/my-change
gh pr create --base dev            # "Closes #N" in the description

# Publish (after the PR is merged into dev)
git switch main && git pull && git merge --ff-only dev && git push
git switch dev && git pull
```

Add a new file with `chezmoi add ~/.config/something/config.toml`.

## Never in the repo 🔒

Credentials and local state. **Never** `chezmoi add` on:

- `~/.codex/auth.json`, `~/.codex/config.toml`, `~/.codex/*.sqlite*`
- `~/.claude.json`, `~/.claude/.credentials.json`, histories and sessions
- `~/.config/gh/`, browser profiles, Slack
- `node_modules/`, logs, caches
- Images without a license to redistribute them (like the wallpaper)

If a config ever needs secrets, it uses a chezmoi template that reads the secret from a password manager (1Password, Bitwarden, `pass`), never the secret in plain text.

---

## Other machines

The desktop needs Arch Linux, but the shell and Neovim configs work on any Linux or macOS machine:

```bash
brew install chezmoi gh neovim     # or your distro's package manager
gh auth login
chezmoi init kats76
chezmoi diff                       # review what would change
chezmoi apply ~/.config/nvim ~/.zshrc
```

`chezmoi apply` with paths only applies those files, so the Hyprland configs stay out of a machine that does not use them. On Windows, use WSL2 (`wsl --install`) and follow the same steps inside it.

## License

[MIT](LICENSE)
