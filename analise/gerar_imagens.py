"""
Gera as imagens que contam a análise no README do repositório.

Um repositório de dados sem imagem obriga quem chega a ler código para
entender o que foi feito. Quase ninguém lê. Estes quatro gráficos carregam o
argumento inteiro antes da primeira linha de Python.

A paleta é a mesma do portfólio e do painel em Power BI.

Saída: analysis/uodly/relatorios/*.png
"""

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

DADOS = Path("dados")
SAIDA = Path("imagens")

ACCENT, ACCENT_DEEP, ACCENT_LINE = "#4F46E5", "#3730A3", "#C7D2FE"
ACCENT_SOFT = "#EEF2FF"
INK, INK2, MUTED = "#0F172A", "#334155", "#5B6472"
LINHA, FUNDO = "#E6E8EC", "#F8FAFC"

plt.rcParams.update({
    "figure.dpi": 160,
    "savefig.dpi": 160,
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "text.color": INK2,
    "axes.labelcolor": MUTED,
    "axes.edgecolor": LINHA,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def br(valor, casas=1):
    """Número no formato pt-BR, com vírgula decimal."""
    return f"{valor:.{casas}f}".replace(".", ",")


def moldar(ax, titulo, subtitulo=None):
    ax.set_title(titulo, color=INK, fontsize=11, fontweight="bold", loc="left", pad=18)
    if subtitulo:
        ax.text(0, 1.035, subtitulo, transform=ax.transAxes, color=MUTED, fontsize=8.5)
    ax.grid(axis="x", color=LINHA, linewidth=0.8)
    ax.set_axisbelow(True)


def salvar(fig, nome):
    SAIDA.mkdir(parents=True, exist_ok=True)
    fig.savefig(SAIDA / nome, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  {nome}")


def grafico_material(segmentos, achados):
    rotulos = {
        "tentativa_tarefa": "Tentativa de tarefa",
        "fala_moderador": "Fala do moderador",
        "pensando_alto": "Pensando alto",
        "silencio": "Silêncio",
        "fora_do_tema": "Fora do tema",
    }
    horas = segmentos.groupby("tipo").duracao_s.sum().sort_values() / 3600
    total = horas.sum()
    horas_achado = achados.duracao_s.sum() / 3600

    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    barras = ax.barh([rotulos[t] for t in horas.index], horas.values, color=ACCENT, height=0.62)
    for barra, valor in zip(barras, horas.values):
        ax.text(valor + 0.12, barra.get_y() + barra.get_height() / 2,
                f"{br(valor)} h", va="center", color=INK2, fontsize=8.5)

    moldar(ax, f"Onde estão as {br(total)} horas gravadas",
           f"De todo o material, {br(horas_achado)} h "
           f"({br(100 * horas_achado / total)}%) sustentam algum achado")
    ax.set_xlim(0, horas.max() * 1.18)
    ax.set_xlabel("horas")
    salvar(fig, "01-material-bruto.png")


def grafico_dito_feito(tarefas):
    matriz = pd.crosstab(tarefas.relato_sucesso, tarefas.concluiu)
    celulas = [
        ("Relatou sucesso", "Concluiu", matriz.loc[True, True], False),
        ("Relatou sucesso", "Não concluiu", matriz.loc[True, False], True),
        ("Relatou fracasso", "Concluiu", matriz.loc[False, True], True),
        ("Relatou fracasso", "Não concluiu", matriz.loc[False, False], False),
    ]

    n = len(tarefas)
    po = (matriz.loc[True, True] + matriz.loc[False, False]) / n
    linhas = matriz.values.sum(axis=1) / n
    colunas = matriz.values.sum(axis=0) / n
    pe = float((linhas * colunas).sum())
    kappa = (po - pe) / (1 - pe)

    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.set_xlim(0, 2)
    ax.set_ylim(0, 2)
    ax.axis("off")

    for rotulo_linha, rotulo_coluna, valor, discorda in celulas:
        x = 1 if rotulo_coluna == "Não concluiu" else 0
        y = 1 if rotulo_linha == "Relatou sucesso" else 0
        ax.add_patch(plt.Rectangle(
            (x + 0.04, y + 0.04), 0.92, 0.92,
            facecolor=ACCENT_SOFT if discorda else FUNDO,
            edgecolor=ACCENT_LINE if discorda else LINHA, linewidth=1.2))
        ax.text(x + 0.5, y + 0.5, str(valor), ha="center", va="center",
                fontsize=26, fontweight="bold",
                color=ACCENT_DEEP if discorda else INK)

    for i, rotulo in enumerate(["Concluiu", "Não concluiu"]):
        ax.text(i + 0.5, 2.06, rotulo.upper(), ha="center", color=MUTED, fontsize=8)
    for i, rotulo in enumerate(["Relatou fracasso", "Relatou sucesso"]):
        ax.text(-0.04, i + 0.5, rotulo.upper(), ha="right", va="center",
                color=MUTED, fontsize=8)

    # Título e subtítulo em coordenadas do eixo: a grade tem os rótulos de
    # linha à esquerda, então o bloco de texto começa antes do x=0 dos dados.
    esquerda = -0.14
    ax.text(esquerda, 1.20, "O que a pessoa disse contra o que ela fez",
            transform=ax.transAxes, color=INK, fontsize=11, fontweight="bold")
    ax.text(esquerda, 1.11,
            f"{n} tentativas · destacadas as células em que relato e observação discordam",
            transform=ax.transAxes, color=MUTED, fontsize=8.5)
    ax.text(esquerda, -0.12,
            f"p₀ = {br(po, 3)}   ·   pₑ = {br(pe, 3)}   ·   κ = {br(kappa, 3)}",
            transform=ax.transAxes, color=ACCENT, fontsize=10, fontweight="bold")
    salvar(fig, "02-dito-contra-feito.png")


def grafico_prioridade(achados, sessoes):
    tabela = achados.groupby("tema").agg(
        sessoes=("sessao_id", "nunique"),
        ocorrencias=("tema", "size"),
        severidade=("severidade", "max"),
    )

    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.scatter(tabela.sessoes, tabela.severidade,
               s=tabela.ocorrencias * 9, color=ACCENT, alpha=0.55,
               edgecolor=ACCENT_DEEP, linewidth=0.6)

    ax.axvline(len(sessoes) / 2, color=ACCENT_LINE, linestyle="--", linewidth=1)
    ax.axhline(2.5, color=ACCENT_LINE, linestyle="--", linewidth=1)

    # O quadrante superior direito é o que decide o backlog; sem os nomes,
    # o gráfico mostra que existe um agrupamento mas não qual é. Os rótulos
    # vão empilhados acima da área de dados para não se sobreporem entre si.
    criticos = tabela[(tabela.severidade >= 4) & (tabela.sessoes > len(sessoes) / 2)]
    for i, (tema, linha) in enumerate(criticos.sort_values("sessoes").iterrows()):
        ax.annotate(
            tema, (linha.sessoes, linha.severidade),
            xytext=(linha.sessoes, 4.7 + 0.32 * i), textcoords="data",
            ha="center", va="bottom", color=ACCENT_DEEP, fontsize=7.5,
            arrowprops=dict(arrowstyle="-", color=ACCENT_LINE, linewidth=0.9,
                            shrinkA=2, shrinkB=6),
        )

    moldar(ax, "Gravidade contra frequência",
           "Cada ponto é um tema · o tamanho mostra quantas vezes ele foi codificado")
    ax.grid(axis="y", color=LINHA, linewidth=0.8)
    ax.set_xlabel("sessões em que apareceu")
    ax.set_ylabel("gravidade")
    ax.set_yticks([1, 2, 3, 4])
    ax.set_xlim(0, len(sessoes))
    ax.set_ylim(0.4, 5.9)
    salvar(fig, "03-gravidade-frequencia.png")


def grafico_saturacao(achados, sessoes):
    rng = np.random.default_rng(4)
    ids = sessoes.sessao_id.to_numpy()
    por_sessao = {s: set(g.tema) for s, g in achados.groupby("sessao_id")}

    def curva(ordem):
        vistos, saida = set(), []
        for s in ordem:
            vistos |= por_sessao.get(s, set())
            saida.append(len(vistos))
        return saida

    curvas = np.array([curva(rng.permutation(ids)) for _ in range(300)])
    media = curvas.mean(axis=0)
    p10, p90 = np.percentile(curvas, 10, axis=0), np.percentile(curvas, 90, axis=0)
    total = achados.tema.nunique()
    x = np.arange(1, len(ids) + 1)
    n80 = int(np.argmax(media >= 0.8 * total) + 1)

    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    # A faixa preenchida é o que o Power BI não desenha nativamente.
    ax.fill_between(x, p10, p90, color=ACCENT_LINE, alpha=0.5, linewidth=0)
    ax.plot(x, media, color=ACCENT, linewidth=2.4)
    ax.axhline(total * 0.8, color=ACCENT_DEEP, linestyle="--", linewidth=1)
    ax.text(len(ids), total * 0.8 + 0.25, "80% dos temas", ha="right",
            color=ACCENT_DEEP, fontsize=8)
    ax.axvline(5, color=MUTED, linestyle=":", linewidth=1)

    moldar(ax, f"Quantas sessões bastam · 80% dos temas na {n80}ª",
           "Linha: média de 300 reordenações sorteadas · faixa: entre os percentis 10 e 90")
    ax.grid(axis="y", color=LINHA, linewidth=0.8)
    ax.set_xlabel("sessões analisadas")
    ax.set_ylabel("temas distintos")
    ax.set_xlim(1, len(ids))
    ax.set_ylim(0, total + 1)
    salvar(fig, "04-saturacao.png")


def main():
    sessoes = pd.read_csv(DADOS / "sessoes.csv")
    segmentos = pd.read_csv(DADOS / "segmentos.csv")
    achados = pd.read_csv(DADOS / "achados.csv")
    tarefas = pd.read_csv(DADOS / "tarefas.csv")

    print("imagens geradas:")
    grafico_material(segmentos, achados)
    grafico_dito_feito(tarefas)
    grafico_prioridade(achados, sessoes)
    grafico_saturacao(achados, sessoes)
    print(f"\n{SAIDA}")


if __name__ == "__main__":
    main()
