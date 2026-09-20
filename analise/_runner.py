"""
Executa um script de análise dividido em células (`# %%`) e captura, para cada
uma, o código e a saída real.

O resultado vira JSON consumido pelo site. A garantia que isso dá: o código
exibido no portfólio é exatamente o código que rodou, e a saída exibida é
exatamente a que ele produziu — nada é transcrito à mão.

Uso: python analysis/_runner.py <script.py> <saida.json>
"""

import ast
import io
import json
import re
import sys
from contextlib import redirect_stdout
from pathlib import Path

MARCADOR = re.compile(r"^# %%(?:\s+(.*))?$", re.MULTILINE)


def dividir_celulas(fonte: str):
    marcas = list(MARCADOR.finditer(fonte))
    celulas = []

    for i, marca in enumerate(marcas):
        fim = marcas[i + 1].start() if i + 1 < len(marcas) else len(fonte)
        codigo = fonte[marca.end() : fim].strip("\n")
        celulas.append({"titulo": (marca.group(1) or "").strip(), "codigo": codigo})

    return celulas


def executar(celula, escopo):
    """Roda a célula e devolve stdout + o repr da última expressão, como no Jupyter."""
    try:
        modulo = ast.parse(celula["codigo"])
    except SyntaxError as erro:
        raise SystemExit(f"erro de sintaxe na célula '{celula['titulo']}': {erro}")

    ultima = None
    if modulo.body and isinstance(modulo.body[-1], ast.Expr):
        ultima = ast.Expression(modulo.body[-1].value)
        ast.copy_location(ultima.body, modulo.body[-1].value)
        modulo = ast.Module(body=modulo.body[:-1], type_ignores=[])

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exec(compile(modulo, "<cell>", "exec"), escopo)

        if ultima is not None:
            valor = eval(compile(ultima, "<cell>", "eval"), escopo)
            if valor is not None:
                print(repr_amigavel(valor))

    return buffer.getvalue().rstrip("\n")


def repr_amigavel(valor):
    try:
        import pandas as pd

        if isinstance(valor, (pd.DataFrame, pd.Series)):
            return valor.to_string()
    except ImportError:
        pass
    return repr(valor)


def main():
    if len(sys.argv) != 3:
        raise SystemExit("uso: python _runner.py <script.py> <saida.json>")

    script = Path(sys.argv[1]).resolve()
    saida = Path(sys.argv[2]).resolve()

    fonte = script.read_text(encoding="utf-8")
    celulas = dividir_celulas(fonte)

    escopo = {"__name__": "__analise__", "__file__": str(script)}
    sys.path.insert(0, str(script.parent))

    resultado = []
    for celula in celulas:
        texto = executar(celula, escopo)
        resultado.append(
            {
                "titulo": celula["titulo"],
                "codigo": celula["codigo"],
                "saida": texto,
            }
        )
        print(f"  célula {len(resultado)}: {celula['titulo'] or '(sem título)'}")

    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n{len(resultado)} células -> {saida}")


if __name__ == "__main__":
    main()
