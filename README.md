# Arrumo Plugin SDK

The versioned contracts, authoring tools, and conformance suite for Arrumo plugins.

Copyright © 2026 DEVS AI Unipessoal LDA. Licensed under the [GNU Affero General Public License v3.0](LICENSE).

For custom AI solutions for your company, visit [DEVS AI](https://aidevs.pt).

## First plugin

Build, package, install, and run the isolated echo action. [English](docs/en/first-plugin.md) · [Español](docs/es/first-plugin.md) · [Português](docs/pt/first-plugin.md)

## Draft manifest

[manifest.schema.json](manifest.schema.json) defines plugin identity and capability metadata. See the [transcription example](examples/transcription.json).

Capability declarations describe what a plugin offers. The editor validates the package and applies scope and grants when a supported runtime or adapter executes a capability.

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

In schema 10, a setting can add `helpUrl`: an `https` page, up to 512 characters, without credentials or a fragment, that explains where to get the value, such as the provider's API key page. Arrumo shows it as Where to find it beside the field and opens it from the installed manifest, so a page cannot be swapped in from the UI.

An app-scoped field is configured at app scope only. A workspace-scoped field can have an app default and a workspace override. Clearing an override restores the app default. A required field needs a configured value before a host can use the plugin for work that depends on that field. The manifest declares metadata only. Values, defaults, and credentials are never part of a declaration. The host currently validates and displays declarations through its catalog API. The host validates and resolves ordinary values separately. Secure credential storage requires separate host support.

### Bundled transcription adapter

Include adapter descriptors explicitly when packaging a provider. The packager
validates recognized root descriptors against their SDK schemas and the package
manifest before it writes the ZIP.

The [transcription descriptor](transcription.schema.json) is a versioned host contract for reviewed, bundled providers. The descriptor identifies a plugin with the `transcription` capability and names a secret field declared in that plugin's manifest. It also declares the HTTPS endpoint, credential header, and model. The host reads the configured credential from its system store and builds the request itself. Bundled plugins can supply a separate `transcription-timed.json` using the same schema for delivery captions. Its `response.words` mapping describes timed text units, which may be words or full segments. Without a timed descriptor, the host uses the standard descriptor when it declares a timing mapping.

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

Schema 9 gives an action a form and places in the app. `inputs` lists up to 16 fields, each with an `id`, `label`, optional `description`, `required` and a `kind`: `text`, `longText`, `number`, `boolean`, `choice` (with `choices`), `language`, `subtitles` or `json`. Arrumo shows the form instead of a JSON box and sends `input` as an object keyed by input ID. A `subtitles` input lets the creator pick a subtitle track of the video in view, open an SRT file or paste one, and it sends the SRT text. `placements` lists where the action is offered besides Settings: `draft` (beside a draft), `generation` (on a video's generation page) and `completed-video` (on a finished video, including its right-click menu). `translations.<lang>.actions.<id>.inputs.<input>` translates an input's `label`, `description` and `choices`.

```json
{"id": "translate-subtitles", "label": "Translate subtitles", "description": "…", "scope": "workspace",
 "inputs": [
   {"id": "subtitles", "label": "Subtitles", "kind": "subtitles", "required": true},
   {"id": "language", "label": "Into", "kind": "language", "required": true}
 ],
 "placements": ["completed-video"]}
```

#### Run an action on its own (hooks)

A schema 9 workspace action can also declare `hooks`, so it runs without anyone opening its form. There are three events, at most one hook each: `video-completed` fires once per finished video, after Arrumo has verified the delivery files; `generation-failed` fires once per failed generation attempt; and `publish-date-reached` fires once per finished output on the date the creator planned for it in the calendar. Each hook names a boolean setting of the same plugin in `enabledBy`, and runs only while that setting resolves to `true` for the workspace, so nothing happens until the creator turns it on. Arrumo shows the hook beside the action's form.

```json
"settings": [{"id": "auto-upload", "label": "Upload finished videos", "description": "…",
              "kind": "boolean", "scope": "workspace", "required": false}],
"actions": [{"id": "upload", "label": "Upload", "description": "…", "scope": "workspace",
             "hooks": [{"event": "video-completed", "enabledBy": "auto-upload"}]}]
```

A hooked run is an ordinary action job, listed with the others in **Plugin actions**. Its input is the event instead of form values:

```json
{"event": "video-completed",
 "video": {"runId": 3, "title": "Launch", "profile": "Shorts",
           "outputs": [{"formatId": 5, "format": "Landscape", "durationSeconds": 12.5, "scheduledFor": "2026-11-20"}],
           "texts": [{"kind": "description", "format_id": null, "text": "…"}]}}
```

`texts` holds the approved title, description and tags; it is emptied when the input would pass the 64 KiB plugin limit. The job ID derives from the event, the video (and the attempt) and the action, so a repeated event never runs a hook twice.

A `generation-failed` hook receives the run, its attempt and the problem Arrumo recorded (up to 2,000 characters):

```json
{"event": "generation-failed",
 "video": {"runId": 3, "title": "Launch", "profile": "Shorts", "attempt": 1, "problem": "The agent stopped before rendering."}}
```

A `publish-date-reached` hook receives the `video-completed` shape with `"event": "publish-date-reached"` and only the output whose date arrived. Arrumo checks every few minutes while it is open; a date up to seven days old still counts, so a day the app was closed is not lost. Each output and date runs the hook once, even if the date is moved back to it.

The creator can skip a switched-on hook for one video when they generate it.

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

An optional `voiceSetting` names a non-secret string setting declared in the
manifest where creators choose a voice, and `defaultVoice` is the voice used
when that setting is empty. Hosts use them when a workflow needs speech
without asking for a voice, such as narrating a storyboarded video.

### Describe an image generation adapter

A plugin declaring `image-generation` can provide an `image-generation.json`
[descriptor](image-generation.schema.json) for an HTTPS JSON POST API that
returns one base64-encoded image. The `request` is a JSON template: string
values that are exactly `{prompt}`, `{aspectRatio}` or `{model}` are replaced,
and `{prompt}` must appear. `aspectRatios` maps the ratios Arrumo asks for
(`16:9`, `9:16`, `1:1`, and optionally more) to the provider's value, such as a
pixel size or the ratio itself. The endpoint may contain `{model}` in a path
segment. `model.default` is used unless the creator sets the string setting
named by `model.setting`, so providers can move to newer models without a new
release. `response.image` points at the base64 data; with `response.items`, the
host uses the first array item where that pointer resolves.

The host checks the descriptor against the manifest, sends the workspace secret
in the declared header, refuses redirects, bounds the response by
`maxImageBytes`, verifies that the decoded bytes are a PNG, JPEG or WebP image,
and stores it as a workspace asset. Providers are tried in the run's captured
`image-generation` order; one without a configured credential is skipped.

### Describe a video generation adapter

A plugin declaring `video-generation` can provide a `video-generation.json`
[descriptor](video-generation.schema.json) for an asynchronous HTTPS API. The
host POSTs the `request` template with `{prompt}`, `{aspectRatio}` and
`{duration}` filled in (the duration as a number, clamped to `durations`),
reads the job's status address from `submission.statusUrl`, and polls it every
`pollSeconds` until `status.state` is one of `completed` or `failed`, or until
`timeoutSeconds` pass. The status address must be HTTPS on the endpoint's host,
because it receives the credential. `status.video` points at the finished
clip's HTTPS address, which the host downloads without the credential, bounds
by `maxVideoBytes`, verifies as MP4, MOV or WebM, and stores as a workspace
asset. `status.error` can point at a short reason shown to the creator.
Providers are tried in the workspace's `video-generation` order; one without a
configured key, or without the requested ratio in `aspectRatios`, is skipped.

Schema 2 descriptors can offer several models. `models` maps each model ID to
up to four request variants; the host calls the first variant whose `images`
and `videos` ranges fit the reference media the creator or agent attached (an
absent range takes none), so one model can have text-to-video, image-to-video
and reference-to-video endpoints. `model.default` and an optional string
setting with matching `choices` pick the model when the caller names none.
References are workspace image or MP4 assets: the host uploads each through
`upload` (a credentialed POST on the provider's host that returns a presigned
HTTPS address and a public one, then a PUT without the credential) and fills
`{image}`, `{images}`, `{video}` or `{videos}` with the public addresses. The
top-level `endpoint`, `aspectRatios`, `durations` and `request` stay as the
schema 1 fallback.

### Describe a usage adapter

A provider plugin can add a `usage.json` [descriptor](usage.schema.json) so
creators see how much of its allowance is left. The host sends a GET to
`endpoint` with the workspace credential, refuses redirects, and reads the
numbers at the `used` and `limit` pointers (and optionally `resetsAt`, in Unix
seconds). Arrumo shows the remaining share in Settings › Services and keys,
warns across the top of the app at 20% left and again in the danger color at
10%, and repeats the warning before a generation that uses the provider. A
failed read is shown as unknown, never as empty.

### Introduction and the plugin tour

Schema version 8 adds an optional `introduction`. When plugins arrive after the
creator's first launch (installed from a ZIP or the registry, or bundled by an
update), Arrumo introduces them in one shared tour, one page per plugin with its
name, `headline` and `body`. Plugins present on first launch are not toured.
Creators can replay the tour from Settings › Plugins. Text is keyed by language:
`en` is required, `es` and `pt` are used when the app is in those languages.
Headlines are at most 80 characters and bodies 320.

```json
"introduction": {
  "headline": {"en": "Your videos, in more languages", "es": "Tus vídeos, en más idiomas"},
  "body": {"en": "Pick a finished video and the languages you want…"}
}
```

### Icon and translations

Schema 8 also adds an optional `icon`: the path of an SVG file in the
package, such as `"icon": "icon.svg"`. Keep the SVG self-contained and at most
8 KiB. Arrumo shows it as an image wherever the plugin appears, such as beside
the agent that is working, so it cannot run script; the host refuses icons with
script, event handlers, `href`, `url(…)`, embedded images or documents. Draw
the icon with its own background shape and colours. `package_plugin.py` adds
the declared icon to the ZIP, and plugins without an icon get a default one.

#### Brand marks: check before you ship one

A company's logo may appear as a plugin icon only when that company's published
brand guidelines allow it inside another app's interface. Do this check before
the logo goes into the package, not after:

1. Read the company's own brand, press or trademark page. A notice in the
   manifest does not grant permission.
2. Use the logo only if the page allows this use without asking (for example a
   mark offered for app ecosystems or integrations). Use the company's own file,
   unmodified, and follow its conditions on clear space, colour and size.
3. If the page asks you to request permission, sits behind a partner login, or
   cannot be found, draw a generic symbol of what the plugin does instead, such as
   a terminal prompt for a command-line agent or a picture frame for images.
4. Record the result in the plugin README under "Icon and trademarks": which page
   you read, what it allows, and why the icon is a mark or a generic symbol.

When the icon is a mark, add `iconNotice` naming the owner (for example
"ElevenLabs and its logo are trademarks of ElevenLabs."). Arrumo shows it
beside the plugin, and `translations` may translate it like other text. Generic
symbols carry no notice.

The official plugins were checked on 2026-11-22. ElevenLabs' brand page
recommends its "11" symbol for app ecosystems. OpenAI asks for permission first,
Google keeps the Gemini guidelines behind a partner login, and Anthropic and
Higgsfield publish no rule for this use. The publisher of the official plugins
chose to show each provider's logo with an `iconNotice` anyway, so creators
recognise the service, and will replace a logo with a generic symbol if its owner
asks. Third-party plugins should still follow the steps above.

#### Icon shape

Draw the icon as a full square tile (for example a 32×32 `viewBox` whose first
shape is a `<rect width="32" height="32">` in the background colour) with
square corners and no border. Arrumo rounds the corners and draws a faint edge
the same way for every plugin, at every size.

Plugins translate their own text. English stays in the manifest's fields, and
`translations.es` and `translations.pt` override the plugin `name` and
`description`, the agent `provider.label`, and each declared capability,
setting (`label`, `description`, and `choices` labels keyed by value) and
action. `translations.en` may add labels the base fields lack, such as choice
labels. Every key must name something the manifest declares.

```json
"translations": {
  "en": {"settings": {"reasoning-effort": {"choices": {"xhigh": "Extra high"}}}},
  "es": {"description": "Usa tu plan de ChatGPT…",
         "settings": {"web-search": {"label": "Búsqueda web"}}}
}
```

### Structured agent runs

Schema version 7 lets an agent provider declare `agentProvider.cli.structuredRun`.
The host uses it for production stages such as writing the script. It runs the
provider's executable once, in an empty temporary directory, with the prompt on
stdin and a JSON Schema the answer must follow.

```json
"structuredRun": {
  "args": ["exec", "--sandbox", "read-only", "--output-schema", "{schemaPath}",
           "--output-last-message", "{outputPath}", "-"],
  "result": { "source": "outputFile" }
}
```

Placeholders are whole arguments: `{schema}` is the schema as JSON, `{schemaPath}`
a file containing it, and `{outputPath}` a file the agent writes its answer to.
Every run must pass the schema through one of the first two. `result.source` is
`outputFile` or `stdout`. `pointer` selects the answer inside that document, and
`errorPointer` names a boolean that is true when the agent reports a failure.
The host validates the answer against the schema, bounds its size, enforces a
time limit, and treats a non-zero exit as a failure. Providers own the flags that
keep the run non-interactive and free of tools, hooks and network access the
stage does not need.

The agent's capabilities belong to its plugin. Declare them as ordinary
`settings` and map each to flags with `settingArgs`; the host inserts the chosen
arguments at a `{settings}` placeholder. A boolean setting uses `args` when true
and `otherwise` when false or unset. Other settings use `args` with `{value}`
replaced, accepting only plain words (letters, digits, `.`, `_`, `:` and `-`),
and a string setting with `choices` only accepts one of them. A setting's
`default` applies when neither the app nor the workspace sets a value. The host
freezes the resolved values into each generation run so it can be reproduced.

`progress` lets the host show what the agent is doing while it works. Each
entry is a regular expression matched against every line the agent prints;
its first capture group (or `label`) becomes a step of kind `thinking`,
`search` or `step`, so creators can follow the reasoning and searches live. Agents that print one JSON event per line add a `pointer` to each pattern to
match the text at that place in the event, and read their answer with the result
source `stdoutLastLine`.

Agents that can look at images declare `imageArgs`, such as `["-i", "{imagePath}"]`,
and place `{images}` in `args`. The host repeats those arguments once per image
it wants the agent to see, such as thumbnail references or images found while
researching a creator, and leaves `{images}` empty for agents without it.

Agents with their own image tool also declare the `image-generation` capability
and an `imageRun`. Arrumo sends the image brief on stdin, reads the session ID
from the printed JSON events at `sessionPointer`, and collects the newest PNG,
JPEG or WebP file from `outputDirectory`: `path` (with `{session}`) under the
directory in the environment variable `env`, or under `fallback` in the home
directory. The agent stays read-only and writes nothing itself. Arrumo verifies
and crops the image like any other provider's, and removes what the run left.
`{images}` attaches style references using `structuredRun.imageArgs`.

```json
"imageRun": {
  "args": ["exec", "--sandbox", "read-only", "--enable", "image_generation", "{images}", "--json", "-"],
  "sessionPointer": "/thread_id",
  "outputDirectory": {"env": "CODEX_HOME", "fallback": ".codex", "path": "generated_images/{session}"}
}
```

```json
"settings": [
  {"id": "web-search", "label": "Web search", "description": "…", "kind": "boolean",
   "scope": "workspace", "required": false, "default": false},
  {"id": "reasoning-effort", "label": "Reasoning effort", "description": "…",
   "kind": "string", "scope": "workspace", "required": false,
   "choices": ["low", "medium", "high"], "default": "medium"}
],
"structuredRun": {
  "args": ["exec", "{settings}", "--output-schema", "{schemaPath}", "-"],
  "settingArgs": [
    {"setting": "web-search", "args": ["-c", "web_search=\"live\""],
     "otherwise": ["-c", "web_search=\"disabled\""]},
    {"setting": "reasoning-effort", "args": ["-c", "model_reasoning_effort=\"{value}\""]}
  ],
  "result": { "source": "outputFile" }
}
```

#### Follow-up messages

When an agent asks the host for workspace material, Arrumo answers in the same
session if the plugin declares `resume`, sending only the new material instead
of the whole brief again. Put `{ephemeral}` in `args` where the flags that stop
the agent keeping a session belong, and list them in `ephemeralArgs`; the host
leaves them out only for a run it will follow up. `resume.args` replaces `args`
for the follow-up, with `{session}` for the ID read from `resume.session`. If a
session cannot be continued (it is gone, unreadable or stuck), the host starts
a new one with the whole brief and all material so far.

Declare `resume.cleanup` so kept sessions do not pile up in the agent's own
history: Arrumo records each session it keeps and deletes its files once the
video it belongs to has completed, failed or been cancelled, or right after a
request that has no video. It looks under `directory` in the folder the
`homeEnv` variable names (absolute paths only), or else `home` in the user's
home folder, for files whose names end with `fileSuffix`. It never follows
links and removes folders the deletion leaves empty.

```json
"args": ["exec", "{ephemeral}", "--output-schema", "{schemaPath}", "-"],
"ephemeralArgs": ["--ephemeral"],
"resume": {
  "args": ["exec", "resume", "--output-schema", "{schemaPath}", "{session}", "-"],
  "session": {"stream": "stderr", "pattern": "^session id: ([0-9A-Za-z-]+)$"},
  "cleanup": {"homeEnv": "CODEX_HOME", "home": ".codex", "directory": "sessions", "fileSuffix": "{session}.jsonl"}
}
```

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
