#!/usr/bin/env python3
"""Offline behaviour tests for Waybar auto-hide and the focused updater."""
import importlib.util
import errno
import json
import os
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bar = load('bar_test', ROOT / 'config/hypr/scripts/waybar-control.py')
update = load('bar_update_test', ROOT / 'update-waybar.py')
MONITORS = [{'x': 0, 'y': 0, 'width': 2560, 'height': 1600, 'scale': 1, 'transform': 0}]
FAR = {'x': 500, 'y': 500}
EDGE = {'x': 500, 'y': 1}


class WaybarTests(unittest.TestCase):
    def test_hide_waits_then_top_edge_reveals(self):
        state = bar.Visibility(0, {})
        self.assertTrue(state.decide(FAR, MONITORS, 1))  # Initial preview.
        self.assertTrue(state.decide(FAR, MONITORS, 4))
        self.assertTrue(state.decide(FAR, MONITORS, 5.1))
        self.assertFalse(state.decide(FAR, MONITORS, 5.3))
        self.assertFalse(state.decide(EDGE, MONITORS, 6))
        self.assertTrue(state.decide(EDGE, MONITORS, 6.2))
        self.assertTrue(state.decide({'x': 500, 'y': 60}, MONITORS, 20))
        self.assertTrue(state.decide(FAR, MONITORS, 21))
        self.assertFalse(state.decide(FAR, MONITORS, 22.3))

    def test_crossing_edge_briefly_does_not_reveal(self):
        state = bar.Visibility(0, {})
        state.visible = False
        state.preview_until = 0
        self.assertFalse(state.decide(EDGE, MONITORS, 1))
        self.assertFalse(state.decide(FAR, MONITORS, 1.1))
        self.assertFalse(state.decide(EDGE, MONITORS, 1.2))
        self.assertFalse(state.decide(EDGE, MONITORS, 1.3))
        self.assertTrue(state.decide(EDGE, MONITORS, 1.4))

    def test_pin_and_peek_override_auto_hide(self):
        state = bar.Visibility(0, {})
        state.pinned = True
        self.assertTrue(state.decide(FAR, MONITORS, 100))
        state.pinned = False
        state.preview_until = 104
        self.assertTrue(state.decide(FAR, MONITORS, 103))
        self.assertTrue(state.decide(FAR, MONITORS, 105))
        self.assertFalse(state.decide(FAR, MONITORS, 107))

    def test_scaled_rotated_monitor_above_left_of_primary(self):
        monitor = {'x': -720, 'y': -1280, 'width': 1920, 'height': 1080, 'scale': 1.5, 'transform': 1}
        self.assertEqual(bar.monitor_rect(monitor), (-720, -1280, 720, 1280))
        state = bar.Visibility(0, {})
        state.visible = False
        state.preview_until = 0
        cursor = {'x': -100, 'y': -1279}
        self.assertFalse(state.decide(cursor, [*MONITORS, monitor], 10))
        self.assertTrue(state.decide(cursor, [*MONITORS, monitor], 10.2))

    def test_jsonc_preserves_urls_and_quoted_comment_characters(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'config.jsonc'
            path.write_text('''{
              // Personal note
              "url": "https://example.test/a//b",
              "literal": "/* keep */ ,}", /* comment */
              "items": [1, 2,],
            }''')
            self.assertEqual(bar.read_jsonc(path), {'url': 'https://example.test/a//b', 'literal': '/* keep */ ,}', 'items': [1, 2]})

    def test_hyprland_socket_request_format_and_connection_close(self):
        with tempfile.TemporaryDirectory() as folder:
            address = Path(folder) / 'ipc.sock'
            received = []
            try:
                server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            except OSError as error:
                if error.errno in {errno.EPERM, errno.EACCES}:
                    self.skipTest('Unix sockets are unavailable in this build environment.')
                raise
            with server:
                server.bind(str(address))
                server.listen(1)
                def answer():
                    connection, _ = server.accept()
                    with connection:
                        received.append(connection.recv(1024))
                        connection.sendall(b'{"x": 123, "y": -12}')
                worker = threading.Thread(target=answer, daemon=True)
                worker.start()
                self.assertEqual(bar.hypr_query(address, 'cursorpos'), {'x': 123, 'y': -12})
                worker.join(timeout=1)
                self.assertFalse(worker.is_alive())
            self.assertEqual(received, [b'j/cursorpos'])

    def test_update_preserves_modules_personal_overrides_and_swaync(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'config'
            shutil.copytree(ROOT / 'config', target)
            main = target / 'hypr/hyprland.lua'
            main.write_text(main.read_text().replace('require("conf.waybar")\n', ''))
            actions = target / 'hypr/scripts/midnight.py'
            actions.write_text(actions.read_text().replace(update.NEW_RELOAD, update.OLD_RELOAD))
            config = target / 'waybar/config.jsonc'
            values = json.loads(config.read_text())
            values['custom/my-widget'] = {'exec': 'printf custom'}
            values['modules-right'].append('custom/my-widget')
            values['mode'] = 'dock'
            config.write_text(json.dumps(values))
            untouched = {name: (target / name).read_bytes() for name in ('hypr/local.lua', 'swaync/config.json', 'swaync/style.css')}
            changes = update.merge_files(target)
            self.assertTrue(all(name not in changes for name in untouched))
            updated = json.loads(changes['waybar/config.jsonc'])
            self.assertEqual(updated['custom/my-widget'], values['custom/my-widget'])
            self.assertIn('custom/my-widget', updated['modules-right'])
            self.assertNotIn('mode', updated)
            self.assertFalse(updated['exclusive'])
            self.assertLess(changes['hypr/hyprland.lua'].index('require("conf.waybar")'), changes['hypr/hyprland.lua'].index('require("local")'))
            for name, text in changes.items():
                (target / name).write_text(text)
            self.assertEqual(update.merge_files(target), changes)
            self.assertEqual({name: (target / name).read_bytes() for name in untouched}, untouched)


if __name__ == '__main__':
    unittest.main(verbosity=2)
