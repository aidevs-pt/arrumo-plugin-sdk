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

Each frontend entrypoint must be a self-contained UTF-8 HTML document of at most 512 KiB. Inline its JavaScript and styles and use data URLs for embedded images or fonts. The desktop app loads the document from a dedicated local protocol in an opaque sandboxed frame. The panel has no direct native command bridge. Workspace data is available only through a declared permission and an explicit grant. The content policy restricts resource loads to the document and its inline assets.

Package the [frontend counter example](examples/frontend) with `--include index.html`. After installing the ZIP, open the panel under **Plugin panels** in desktop Settings.

### Read context from a frontend panel

In schema v5, a `workspace` or `completed_video` panel can declare `"permissions": ["workspace-context-read"]`. The operator must grant access to the installed package in the current workspace. The workspace is selected by the host.

Send a message to `parent` with `type: "arrumo:workspace-context"` and `nonce: location.hash.slice(1)`. Transfer one `MessageChannel` port with the request. The host responds once per panel opening on that port with `{ok: true, context: string | null}` or `{ok: false, error: "context_unavailable"}`. The package revision, panel declaration, and workspace grant are checked at the time of the request. See the [workspace panel example](examples/workspace-panel). Use text rendering for the returned context.

### Declare backend actions

Schema v6 lets a plugin with a backend component declare up to 64 entries in `actions`. Each entry has a unique `id`, a human-readable `label` and `description`, and `scope` set to `app` or `workspace`. The host calls `invoke` with JSON shaped as `{"action":"action-id","input":...}`, using the caller’s explicit app or workspace scope. Actions remain subject to component sandbox limits and the plugin’s grants. Invoking a package that declares actions requires a declared action ID.

The [action example](examples/actions/manifest.json) uses the same compiled echo component as the backend example. Compile `examples/component/echo.wat` to `examples/actions/echo.wasm`, package with `--include echo.wasm`, and install the ZIP. Use `plugin-actions` to discover actions and send JSON on stdin to `invoke-plugin-action action-echo echo app`.

### Hand off rendered motion media

Use the [motion result schema](motion-result.schema.json) for the motion portion of an Assets stage result. The [example](examples/motion-result.json) references a managed video preview and thumbnail. Items can also reference audio and a profile. These are workspace-local asset and profile IDs allocated by Arrumo. The host checks ownership, media kinds, and the current generation lease before accepting the result.

A renderer adapter runs in its own authorized environment. Import its finished preview and any supporting media through the host's asset import operation, then submit the returned IDs in `motion_items` for the run's Assets stage. Filesystem paths and executable source are outside this result contract. Generic WIT components cannot spawn external renderer processes or access the host filesystem. The schema supports producer-side validation of the JSON shape, while the host remains responsible for checking what each ID refers to.

### Submit a local renderer batch

Use the [motion artifact schema](motion-artifacts.schema.json) and [example batch](examples/motion-artifacts.json) when the renderer has produced local files and the worker holds the Assets-stage lease. Pass the batch JSON to the editor CLI as the final argument of `submit-motion-artifacts <workspace-id> <run-id> <attempt> <artifacts-json>`. With MCP or A2A, pass it as `artifacts` to `submit_motion_artifacts` together with `workspaceId`, `runId`, and `attempt`.

File paths refer to the machine and filesystem where the host runs. If a renderer uses a mount such as `/output`, translate each path to its host-visible location before submission. The schema checks the input shape. Arrumo checks the lease and probes the actual media before committing the batch and emitting managed IDs.

When an isolated renderer returns paths under `/output`, stop the renderer before resolving or importing its files. Run `python tools/resolve_motion_artifacts.py <host-output-directory>` with the artifact batch on stdin. It emits the batch with host-visible absolute paths on stdout and rejects missing files, traversal, and symlinks that resolve outside the output directory. Use a fresh output directory for each job and keep it private to the worker until the host finishes the import.

#### Local Linux renderer runner

`python tools/run_motion_renderer.py --project <project-directory> --output <new-output-directory> -- /usr/bin/sh /input/render.sh` launches an operator-selected renderer in Bubblewrap. The project is mounted read-only at `/input`, the job gets writable `/output` and temporary storage, and the runner clears inherited environment variables and isolates the network. An optional `--toolchain <directory>` is mounted read-only at `/renderer`. The output path must be new and outside both input directories. Set a wall-clock limit with `--timeout`.

The renderer writes `/output/artifacts.json` conforming to the motion artifact schema and then exits. The SDK prints host-visible paths after validating that the files stay within the job directory. Use those paths with `submit_motion_artifacts`. The worker owns the job directory until submission finishes. This runner requires Linux with Bubblewrap and a compatible system toolchain. Installed editor packages and other operating systems need runtime integration separately.

The Linux runner also requires `prlimit` from util-linux. Use `--max-output-bytes` to set the hard per-file write limit and the aggregate size limit for unique files referenced by the artifact batch. The default is 512 MiB. The aggregate check runs after rendering. A worker that can create many files still needs a job-level filesystem quota.

