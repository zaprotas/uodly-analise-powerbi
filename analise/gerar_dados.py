"""
Gera o corpus sintético de pesquisa do caso "Uodly.app".

ATENÇÃO — este caso é diferente dos outros dois do portfólio.

Nos casos de Smiles e CVC, o resultado é real e histórico; só o caminho
analítico é reconstruído. Aqui não há resultado histórico: o Uodly.app é um
produto em operação hoje. Então este corpus é inteiramente fictício e serve
para demonstrar o MÉTODO de análise que o pipeline implementa.

Nenhum número gerado aqui é métrica de desempenho do produto. Não há medição
de acurácia da ferramenta, de tempo economizado ou de qualidade de saída, e
nada nesta página deve ser lido como tal.

Saída: analysis/uodly/dados/*.csv
"""

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 30518
N_SESSOES = 24
TAREFAS_POR_SESSAO = 5

TIPOS_SEGMENTO = {
    'tentativa_tarefa': 0.34,
    'fala_moderador': 0.23,
    'pensando_alto': 0.18,
    'silencio': 0.14,
    'fora_do_tema': 0.11,
}

# Só estes dois tipos podem gerar um achado codificado.
TIPOS_CODIFICAVEIS = ['tentativa_tarefa', 'pensando_alto']

TEMAS = [
    ('Não sabe onde a análise começa', 4),
    ('Não entende quais formatos são aceitos', 3),
    ('Upload falha sem dizer o motivo', 4),
    ('Não encontra o relatório depois de pronto', 4),
    ('Confunde projeto com estudo', 2),
    ('Não sabe o que conta como acionável', 3),
    ('Espera que a exportação seja automática', 2),
    ('Não entende a barra de progresso', 2),
    ('Procura um filtro que não existe', 3),
    ('Não sabe como compartilhar o relatório', 3),
    ('Acha que a integração já vem conectada', 2),
    ('Não reconhece o termo transcrição', 1),
    ('Perde o contexto ao voltar uma tela', 3),
    ('Não sabe que dá para editar o achado', 1),
]

TAREFAS = [
    'Subir um vídeo de sessão',
    'Encontrar os acionáveis do estudo',
    'Filtrar achados por severidade',
    'Exportar para o Power BI',
    'Compartilhar o relatório com o time',
]


def gerar_sessoes(rng):
    return pd.DataFrame(
        {
            'sessao_id': [f'S{i:02d}' for i in range(1, N_SESSOES + 1)],
            'segmento': rng.choice(
                ['novato', 'experiente'], size=N_SESSOES, p=[0.55, 0.45]
            ),
            'duracao_min': rng.normal(52, 8, N_SESSOES).round(0).astype(int),
        }
    )


def gerar_segmentos(rng, sessoes):
    """Cada sessão vira uma sequência de trechos transcritos."""
    tipos = list(TIPOS_SEGMENTO)
    pesos = np.array([TIPOS_SEGMENTO[t] for t in tipos])
    linhas = []

    for _, sessao in sessoes.iterrows():
        restante = sessao.duracao_min * 60
        relogio = 0

        while restante > 25:
            tipo = rng.choice(tipos, p=pesos)
            # Duração lognormal: muitos trechos curtos, poucos longos.
            duracao = int(min(restante, max(8, rng.lognormal(3.5, 0.6))))

            linhas.append(
                {
                    'sessao_id': sessao.sessao_id,
                    'inicio_s': relogio,
                    'duracao_s': duracao,
                    'tipo': tipo,
                }
            )
            relogio += duracao
            restante -= duracao

    return pd.DataFrame(linhas)


