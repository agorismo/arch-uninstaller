# Arch Uninstaller

a clean, lightweight GTK 4 graphical interface written in Python 3 to list and remove explicitly installed desktop applications on Arch Linux.

the application matches system `.desktop` shortcuts with `pacman` database entries (using `pacman -Qet` and `pacman -Qo`). packages are uninstalled using `pacman -Rs` to ensure unused dependencies are cleaned up.

## dependencies

install the required packages on Arch Linux:

```bash
sudo pacman -S python-gobject gtk4 polkit polkit-gnome
```

*note: a graphical Polkit agent (such as `polkit-gnome` or `polkit-kde-agent`) must be running in your desktop session for privilege elevation.*

## usage

run directly:

```bash
python3 archpanel_uninstaller.py
```

### installation

to install system-wide:

```bash
sudo install -Dm644 arch-uninstaller.desktop /usr/share/applications/arch-uninstaller.desktop
```

## troubleshooting

### `polkit-gnome` warning about `~/.face`
if you run the application via terminal and see a warning like:
`Couldn't open user icon: Failure opening file '/home/user/.face'`

this is a cosmetic warning from `polkit-gnome` indicating that no user avatar image was found. It does not affect functionality. uou can suppress it by creating a dummy file:

```bash
touch ~/.face && chmod 644 ~/.face
```

## license

MIT
