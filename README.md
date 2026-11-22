# Arrumo Plugin SDK

The versioned contracts, authoring tools, and conformance suite for Arrumo plugins.

Copyright © 2026 DEVS AI Unipessoal LDA. Licensed under the [GNU Affero General Public License v3.0](LICENSE).

For custom AI solutions for your company, visit [DEVS AI](https://aidevs.pt).

## First plugin

Build, package, install, and run the isolated echo action. [English](https://github.com/aidevs-pt/arrumo-docs/blob/main/content/docs/en/developer/first-plugin.md) · [Español](https://github.com/aidevs-pt/arrumo-docs/blob/main/content/docs/es/developer/first-plugin.md) · [Português](https://github.com/aidevs-pt/arrumo-docs/blob/main/content/docs/pt/developer/first-plugin.md)

## Reference

The JSON schemas in this repository are the source of truth. [Arrumo Docs](https://github.com/aidevs-pt/arrumo-docs) explains each contract in English, Spanish and Portuguese ([English](https://github.com/aidevs-pt/arrumo-docs/blob/main/content/docs/en/developer/sdk/index.md) · [Español](https://github.com/aidevs-pt/arrumo-docs/blob/main/content/docs/es/developer/sdk/index.md) · [Português](https://github.com/aidevs-pt/arrumo-docs/blob/main/content/docs/pt/developer/sdk/index.md)), including how to document your plugin.

| Page | Covers | Schemas and tools |
| --- | --- | --- |
| [Manifest](https://github.com/aidevs-pt/arrumo-docs/blob/main/content/docs/en/developer/sdk/manifest.md) | Identity, settings, introduction, icon, brand marks and translations | [`manifest.schema.json`](manifest.schema.json) |
| [Packages and code](https://github.com/aidevs-pt/arrumo-docs/blob/main/content/docs/en/developer/sdk/packages.md) | ZIP rules, WebAssembly backends, frontend panels, workspace context, reviewed files | [`tools/package_plugin.py`](tools/package_plugin.py), [`wit/plugin.wit`](wit/plugin.wit) |
| [Actions and hooks](https://github.com/aidevs-pt/arrumo-docs/blob/main/content/docs/en/developer/sdk/actions.md) | Actions, their forms and placements, event hooks | [`examples/actions`](examples/actions) |
| [Provider adapters](https://github.com/aidevs-pt/arrumo-docs/blob/main/content/docs/en/developer/sdk/adapters.md) | Transcription, speech, music and sound effects, voice changing and isolation, dubbing, image, video, usage and subtitle translation | [`transcription`](transcription.schema.json), [`speech-synthesis`](speech-synthesis.schema.json), [`audio-generation`](audio-generation.schema.json), [`audio-transform`](audio-transform.schema.json), [`dubbing`](dubbing.schema.json), [`image-generation`](image-generation.schema.json), [`video-generation`](video-generation.schema.json), [`usage`](usage.schema.json) |
| [Agent providers](https://github.com/aidevs-pt/arrumo-docs/blob/main/content/docs/en/developer/sdk/agents.md) | Status checks, structured runs, images, plan usage, follow-up messages | [`manifest.schema.json`](manifest.schema.json) |
| [Motion renderers](https://github.com/aidevs-pt/arrumo-docs/blob/main/content/docs/en/developer/sdk/motion.md) | Motion results and artifacts, the Linux renderer sandbox, the SDK worker | [`motion-result`](motion-result.schema.json), [`motion-artifacts`](motion-artifacts.schema.json), [`tools/run_motion_package.py`](tools/run_motion_package.py) |
