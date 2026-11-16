#!/usr/bin/env python3
"""Expose a signed-in TuneIn account's favorite live stations to myMPD."""

import argparse
import configparser
from concurrent.futures import ThreadPoolExecutor
from getpass import getpass
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import re
import socket
import sys
from tempfile import NamedTemporaryFile
from urllib.parse import parse_qs, urlsplit
from urllib.request import urlopen

from vendor.tunein_kodi.tunein import TuneIn


def playable_url(url: str) -> bool:
    """Accept HTTP audio candidates and reject TuneIn's error recordings."""
    target = urlsplit(url)
    return (
        target.scheme in {"http", "https"}
        and bool(target.hostname)
        and not (
            target.hostname == "cdn-cms.tunein.com"
            and target.path.lower().startswith("/service/audio/")
        )
    )


def resolve_stream(client: TuneIn, station_id: str) -> str | None:
    """Prefer a reachable audio stream over playlists and non-audio replies."""
    playlist = None
    for record in client.stream_candidates(station_id):
        url = record.get("url") or ""
        if not playable_url(url):
            continue
        try:
            with urlopen(url, timeout=4) as response:
                if not playable_url(response.url):
                    continue
                content_type = response.headers.get_content_type()
                if content_type in {
                    "audio/x-scpls", "audio/x-mpegurl", "audio/mpegurl",
                    "application/vnd.apple.mpegurl", "application/x-mpegurl",
                }:
                    playlist = playlist or response.url
                elif content_type.startswith("audio/"):
                    return response.url
        except (OSError, ValueError):
            continue
    return playlist


def supported_stations(
    client: TuneIn, stations: dict[str, dict[str, str]]
) -> dict[str, dict[str, str]]:
    """Remove stations whose TuneIn stream records contain no playable URL."""
    def supported(station_id):
        try:
            return any(
                playable_url(record.get("url") or "")
                for record in client.stream_candidates(station_id)
            )
        except (TuneIn.TuneInError, OSError, ValueError, KeyError, TypeError):
            # A failed lookup cannot establish that a station is unsupported.
            return True

    with ThreadPoolExecutor(max_workers=8) as pool:
        return {
            station_id: station
            for (station_id, station), keep in zip(
                stations.items(), pool.map(supported, stations)
            )
            if keep
        }


def station_info(entry: dict) -> dict[str, str]:
    """Preserve the station name and HTTPS artwork supplied by TuneIn."""
    station = {"id": entry["guide_id"], "name": entry["text"]}
    image = entry.get("image")
    if isinstance(image, str):
        try:
            url = urlsplit(image)
            if url.scheme in {"http", "https"} and url.hostname in {
                "cdn-profiles.tunein.com", "cdn-radiotime-logos.tunein.com"
            }:
                station["artUrl"] = url._replace(scheme="https").geturl()
        except ValueError:
            pass
    return station


def cache_artwork(station: dict[str, str], directory: Path | None) -> str:
    """Make a TuneIn station logo available to the local myMPD web server."""
    if directory is None or not station.get("artUrl"):
        return ""
    for extension in (".jpg", ".png"):
        cached = directory / (station["id"] + extension)
        if cached.is_file():
            return cached.name
    try:
        with urlopen(station["artUrl"], timeout=3) as response:
            image = response.read(2 * 1024 * 1024 + 1)
        if len(image) > 2 * 1024 * 1024:
            return ""
        if image.startswith(b"\x89PNG\r\n\x1a\n"):
            extension = ".png"
        elif image.startswith(b"\xff\xd8\xff") and image.endswith(b"\xff\xd9"):
            extension = ".jpg"
        else:
            return ""
        destination = directory / (station["id"] + extension)
        with NamedTemporaryFile(dir=directory, delete=False) as output:
            temporary = Path(output.name)
            try:
                output.write(image)
                output.close()
                temporary.chmod(0o644)
                os.replace(temporary, destination)
            finally:
                temporary.unlink(missing_ok=True)
        return destination.name
    except (OSError, ValueError):
        return ""


def station_entries(entries):
    """Yield station outlines, including inline groups."""
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        station_id = entry.get("guide_id") or ""
        name = entry.get("text")
        if re.fullmatch(r"s[0-9]+", station_id) and isinstance(name, str) and name:
            yield station_id, station_info(entry)
        yield from station_entries(entry.get("children") or [])


def favorite_stations(client: TuneIn, username: str):
    """Read favorite stations and record which folders contain each one."""
    stations = {}
    folders = {}
    seen_folders = set()
    pending = [(entry, None) for entry in reversed(client.browse_presets(username))]
    while pending:
        entry, folder = pending.pop()
        if not isinstance(entry, dict):
            continue
        station_id = entry.get("guide_id") or ""
        name = entry.get("text")
        children = entry.get("children") or []
        if re.fullmatch(r"s[0-9]+", station_id) and isinstance(name, str) and name:
            stations.setdefault(station_id, station_info(entry))
            folders.setdefault(station_id, set()).add(folder)
        elif re.fullmatch(r"f[0-9]+", station_id):
            if station_id in seen_folders:
                continue
            seen_folders.add(station_id)
            folder = station_id
            if not children:
                children = client.browse(id=station_id, username=username)
        pending.extend((child, folder) for child in reversed(children))
    return stations, folders


def scan_statuses(report: Path | None) -> dict[str, str]:
    """Read optional Last.fm scan labels without filtering TuneIn stations."""
    if report is None:
        return {}
    try:
        with report.open(encoding="utf-8") as source:
            entries = json.load(source)["stations"]
        return {
            row["id"]: row["result"] for row in entries
            if re.fullmatch(r"s[0-9]+", row["id"])
            and row["result"] in {"plain-title-candidate", "inconclusive"}
        }
    except (OSError, ValueError, KeyError, TypeError):
        return {}


