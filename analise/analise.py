"""
Análise do corpus de pesquisa do caso "Uodly.app".

O objeto da análise é o corpus e o método de priorização — não o desempenho
do produto. Ver o cabeçalho de gerar_dados.py.

Rode com o runner para capturar código e saída de cada célula:
    python analysis/_runner.py analysis/uodly/analise.py \
        src/data/analise/uodly.celulas.json
"""

# %% Carregando o corpus
import json
from pathlib import Path

import numpy as np
import pandas as pd

DADOS = Path("dados")

sessoes = pd.read_csv(DADOS / "sessoes.csv")
segmentos = pd.read_csv(DADOS / "segmentos.csv")
achados = pd.read_csv(DADOS / "achados.csv")
tarefas = pd.read_csv(DADOS / "tarefas.csv")

print(f"{len(sessoes)} sessões · {segmentos.duracao_s.sum() / 3600:.1f} h de material")
segmentos.head(5)

# %% Onde está o sinal no material bruto
tempo = (
    segmentos.groupby("tipo").duracao_s.sum().sort_values(ascending=False) / 3600
).round(2)
tempo = tempo.to_frame("horas")
tempo["pct"] = (tempo.horas / tempo.horas.sum() * 100).round(1)

horas_achado = achados.duracao_s.sum() / 3600
print(tempo.to_string())
print(f"\ntotal: {tempo.horas.sum():.1f} h")
print(f"trechos que viraram achado: {horas_achado:.1f} h ({horas_achado / tempo.horas.sum():.1%})")

# %% O que se diz contra o que se faz
matriz = pd.crosstab(tarefas.relato_sucesso, tarefas.concluiu)
matriz.index = ["relatou fracasso", "relatou sucesso"]
matriz.columns = ["não concluiu", "concluiu"]

# Kappa de Cohen na mão: a concordância observada menos a que aconteceria por
# acaso, normalizada pelo espaço que sobra para concordar.
n = matriz.values.sum()

# Concordar é relatar sucesso tendo concluído, ou relatar fracasso tendo
# falhado — a diagonal principal da matriz.
po = float(np.trace(matriz.values) / n)

linhas = matriz.values.sum(axis=1) / n
colunas = matriz.values.sum(axis=0) / n
pe = float((linhas * colunas).sum())

kappa = (po - pe) / (1 - pe)

print(matriz.to_string())
print(f"\nconcluiu a tarefa: {tarefas.concluiu.mean():.1%}")
print(f"relatou sucesso:   {tarefas.relato_sucesso.mean():.1%}")
print(f"\nconcordância observada  po = {po:.3f}")
print(f"concordância por acaso  pe = {pe:.3f}")
print(f"kappa de Cohen           κ = {kappa:.3f}")

# %% Severidade contra frequência
matriz_temas = (
    achados.groupby("tema")
    .agg(ocorrencias=("tema", "size"),
         sessoes=("sessao_id", "nunique"),
         severidade=("severidade", "max"))
    .reset_index()
)
matriz_temas["pct_sessoes"] = (matriz_temas.sessoes / len(sessoes) * 100).round(0)
matriz_temas = matriz_temas.sort_values(["severidade", "sessoes"], ascending=False)

print(matriz_temas.head(8).to_string(index=False))

# %% Quantas sessões bastam
def temas_acumulados(ordem):
    vistos, curva = set(), []
    for sessao in ordem:
        vistos |= set(achados[achados.sessao_id == sessao].tema)
        curva.append(len(vistos))
    return curva


rng = np.random.default_rng(4)
ids = sessoes.sessao_id.to_numpy()

# Bootstrap: a curva depende da ordem em que as sessões acontecem, então
# sorteia 300 ordens e olha a distribuição, não uma ordem só.
curvas = np.array([temas_acumulados(rng.permutation(ids)) for _ in range(300)])

media = curvas.mean(axis=0)
total = achados.tema.nunique()
n80 = int(np.argmax(media >= 0.8 * total) + 1)

print(f"{total} temas no corpus inteiro")
print(f"80% deles aparecem, em média, até a sessão {n80}")
print()
for k in (3, 5, 8, 12, 24):
    print(f"  {k:>2} sessões: {media[k - 1]:.1f} temas ({media[k - 1] / total:.0%})")

# %% A priorização muda conforme o critério
ranking = matriz_temas.set_index("tema")
criterios = {
    "Por frequência": ranking.sessoes,
    "Por severidade": ranking.severidade,
    "Severidade × frequência": ranking.severidade * ranking.sessoes,
}

posicoes = pd.DataFrame(
    {nome: valor.rank(ascending=False, method="first").astype(int)
     for nome, valor in criterios.items()}
)
topo = posicoes[posicoes["Severidade × frequência"] <= 8].sort_values(
    "Severidade × frequência"
)

print(topo.to_string())
print(f"\ntroca de posição entre os critérios extremos: "
      f"{int((topo['Por frequência'] - topo['Por severidade']).abs().max())} lugares")

# %% Exportando as séries para o site
saida = {
    "tempo": [
        {"tipo": t, "horas": float(r.horas), "pct": float(r.pct)}
        for t, r in tempo.iterrows()
    ],
    "sinal": {
        "horasTotal": round(float(tempo.horas.sum()), 1),
        "horasAchado": round(float(horas_achado), 1),
        "pct": round(float(horas_achado / tempo.horas.sum() * 100), 1),
    },
    "ditoFeito": {
        "matriz": [
            {"relato": i, "feito": c, "n": int(matriz.loc[i, c])}
            for i in matriz.index
            for c in matriz.columns
        ],
        "po": round(float(po), 3),
        "pe": round(float(pe), 3),
        "kappa": round(float(kappa), 3),
        "concluiu": round(float(tarefas.concluiu.mean() * 100), 1),
        "relatou": round(float(tarefas.relato_sucesso.mean() * 100), 1),
    },
    "temas": [
        {"tema": r.tema, "sessoes": int(r.sessoes), "severidade": int(r.severidade),
         "ocorrencias": int(r.ocorrencias)}
        for r in matriz_temas.itertuples()
    ],
    "saturacao": {
        "total": int(total),
        "n80": n80,
        "media": [round(float(v), 2) for v in media],
        "p10": [round(float(v), 2) for v in np.percentile(curvas, 10, axis=0)],
        "p90": [round(float(v), 2) for v in np.percentile(curvas, 90, axis=0)],
    },
    "ranking": [
        {"tema": tema, **{criterio: int(pos) for criterio, pos in linha.items()}}
        for tema, linha in topo.iterrows()
    ],
}

destino = Path("src/data/analise/uodly.series.json")
destino.parent.mkdir(parents=True, exist_ok=True)
destino.write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"{destino} · {len(saida)} blocos")
