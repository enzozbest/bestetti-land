#!/usr/bin/env python3
"""Offline app setup tests: all package managers and desktop commands are mocked."""
import ast
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
import desktop_setup as setup


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


installer = load("apps_installer", ROOT / "install.py")
actions = load("apps_actions", ROOT / "config/hypr/scripts/midnight.py")
DEFAULTS = setup.load_defaults(ROOT / "config/hypr/app-defaults.json")


class FakeDconf:
    def __init__(self):
        self.values = {"gtk-theme": "'Old theme'", "font-name": "'Old Font 10'"}
        self.fail_key = None
        self.fail_once = True

    def query(self, *args):
        stdout, stderr, code = "", "", 0
        if args[:2] == ("dconf", "read"):
            stdout = self.values.get(args[2].rsplit("/", 1)[-1], "")
        elif args[:2] == ("gsettings", "list-keys"):
            stdout = "\n".join(DEFAULTS["interface"])
        elif args[:2] == ("gsettings", "writable"):
            stdout = "true"
        elif args[:2] == ("gsettings", "range"):
            stdout = "enum\n'prefer-dark'\n'default'" if args[3] == "color-scheme" else "type s"
        elif args[:2] == ("gsettings", "set"):
            key, value = args[3:]
            if key == self.fail_key and self.fail_once:
                code, stderr, self.fail_once = 1, "simulated dconf failure", False
            else:
                self.values[key] = repr(ast.literal_eval(value))
        elif args[:2] == ("gsettings", "reset"):
            self.values.pop(args[3], None)
        elif args[:2] == ("gsettings", "get"):
            stdout = self.values.get(args[3], "'schema default'")
        else:
            raise AssertionError(f"Unexpected command: {args}")
        return subprocess.CompletedProcess(args, code, stdout, stderr)


class DependencyTests(unittest.TestCase):
    def test_flatpak_scope_and_runtime_launcher_agree(self):
        for present in ("--user", "--system"):
            with self.subTest(scope=present):
                def which(command):
                    return "/usr/bin/flatpak" if command == "flatpak" else None
                def info(*args, **kwargs):
                    return subprocess.CompletedProcess(args, 0 if args[2] == present else 1, "", "")
                with patch.object(setup.shutil, "which", side_effect=which), \
                     patch.object(setup, "query", side_effect=info), \
                     patch.object(actions, "run", side_effect=info), \
                     patch.object(actions, "launch") as launch:
                    self.assertEqual(setup.audio_installation(), present)
                    actions.audio()
                    launch.assert_called_once_with("flatpak", "run", present, setup.AUDIO_APP)

    def test_native_audio_needs_no_flatpak_probe(self):
        with patch.object(setup.shutil, "which", return_value="/usr/bin/pwvucontrol"), \
             patch.object(setup, "query") as query, \
             patch.object(actions, "run") as run, \
             patch.object(actions, "launch") as launch:
            self.assertEqual(setup.audio_installation(), "native")
            actions.audio()
            query.assert_not_called()
            run.assert_not_called()
            launch.assert_called_once_with("pwvucontrol")

    def test_runtime_retains_pavucontrol_fallback(self):
        with patch.object(actions.shutil, "which", side_effect=lambda name: name if name == "pavucontrol" else None), \
             patch.object(actions, "launch") as launch:
            actions.audio()
            launch.assert_called_once_with("pavucontrol")

    def test_packages_keep_interactive_prompts_and_flatpak_user_scope(self):
        with patch.object(setup, "missing_packages", return_value=["nautilus", "flatpak"]), \
             patch.object(setup.shutil, "which", side_effect=lambda name: "/usr/bin/" + name), \
             patch.object(setup, "audio_installation", side_effect=[None, "--user"]), \
             patch.object(setup, "run_visible") as run:
            setup.ensure_dependencies()
        self.assertEqual([call.args for call in run.call_args_list], [
            ("sudo", "pacman", "-Syu", "--needed", "nautilus", "flatpak"),
            ("flatpak", "remote-add", "--user", "--if-not-exists", "flathub",
             "https://flathub.org/repo/flathub.flatpakrepo"),
            ("flatpak", "install", "--user", "flathub", setup.AUDIO_APP),
        ])

    def test_repeat_provisioning_does_not_reinstall_existing_apps(self):
        for installed in ("native", "--user", "--system"):
            with self.subTest(installed=installed), \
                 patch.object(setup, "missing_packages", return_value=[]), \
                 patch.object(setup, "audio_installation", return_value=installed), \
                 patch.object(setup, "run_visible") as run:
                setup.ensure_dependencies()
                run.assert_not_called()

    def test_missing_asset_is_detected_even_when_commands_exist(self):
        def query(*args):
            if args[-1] == "--version":
                return subprocess.CompletedProcess(args, 0, "Hyprland 0.56.2", "")
            raise AssertionError(args)
        with patch.object(setup, "COMMAND_PACKAGES", {"nautilus": "nautilus"}), \
             patch.object(setup, "ASSET_PACKAGES", {"/not-installed/theme.css": "adw-gtk-theme"}), \
             patch.object(setup, "FONT_PACKAGES", {}), \
             patch.object(setup.shutil, "which", side_effect=lambda name: "/usr/bin/" + name), \
             patch.object(setup, "query", side_effect=query):
            self.assertEqual(setup.missing_packages(), ["adw-gtk-theme"])

    def test_font_substitution_is_not_accepted(self):
        with patch.object(setup.shutil, "which", return_value="fc-match"), \
             patch.object(setup, "query", return_value=subprocess.CompletedProcess([], 0, "DejaVu Sans", "")):
            self.assertFalse(setup.font_matches("Inter"))


