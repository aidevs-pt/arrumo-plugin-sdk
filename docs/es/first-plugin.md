# Compila y ejecuta tu primer plugin

[English](../en/first-plugin.md) · [Português](../pt/first-plugin.md)

Este ejemplo compila un componente WebAssembly aislado y ejecuta una acción que devuelve el JSON enviado. Necesitas la CLI local del editor, Python 3.11 o posterior con jsonschema y una versión de wasm-tools compatible con el modelo de componentes.

## Compila e instala el ejemplo

Desde el repositorio del SDK, sustituye la ruta del editor por la ruta absoluta de tu CLI local. El ejemplo usa un directorio temporal y una base de datos nueva.

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

El último comando devuelve JSON con el valor echo en action y tu mensaje dentro de input. La instalación del ZIP también muestra un resumen SHA-256. Guárdalo para revisar el paquete o verificarlo en el registro.

## Adapta el ejemplo

Asigna a tu plugin un identificador propio en manifest.json. Declara las acciones y su ámbito en el manifiesto e implementa la interfaz de componentes del SDK en el backend. Prueba cada acción con el mismo ámbito y formato de entrada que usarán tus clientes.

Limita el plugin a las capacidades que necesite. Una acción de ámbito de aplicación no recibe datos del espacio de trabajo. Para una acción de ámbito de espacio de trabajo, pasa su identificador y obtén los permisos que requieran las llamadas al host. Mantén las credenciales fuera del manifiesto, del paquete y de los ejemplos.

Consulta el [esquema del manifiesto](../../manifest.schema.json), la [interfaz de componentes](../../wit/plugin.wit) y la [referencia del SDK](../../README.md) antes de añadir capacidades del host o una interfaz de usuario.