Use `--max-scratch-bytes` to size the renderer's private `/tmp` filesystem. It defaults to 256 MiB. The runner sets both `HOME` and `TMPDIR` to that mount. This limit applies to temporary storage during execution. The separate job output directory is governed by the per-file and post-render checks above.

#### Run a reviewed renderer ZIP

A local worker can run a reviewed ZIP that declares a `motion-render` capability and includes `renderer.json` with a single `entrypoint` field naming a packaged shell script. Include both files with the packaging tool. The script runs inside the same Linux sandbox and writes the same `/output/artifacts.json` manifest.

Run `python tools/run_motion_package.py <package.zip> --sha256 <reviewed-digest> --output <new-output-directory>`. Supply the digest from the reviewed package record. The worker checks the digest, expanded package limits, file paths, and manifest before invoking the script. It can mount an operator-provisioned toolchain with `--toolchain`. The editor uses this entry point for installed renderer dispatch on Linux.

#### Distribute the Linux SDK worker

SDK conformance builds publish an `arrumo-motion-worker-linux` CI artifact containing the worker ZIP and `SHA256SUMS`. To build it locally, run `python tools/package_motion_worker.py arrumo-motion-worker-linux.zip` from the SDK checkout. The tool prints the archive's SHA-256. Select a trusted SDK revision or CI run, then verify the archive checksum before extracting it to a trusted location outside individual plugin directories.

Install the extracted `motion-worker-requirements.txt` into the Python 3 environment that launches Arrumo. The host also needs Bubblewrap, util-linux with `prlimit`, and FFprobe. Set `ARRUMO_MOTION_SDK_WORKER` to the extracted absolute path of `tools/run_motion_package.py` when starting the editor, MCP, or A2A. Keep the extracted layout intact so the worker can load its SDK schemas.

### Describe a speech synthesis adapter

A plugin declaring `text-to-speech` can provide a `speech-synthesis.json`
[descriptor](speech-synthesis.schema.json) for a reviewed HTTPS JSON POST API
that takes a voice identifier as the last path segment. The descriptor names
the JSON text field, static body and query values, response encoding, and the
workspace secret setting used for authentication. The response encoding is
`mp3` or `wav`.

The host must match the descriptor's plugin ID to the manifest and check the
credential against a declared workspace secret. It must reject credentials,
queries, fragments, dot segments, and non-HTTPS URLs in the endpoint, and
reject a static body key that conflicts with the text field. Hosts must append
the caller's voice ID as one encoded path segment, encode query values, apply
the descriptor's Unicode character limit, refuse redirects, and bound and
validate the audio response before storing it. The host owns credentials and
must redact provider errors. The descriptor is for trusted provider inputs.
Host dispatch is pending.

### Local subtitle translators

A bundled provider can declare the `subtitle-translation` capability and ship
`tools/translate-subtitles.py` in its development checkout. The script reads
a JSON object with `targetLanguage` and `cues` from stdin and writes an object
with `translations` to stdout. Both cue arrays use `{ "cue": 1, "text": "…" }`
items. Cue IDs are positive integers and must match exactly across the request
and response. Translation adapters own provider authentication and must keep
credentials out of the response.

Auto-Dubbing resolves this entry point only for explicitly selected bundled
plugin IDs in its local checkout workflow. This convention relies on trusted
local plugin sources.

### Stage reviewed package files

Use `tools/stage_plugin_package.py` to copy explicit files from an installed
or bundled ZIP exported by the editor. Pass the digest reviewed in the catalog
and a new destination directory.

```sh
python3 tools/stage_plugin_package.py package.zip /path/to/new-stage \
  --sha256 <reviewed-digest> --include tools/worker.py
```

Repeat `--include` for each dependency the worker needs. The tool verifies the
exact ZIP, checks member paths and entry types, applies the compressed and
expanded size limits, and publishes the directory after the selected files
have been written. Execution belongs to the consumer's configured runtime.

### Run a reviewed media worker on Linux

`tools/run_media_package.py` runs a reviewed Python entrypoint using the same
Bubblewrap sandbox as the motion renderer. The package code is read-only at
`/input`. A dedicated input directory is read-only at `/media`, and the
worker writes to `/output`. The process uses a cleared environment and a
separate network namespace. Pass only the media the job needs.

```sh
python3 tools/run_media_package.py package.zip --sha256 <reviewed-digest> \
  --inputs /path/to/media --output /path/to/new-output \
  --entrypoint tools/worker.py --include tools/helper.py
```

The worker writes `/output/result.json` as `{"file":"artifact.mp4"}` or names a
WAV file in the same directory. The host must validate the media before
importing it. This runner needs Bubblewrap, Python and any media tools used
by the worker on Linux. The supported command uses a wall-clock timeout,
bounded scratch and a per-file output limit.
