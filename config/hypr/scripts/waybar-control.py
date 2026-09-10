#!/usr/bin/env python3
"""Top-edge reveal for Waybar on Hyprland, using standard-library IPC.

SIGUSR1 explicitly shows Waybar; SIGUSR2 explicitly hides it. Use this helper's
reload command instead of sending SIGUSR2 to reload. No cursor positions are saved.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import select
import shutil
import signal
import socket
import subprocess
import sys
import time


def config_home():
    return Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config')


def state_home():
    return Path(os.environ.get('XDG_STATE_HOME') or Path.home() / '.local/state')


def read_jsonc(path):
    data = path.read_text()
    data = re.sub(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*[\s\S]*?\*/',
                  lambda m: m[0] if m[0].startswith('"') else '\n' * m[0].count('\n'), data)
    data = re.sub(r'"(?:\\.|[^"\\])*"|,\s*(?=[}\]])',
                  lambda m: m[0] if m[0].startswith('"') else '', data)
    return json.loads(data)


def session_paths():
    signature = os.environ.get('HYPRLAND_INSTANCE_SIGNATURE', '')
    runtime = os.environ.get('XDG_RUNTIME_DIR', '')
    if not signature or not runtime:
        raise RuntimeError('Run this command from your Hyprland session.')
    ipc = Path(runtime) / 'hypr' / signature / '.socket.sock'
    token = hashlib.sha256(signature.encode()).hexdigest()[:12]
    folder = Path(runtime) / ('midnight-waybar-' + token)
    folder.mkdir(mode=0o700, exist_ok=True)
    return ipc, folder


def hypr_query(ipc, command):
    # Hyprland handles this socket synchronously: connect, write immediately,
    # read the reply, then close. Never hold an idle compositor connection open.
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(0.4)
        connection.connect(str(ipc))
        connection.sendall(('j/' + command).encode())
        response = bytearray()
        while True:
            chunk = connection.recv(65536)
            if not chunk:
                break
            response.extend(chunk)
            if len(response) > 2_000_000:
                raise ValueError('Unexpectedly large compositor reply.')
    return json.loads(response)


def monitor_rect(monitor):
    scale = float(monitor.get('scale', 1))
    if scale <= 0:
        raise ValueError('Invalid monitor scale.')
    width, height = float(monitor['width']), float(monitor['height'])
    if int(monitor.get('transform', 0)) % 2:
        width, height = height, width
    return float(monitor['x']), float(monitor['y']), width / scale, height / scale


class Visibility:
    def __init__(self, now, options):
        self.visible = True
        self.pinned = False
        self.preview_until = now + 3.0
        self.away_since = None
        self.edge_since = None
        self.hide_delay = float(options.get('hide-delay', 1.2))
        self.reveal_delay = float(options.get('reveal-delay', 0.15))
        self.edge = float(options.get('edge-pixels', 3))
        self.band = float(options.get('bar-height', 56)) + float(options.get('margin-top', 8)) + 8

    def decide(self, cursor, monitors, now):
        if self.pinned or now < self.preview_until:
            self.visible = True
            self.away_since = None
            return True
        edge, over_bar = False, False
        for monitor in monitors:
            if monitor.get('disabled') or monitor.get('dpmsStatus') is False:
                continue
            x, y, width, height = monitor_rect(monitor)
            px, py = float(cursor['x']), float(cursor['y'])
            if x <= px < x + width and y <= py < y + height:
                edge = py <= y + self.edge
                over_bar = py <= y + self.band
                break
        if self.visible:
            if over_bar:
                self.away_since = None
            else:
                if self.away_since is None:
                    self.away_since = now
                if now - self.away_since >= self.hide_delay:
                    self.visible = False
                    self.edge_since = None
        elif edge:
            if self.edge_since is None:
                self.edge_since = now
            if now - self.edge_since >= self.reveal_delay:
                self.visible = True
                self.away_since = None
        else:
            self.edge_since = None
        return self.visible


def waybar_pids():
    result = subprocess.run(['pgrep', '-u', str(os.getuid()), '-x', 'waybar'],
                            capture_output=True, text=True, timeout=2)
    signature = os.environ.get('HYPRLAND_INSTANCE_SIGNATURE', '')
    display = os.environ.get('WAYLAND_DISPLAY', '')
    matches = []
    for raw in result.stdout.split():
        try:
            pid = int(raw)
            entries = (Path('/proc') / raw / 'environ').read_bytes().split(b'\0')
            environment = dict(item.split(b'=', 1) for item in entries if b'=' in item)
            same_session = signature and environment.get(b'HYPRLAND_INSTANCE_SIGNATURE') == signature.encode()
            same_display = display and environment.get(b'WAYLAND_DISPLAY') == display.encode()
            if same_session or same_display:
                matches.append(pid)
        except (OSError, ValueError):
            continue
    return matches


def set_visible(pids, visible):
    for pid in pids:
        try:
            process = Path('/proc') / str(pid)
            if process.stat().st_uid != os.getuid() or (process / 'comm').read_text().strip() != 'waybar':
                continue
            status = (process / 'status').read_text()
            caught = re.search(r'^SigCgt:\s*([0-9a-fA-F]+)', status, re.M)
            required = (1 << (signal.SIGUSR1 - 1)) | (1 << (signal.SIGUSR2 - 1))
            # A new Waybar process must install its handlers before signals arrive.
            if not caught or int(caught[1], 16) & required != required:
                continue
            os.kill(pid, signal.SIGUSR1 if visible else signal.SIGUSR2)
        except (OSError, ValueError):
            pass


def request(command):
    _, folder = session_paths()
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(3)
        connection.connect(str(folder / 'control.sock'))
        connection.sendall((command + '\n').encode())
        return connection.recv(4096).decode().strip()


def read_options():
    path = config_home() / 'waybar/autohide.json'
    options = json.loads(path.read_text()) if path.exists() else {}
    for key, default, low, high in (
        ('hide-delay', 1.2, 0.1, 30), ('reveal-delay', 0.15, 0, 3),
        ('edge-pixels', 3, 1, 16), ('bar-height', 56, 20, 200),
        ('margin-top', 8, 0, 100), ('poll-interval', 0.1, 0.05, 1),
    ):
        value = float(options.get(key, default))
        if not low <= value <= high:
            raise ValueError(f'{key} must be between {low} and {high}.')
        options[key] = value
    return options


def daemon():
    ipc, folder = session_paths()
    if not ipc.exists():
        raise RuntimeError('The Hyprland IPC socket is not available.')
    options = read_options()
    with (folder / 'daemon.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        address = folder / 'control.sock'
        address.unlink(missing_ok=True)
        running, paused = True, False
        def finish(*_):
            nonlocal running
            running = False
        signal.signal(signal.SIGTERM, finish)
        signal.signal(signal.SIGINT, finish)
        state = Visibility(time.monotonic(), options)
        monitors, pids = [], []
        next_monitors = next_processes = next_refresh = 0
        last_sent = None
        failures = 0
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
            server.bind(str(address))
            os.chmod(address, 0o600)
            server.listen(8)
            try:
                while running and ipc.exists():
                    ready, _, _ = select.select([server], [], [], options['poll-interval'])
                    if ready:
                        connection, _ = server.accept()
                        with connection:
                            connection.settimeout(1)
                            command = connection.recv(64).decode().strip()
                            now = time.monotonic()
                            if command == 'toggle-pin':
                                state.pinned = not state.pinned
                                state.preview_until = now + 1
                            elif command == 'pin':
                                state.pinned = True
                            elif command == 'auto':
                                state.pinned = False
                                state.preview_until = now + 1
                            elif command == 'peek':
                                state.preview_until = now + 4
                            elif command == 'pause':
                                paused = True
                            elif command == 'resume':
                                # Reload timing preferences without losing a pin.
                                options = read_options()
                                pinned = state.pinned
                                state = Visibility(now, options)
                                state.pinned = pinned
                                paused = False
                            elif command == 'stop':
                                running = False
                            elif command != 'status':
                                connection.sendall(b'Unknown command')
                                continue
                            last_sent = None
                            next_processes = next_refresh = 0
                            connection.sendall(('pinned' if state.pinned else 'auto').encode())
                    if paused or not running:
                        continue
                    now = time.monotonic()
                    if now >= next_processes:
                        pids = waybar_pids()
                        next_processes = now + 1
                    try:
                        if now >= next_monitors:
                            monitors = hypr_query(ipc, 'monitors')
                            next_monitors = now + 2
                        cursor = hypr_query(ipc, 'cursorpos')
                        visible = state.decide(cursor, monitors, now)
                        failures = 0
                    except (OSError, ValueError, TypeError, KeyError):
                        # A temporary IPC failure must not strand the user without a bar.
                        visible = True
                        state.visible = True
                        failures += 1
                        if failures == 1:
                            print('Compositor query failed; keeping Waybar visible.', flush=True)
                        if failures > 10:
                            set_visible(pids, True)
                            break
                    identity = (tuple(pids), visible)
                    if identity != last_sent or now >= next_refresh:
                        set_visible(pids, visible)
                        last_sent = identity
                        next_refresh = now + 1
            finally:
                # Exiting or crashing leaves the bar available.
                set_visible(pids, True)
                address.unlink(missing_ok=True)


def ensure():
    try:
        return request('status')
    except OSError:
        pass
    log_dir = state_home() / 'midnight-glass/logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    with (log_dir / 'waybar-autohide.log').open('ab') as log:
        child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), 'daemon'],
                                 stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
    for _ in range(30):
        try:
            return request('status')
        except OSError:
            if child.poll() is not None:
                raise RuntimeError(f'Auto-hide did not start; see {log_dir / "waybar-autohide.log"}')
            time.sleep(0.05)
    raise RuntimeError('Auto-hide did not answer in time.')


def restart_waybar(start_autohide=True):
    try:
        request('pause')
    except OSError:
        pass
    try:
        pids = waybar_pids()
        service = subprocess.run(['systemctl', '--user', 'show', 'waybar.service', '-p', 'MainPID', '--value'],
                                 capture_output=True, text=True, timeout=5)
        if service.returncode == 0 and service.stdout.strip().isdigit() and int(service.stdout) in pids:
            subprocess.run(['systemctl', '--user', 'restart', 'waybar.service'], check=True, timeout=10)
        else:
            for pid in pids:
                try:
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            deadline = time.monotonic() + 3
            while set(waybar_pids()).intersection(pids):
                if time.monotonic() >= deadline:
                    raise RuntimeError('The previous Waybar has not exited; a duplicate was not started.')
                time.sleep(0.1)
            # A supervisor may have already restarted it after SIGTERM.
            if not waybar_pids():
                log_dir = state_home() / 'midnight-glass/logs'
                log_dir.mkdir(parents=True, exist_ok=True)
                with (log_dir / 'waybar.log').open('ab') as log:
                    child = subprocess.Popen(['waybar', '-c', str(config_home() / 'waybar/config.jsonc'),
                                              '-s', str(config_home() / 'waybar/style.css')],
                                             stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
                time.sleep(0.4)
                if child.poll() is not None:
                    raise RuntimeError(f'Waybar did not stay running; see {log_dir / "waybar.log"}')
    finally:
        try:
            request('resume')
        except OSError:
            pass
    if start_autohide:
        ensure()
        print('Waybar reloaded. Top edge reveals it; Super + B pins it.')
    else:
        print('Waybar restarted.')


def main():
    command = sys.argv[1] if len(sys.argv) == 2 else 'status'
    if command == 'daemon':
        daemon()
    elif command == 'ensure':
        ensure()
    elif command == 'reload':
        restart_waybar()
    elif command in {'status', 'stop'}:
        print(request(command))
    elif command in {'pin', 'auto', 'peek', 'toggle-pin'}:
        ensure()
        result = request(command)
        print(result)
        if command != 'peek' and shutil.which('notify-send'):
            subprocess.run(['notify-send', '-a', 'Midnight', '-t', '1600', 'Waybar',
                            'Pinned open · Super + B returns to auto-hide' if result == 'pinned'
                            else 'Auto-hide on · move to the top edge to reveal'], check=False)
    else:
        raise RuntimeError('Use ensure, reload, status, stop, pin, auto, peek, or toggle-pin.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, subprocess.SubprocessError) as error:
        print(error, file=sys.stderr)
        sys.exit(1)
