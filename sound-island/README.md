# Sound Island 🏝️

*Part of [Bandanix](../README.md).*

A floating "now playing" island for Linux desktops, inspired by Apple's Dynamic Island.
It sits as a slim pill at the top of your screen and grows into a mini player when you hover over it.

Works with **Spotify** and any other player that speaks [MPRIS](https://specifications.freedesktop.org/mpris-spec/latest/)
(VLC, Firefox, Brave, Chromium, mpv, Rhythmbox…). No Spotify account, API key or Premium needed: everything is read locally.

## Features

- **Pill mode:** spinning album cover, song title and artist, a thin progress line and animated bars
- **Player mode (hover):** large cover, play/pause, previous/next, click-to-seek progress bar
- **Synced lyrics:** the current lyric line, from the free [LRCLIB](https://lrclib.net) API
- **Adaptive colour:** the accent colour is picked from the album cover (or the Bandanix accent)
- **New song toast:** the island opens for a moment when the track changes
- Hides itself when nothing is playing
- Right-click → Quit

## Install

From the Bandanix folder:

```bash
./install.sh sound-island
```

This adds **Sound Island** to your app menu, a `sound-island` command, and (if you want) autostart on login.

Use another player with `--player` (see `playerctl -l` for names):

```bash
sound-island --player vlc
```

## Settings

In `~/.config/bandanix/theme.toml`:

```toml
[sound-island]
follow_cover = true       # accent colour from the album cover
hide_when_idle = true     # hide when nothing is playing
```

## Run from source (development)

```bash
sudo apt install playerctl python3-venv libxcb-cursor0
cd sound-island
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover tests
python -m sound_island
```

## Roadmap

- [ ] Real audio-reactive bars (PipeWire monitor / cava); the bars are simulated for now
- [ ] More settings: position, size, pill/lyrics options
- [ ] Cinnamon panel applet

Lyrics come from LRCLIB, a community database.
