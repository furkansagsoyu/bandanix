<div align="center">

```
 ____      _     _   _  ____      _     _   _  ___ __  __
| __ )    / \   | \ | ||  _ \    / \   | \ | ||_ _|\ \/ /
|  _ \   / _ \  |  \| || | | |  / _ \  |  \| | | |  \  /
| |_) | / ___ \ | |\  || |_| | / ___ \ | |\  | | |  /  \
|____/ /_/   \_\|_| \_||____/ /_/   \_\|_| \_||___|/_/\_\
```

**A desktop kit for Linux Mint, by Bandana.**
Small tools that look like one family. Install them all, or just the ones you like.

</div>

## Components

| Component | What it does |
|---|---|
| [**Sound Island**](sound-island/) | A floating "now playing" pill for Spotify and other players. Hover to open a mini player with controls and synced lyrics. |

More components are on the way.

## Install

```bash
git clone https://github.com/furkansagsoyu/bandanix.git
cd bandanix
./install.sh
```

The installer shows a menu: pick numbers (`1 2`) or `a` for everything.
You can also skip the menu:

```bash
./install.sh --all            # everything
./install.sh sound-island     # just one component
```

Everything is installed for your user only (`~/.local`), each component in its own Python environment.
Missing system packages are installed with `apt` (you'll be asked for your password).

## Shared theme

All components read one file: `~/.config/bandanix/theme.toml`

```toml
[colors]
accent = "#C8102E"        # bandana red

[fonts]
ui = ""                   # empty = system default
```

Change it once and every component follows. Reinstalling never overwrites your edits.

## Uninstall

```bash
./uninstall.sh                  # menu
./uninstall.sh --all            # remove everything, keep the theme file
./uninstall.sh --all --purge    # remove everything, including the theme file
```

## Tested on

Linux Mint 22 (Cinnamon, X11). Other Debian/Ubuntu-based desktops with X11 should work too.

## Notes

Built by Furkan Sağsoyu (Bandana) with help from an AI assistant (Claude).
Not affiliated with Spotify, Apple or Linux Mint.

## License

MIT
