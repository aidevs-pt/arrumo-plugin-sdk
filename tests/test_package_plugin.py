import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.package_plugin import build_package


class PackagePluginTest(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.source = Path(directory)
        self.manifest = Path("examples/transcription.json").read_bytes()
        (self.source / "manifest.json").write_bytes(self.manifest)
        (self.source / "LICENSE").write_text("fixture", encoding="utf-8")
        (self.source / "README.md").write_text("fixture", encoding="utf-8")

    def test_build_is_reproducible_and_contains_only_selected_files(self):
        (self.source / ".env").write_text("fixture", encoding="utf-8")
        first, metadata = build_package(self.source, ["README.md", "LICENSE"])
        os.utime(self.source / "README.md", (0, 0))
        second, _ = build_package(self.source, ["LICENSE", "README.md"])
        self.assertEqual(first, second)
        self.assertEqual(metadata["sha256"], hashlib.sha256(first).hexdigest())
        with zipfile.ZipFile(io.BytesIO(first)) as archive:
            self.assertEqual(archive.namelist(), ["LICENSE", "README.md", "manifest.json"])
            self.assertEqual(archive.read("manifest.json"), self.manifest)

    def test_rejects_duplicate_paths_and_traversal(self):
        for path in ("MANIFEST.JSON", "../README.md", "a\\b", "/README.md"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                build_package(self.source, [path])

    def test_rejects_symlinked_files_and_parent_directories(self):
        (self.source / "linked.txt").symlink_to("README.md")
        (self.source / "real").mkdir()
        (self.source / "real" / "payload.txt").write_text("fixture", encoding="utf-8")
        (self.source / "linked").symlink_to("real", target_is_directory=True)
        for path in ("linked.txt", "linked/payload.txt"):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "Symbolic links"):
                build_package(self.source, [path])

    def test_rejects_duplicate_and_unsupported_manifest_data(self):
        from jsonschema import ValidationError

        manifest = self.source / "manifest.json"
        manifest.write_bytes(b'{"id":"first","id":"second"}')
        with self.assertRaisesRegex(ValueError, "Duplicate manifest field"):
            build_package(self.source, [])
        manifest.write_bytes(self.manifest.replace(b'"schemaVersion": 2', b'"schemaVersion": 99'))
        with self.assertRaises(ValidationError):
            build_package(self.source, [])

    def test_packages_the_declared_icon_file(self):
        manifest = json.loads(self.manifest)
        manifest["schemaVersion"] = 8
        manifest["icon"] = "icon.svg"
        manifest["iconNotice"] = "Example and its logo are trademarks of Example."
        (self.source / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Expected a regular file: icon.svg"):
            build_package(self.source, [])
        (self.source / "icon.svg").write_text("<svg></svg>", encoding="utf-8")
        package, _ = build_package(self.source, [])
        with zipfile.ZipFile(io.BytesIO(package)) as archive:
            self.assertEqual(archive.namelist(), ["icon.svg", "manifest.json"])
        (self.source / "icon.svg").write_text("<svg>" + " " * 9000 + "</svg>", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "size limit: icon.svg"):
            build_package(self.source, [])
        manifest["icon"] = "<svg></svg>"
        (self.source / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(Exception):
            build_package(self.source, [])

    def test_requires_nonempty_backend_and_frontend_entrypoints(self):
        import json

        manifest = json.loads(self.manifest)
        manifest["schemaVersion"] = 3
        manifest["code"] = {
            "backend": {"component": "component.wasm"},
            "frontend": [{
                "id": "fixture-panel",
                "document": "index.html",
                "title": "Fixture",
                "placement": "workspace",
            }],
        }
        (self.source / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (self.source / "component.wasm").write_bytes(b"\0asm\r\0\1\0")
        (self.source / "index.html").write_text("<p>Fixture</p>", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Include every declared"):
            build_package(self.source, ["component.wasm"])
        package, metadata = build_package(self.source, ["component.wasm", "index.html"])
        self.assertEqual(metadata["manifestSchemaVersion"], 3)
        with zipfile.ZipFile(io.BytesIO(package)) as archive:
            self.assertIn("component.wasm", archive.namelist())
            self.assertIn("index.html", archive.namelist())

    def test_validates_provider_adapter_identity_credential_and_timings(self):
        name = "transcription-timed.json"
        descriptor = {
            "schemaVersion": 2, "pluginId": "example-transcription",
            "endpoint": "https://example.com/transcription",
            "credentialSetting": "api-key", "credentialHeader": "authorization",
            "credentialPrefix": "Bearer ", "maxAudioBytes": 100000,
            "fileField": "file", "form": {"model": "example"},
            "response": {"text": "/text", "language": "/language", "words": {
                "items": "/segments", "text": "/text", "start": "/start", "end": "/end",
            }},
        }
        adapter = self.source / name
        def write(value):
            adapter.write_text(json.dumps(value), encoding="utf-8")

        write(descriptor)
        package, _ = build_package(self.source, [name])
        with zipfile.ZipFile(io.BytesIO(package)) as archive:
            self.assertEqual(json.loads(archive.read(name)), descriptor)

        for changed, error in (
            (dict(descriptor, pluginId="other-plugin"), "manifest identity"),
            (dict(descriptor, credentialSetting="language"), "matching secret setting"),
            (dict(descriptor, response={"text": "/text", "language": "/language"}), "timing mapping"),
        ):
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                write(changed)
                build_package(self.source, [name])

    def test_packages_a_usage_adapter_without_a_capability(self):
        name = "usage.json"
        descriptor = {
            "schemaVersion": 1, "pluginId": "example-transcription",
            "endpoint": "https://example.com/v1/user/subscription",
            "credentialSetting": "api-key", "credentialHeader": "x-api-key", "credentialPrefix": "",
            "used": "/character_count", "limit": "/character_limit", "unit": "characters",
        }
        (self.source / name).write_text(json.dumps(descriptor), encoding="utf-8")
        package, _ = build_package(self.source, [name])
        with zipfile.ZipFile(io.BytesIO(package)) as archive:
            self.assertEqual(json.loads(archive.read(name)), descriptor)
        (self.source / name).write_text(json.dumps({**descriptor, "pluginId": "other"}), encoding="utf-8")
        with self.assertRaises(ValueError):
            build_package(self.source, [name])

    def test_usage_events_need_schema_twelve(self):
        manifest = {
            "schemaVersion": 12, "id": "example-agent", "name": "Example agent",
            "description": "An agent provider.",
            "capabilities": {"agents": {"name": "Agent", "description": "Runs editing stages."}},
            "agentProvider": {"label": "Example", "setupUrl": "https://example.com/setup",
                              "cli": {"executable": "example", "authStatusArgs": ["auth", "status"]}},
        }
        manifest["agentProvider"]["cli"]["usageEvent"] = {
            "typePointer": "/type", "typeValue": "rate_limit_event",
            "windows": [{"used": "/info/seven_day/utilization", "scale": "fraction", "minutes": 10080}],
        }
        manifest["schemaVersion"] = 12
        (self.source / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        build_package(self.source, [])
        manifest["schemaVersion"] = 11
        (self.source / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(Exception):
            build_package(self.source, [])

    def test_validates_audio_adapter_kinds_against_capabilities(self):
        manifest = json.loads(self.manifest)
        manifest["settings"][0]["scope"] = "workspace"
        manifest["capabilities"]["music-generation"] = {"name": "Music", "description": "Compose music."}
        (self.source / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        name = "audio-generation.json"
        music = {
            "endpoint": "https://example.com/v1/music", "promptField": "prompt",
            "durationField": "music_length_ms", "durationUnit": "milliseconds",
            "minSeconds": 3, "maxSeconds": 600, "maxPromptCharacters": 2000,
            "body": {"model_id": "music_v1", "force_instrumental": True},
            "query": {"output_format": "mp3_44100_128"},
        }
        descriptor = {
            "schemaVersion": 1, "pluginId": "example-transcription", "credentialSetting": "api-key",
            "credentialHeader": "x-api-key", "credentialPrefix": "", "responseFormat": "mp3",
            "kinds": {"music": music},
        }
        adapter = self.source / name

        def write(value):
            adapter.write_text(json.dumps(value), encoding="utf-8")

        write(descriptor)
        package, _ = build_package(self.source, [name])
        with zipfile.ZipFile(io.BytesIO(package)) as archive:
            self.assertEqual(json.loads(archive.read(name)), descriptor)
        for changed, error in (
            (dict(descriptor, kinds={"sound-effect": music}), "sound-effect-generation capability"),
            (dict(descriptor, kinds={"music": dict(music, minSeconds=700)}), "minSeconds <= maxSeconds"),
            (dict(descriptor, kinds={"music": dict(music, body={"prompt": "x"})}), "twice"),
        ):
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                write(changed)
                build_package(self.source, [name])
        for changed in (
            dict(descriptor, kinds={"music": dict(music, endpoint="http://example.com/v1/music")}),
            dict(descriptor, kinds={"speech": music}),
            dict(descriptor, kinds={"music": dict(music, durationUnit="minutes")}),
        ):
            with self.subTest(changed=changed), self.assertRaises(Exception):
                write(changed)
                build_package(self.source, [name])

    def test_validates_image_adapter_placeholders_and_model_setting(self):
        manifest = json.loads(self.manifest)
        manifest["capabilities"]["image-generation"] = {
            "name": "Image generation", "description": "Generate images from prompts.",
        }
        (self.source / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        name = "image-generation.json"
        descriptor = {
            "schemaVersion": 1, "pluginId": "example-transcription",
            "endpoint": "https://example.com/v1/models/{model}:generate",
            "credentialSetting": "api-key", "credentialHeader": "x-api-key", "credentialPrefix": "",
            "model": {"default": "image-1", "setting": "language"},
            "aspectRatios": {"16:9": "1536x1024", "9:16": "1024x1536", "1:1": "1024x1024"},
            "request": {"input": [{"text": "{prompt}"}], "size": "{aspectRatio}"},
            "response": {"items": "/candidates", "image": "/data"},
            "maxImageBytes": 10000000,
        }
        adapter = self.source / name

        def write(value):
            adapter.write_text(json.dumps(value), encoding="utf-8")

        write(descriptor)
        package, _ = build_package(self.source, [name])
        with zipfile.ZipFile(io.BytesIO(package)) as archive:
            self.assertEqual(json.loads(archive.read(name)), descriptor)

        for changed, error in (
            (dict(descriptor, request={"size": "{aspectRatio}"}), "must contain \\{prompt\\}"),
            (dict(descriptor, model={"default": "image-1", "setting": "api-key"}), "declared string setting"),
            (dict(descriptor, credentialSetting="language"), "matching secret setting"),
        ):
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                write(changed)
                build_package(self.source, [name])

        for changed in (
            dict(descriptor, endpoint="http://example.com/v1/images"),
            dict(descriptor, aspectRatios={"16:9": "wide"}),
            dict(descriptor, model={"default": "../image"}),
        ):
            with self.subTest(changed=changed), self.assertRaises(Exception):
                write(changed)
                build_package(self.source, [name])


class NamedModelTest(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.source = Path(directory)
        manifest = json.loads(Path("examples/transcription.json").read_text(encoding="utf-8"))
        manifest["capabilities"]["video-generation"] = {"name": "Video", "description": "Clips."}
        manifest["capabilities"]["image-generation"] = {"name": "Images", "description": "Images."}
        for setting in manifest["settings"]:
            if setting["kind"] == "secret":
                setting["scope"] = "workspace"
        manifest["settings"] += [
            {"id": "video-model", "label": "Video model", "description": "Default video model.",
             "kind": "string", "scope": "workspace", "required": False, "choices": ["quick", "edit"]},
            {"id": "image-model", "label": "Image model", "description": "Default image model.",
             "kind": "string", "scope": "workspace", "required": False, "choices": ["poster"]},
        ]
        self.manifest = manifest
        (self.source / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        best = {"en": "Short drafts.", "es": "Borradores.", "pt": "Rascunhos."}
        api = "https://api.example.com"
        self.video = {
            "schemaVersion": 3, "pluginId": "example-transcription", "endpoint": f"{api}/t2v",
            "credentialSetting": "api-key", "credentialHeader": "authorization", "credentialPrefix": "Key ",
            "aspectRatios": {"16:9": "16:9"}, "durations": {"min": 5, "max": 10, "default": 5},
            "request": {"prompt": "{prompt}", "duration": "{duration}"},
            "submission": {"statusUrl": "/status_url"},
            "status": {"state": "/status", "completed": ["completed"], "failed": ["failed"], "video": "/video/url"},
            "pollSeconds": 5, "timeoutSeconds": 600, "maxVideoBytes": 1000000,
            "model": {"default": "quick", "setting": "video-model"},
            "models": {
                "quick": {"label": "Quick", "bestFor": best, "variants": [
                    {"endpoint": f"{api}/t2v", "aspectRatios": {"16:9": "16:9"},
                     "durations": {"min": 5, "max": 10, "default": 5, "allowed": [5, 10]},
                     "request": {"prompt": "{prompt}", "duration": "{duration}"}},
                    {"endpoint": f"{api}/i2v", "durations": {"min": 5, "max": 10, "default": 5},
                     "request": {"prompt": "{prompt}", "image_url": "{image}", "end_image_url": "{lastImage}"},
                     "images": {"min": 1, "max": 2}},
                ]},
                "edit": {"label": "Edit", "bestFor": best, "variants": [
                    {"endpoint": f"{api}/edit", "request": {"prompt": "{prompt}", "video_url": "{video}"},
                     "videos": {"min": 1, "max": 1}},
                ]},
            },
            "upload": {"endpoint": f"{api}/upload", "request": {"content_type": "{contentType}"},
                       "uploadUrl": "/upload_url", "publicUrl": "/public_url"},
        }
        self.image = {
            "schemaVersion": 3, "pluginId": "example-transcription", "endpoint": f"{api}/image",
            "credentialSetting": "api-key", "credentialHeader": "authorization", "credentialPrefix": "Key ",
            "model": {"default": "poster", "setting": "image-model"},
            "aspectRatios": {"16:9": "16:9", "9:16": "9:16", "1:1": "1:1"},
            "request": {"prompt": "{prompt}"}, "maxImageBytes": 1000000,
            "job": {"submission": {"statusUrl": "/status_url"},
                    "status": {"state": "/status", "completed": ["completed"], "failed": [], "image": "/images/0/url"},
                    "pollSeconds": 3, "timeoutSeconds": 600},
            "upload": {"endpoint": f"{api}/upload", "request": {"content_type": "{contentType}"},
                       "uploadUrl": "/upload_url", "publicUrl": "/public_url"},
            "models": {"poster": {
                "label": "Poster", "bestFor": best, "endpoint": f"{api}/poster",
                "aspectRatios": {"16:9": "16:9", "9:16": "9:16", "1:1": "1:1", "4:5": "4:5"},
                "request": {"prompt": "{prompt}", "aspect_ratio": "{aspectRatio}"},
                "references": {"encoding": "urls", "endpoint": f"{api}/poster", "field": "image_url",
                               "maxImages": 1, "single": True},
            }},
        }

    def build(self, name, descriptor):
        (self.source / name).write_text(json.dumps(descriptor), encoding="utf-8")
        return build_package(self.source, [name])

    def test_accepts_described_models(self):
        self.build("video-generation.json", self.video)
        self.build("image-generation.json", self.image)

    def test_rejects_inconsistent_video_models(self):
        quick = self.video["models"]["quick"]
        cases = [
            (dict(self.video, schemaVersion=2), "needs schema 3"),
            (dict(self.video, model={"default": "slow", "setting": "video-model"}), "default model"),
            (dict(self.video, models={"quick": quick}), "choices must match"),
            (dict(self.video, models=dict(self.video["models"], edit=dict(
                self.video["models"]["edit"], variants=[dict(self.video["models"]["edit"]["variants"][0],
                                                             request={"prompt": "{prompt}", "video_url": "{video}",
                                                                      "duration": "{duration}"})]))),
             "without durations"),
            (dict(self.video, models=dict(self.video["models"], quick=dict(quick, variants=[dict(
                quick["variants"][0], durations={"min": 5, "max": 10, "default": 5, "allowed": [6]})]))),
             "allowed must"),
        ]
        for descriptor, error in cases:
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                self.build("video-generation.json", descriptor)

    def test_rejects_inconsistent_image_models(self):
        poster = self.image["models"]["poster"]
        references = dict(poster["references"], maxImages=2)
        cases = [
            (dict(self.image, schemaVersion=2), "need schema 3"),
            (dict(self.image, models={"poster": dict(poster, references=references)}), "maxImages must be 1"),
            (dict(self.image, models={"poster": dict(poster, aspectRatios={"16:9": "16:9", "9:16": "9:16",
                                                                           "1:1": "1:1"}),
                                      "other": poster}), "choices must match"),
        ]
        for descriptor, error in cases:
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                self.build("image-generation.json", descriptor)
