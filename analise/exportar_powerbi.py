"""
Exporta o corpus do caso Uodly.app em formato de modelo dimensional, pronto
para o Power BI consumir.

Os CSVs de `dados/` são o formato da análise: largos, com colunas derivadas e
índices implícitos. O Power BI trabalha melhor com estrela — fatos finos
ligados a dimensões por chave. Este script faz essa tradução.

Saída: analysis/uodly/powerbi/*.csv
"""

from pathlib import Path

import numpy as np
import pandas as pd

ORIGEM = Path(__file__).resolve().parents[1] / "dados"
DESTINO = Path(__file__).resolve().parents[1] / "dados"

CONTEUDO_CODIFICAVEL = ["tentativa_tarefa", "pensando_alto"]

ROTULOS_TIPO = {
    "tentativa_tarefa": "Tentativa de tarefa",
    "fala_moderador": "Fala do moderador",
    "pensando_alto": "Pensando alto",
    "silencio": "Silêncio",
    "fora_do_tema": "Fora do tema",
}


def main():
    DESTINO.mkdir(parents=True, exist_ok=True)

    sessoes = pd.read_csv(ORIGEM / "sessoes.csv")
    segmentos = pd.read_csv(ORIGEM / "segmentos.csv")
    achados = pd.read_csv(ORIGEM / "achados.csv")
    tarefas = pd.read_csv(ORIGEM / "tarefas.csv")

    # --- Dimensões ---
    dim_sessao = sessoes.rename(
        columns={"segmento": "perfil", "duracao_min": "duracao_minutos"}
    )
    dim_sessao["duracao_horas"] = (dim_sessao.duracao_minutos / 60).round(2)

    dim_tema = (
        achados.groupby("tema", as_index=False)
        .severidade.max()
        .assign(
            gravidade=lambda d: d.severidade.map(
                {1: "1 · baixa", 2: "2 · média", 3: "3 · alta", 4: "4 · crítica"}
            )
        )
    )

    dim_tipo_trecho = pd.DataFrame(
        {
            "tipo": list(ROTULOS_TIPO),
            "tipo_rotulo": list(ROTULOS_TIPO.values()),
            "codificavel": [t in CONTEUDO_CODIFICAVEL for t in ROTULOS_TIPO],
        }
    )

    # --- Fatos ---
    # Marca quais trechos viraram achado, casando pela posição no vídeo.
    chave_achado = set(zip(achados.sessao_id, achados.inicio_s))
    fato_trecho = segmentos.copy()
    fato_trecho["gerou_achado"] = [
        (s, i) in chave_achado for s, i in zip(fato_trecho.sessao_id, fato_trecho.inicio_s)
    ]
    fato_trecho["duracao_min"] = (fato_trecho.duracao_s / 60).round(3)

    fato_achado = achados.copy()
    fato_achado["duracao_min"] = (fato_achado.duracao_s / 60).round(3)

    fato_tarefa = tarefas.copy()
    # Coluna explícita para o caso que sustenta a hipótese 02: a pessoa disse
    # que deu certo e não deu. Em DAX daria para derivar, mas deixar pronta
    # evita que o visual dependa de uma medida escrita errado.
    fato_tarefa["relato_falso_positivo"] = (
        fato_tarefa.relato_sucesso & ~fato_tarefa.concluiu
    )
    fato_tarefa["resultado"] = np.where(
        fato_tarefa.concluiu, "Concluiu", "Não concluiu"
    )
    fato_tarefa["relato"] = np.where(
        fato_tarefa.relato_sucesso, "Relatou sucesso", "Relatou fracasso"
    )

    # --- Apoio: a curva de saturação vem de bootstrap, não sai em DAX ---
    rng = np.random.default_rng(4)
    ids = sessoes.sessao_id.to_numpy()

    def acumulado(ordem):
        vistos, curva = set(), []
        for sessao in ordem:
            vistos |= set(achados[achados.sessao_id == sessao].tema)
            curva.append(len(vistos))
        return curva

    curvas = np.array([acumulado(rng.permutation(ids)) for _ in range(300)])
    apoio_saturacao = pd.DataFrame(
        {
            "sessoes_analisadas": np.arange(1, len(ids) + 1),
            "temas_media": curvas.mean(axis=0).round(2),
            "temas_p10": np.percentile(curvas, 10, axis=0).round(2),
            "temas_p90": np.percentile(curvas, 90, axis=0).round(2),
        }
    )
    apoio_saturacao["cobertura_pct"] = (
        apoio_saturacao.temas_media / achados.tema.nunique() * 100
    ).round(1)

    tabelas = {
        "dim_sessao": dim_sessao,
        "dim_tema": dim_tema,
        "dim_tipo_trecho": dim_tipo_trecho,
        "fato_trecho": fato_trecho,
        "fato_achado": fato_achado,
        "fato_tarefa": fato_tarefa,
        "apoio_saturacao": apoio_saturacao,
    }

    for nome, df in tabelas.items():
        # UTF-8 com BOM: é o que faz o Power BI reconhecer acentuação nos
        # CSVs sem precisar escolher a codificação na mão a cada importação.
        df.to_csv(DESTINO / f"{nome}.csv", index=False, encoding="utf-8-sig")
        print(f"{nome + '.csv':<24} {len(df):>5} linhas · {len(df.columns)} colunas")

    # Uma pasta com sete CSVs de formatos diferentes é uma armadilha no Power
    # BI: o conector de pasta oferece "Combinar", que empilha tudo numa tabela
    # só. Um .xlsx com sete abas resolve em uma importação, e cada aba entra
    # como uma tabela com o nome certo.
    planilha = DESTINO / "uodly_powerbi.xlsx"
    with pd.ExcelWriter(planilha, engine="openpyxl") as writer:
        for nome, df in tabelas.items():
            df.to_excel(writer, sheet_name=nome, index=False)

    print(f"\n{planilha.name:<24} {len(tabelas)} abas")
    print(f"\n{DESTINO}")


if __name__ == "__main__":
    main()