class DefaultsTests(unittest.TestCase):
    def test_failed_mime_query_reports_uncertainty_and_checks_remaining_defaults(self):
        profile = {"mime": {"application/pdf": "org.gnome.Papers.desktop",
                            "image/png": "org.gnome.Loupe.desktop"}}
        with patch.object(setup, "checked", side_effect=[RuntimeError("query failed"), "old.desktop"]) as query, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            setup.verify_defaults(profile)
        self.assertIn("could not verify it: query failed", output.getvalue())
        self.assertIn("image/png currently resolves to old.desktop", output.getvalue())
        self.assertEqual(query.call_count, 2)

    def test_merge_preserves_other_settings_modes_and_css(self):
        with tempfile.TemporaryDirectory() as folder:
            target, stage = Path(folder) / "target", Path(folder) / "stage"
            (target / "gtk-3.0").mkdir(parents=True)
            gtk = target / "gtk-3.0/settings.ini"
            gtk.write_text("[Settings]\ngtk-cursor-theme-name=My cursor\ngtk-font-name=Old font\n")
            gtk.chmod(0o600)
            (target / "gtk-4.0").mkdir()
            css = target / "gtk-4.0/gtk.css"
            css.write_text("/* personal CSS */")
            mime = target / "mimeapps.list"
            mime.write_text("[Default Applications]\ntext/plain=editor.desktop;\napplication/pdf=old.desktop;\n"
                            "[Added Associations]\ntext/plain=other.desktop;\n")
            before = {p.relative_to(target): p.read_bytes() for p in target.rglob("*") if p.is_file()}
            setup.stage_defaults(target, stage, DEFAULTS)
            merged = setup.read_ini(stage / "gtk-3.0/settings.ini")
            self.assertEqual(merged["Settings"]["gtk-cursor-theme-name"], "My cursor")
            self.assertEqual(merged["Settings"]["gtk-font-name"], "Inter 12")
            self.assertEqual((stage / "gtk-3.0/settings.ini").stat().st_mode & 0o777, 0o600)
            merged = setup.read_ini(stage / "mimeapps.list")
            self.assertEqual(merged["Default Applications"]["text/plain"], "editor.desktop;")
            self.assertEqual(merged["Added Associations"]["text/plain"], "other.desktop;")
            self.assertEqual(merged["Default Applications"]["application/pdf"], "org.gnome.Papers.desktop;")
            self.assertEqual({p.relative_to(target): p.read_bytes() for p in target.rglob("*") if p.is_file()}, before)
            self.assertFalse((stage / "gtk-4.0/gtk.css").exists())
            second = Path(folder) / "second"
            setup.stage_defaults(stage, second, DEFAULTS)
            self.assertEqual({p.relative_to(stage): p.read_bytes() for p in stage.rglob("*") if p.is_file()},
                             {p.relative_to(second): p.read_bytes() for p in second.rglob("*") if p.is_file()})

    def test_schema_defaults_are_restored_with_reset(self):
        backend = FakeDconf()
        original = dict(backend.values)
        with patch.object(setup, "query", side_effect=backend.query):
            before = setup.snapshot_settings(DEFAULTS["interface"])
            self.assertIsNone(before["accent-color"])
            setup.apply_settings(DEFAULTS["interface"])
            self.assertEqual(setup.restore_settings(before), [])
        self.assertEqual(backend.values, original)

    def test_invalid_enum_is_rejected_before_writing(self):
        backend = FakeDconf()
        profile = json.loads(json.dumps(DEFAULTS))
        profile["interface"]["color-scheme"] = "invalid"
        with patch.object(setup, "query", side_effect=backend.query):
            with self.assertRaisesRegex(RuntimeError, "Unsupported color-scheme"):
                setup.supported_settings(profile)
        self.assertEqual(backend.values, FakeDconf().values)

    def test_old_schema_without_accent_is_reported_and_supported(self):
        backend = FakeDconf()
        def query(*args):
            result = backend.query(*args)
            if args[:2] == ("gsettings", "list-keys"):
                result.stdout = result.stdout.replace("accent-color", "")
            return result
        with patch.object(setup, "query", side_effect=query), contextlib.redirect_stdout(io.StringIO()) as output:
            settings = setup.supported_settings(DEFAULTS)
        self.assertNotIn("accent-color", settings)
        self.assertIn("no accent-color", output.getvalue())


class InstallFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = self.base / "home"
        self.target = self.home / ".config"
        self.target.mkdir(parents=True)
        self.backups = self.base / "backups"
        self.kit = self.base / "kit"
        shutil.copytree(ROOT / "config", self.kit / "config")
        (self.target / "hypr").mkdir()
        (self.target / "hypr/local.lua").write_text("-- my overrides\n")
        (self.target / "mimeapps.list").write_text("[Default Applications]\ntext/plain=mine.desktop;\n")
        self.backend = FakeDconf()
        self.before_files = self.contents()
        self.before_settings = dict(self.backend.values)
        self.stack = contextlib.ExitStack()
        self.stack.enter_context(patch.object(setup, "query", side_effect=self.backend.query))
        self.stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        self.stack.enter_context(contextlib.redirect_stderr(io.StringIO()))

    def tearDown(self):
        self.stack.close()
        self.temp.cleanup()

    def contents(self):
        return {p.relative_to(self.target): p.read_bytes() for p in self.target.rglob("*") if p.is_file()}

    def stage(self):
        setup.stage_defaults(self.target, self.kit / "config", DEFAULTS)

    def test_install_restore_covers_files_mime_and_desktop_preferences(self):
        self.stage()
        backup = installer.install_tree(self.target, self.backups, self.kit, DEFAULTS["interface"])
        self.assertEqual(setup.read_ini(self.target / "mimeapps.list")["Default Applications"]["application/pdf"],
                         "org.gnome.Papers.desktop;")
        self.backend.values["font-name"] = "'Later preference'"
        installer.restore_tree(backup, self.target)
        self.assertEqual(self.contents(), self.before_files)
        self.assertEqual(self.backend.values, self.before_settings)
        saved = list(backup.glob("after-desktop-*.json"))
        self.assertEqual(json.loads(saved[0].read_text())["font-name"], "'Later preference'")

    def test_settings_failure_rolls_back_files_and_prior_settings(self):
        self.stage()
        self.backend.fail_key = "icon-theme"
        with self.assertRaisesRegex(RuntimeError, "simulated dconf failure"):
            installer.install_tree(self.target, self.backups, self.kit, DEFAULTS["interface"])
        self.assertEqual(self.contents(), self.before_files)
        self.assertEqual(self.backend.values, self.before_settings)

    def test_generated_symlink_is_rejected_before_installation(self):
        self.stage()
        outside = self.base / "managed-settings"
        outside.write_text("managed elsewhere")
        (self.target / "gtk-3.0").mkdir()
        (self.target / "gtk-3.0/settings.ini").symlink_to(outside)
        with self.assertRaisesRegex(RuntimeError, "Symlink-managed"):
            installer.install_tree(self.target, self.backups, self.kit, DEFAULTS["interface"])
        self.assertEqual(outside.read_text(), "managed elsewhere")
        self.assertEqual(self.backend.values, self.before_settings)
        self.assertFalse(self.backups.exists())

    def cli_context(self, arguments):
        self.stack.enter_context(patch.object(sys, "argv", ["install.py", *arguments]))
        self.stack.enter_context(patch.object(installer, "ROOT", self.kit))
        self.stack.enter_context(patch.object(Path, "home", return_value=self.home))
        self.stack.enter_context(patch.dict(os.environ, {"XDG_CONFIG_HOME": str(self.target),
                                                      "XDG_STATE_HOME": str(self.base / "state")}))
        self.stack.enter_context(patch.object(installer.os, "geteuid", return_value=1000))
        self.stack.enter_context(patch.object(installer, "preflight", return_value=True))
        self.stack.enter_context(patch.object(installer, "verify_compositor"))
        self.stack.enter_context(patch.object(setup, "verify_defaults"))
        self.stack.enter_context(patch.object(setup, "require_session"))
        # staged_config's only runtime query is backlight detection.
        self.stack.enter_context(patch.object(installer, "command_output", return_value=(0, "amdgpu_bl2,backlight,10,50%,20")))

    def test_check_stages_everything_without_live_mutations(self):
        self.cli_context(["--check"])
        with patch.object(setup, "ensure_dependencies") as provision, \
             patch.object(setup, "apply_settings") as apply, \
             patch.object(installer, "install_tree") as install:
            installer.main()
        provision.assert_not_called()
        apply.assert_not_called()
        install.assert_not_called()
        self.assertEqual(self.contents(), self.before_files)
        self.assertFalse((self.base / "state").exists())

    def test_apply_calls_provisioning_and_installs_all_defaults(self):
        self.cli_context(["--apply"])
        with patch.object(setup, "ensure_dependencies") as provision:
            installer.main()
        provision.assert_called_once()
        self.assertEqual(ast.literal_eval(self.backend.values["gtk-theme"]), "adw-gtk3-dark")
        self.assertTrue((self.target / "networkmanager-dmenu/config.ini").is_file())
        self.assertIn('M.files = "nautilus"', (self.target / "hypr/conf/common.lua").read_text())
        # The successful installation uses the repository's exact shell styling.
        self.assertEqual((self.target / "waybar/style.css").read_bytes(),
                         (ROOT / "config/waybar/style.css").read_bytes())

    def test_skip_packages_still_applies_user_defaults(self):
        self.cli_context(["--apply", "--skip-packages"])
        with patch.object(setup, "ensure_dependencies") as provision:
            installer.main()
        provision.assert_not_called()
        self.assertEqual(ast.literal_eval(self.backend.values["gtk-theme"]), "adw-gtk3-dark")

    def test_failed_package_command_cannot_install_config(self):
        self.cli_context(["--apply"])
        with patch.object(setup, "ensure_dependencies", side_effect=subprocess.CalledProcessError(1, ["pacman"])):
            with self.assertRaises(subprocess.CalledProcessError):
                installer.main()
        self.assertEqual(self.contents(), self.before_files)
        self.assertEqual(self.backend.values, self.before_settings)

    def test_root_is_rejected_before_commands_or_config_changes(self):
        self.cli_context(["--apply"])
        with patch.object(installer.os, "geteuid", return_value=0), \
             patch.object(setup, "ensure_dependencies") as provision:
            with self.assertRaisesRegex(RuntimeError, "without sudo"):
                installer.main()
        provision.assert_not_called()
        self.assertEqual(self.contents(), self.before_files)


if __name__ == "__main__":
    unittest.main(verbosity=2)
