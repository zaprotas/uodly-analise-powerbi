"""
Monta a página do dashboard do Uodly.app no formato PBIR.

Os visuais do Power BI são pastas com um visual.json cada, num esquema público
e documentado. Este script gera todos de uma vez, o que resolve dois problemas
de montar no editor: posicionamento exato e formatação idêntica entre cartões.

A paleta é a do portfólio — o dashboard e o site precisam ler como obra da
mesma pessoa.

Uso: python analysis/uodly/montar_dashboard.py
"""

import json
import shutil
from pathlib import Path

RAIZ = Path(
    "powerbi/Uodly Analytics.Report/definition"
)
PAGINA = RAIZ / "pages" / "b0a69b7a02b207b70d81"
SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/"
    "definition/visualContainer/2.9.0/schema.json"
)

ACCENT, ACCENT_DEEP, ACCENT_LINE = "#4F46E5", "#3730A3", "#C7D2FE"
ACCENT_SOFT = "#EEF2FF"
INK, INK2, MUTED = "#0F172A", "#334155", "#5B6472"
LINHA, FUNDO, BRANCO, CINZA_CLARO = "#E6E8EC", "#F8FAFC", "#FFFFFF", "#94A3B8"


# --- helpers de expressão -------------------------------------------------
# O Power BI guarda todo valor de formatação como expressão literal. Texto vai
# entre aspas simples dentro da string; número leva sufixo D.
def lit(valor):
    return {"expr": {"Literal": {"Value": valor}}}


def txt(valor):
    return lit(f"'{valor}'")


def num(valor):
    return lit(f"{valor}D")


def boo(valor):
    return lit("true" if valor else "false")


def cor(hexa):
    return {"solid": {"color": lit(f"'{hexa}'")}}


# --- helpers de campo -----------------------------------------------------
def coluna(tabela, campo):
    return {
        "Column": {
            "Expression": {"SourceRef": {"Entity": tabela}},
            "Property": campo,
        }
    }


def medida(tabela, nome):
    return {
        "Measure": {
            "Expression": {"SourceRef": {"Entity": tabela}},
            "Property": nome,
        }
    }


def soma(tabela, campo):
    return {"Aggregation": {"Expression": coluna(tabela, campo), "Function": 0}}


def proj(campo, tabela, nome):
    return {"field": campo, "queryRef": f"{tabela}.{nome}", "nativeQueryRef": nome}


# --- blocos de construção -------------------------------------------------
def moldura(titulo=None):
    """Fundo branco, borda fina e sombra discreta — o cartão do site."""
    objetos = {
        "background": [
            {"properties": {"show": boo(True), "color": cor(BRANCO), "transparency": num(0)}}
        ],
        "border": [
            {"properties": {"show": boo(True), "color": cor(LINHA), "radius": num(10)}}
        ],
        # A propriedade é shadowBlur, não blur: o Power BI recusa nomes que
        # não estejam no esquema e ignora o objeto inteiro.
        "dropShadow": [
            {
                "properties": {
                    "show": boo(True),
                    "color": cor(INK),
                    "transparency": num(92),
                    "shadowBlur": num(12),
                    "shadowSpread": num(0),
                    "shadowDistance": num(2),
                    "angle": num(90),
                    "position": txt("Outer"),
                }
            }
        ],
        "padding": [
            {"properties": {"left": num(14), "right": num(14), "top": num(12), "bottom": num(12)}}
        ],
    }
    if titulo:
        objetos["title"] = [
            {
                "properties": {
                    "show": boo(True),
                    "text": txt(titulo),
                    "fontColor": cor(INK),
                    "fontSize": num(13),
                    "bold": boo(True),
                    "alignment": txt("left"),
                }
            }
        ]
    else:
        objetos["title"] = [{"properties": {"show": boo(False)}}]

    # Ao definir título próprio, o Power BI empurra o título automático para
    # subtítulo — "Soma de temas_media por sessoes_analisadas" e afins. Some.
    objetos["subTitle"] = [{"properties": {"show": boo(False)}}]
    return objetos


