# Uodly.app — análise de pesquisa de UX em Power BI

Painel em Power BI construído sobre um estudo de usabilidade de 24 sessões:
modelo dimensional, medidas em DAX e um relatório cujo layout é gerado por
código, não arrastado na tela.

## Aviso sobre os dados

**O corpus é fictício.** O Uodly.app é um produto em operação, e este estudo
não o avalia: nenhum número aqui mede acurácia, tempo economizado ou qualidade
de saída da ferramenta. O que o projeto demonstra é o **método de análise** —
densidade de sinal no material bruto, concordância entre relato e observação,
priorização por gravidade e frequência, e saturação temática.

As distribuições foram escolhidas para reproduzir padrões conhecidos de
pesquisa de UX, não para favorecer uma conclusão.

## O que tem aqui

```
analise/     os scripts que geram o corpus, analisam e montam o painel
dados/       o corpus gerado, em CSV, e a planilha que o Power BI consome
powerbi/     o projeto .pbip — modelo em TMDL e relatório em PBIR
```

## Como abrir o painel

1. Abra `powerbi/Uodly Analytics.pbip` no Power BI Desktop.
   É preciso ter **Arquivo → Opções → Recursos de visualização → Power BI
   Project (.pbip)** marcado, e reiniciar o Desktop depois de marcar.

2. O modelo aponta para a planilha por um parâmetro. Vá em **Transformar dados
   → Gerenciar parâmetros** e troque `PastaDados` pelo caminho da pasta
   `dados` deste repositório na sua máquina.

3. **Atualizar** para carregar os dados.

## Como refazer tudo do zero

```bash
pip install -r requirements.txt

python analise/gerar_dados.py          # gera o corpus sintético
python analise/exportar_powerbi.py     # traduz para modelo dimensional
python analise/montar_dashboard.py     # escreve os visuais do relatório
```

O `montar_dashboard.py` grava os arquivos `visual.json` diretamente. Layout em
código significa que trocar a paleta, reposicionar tudo ou acrescentar uma
página é edição de script — não é arrastar trinta objetos na tela.

## As medidas

Estão em `powerbi/Uodly Analytics.SemanticModel/definition/tables/`, em TMDL.
Vale olhar `fato_tarefa.tmdl`: o kappa de Cohen está decomposto em três
medidas — concordância observada, concordância esperada por acaso e o
resultado — para que o painel possa mostrar a conta, não só o número.

## Onde isso aparece

Este caso integra o portfólio em
[bruno-dados-python.vercel.app](https://bruno-dados-python.vercel.app/projetos/uodly),
onde a mesma análise está em versão web.
