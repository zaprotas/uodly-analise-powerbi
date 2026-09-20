"""
Troca o caminho absoluto das sete consultas por um parâmetro do Power Query.

Antes, cada partição trazia o caminho absoluto da máquina de quem construiu:
    File.Contents("C:\\Users\\...\\uodly_powerbi.xlsx")

Isso tem dois problemas num repositório público: revela a estrutura de pastas
de quem construiu, e quebra para qualquer pessoa que clone — ela teria que
editar sete arquivos à mão.

Com o parâmetro, quem clonar muda um valor só, em Transformar dados →
Gerenciar parâmetros.

Uso: python analysis/uodly/parametrizar_caminho.py <pasta-dos-dados>
"""

import re
import sys
import uuid
from pathlib import Path

MODELO = Path(
    "powerbi/Uodly Analytics.SemanticModel/definition"
)
PARAMETRO = "PastaDados"
PLANILHA = "uodly_powerbi.xlsx"


def gravar(caminho: Path, texto: str):
    """UTF-8 sem BOM e CRLF, como o Power BI Desktop grava."""
    caminho.write_text(
        texto.replace("\r\n", "\n").replace("\n", "\r\n"), encoding="utf-8", newline=""
    )


def criar_expressao(pasta_padrao: str):
    """O parâmetro em si, num expressions.tmdl ao lado do model.tmdl."""
    destino = MODELO / "expressions.tmdl"
    # Sem `queryGroup`: o grupo de consultas precisaria estar declarado no
    # modelo, e referenciar um que não existe impede o projeto de abrir.
    conteudo = f'''expression {PARAMETRO} = "{pasta_padrao}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
\tlineageTag: {uuid.uuid4()}

\tannotation PBI_NavigationStepName = Navigation

\tannotation PBI_ResultType = Text

'''
    gravar(destino, conteudo)
    return destino


def referenciar_no_modelo():
    caminho = MODELO / "model.tmdl"
    texto = caminho.read_text(encoding="utf-8")
    if f"ref expression {PARAMETRO}" in texto:
        return False

    # A referência entra logo depois do último `ref table`, antes do cultureInfo.
    marcador = "\nref cultureInfo"
    pos = texto.index(marcador)
    novo = texto[:pos] + f"\nref expression {PARAMETRO}\n" + texto[pos:]
    gravar(caminho, novo)
    return True


def trocar_partições():
    alterados = []
    padrao = re.compile(r'File\.Contents\("[^"]*' + re.escape(PLANILHA) + r'"\)')
    substituto = f'File.Contents({PARAMETRO} & "\\\\{PLANILHA}")'

    for arquivo in sorted((MODELO / "tables").glob("*.tmdl")):
        texto = arquivo.read_text(encoding="utf-8")
        novo, n = padrao.subn(substituto, texto)
        if n:
            gravar(arquivo, novo)
            alterados.append((arquivo.name, n))
    return alterados


def main():
    pasta = sys.argv[1] if len(sys.argv) > 1 else str(
        (Path.cwd() / "analysis/uodly/powerbi").resolve()
    )

    # Sem duplicar barras: em Power Query a barra invertida não é caractere
    # de escape, então "C:\\dev" seria um caminho literalmente com duas barras.
    expressao = criar_expressao(pasta)
    print(f"parâmetro criado em {expressao.name} com valor padrão:")
    print(f"  {pasta}")

    if referenciar_no_modelo():
        print("referência adicionada em model.tmdl")
    else:
        print("model.tmdl já referenciava o parâmetro")

    print("\npartições reescritas:")
    for nome, n in trocar_partições():
        print(f"  {nome:<26} {n} ocorrência")


if __name__ == "__main__":
    main()