def eixos(titulo_categoria=False, titulo_valor=False):
    """Eixos discretos: sem título, rótulo apagado, grade quase invisível."""
    return {
        "categoryAxis": [
            {
                "properties": {
                    "showAxisTitle": boo(titulo_categoria),
                    "labelColor": cor(MUTED),
                    "fontSize": num(10),
                }
            }
        ],
        "valueAxis": [
            {
                "properties": {
                    "showAxisTitle": boo(titulo_valor),
                    "labelColor": cor(MUTED),
                    "fontSize": num(9),
                    "gridlineColor": cor(LINHA),
                    "gridlineThickness": num(1),
                }
            }
        ],
    }


def visual(nome, x, y, w, h, ordem, tipo, papeis=None, objetos=None, container=None, z=0):
    conteudo = {"visualType": tipo, "drillFilterOtherVisuals": True}
    if papeis:
        conteudo["query"] = {
            "queryState": {papel: {"projections": p} for papel, p in papeis.items()}
        }
    if objetos:
        conteudo["objects"] = objetos
    if container:
        conteudo["visualContainerObjects"] = container
    return {
        "$schema": SCHEMA,
        "name": nome,
        "position": {"x": x, "y": y, "z": z, "width": w, "height": h, "tabOrder": ordem},
        "visual": conteudo,
    }


def trecho(valor, tamanho=12, cor_hex=INK, negrito=False, fonte="Segoe UI"):
    return {
        "value": valor,
        "textStyle": {
            "fontSize": f"{tamanho}pt",
            "color": cor_hex,
            "fontFamily": fonte,
            "fontWeight": "bold" if negrito else "normal",
        },
    }


def paragrafo(trechos, alinhamento="left", espaco_depois=0):
    return {
        "horizontalTextAlignment": alinhamento,
        "textRuns": trechos,
        "paragraphSpacingAfter": espaco_depois,
    }


def caixa_texto(nome, x, y, w, h, ordem, paragrafos, z=0, fundo=None, raio=None):
    """
    Caixa de texto, opcionalmente com fundo colorido.

    Painéis coloridos aqui são caixas de texto com fundo, não visuais do tipo
    `shape`: o Power BI ignorou os shapes em silêncio, enquanto o fundo de
    contêiner é propriedade documentada e funciona.
    """
    container = {
        "title": [{"properties": {"show": boo(False)}}],
        "padding": [
            {"properties": {"left": num(0), "right": num(0), "top": num(0), "bottom": num(0)}}
        ],
    }
    if fundo:
        container["background"] = [
            {"properties": {"show": boo(True), "color": cor(fundo), "transparency": num(0)}}
        ]
        if raio is not None:
            container["border"] = [
                {"properties": {"show": boo(True), "color": cor(fundo), "radius": num(raio)}}
            ]
    else:
        container["background"] = [{"properties": {"show": boo(False)}}]

    return visual(
        nome, x, y, w, h, ordem, "textbox",
        objetos={"general": [{"properties": {"paragraphs": paragrafos}}]},
        container=container,
        z=z,
    )


def painel(nome, x, y, w, h, ordem, preenchimento, z=0, raio=None):
    """Retângulo de cor sólida, feito de caixa de texto vazia."""
    return caixa_texto(
        nome, x, y, w, h, ordem, [paragrafo([trecho("", 8, preenchimento)])],
        z=z, fundo=preenchimento, raio=raio,
    )


def filtro(nome, x, y, w, h, ordem, tabela, campo, titulo, z=20):
    """
    Segmentação sobre fundo branco.

    O fundo claro é decisão de robustez: a cor de fonte do slicer tem nomes de
    propriedade que variam por tipo de item, e se alguma não pegar o texto sai
    escuro. Sobre branco, sai legível de qualquer jeito.
    """
    return visual(
        nome, x, y, w, h, ordem, "slicer",
        {"Values": [proj(coluna(tabela, campo), tabela, campo)]},
        objetos={
            "items": [{"properties": {"fontColor": cor(INK2), "fontSize": num(10)}}],
            "selection": [{"properties": {"singleSelect": boo(False)}}],
        },
        container={
            "background": [
                {"properties": {"show": boo(True), "color": cor(BRANCO), "transparency": num(0)}}
            ],
            "border": [{"properties": {"show": boo(True), "color": cor(LINHA), "radius": num(8)}}],
            "title": [
                {
                    "properties": {
                        "show": boo(True),
                        "text": txt(titulo),
                        "fontColor": cor(MUTED),
                        "fontSize": num(9),
                        "bold": boo(True),
                        "alignment": txt("left"),
                    }
                }
            ],
            "padding": [
                {"properties": {"left": num(10), "right": num(10), "top": num(8), "bottom": num(8)}}
            ],
        },
        z=z,
    )


