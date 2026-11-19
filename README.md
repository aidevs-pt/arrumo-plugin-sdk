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
