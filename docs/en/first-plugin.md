# Build and run your first plugin

[Español](../es/first-plugin.md) · [Português](../pt/first-plugin.md)

This example builds an isolated WebAssembly component and runs an action that returns the JSON you sent. Use a local editor CLI, Python 3.11 or later with jsonschema, and wasm-tools with component-model support.

## Build and install the example

From the Plugin SDK checkout, replace the editor path below with the absolute path to your local CLI. The example uses a temporary directory and a fresh database.

```sh
sdk="$PWD"
editor="/absolute/path/to/arrumo-workspaces"
work="$(mktemp -d)"
cp "$sdk/examples/actions/manifest.json" "$work/manifest.json"
wasm-tools parse "$sdk/examples/component/echo.wat" -o "$work/echo.wasm"
wasm-tools validate "$work/echo.wasm"
python3 "$sdk/tools/package_plugin.py" "$work" "$work/action-echo.zip" --include echo.wasm

database="$work/workspaces.sqlite"
"$editor" "$database" install-plugin-zip "$work/action-echo.zip"
"$editor" "$database" plugin-actions
printf '%s\n' '{"message":"Hello"}' |
  "$editor" "$database" invoke-plugin-action action-echo echo app
```

The last command returns JSON with action set to echo and input containing your message. The ZIP installation also reports a SHA-256 digest. Keep it for package review or registry verification.

## Adapt the example

Give your plugin its own ID in manifest.json. Declare actions and their scope in the manifest, and implement the SDK component interface in your backend. Test each action with the same scope and input shape your callers will use.

Limit your plugin to the capabilities it needs. An app-scoped action does not receive workspace data. For a workspace action, pass a workspace ID and obtain any permissions required by its host calls. Keep credentials out of the manifest, package and example payloads.

Review the [manifest schema](../../manifest.schema.json), [component interface](../../wit/plugin.wit), and [SDK reference](../../README.md) before adding host capabilities or a frontend surface.
