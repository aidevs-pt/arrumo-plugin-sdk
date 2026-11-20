# Compila e executa o teu primeiro plugin

[English](../en/first-plugin.md) · [Español](../es/first-plugin.md)

Este exemplo compila um componente WebAssembly isolado e executa uma ação que devolve o JSON enviado. Usa a CLI local do editor, Python 3.11 ou posterior com jsonschema e uma versão de wasm-tools compatível com o modelo de componentes.

## Compila e instala o exemplo

A partir do repositório do SDK, substitui o caminho do editor pelo caminho absoluto da tua CLI local. O exemplo usa uma pasta temporária e uma base de dados nova.

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

O último comando devolve JSON com o valor echo em action e a tua mensagem em input. A instalação do ZIP também apresenta o resumo SHA-256. Guarda-o para a revisão do pacote ou a verificação no registo.

## Adapta o exemplo

Atribui ao plugin um identificador próprio em manifest.json. Declara as ações e o respetivo âmbito no manifesto e implementa no backend a interface de componentes do SDK. Testa cada ação com o mesmo âmbito e formato de entrada que os teus clientes vão usar.

Limita o plugin às capacidades de que precisa. Uma ação ao nível da aplicação não recebe dados do espaço de trabalho. Para uma ação ao nível do espaço de trabalho, passa o seu identificador e obtém as permissões necessárias para as chamadas ao host. Mantém as credenciais fora do manifesto, do pacote e dos exemplos.

Consulta o [esquema do manifesto](../../manifest.schema.json), a [interface de componentes](../../wit/plugin.wit) e a [referência do SDK](../../README.md) antes de adicionares capacidades do host ou uma interface de utilizador.
