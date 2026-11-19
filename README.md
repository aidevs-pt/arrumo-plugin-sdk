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

An app-scoped field is configured at app scope only. A workspace-scoped field can have an app default and a workspace override. Clearing an override restores the app default. A required field needs a configured value before a host can use the plugin for work that depends on that field. The manifest declares metadata only. Values, defaults, and credentials are never part of a declaration. The host currently validates and displays declarations through its catalog API. The host validates and resolves ordinary values separately. Secure credential storage requires separate host support.

### Bundled transcription adapter

The [transcription descriptor](transcription.schema.json) is a versioned host contract for reviewed, bundled providers. The descriptor identifies a plugin with the `transcription` capability and names a secret field declared in that plugin's manifest. It also declares the HTTPS endpoint, credential header, and model. The host reads the configured credential from its system store and builds the request itself.

The descriptor declares the multipart file field, static form fields, credential prefix, input limit, and JSON response field pointers. Optional word mappings select timestamped tokens and optional speaker labels. The host applies these declarations using a generic HTTPS transport with redirects disabled. Only descriptors in the reviewed application bundle can use this transport.

## Code packages

Manifest schema v3 adds an optional `code` section. Include a WebAssembly backend component under `backend.component`, custom HTML entry documents under `frontend`, or both. Every entrypoint must be a non-empty file in the ZIP. Include any bundled JavaScript, styles, and assets explicitly when packaging.

```json
{
  "backend": { "component": "backend/plugin.wasm" },
  "frontend": [
    {
      "id": "example-panel",
      "title": "Example panel",
      "document": "frontend/index.html",
      "placement": "workspace"
    }
  ]
}
```

Use unique surface IDs. Supported placements are `settings`, `workspace`, and `completed_video`. The host validates the declaration, checks that the ZIP contains the entrypoints, and retains the package. Installed backend components can be invoked explicitly through Arrumo. Installed frontend surfaces render in sandboxed frames. Host capability grants are declared and enforced separately.

### Invoke a backend

Implement the [WIT backend world](wit/plugin.wit). The `invoke` export receives UTF-8 JSON text and returns UTF-8 JSON text. The host instantiates a fresh component with no host imports or WASI. A component therefore receives only the input the caller supplies. The host limits component size to 4 MiB, input and output to 64 KiB each, and applies memory and fuel limits.

The [echo example](examples/component) includes the manifest and a handwritten component in WebAssembly text format. Compile it with `wasm-tools parse examples/component/echo.wat -o examples/component/echo.wasm`, then package the example directory with `--include echo.wasm`. After installation, pass JSON on stdin to the editor CLI's `invoke-plugin component-echo` command.

### Read explicitly shared workspace context

With manifest schema v4, a backend can declare `"permissions": ["workspace-context-read"]` in `code.backend` and implement the `workspace-plugin` WIT world. Installation alone grants no permission. An operator can grant this permission to a specific installed package in a specific workspace.

Invoke the plugin with that workspace ID. The host links `read-workspace-context` only when the grant matches the current package. The function returns the workspace's context as a JSON string or `null`, and can be called once per invocation. The grant is evaluated at invocation start. Updating or removing the package revokes the grant for subsequent calls.

### Render a frontend panel

Each frontend entrypoint must be a self-contained UTF-8 HTML document of at most 512 KiB. Inline its JavaScript and styles and use data URLs for embedded images or fonts. The desktop app loads the document from a dedicated local protocol in an opaque sandboxed frame. The panel receives no native command bridge or workspace data. The content policy restricts resource loads to the document and its inline assets.

Package the [frontend counter example](examples/frontend) with `--include index.html`. After installing the ZIP, open the panel under **Plugin panels** in desktop Settings.
