# TuneIn Favorites for myMPD

Sign in to TuneIn locally and play a favorite live station from the
myMPD Scripts menu. The bridge refreshes favorites when you open the
picker and resolves the stream when you select a station.

## Docker Compose

Create the config once, then fill in your TuneIn username and password
in `tunein.cfg`. Compose mounts the file read-only.

```sh
test -e tunein.cfg || install -m 600 tunein.cfg.example tunein.cfg
export TUNEIN_UID="$(id -u)" TUNEIN_GID="$(id -g)"
```

If myMPD uses host networking, start the bridge on loopback.

```sh
docker compose -f compose.yaml -f compose.host.yaml up --build -d
```

If myMPD uses a private Docker network, start the bridge on that network
and set the Lua script's `service` URL to `http://tunein:18766`.

```sh
export MPD_NETWORK=your-existing-mpd-network
docker compose up --build -d
```

Set `TUNEIN_CONFIG` to an absolute path to use a different config file.
The bridge signs in on startup over HTTPS. Restart the container after
changing the credentials.

## Dockhand

For a host-networked Dockhand stack, copy the contents of `dockhand/`
into the stack directory alongside `Dockerfile`, `.dockerignore`,
`bridge.py`, `vendor/`, `install-picker.py`, and `tunein.lua`. The Dockhand Compose file
expects the private config at `data/tunein.cfg` and runs as UID and GID
1000. Build the stack in Dockhand. Run `make` in the stack directory to
list its management commands.

## Run without Docker

With Python 3.10 or later, run `python3 bridge.py --config tunein.cfg`
in the same network namespace as myMPD. Omit `--config` to sign in
interactively.

## Install the picker

Enable Lua scripting in myMPD, then install the picker.

```sh
python3 install-picker.py --mympd http://127.0.0.1:8081
```

For a shared Docker network, pass `--service http://tunein:18766`. For
a PIN-protected instance, set `MYMPD_SESSION` to a valid session token.
Use `--partition` for a different partition or `--replace` to update an
existing picker. You can also paste `tunein.lua` into the myMPD script
editor as **TuneIn Favorites** with menu order 2.

Open **TuneIn Favorites** from the Scripts menu and select a station.
MPD plays the resolved stream directly.

On the loopback deployment, choose **Find and save a station** to search
TuneIn and add a station to the account, or **Remove selected station**
to remove a favorite after confirming. The bridge declines removal when
the same station is saved in several folders. Account changes require
myMPD to reach the bridge through loopback.

Choose **Browse by location** to navigate TuneIn's region directory and
save a station.

## Now Playing display

Copy `tunein-display.js` to myMPD's `pics/` directory and append
`tunein-loader.js` to `config/custom_js` once. Restart myMPD and reload
the web app. Select the station again from the picker to add its display
metadata to the queue entry.

While a TuneIn station is selected, the compact player's **Open TuneIn
station picker** button opens the same popup as the Home launcher.

The Dockhand Compose file mounts myMPD's `pics/tunein-stations/` folder
for artwork. Create that folder before starting the stack and make it
writable by the bridge user. Outside Dockhand, pass `--artwork-dir` with
the corresponding directory to cache station logos.

## Contributing

- **Bug reports** can go in [Issues](https://github.com/bonelifer/mympd-tunein/issues).
- **Questions and feature ideas** belong in [Discussions](https://github.com/bonelifer/mympd-tunein/discussions).
- Pull requests are welcome for bug fixes and discussed features.

## Acknowledgments

The vendored [Kodi TuneIn client](https://github.com/joaconigro/plugin.audio.tuneinradio/tree/c12c43e4244563341d98ca020490067b8527b142/resources/lib)
is from commit `c12c43e`. Its source headers and upstream license file are
included. The myMPD picker follows the approach used by
[mympd-pandora](https://github.com/bonelifer/mympd-pandora).

- Code and documentation assisted by [Codex](https://openai.com/codex/).

## License

GNU General Public License v3.0. See [LICENSE](LICENSE).