def gerar_achados(rng, segmentos):
    """
    Marca quais trechos viraram achado codificado e com que tema.

    Cada sessão esbarra num subconjunto dos problemas, não em todos — é assim
    que acontece na prática, e é isso que dá forma à curva de saturação. Se
    toda sessão visse todos os temas, a curva saturaria na terceira e a
    pergunta "quantas sessões bastam" não teria graça nem sentido.
    """
    nomes = [t for t, _ in TEMAS]
    severidades = dict(TEMAS)

    # Zipf: o tema mais comum tem ~8x a chance do mais raro de entrar no
    # subconjunto de uma sessão.
    pesos = 1 / np.power(np.arange(1, len(nomes) + 1), 1.0)
    pesos = pesos / pesos.sum()

    codificaveis = segmentos[segmentos.tipo.isin(TIPOS_CODIFICAVEIS)]
    # Calibrado para que os trechos com achado somem perto de 15% do tempo.
    marcados = codificaveis.sample(frac=0.30, random_state=11).copy()

    temas_do_trecho = []
    for sessao_id, trechos in marcados.groupby('sessao_id'):
        # 4 a 6 problemas distintos por sessão.
        k = int(rng.integers(4, 7))
        subconjunto = rng.choice(nomes, size=k, replace=False, p=pesos)
        # Dentro da sessão, os problemas mais graves são revisitados mais.
        peso_interno = np.array([severidades[t] for t in subconjunto], dtype=float)
        peso_interno /= peso_interno.sum()

        temas_do_trecho.append(
            pd.Series(
                rng.choice(subconjunto, size=len(trechos), p=peso_interno),
                index=trechos.index,
            )
        )

    marcados['tema'] = pd.concat(temas_do_trecho)
    marcados['severidade'] = marcados.tema.map(severidades)

    return marcados[['sessao_id', 'inicio_s', 'duracao_s', 'tema', 'severidade']]


def gerar_tarefas(rng, sessoes):
    """
    O que a pessoa fez contra o que ela disse.

    As probabilidades são desenhadas para reproduzir um padrão conhecido de
    pesquisa de UX: quase todo mundo relata sucesso, inclusive quem não
    concluiu. É a base da hipótese 02.
    """
    linhas = []

    for _, sessao in sessoes.iterrows():
        p_conclui = 0.68 if sessao.segmento == 'experiente' else 0.47

        for tarefa in TAREFAS:
            concluiu = bool(rng.random() < p_conclui)
            # Quem concluiu quase sempre relata sucesso. Quem não concluiu
            # relata sucesso na maioria das vezes mesmo assim.
            p_relato = 0.94 if concluiu else 0.71
            relato = bool(rng.random() < p_relato)

            linhas.append(
                {
                    'sessao_id': sessao.sessao_id,
                    'tarefa': tarefa,
                    'concluiu': concluiu,
                    'tempo_s': int(rng.normal(140 if concluiu else 210, 45)),
                    'relato_sucesso': relato,
                    'relato_nota': int(
                        np.clip(rng.normal(4.2 if relato else 2.6, 0.8), 1, 5)
                    ),
                }
            )

    return pd.DataFrame(linhas)


def main():
    rng = np.random.default_rng(SEED)
    destino = Path(__file__).parent / 'dados'
    destino.mkdir(parents=True, exist_ok=True)

    sessoes = gerar_sessoes(rng)
    segmentos = gerar_segmentos(rng, sessoes)
    achados = gerar_achados(rng, segmentos)
    tarefas = gerar_tarefas(rng, sessoes)

    sessoes.to_csv(destino / 'sessoes.csv', index=False)
    segmentos.to_csv(destino / 'segmentos.csv', index=False)
    achados.to_csv(destino / 'achados.csv', index=False)
    tarefas.to_csv(destino / 'tarefas.csv', index=False)

    horas = segmentos.duracao_s.sum() / 3600
    horas_achado = achados.duracao_s.sum() / 3600

    print(f'sessoes.csv     {len(sessoes):>6,} linhas')
    print(f'segmentos.csv   {len(segmentos):>6,} linhas')
    print(f'achados.csv     {len(achados):>6,} linhas')
    print(f'tarefas.csv     {len(tarefas):>6,} linhas')
    print()
    print(f'material bruto:        {horas:.1f} h')
    print(f'trechos com achado:    {horas_achado:.1f} h ({horas_achado / horas:.1%})')
    print(f'temas distintos:       {achados.tema.nunique()}')
    print(f'concluiu a tarefa:     {tarefas.concluiu.mean():.1%}')
    print(f'relatou sucesso:       {tarefas.relato_sucesso.mean():.1%}')


if __name__ == '__main__':
    main()
