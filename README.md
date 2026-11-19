# Arrumo Plugin SDK

The versioned contracts, authoring tools, and conformance suite for Arrumo plugins.

This repository is being initialized. See the Arrumo workspace roadmap for implementation status.

Copyright © 2026 DEVS AI Unipessoal LDA. Licensed under the [GNU Affero General Public License v3.0](LICENSE).

For custom AI solutions for your company, visit [DEVS AI](https://aidevs.pt).

## Draft manifest

[manifest.schema.json](manifest.schema.json) defines plugin identity and capability metadata. See the [transcription example](examples/transcription.json).

Capability declarations describe what a plugin offers. Host settings and permissions will govern whether a capability can run. Package versions, runtime loading, grants, and execution contracts are pending.

## Agent provider declaration

An agent plugin can add an `agentProvider` descriptor and must declare the `agents` capability. The manifest's plugin ID is the provider ID. `label` is the displayed product name and `setupUrl` links to the provider's HTTPS setup guide. `cli.executable` and `cli.authStatusArgs` describe its local status command as a program name and literal argument list.

The host may run this command only for a trusted plugin whose adapter supports the host's execution policy. It resolves the executable through the host's PATH and reports a bounded status without capturing command output. Exit 0 confirms local authentication, exit 1 leaves it unconfirmed, and other exits report failure. The descriptor does not grant shell or process access to a plugin and does not declare a generation adapter. Never include credentials in the descriptor or probe arguments.

## Local ZIP packages

Place a single SDK `manifest.json` at the ZIP root. Stored and Deflate-compressed manifests are supported. The editor limits a package to 16 MiB and 512 entries and its manifest to 64 KiB. Use relative UTF-8 entry names with forward slashes. Avoid duplicate names, including names that differ only by case. Encrypted entries and symbolic links are rejected.

Arrumo records the original ZIP and its SHA-256 digest. The digest identifies the imported bytes for comparison with a release checksum. Package registration leaves the contents inert. Capability execution requires a separate trusted adapter.

### Build a package

With Python 3.11 or later and `jsonschema` installed, run:

```console
python /path/to/plugin-sdk/tools/package_plugin.py /path/to/plugin plugin.zip --include LICENSE --include README.md
```

The tool validates and includes the root manifest automatically. Pass each additional file explicitly with `--include`. The same files produce identical ZIP bytes regardless of argument order or filesystem timestamps. The output is a new file and the tool prints its plugin ID, manifest schema version, byte length, and SHA-256. Use that digest when preparing the registry release record.

## Settings declarations

Manifest schema v2 can include up to 64 entries in `settings`. Give each entry a unique plugin-local `id`, a `label` and `description`, a `kind` of `string`, `boolean`, `integer`, or `secret`, a `scope` of `app` or `workspace`, and a boolean `required` flag. An omitted settings array is valid. SDK v1 remains readable by current hosts and has no settings declarations.

The scope declares where the plugin expects the host to configure the field. A required field needs a configured value before a host can use the plugin for work that depends on that field. The manifest declares metadata only. Values, defaults, and credentials are never part of a declaration. The host currently validates and displays declarations through its catalog API. Setting values and secure credential storage require separate host support.