def celula_matriz(nome, x, y, w, h, ordem, nome_medida, discorda):
    """
    Uma célula da matriz de confusão: um cartão só, com o número.

    A tabela dinâmica do Power BI não deixa colorir célula por posição — só
    por regra sobre o valor. Quatro cartões independentes resolvem: cada um
    tem sua própria medida e seu próprio fundo, e as duas células de
    discordância ficam em índigo claro, como na versão web do caso.
    """
    fundo = ACCENT_SOFT if discorda else FUNDO
    borda = ACCENT_LINE if discorda else LINHA
    tinta = ACCENT_DEEP if discorda else INK
    return visual(
        nome, x, y, w, h, ordem, "card",
        {"Values": [proj(medida("fato_tarefa", nome_medida), "fato_tarefa", nome_medida)]},
        objetos={
            "labels": [{"properties": {"color": cor(tinta), "fontSize": num(28),
                                       "bold": boo(True)}}],
            "categoryLabels": [{"properties": {"show": boo(False)}}],
        },
        container={
            "background": [
                {"properties": {"show": boo(True), "color": cor(fundo), "transparency": num(0)}}
            ],
            "border": [{"properties": {"show": boo(True), "color": cor(borda), "radius": num(8)}}],
            "title": [{"properties": {"show": boo(False)}}],
            "padding": [
                {"properties": {"left": num(6), "right": num(6), "top": num(6), "bottom": num(6)}}
            ],
        },
        z=25,
    )


def estatistica(nome, x, y, w, h, ordem, nome_medida, rotulo):
    """Cartão pequeno e sem moldura, para a linha de po, pe e kappa."""
    return visual(
        nome, x, y, w, h, ordem, "card",
        {"Values": [proj(medida("fato_tarefa", nome_medida), "fato_tarefa", nome_medida)]},
        objetos={
            "labels": [{"properties": {"color": cor(ACCENT), "fontSize": num(15),
                                       "bold": boo(True)}}],
            "categoryLabels": [{"properties": {"show": boo(True), "color": cor(MUTED),
                                               "fontSize": num(8),
                                               "fontFamily": txt("Segoe UI")}}],
        },
        container={
            "background": [{"properties": {"show": boo(False)}}],
            "title": [{"properties": {"show": boo(False)}}],
            "padding": [
                {"properties": {"left": num(0), "right": num(0), "top": num(0), "bottom": num(0)}}
            ],
        },
        z=25,
    )


def matriz_confusao(x, y, w, h):
    """Monta a matriz 2x2 inteira: moldura, rótulos, células e estatísticas."""
    visuais = []
    pad = 18
    larg_rotulo = 150
    larg_celula = (w - pad * 2 - larg_rotulo - 12) // 2
    x_col1 = x + pad + larg_rotulo
    x_col2 = x_col1 + larg_celula + 12
    y_cabecalho = y + 54
    y_linha1 = y_cabecalho + 26
    y_linha2 = y_linha1 + 92
    alt_celula = 84

    visuais.append(caixa_texto(
        "matrizmoldura0000000", x, y, w, h, 20,
        [paragrafo([trecho("", 8, BRANCO)])], z=20, fundo=BRANCO, raio=10,
    ))
    visuais.append(caixa_texto(
        "matriztitulo00000000", x + pad, y + 14, w - pad * 2, 36, 21, [
            paragrafo([trecho("O que a pessoa disse contra o que ela fez", 13, INK, True)]),
            paragrafo([trecho("120 tentativas · destacadas as células em que relato e "
                              "observação discordam", 8, MUTED)]),
        ], z=21,
    ))

    for i, rotulo in enumerate(["CONCLUIU", "NÃO CONCLUIU"]):
        visuais.append(caixa_texto(
            f"matrizcabec{i}00000000"[:20], [x_col1, x_col2][i], y_cabecalho, larg_celula, 22,
            22 + i, [paragrafo([trecho(rotulo, 8, MUTED, True, "Consolas")], "center")], z=22,
        ))

    for i, rotulo in enumerate(["RELATOU SUCESSO", "RELATOU FRACASSO"]):
        visuais.append(caixa_texto(
            f"matrizrotulo{i}0000000"[:20], x + pad, [y_linha1, y_linha2][i] + 30, larg_rotulo, 24,
            24 + i, [paragrafo([trecho(rotulo, 8, MUTED, True, "Consolas")], "right")], z=23,
        ))

    # (medida, coluna, linha, é discordância)
    celulas = [
        ("Acertou o relato · concluiu", 0, 0, False),
        ("Errou o relato · não concluiu", 1, 0, True),
        ("Errou o relato · concluiu", 0, 1, True),
        ("Acertou o relato · não concluiu", 1, 1, False),
    ]
    for i, (nome_medida, col, linha, discorda) in enumerate(celulas):
        visuais.append(celula_matriz(
            f"matrizcelula{i}000000"[:20], [x_col1, x_col2][col], [y_linha1, y_linha2][linha],
            larg_celula, alt_celula, 26 + i, nome_medida, discorda,
        ))

    y_stats = y_linha2 + alt_celula + 16
    larg_stat = (w - pad * 2) // 3
    for i, (nome_medida, _) in enumerate([
        ("Concordância observada", "p₀"),
        ("Concordância por acaso", "pₑ"),
        ("Kappa de Cohen", "κ"),
    ]):
        visuais.append(estatistica(
            f"matrizstat{i}00000000"[:20], x + pad + i * larg_stat, y_stats, larg_stat, 54,
            30 + i, nome_medida, nome_medida,
        ))

    return visuais


