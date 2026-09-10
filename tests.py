#!/usr/bin/env python3
"""Offline regression tests for the actions that can alter files or session state."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


installer = load("midnight_installer", ROOT / "install.py")
actions = load("midnight_actions", ROOT / "config/hypr/scripts/midnight.py")


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.kit = self.base / "kit"
        self.target = self.base / "config"
        self.backups = self.base / "backups"
        for root in (self.kit / "config", self.target):
            (root / "hypr").mkdir(parents=True)
        (self.kit / "config/hypr/hyprland.lua").write_text("new main")
        (self.kit / "config/hypr/helper").write_text("new helper")
        (self.kit / "config/hypr/local.lua").write_text("starter personal config")
        (self.target / "hypr/hyprland.lua").write_text("old main")
        (self.target / "hypr/hyprland.lua").chmod(0o600)
        (self.target / "hypr/local.lua").write_text("user's personal config")
        (self.target / "unrelated").write_text("keep me")

    def tearDown(self):
        self.temp.cleanup()

    def test_roundtrip_preserves_originals_and_later_user_edits(self):
        backup = installer.install_tree(self.target, self.backups, self.kit)
        self.assertEqual((self.target / "hypr/local.lua").read_text(), "user's personal config")
        (self.target / "hypr/helper").write_text("later user's edit")
        installer.restore_tree(backup, self.target)
        self.assertEqual((self.target / "hypr/hyprland.lua").read_text(), "old main")
        self.assertEqual((self.target / "hypr/hyprland.lua").stat().st_mode & 0o777, 0o600)
        self.assertFalse((self.target / "hypr/helper").exists())
        self.assertEqual((self.target / "unrelated").read_text(), "keep me")
        stashed = list(backup.glob("after-*/hypr/helper"))
        self.assertEqual(len(stashed), 1)
        self.assertEqual(stashed[0].read_text(), "later user's edit")

    def test_failed_install_restores_files_already_written(self):
        original = installer.atomic_copy
        failed = False
        def fail_once(source, destination):
            nonlocal failed
            if destination.name == "hyprland.lua" and not failed:
                failed = True
                raise OSError("simulated disk failure")
            return original(source, destination)
        with patch.object(installer, "atomic_copy", side_effect=fail_once):
            with self.assertRaises(OSError):
                installer.install_tree(self.target, self.backups, self.kit)
        self.assertEqual((self.target / "hypr/hyprland.lua").read_text(), "old main")
        self.assertFalse((self.target / "hypr/helper").exists())

    def test_symlink_is_rejected_before_writing(self):
        outside = self.base / "managed-file"
        outside.write_text("managed externally")
        (self.target / "hypr/helper").symlink_to(outside)
        with self.assertRaises(RuntimeError):
            installer.install_tree(self.target, self.backups, self.kit)
        self.assertEqual(outside.read_text(), "managed externally")
        self.assertEqual((self.target / "hypr/hyprland.lua").read_text(), "old main")
        self.assertFalse(self.backups.exists())

    def test_lua_migration_preserves_legacy_config_and_installs_entrypoint_last(self):
        legacy = self.target / "hypr/hyprland.conf"
        legacy.write_text("original legacy config")
        (self.target / "hypr/hyprland.lua").unlink()
        written = []
        original = installer.atomic_copy
        def record(source, destination):
            written.append(destination.relative_to(self.target).as_posix())
            return original(source, destination)
        with patch.object(installer, "atomic_copy", side_effect=record):
            backup = installer.install_tree(self.target, self.backups, self.kit)
        self.assertEqual(written[-1], "hypr/hyprland.lua")
        self.assertEqual(legacy.read_text(), "original legacy config")
        installer.restore_tree(backup, self.target)
        self.assertFalse((self.target / "hypr/hyprland.lua").exists())
        self.assertEqual(legacy.read_text(), "original legacy config")


class ActionTests(unittest.TestCase):
    def test_dimming_uses_native_lua_eval(self):
        with patch.object(actions, "run") as run:
            actions.set_dim(True)
            actions.set_dim(False)
        self.assertEqual([call.args for call in run.call_args_list], [
            ("hyprctl", "eval", "hl.config({ decoration = { dim_inactive = true } })"),
            ("hyprctl", "eval", "hl.config({ decoration = { dim_inactive = false } })"),
        ])

    def test_cancelled_screenshot_does_not_capture_or_copy(self):
        with patch.object(actions, "run", return_value=subprocess.CompletedProcess(["slurp"], 1, b"", b"")) as call:
            actions.screenshot("region")
        call.assert_called_once_with("slurp", check=False)

    def test_rapid_terminal_toggles_only_launch_one_process(self):
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(actions, "runtime", return_value=Path(folder)), \
             patch.object(actions, "text", return_value="[]"), \
             patch.object(actions, "run"), \
             patch.object(actions, "launch") as launch:
            actions.terminal()
            actions.terminal()
        self.assertEqual(launch.call_count, 1)

    def test_focus_mode_restores_each_preexisting_dnd_state(self):
        for previous_dnd in (False, True):
            with self.subTest(dnd=previous_dnd), tempfile.TemporaryDirectory() as folder:
                state = {"dim": 0, "dnd": previous_dnd}
                def read(*args, **kwargs):
                    if args[0] == "hyprctl":
                        return json.dumps({"int": state["dim"]})
                    return str(state["dnd"]).lower()
                def run(*args, **kwargs):
                    if args[0] == "hyprctl":
                        state["dim"] = int("dim_inactive = true" in args[-1])
                    return subprocess.CompletedProcess(args, 0, b"", b"")
                with patch.object(actions, "runtime", return_value=Path(folder)), \
                     patch.object(actions, "text", side_effect=read), \
                     patch.object(actions, "run", side_effect=run), \
                     patch.object(actions, "set_dnd", side_effect=lambda x: state.update(dnd=x)), \
                     patch.object(actions, "notify"):
                    actions.focus()
                    self.assertEqual(state, {"dim": 1, "dnd": True})
                    actions.focus()
                    self.assertEqual(state, {"dim": 0, "dnd": previous_dnd})
                    self.assertFalse((Path(folder) / "focus.json").exists())

    def test_cancelling_power_confirmation_does_not_power_off(self):
        with patch.object(actions, "menu", side_effect=["Shut down", "Cancel"]), \
             patch.object(actions, "run") as run, patch.object(actions, "launch") as launch:
            actions.power()
        run.assert_not_called()
        launch.assert_not_called()

    def test_untrusted_window_title_is_never_executed(self):
        clients = [{"address": "0x123", "class": "kitty", "workspace": {"name": "1"},
                    "title": "$(touch /tmp/not-a-command); `uname`\nsecond line"}]
        with patch.object(actions, "text", return_value=json.dumps(clients)), \
             patch.object(actions, "menu", side_effect=lambda prompt, choices: next(iter(choices))), \
             patch.object(actions, "run") as call:
            actions.windows()
        call.assert_called_once_with("hyprctl", "dispatch", 'hl.dsp.focus({ window = "address:0x123" })', check=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