class FavoritesHandler(BaseHTTPRequestHandler):
    """Serve favorite stations and resolve a selected station on demand."""

    def do_GET(self) -> None:
        """Return a station list or a playable URL as JSON."""
        server = self.server
        request = urlsplit(self.path)
        path = request.path
        station_id = path.removeprefix("/stations/")
        try:
            if path == "/stations":
                server.stations, _ = favorite_stations(
                    server.client, server.username
                )
                server.stations = supported_stations(server.client, server.stations)
                statuses = scan_statuses(server.scan_report)
                self.respond(200, [
                    {**item, "scrobbleStatus": statuses.get(item["id"], "")}
                    for item in server.stations.values()
                ])
            elif path == "/search":
                query = parse_qs(request.query).get("q", [""])[0].strip()
                if not 1 <= len(query) <= 100:
                    self.respond(400, {"error": "Enter a station name or call sign"})
                    return
                matches = dict(station_entries(server.client.search(query)))
                matches = supported_stations(
                    server.client, dict(list(matches.items())[:25])
                )
                self.respond(200, list(matches.values()))
            elif re.fullmatch(r"/locations/r[0-9]+", path):
                region = path.removeprefix("/locations/")
                entries = server.client.browse(id=region)
                locations = [
                    {"id": item["guide_id"], "name": item["text"]}
                    for item in entries
                    if re.fullmatch(r"r[0-9]+", item.get("guide_id") or "")
                    and item.get("text")
                ]
                stations = supported_stations(
                    server.client, dict(station_entries(entries))
                )
                self.respond(200, locations + list(stations.values()))
            elif path.startswith("/stations/") and station_id in server.stations:
                stream = resolve_stream(server.client, station_id)
                if stream:
                    station = server.stations[station_id]
                    self.respond(200, {
                        **station, "url": stream,
                        "artFile": cache_artwork(station, server.artwork_dir)
                    })
                else:
                    self.respond(502, {"error": "No HTTP audio stream available"})
            else:
                self.respond(404, {"error": "Unknown favorite station"})
        except (TuneIn.TuneInError, OSError, ValueError, KeyError, TypeError):
            self.respond(502, {"error": "TuneIn request failed"})

    def do_POST(self) -> None:
        """Add a station or remove an unambiguous favorite."""
        match = re.fullmatch(r"/favorites/(add|remove)/(s[0-9]+)", self.path)
        if not match:
            self.respond(404, {"error": "Unknown favorite action"})
            return
        if (self.client_address[0] != "127.0.0.1"
                or self.headers.get("Content-Type") != "application/json"
                or self.headers.get("Origin")):
            self.respond(403, {"error": "Favorite changes require local myMPD"})
            return
        action, station_id = match.groups()
        server = self.server
        try:
            _, folders = favorite_stations(server.client, server.username)
            credentials = {"username": server.username, "password": server.password}
            if action == "add":
                if station_id not in folders:
                    server.client.preset_add(id=station_id, **credentials)
            elif len(folders.get(station_id, ())) == 1:
                folder, = folders[station_id]
                server.client.preset_remove(
                    id=station_id, folderid=folder, **credentials
                )
            else:
                self.respond(409, {"error": "Station is missing or saved in several folders"})
                return
            server.stations, _ = favorite_stations(server.client, server.username)
            self.respond(200, {"ok": True})
        except (TuneIn.TuneInError, OSError, ValueError, KeyError, TypeError):
            self.respond(502, {"error": "TuneIn request failed. Refresh favorites before retrying."})

    def respond(self, status: int, payload: dict | list) -> None:
        """Send a JSON response."""
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    """Authenticate from a config file or terminal, then run the bridge."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-c", "--config", help="Path to the TuneIn INI file")
    parser.add_argument("-l", "--listen", default="127.0.0.1")
    parser.add_argument("--artwork-dir", type=Path)
    parser.add_argument("--scan-report", type=Path, help="Optional Last.fm TuneIn scan JSON")
    parser.add_argument("-p", "--port", type=int, default=18766)
    args = parser.parse_args()
    if args.config:
        config = configparser.ConfigParser(interpolation=None)
        try:
            with open(args.config, encoding="utf-8") as config_file:
                config.read_file(config_file)
            username = config["tunein"]["username"]
            password = config["tunein"]["password"]
        except (OSError, UnicodeError, configparser.Error, KeyError):
            parser.error("Read [tunein] username and password from --config failed.")
        finally:
            del config
    else:
        if not sys.stdin.isatty():
            parser.error("Use --config or run in an interactive terminal.")
        username = input("TuneIn username: ").strip()
        password = getpass("TuneIn password: ")
    socket.setdefaulttimeout(10)
    if not username or not password:
        parser.error("Enter both a username and a password.")
    client = TuneIn("RadioTime", formats="mp3,aac", https=True)
    try:
        client.account_auth(username, password)
    except TuneIn.TuneInError as error:
        print(f"TuneIn rejected login (status {error.status}).", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError):
        print("Could not verify the TuneIn login.", file=sys.stderr)
        return 1
    with HTTPServer((args.listen, args.port), FavoritesHandler) as server:
        server.client = client
        server.username = username
        server.password = password
        server.artwork_dir = args.artwork_dir
        server.scan_report = args.scan_report
        server.stations = {}
        print(f"TuneIn Favorites is listening on {server.server_address}.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