# --- layout ---------------------------------------------------------------
LATERAL = 300
MARGEM = 40
X0 = LATERAL + MARGEM
UTIL = 1920 - X0 - MARGEM

CARTOES = [
    ("Horas de material", "fato_trecho"),
    ("% do tempo com achado", "fato_trecho"),
    ("Kappa de Cohen", "fato_tarefa"),
    ("Temas distintos", "fato_achado"),
]


def montar():
    visuais = []

    # Barra lateral escura. z crescente: o painel é desenhado primeiro e os
    # textos por cima. Sem isso os textos claros ficam brancos sobre branco.
    visuais.append(painel("faixafundo0000000000", 0, 0, LATERAL, 1080, 0, INK, z=0))
    visuais.append(
        caixa_texto("faixamonograma000000", 36, 44, 46, 46, 1,
                    [paragrafo([trecho("BR", 14, BRANCO, True)], "center")],
                    z=10, fundo=ACCENT, raio=10)
    )
    visuais.append(
        caixa_texto("faixamarca0000000000", 94, 46, 195, 50, 2, [
            paragrafo([trecho("Bruno Rodrigues", 12, BRANCO, True)]),
            paragrafo([trecho("Content Design · Dados", 8, CINZA_CLARO, False, "Consolas")]),
        ], z=11)
    )
    visuais.append(
        caixa_texto("faixanav000000000000", 36, 160, 240, 220, 3, [
            paragrafo([trecho("VISÃO GERAL", 9, ACCENT_LINE, True, "Consolas")], espaco_depois=16),
            paragrafo([trecho("O material bruto", 10, CINZA_CLARO)], espaco_depois=12),
            paragrafo([trecho("Dito × feito", 10, CINZA_CLARO)], espaco_depois=12),
            paragrafo([trecho("Prioridade", 10, CINZA_CLARO)], espaco_depois=12),
            paragrafo([trecho("Saturação", 10, CINZA_CLARO)]),
        ], z=12)
    )
    # Filtros. Só entram os dois que abrem uma pergunta de verdade: perfil,
    # porque novato e experiente concluem em taxas diferentes e isso move o
    # kappa; e gravidade, para separar o que é incômodo do que trava.
    visuais.append(
        caixa_texto("faixarotulofiltro000", 36, 410, 240, 26, 5,
                    [paragrafo([trecho("FILTROS", 9, ACCENT_LINE, True, "Consolas")])], z=14)
    )
    visuais.append(
        filtro("filtroperfil00000000", 36, 442, 240, 118, 6,
               "dim_sessao", "perfil", "Perfil do participante")
    )
    visuais.append(
        filtro("filtrogravidade00000", 36, 574, 240, 156, 7,
               "dim_tema", "gravidade", "Gravidade do tema")
    )

    # A tarja de transparência: o mesmo aviso que a página do site carrega.
    visuais.append(
        caixa_texto("faixaaviso0000000000", 36, 860, 240, 180, 4, [
            paragrafo([trecho("SOBRE ESTES DADOS", 8, ACCENT_LINE, True, "Consolas")],
                      espaco_depois=10),
            paragrafo([trecho(
                "Estudo fictício de 24 sessões, feito para demonstrar o método de análise. "
                "Nenhum número aqui mede o desempenho do Uodly.app.",
                8, CINZA_CLARO)]),
        ], z=13)
    )

    visuais.append(
        caixa_texto("tituloprincipal00000", X0, 40, 1000, 92, 6, [
            paragrafo([trecho("Uodly", 28, ACCENT, True), trecho("  Analytics", 28, INK, True)]),
            paragrafo([trecho("ANÁLISE DE PESQUISA DE UX  ·  24 SESSÕES", 9, MUTED, True,
                              "Consolas")]),
        ])
    )

    largura_kpi = (UTIL - 3 * 20) // 4
    for i, (nome_medida, tabela) in enumerate(CARTOES):
        visuais.append(
            visual(
                f"kpi{i}0000000000000000"[:20],
                X0 + i * (largura_kpi + 20), 150, largura_kpi, 140, 7 + i,
                "card",
                {"Values": [proj(medida(tabela, nome_medida), tabela, nome_medida)]},
                objetos={
                    "labels": [{"properties": {"color": cor(ACCENT), "fontSize": num(30),
                                               "bold": boo(True)}}],
                    "categoryLabels": [{"properties": {"show": boo(True), "color": cor(MUTED),
                                                       "fontSize": num(9),
                                                       "fontFamily": txt("Consolas")}}],
                },
                container=moldura(),
            )
        )

    largura_g = (UTIL - 20) // 2
    direita = X0 + largura_g + 20

    visuais.append(visual(
        "grafcomposicao000000", X0, 320, largura_g, 340, 11, "clusteredBarChart",
        {"Category": [proj(coluna("dim_tipo_trecho", "tipo_rotulo"), "dim_tipo_trecho",
                           "tipo_rotulo")],
         "Y": [proj(medida("fato_trecho", "Horas de material"), "fato_trecho",
                    "Horas de material")]},
        objetos={
            "dataPoint": [{"properties": {"fill": cor(ACCENT)}}],
            # Rótulo no fim da barra dispensa a leitura do eixo.
            "labels": [{"properties": {"show": boo(True), "color": cor(INK2),
                                       "fontSize": num(10), "labelDisplayUnits": num(0),
                                       "labelPrecision": num(1)}}],
            **eixos(),
        },
        container=moldura("Onde estão as 21,5 horas gravadas"),
    ))

    visuais.extend(matriz_confusao(direita, 320, largura_g, 340))

    visuais.append(visual(
        "grafgravidade0000000", X0, 690, largura_g, 340, 13, "scatterChart",
        {"Category": [proj(coluna("dim_tema", "tema"), "dim_tema", "tema")],
         "X": [proj(medida("fato_achado", "Sessões com o tema"), "fato_achado",
                    "Sessões com o tema")],
         "Y": [proj(medida("fato_achado", "Gravidade máxima"), "fato_achado",
                    "Gravidade máxima")],
         # Tamanho por volume de codificação: o ponto grande é o tema que
         # reapareceu muitas vezes, não só em muitas sessões.
         "Size": [proj(medida("fato_achado", "Achados codificados"), "fato_achado",
                       "Achados codificados")]},
        objetos={
            "dataPoint": [{"properties": {"defaultColor": cor(ACCENT)}}],
            # bubbleSize vai de -100 a +100, com 0 no padrão. Negativo encolhe.
            "bubbles": [{"properties": {"bubbleSize": num(20)}}],
            "fillPoint": [{"properties": {"show": boo(True)}}],
            # As duas linhas dividem o plano em quadrantes: o canto superior
            # direito é grave e frequente, que ninguém discute. A decisão
            # difícil está nos outros dois.
            "y1AxisReferenceLine": [
                {"selector": {"id": "meiaGravidade"},
                 "properties": {"show": boo(True), "value": txt("2.5"),
                                "lineColor": cor(ACCENT_LINE), "style": txt("dashed"),
                                "transparency": num(0)}}
            ],
            "xAxisReferenceLine": [
                {"selector": {"id": "meiaFrequencia"},
                 "properties": {"show": boo(True), "value": txt("12"),
                                "lineColor": cor(ACCENT_LINE), "style": txt("dashed"),
                                "transparency": num(0)}}
            ],
            **eixos(titulo_categoria=True, titulo_valor=True),
        },
        container=moldura("Gravidade contra frequência"),
    ))

    visuais.append(visual(
        "grafsaturacao0000000", direita, 690, largura_g, 340, 14, "lineChart",
        # Três séries: a média grossa em índigo e os percentis 10 e 90 como
        # linhas finas em volta. O Power BI não preenche a faixa entre elas —
        # mas as duas linhas dizem a mesma coisa que a área sombreada do site.
        {"Category": [proj(coluna("apoio_saturacao", "sessoes_analisadas"), "apoio_saturacao",
                           "sessoes_analisadas")],
         "Y": [proj(soma("apoio_saturacao", "temas_media"), "apoio_saturacao", "temas_media"),
               proj(soma("apoio_saturacao", "temas_p10"), "apoio_saturacao", "temas_p10"),
               proj(soma("apoio_saturacao", "temas_p90"), "apoio_saturacao", "temas_p90")]},
        # Linha precisa de seletor apontando a série; sem ele o fill é ignorado
        # e a linha sai na cor padrão do tema, como aconteceu na primeira volta.
        objetos={
            "dataPoint": [
                {"selector": {"metadata": "apoio_saturacao.temas_media"},
                 "properties": {"fill": cor(ACCENT)}},
                {"selector": {"metadata": "apoio_saturacao.temas_p10"},
                 "properties": {"fill": cor(ACCENT_LINE)}},
                {"selector": {"metadata": "apoio_saturacao.temas_p90"},
                 "properties": {"fill": cor(ACCENT_LINE)}},
            ],
            "lineStyles": [
                {"selector": {"metadata": "apoio_saturacao.temas_media"},
                 "properties": {"strokeWidth": num(3), "showMarker": boo(False)}},
                {"selector": {"metadata": "apoio_saturacao.temas_p10"},
                 "properties": {"strokeWidth": num(1), "showMarker": boo(False)}},
                {"selector": {"metadata": "apoio_saturacao.temas_p90"},
                 "properties": {"strokeWidth": num(1), "showMarker": boo(False)}},
            ],
            # A linha por si só não diz o que é "bastar". A referência em 80%
            # dos temas transforma a curva numa resposta.
            "y1AxisReferenceLine": [
                {
                    "selector": {"id": "saturacao80"},
                    "properties": {
                        "show": boo(True),
                        "value": txt("11.2"),
                        "lineColor": cor(ACCENT_LINE),
                        "style": txt("dashed"),
                        "transparency": num(0),
                        "dataLabelShow": boo(True),
                        "dataLabelText": txt("Horizontal"),
                        "dataLabelColor": cor(MUTED),
                        "dataLabelHorizontalPosition": txt("Left"),
                        "dataLabelVerticalPosition": txt("Above"),
                    },
                }
            ],
            **eixos(),
        },
        container=moldura("Quantas sessões bastam · 80% dos temas na 6ª sessão"),
    ))

    return visuais


def gravar(visuais):
    destino = PAGINA / "visuals"
    if destino.exists():
        shutil.rmtree(destino)
    destino.mkdir(parents=True)

    for v in visuais:
        pasta = destino / v["name"]
        pasta.mkdir()
        # UTF-8 sem BOM e CRLF, que é como o Power BI Desktop grava.
        (pasta / "visual.json").write_text(
            json.dumps(v, ensure_ascii=False, indent=2).replace("\n", "\r\n"),
            encoding="utf-8", newline="",
        )

    pagina = json.loads((PAGINA / "page.json").read_text(encoding="utf-8"))
    pagina["displayName"] = "Visão geral"
    pagina["objects"] = {
        "background": [{"properties": {"color": cor(FUNDO), "transparency": num(0)}}],
        "outspace": [{"properties": {"color": cor(FUNDO), "transparency": num(0)}}],
    }
    (PAGINA / "page.json").write_text(
        json.dumps(pagina, ensure_ascii=False, indent=2).replace("\n", "\r\n"),
        encoding="utf-8", newline="",
    )

    for v in visuais:
        print(f"  {v['visual']['visualType']:<18} {v['name']}")
    print(f"\n{len(visuais)} visuais em {destino}")


if __name__ == "__main__":
    gravar(montar())
