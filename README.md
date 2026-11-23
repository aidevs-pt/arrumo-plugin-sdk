<p align="center">
  <img src="https://raw.githubusercontent.com/aidevs-pt/arrumo-video-editor/main/public/arrumo-icon.svg" width="88" height="88" alt="">
</p>

<h1 align="center">Arrumo Plugin SDK</h1>

<p align="center">Add AI agents and media providers to <b>Arrumo AI Video Editor</b>: versioned contracts, authoring tools and a conformance suite.</p>

<p align="center">
  <a href="LICENSE"><img alt="License: AGPL-3.0" src="https://img.shields.io/badge/license-AGPL--3.0-2337B4"></a>
  <img alt="Manifest schema 14" src="https://img.shields.io/badge/manifest%20schema-14-111">
  <a href="https://www.aidevs.pt/tools/arrumo/docs/developer/sdk"><img alt="Docs in English, Spanish and Portuguese" src="https://img.shields.io/badge/docs-EN%20%C2%B7%20ES%20%C2%B7%20PT-2337B4"></a>
</p>

<p align="center">
  <a href="https://www.aidevs.pt/tools/arrumo/docs/developer/first-plugin"><b>Your first plugin</b></a> · <a href="https://www.aidevs.pt/tools/arrumo/docs/developer/sdk">SDK guide</a> · <a href="https://github.com/aidevs-pt/arrumo-plugin-registry">Official plugins</a>
</p>

A plugin is a ZIP with a `manifest.json` that Arrumo validates at the host boundary before anything runs. It can:

- **Call a provider's HTTP API** declaratively, through adapters for transcription, speech, music and sound effects, voice changing, dubbing, images, video, usage and subtitle translation, with keys kept in the system vault.
- **Add an agent provider** such as Claude Code or Codex: status checks, structured runs with JSON Schema answers, image input, follow-up sessions, plan usage, and settings mapped to CLI flags.
- **Run its own code** in an isolated WebAssembly backend or the Linux renderer sandbox, with only the capabilities it declares and the creator grants.
- **Show its own panels** in Settings, workspace Context and finished videos, and actions with forms and event hooks.
- **Speak the creator's language**, with names, settings and actions translated into English, Spanish and Portuguese.

All [official plugins](https://github.com/aidevs-pt/arrumo-plugin-registry) are built with this SDK.

## First plugin

Build, package, install, and run the isolated echo action. [English](https://www.aidevs.pt/tools/arrumo/docs/developer/first-plugin) · [Español](https://www.aidevs.pt/es/tools/arrumo/docs/developer/first-plugin) · [Português](https://www.aidevs.pt/pt/tools/arrumo/docs/developer/first-plugin)

## Reference

The JSON schemas in this repository are the source of truth. [Arrumo Docs](https://github.com/aidevs-pt/arrumo-docs) explains each contract in English, Spanish and Portuguese ([English](https://www.aidevs.pt/tools/arrumo/docs/developer/sdk) · [Español](https://www.aidevs.pt/es/tools/arrumo/docs/developer/sdk) · [Português](https://www.aidevs.pt/pt/tools/arrumo/docs/developer/sdk)), including how to document your plugin.

| Page | Covers | Schemas and tools |
| --- | --- | --- |
| [Manifest](https://www.aidevs.pt/tools/arrumo/docs/developer/sdk/manifest) | Identity, settings, introduction, icon, brand marks and translations | [`manifest.schema.json`](manifest.schema.json) |
| [Packages and code](https://www.aidevs.pt/tools/arrumo/docs/developer/sdk/packages) | ZIP rules, WebAssembly backends, frontend panels, workspace context, reviewed files | [`tools/package_plugin.py`](tools/package_plugin.py), [`wit/plugin.wit`](wit/plugin.wit) |
| [Actions and hooks](https://www.aidevs.pt/tools/arrumo/docs/developer/sdk/actions) | Actions, their forms and placements, event hooks | [`examples/actions`](examples/actions) |
| [Provider adapters](https://www.aidevs.pt/tools/arrumo/docs/developer/sdk/adapters) | Transcription, speech, music and sound effects, voice changing and isolation, dubbing, image, video, usage and subtitle translation | [`transcription`](transcription.schema.json), [`speech-synthesis`](speech-synthesis.schema.json), [`audio-generation`](audio-generation.schema.json), [`audio-transform`](audio-transform.schema.json), [`dubbing`](dubbing.schema.json), [`image-generation`](image-generation.schema.json), [`video-generation`](video-generation.schema.json), [`usage`](usage.schema.json) |
| [Agent providers](https://www.aidevs.pt/tools/arrumo/docs/developer/sdk/agents) | Status checks, structured runs, images, plan usage, follow-up messages | [`manifest.schema.json`](manifest.schema.json) |
| [Motion renderers](https://www.aidevs.pt/tools/arrumo/docs/developer/sdk/motion) | Motion results and artifacts, the Linux renderer sandbox, the SDK worker | [`motion-result`](motion-result.schema.json), [`motion-artifacts`](motion-artifacts.schema.json), [`tools/run_motion_package.py`](tools/run_motion_package.py) |

## License

Copyright © 2026 DEVS AI Unipessoal LDA. Licensed under the [GNU Affero General Public License v3.0](LICENSE). Part of [Arrumo AI Video Editor](https://github.com/aidevs-pt/arrumo-video-editor), built by [DEVS AI](https://aidevs.pt), who make custom AI solutions for companies.
