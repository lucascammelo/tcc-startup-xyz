# Custos da solução (us-east-1)

Preços oficiais da AWS de outubro/2026, **sem Free Tier**. O cálculo completo está em `modelo_custos.py`.

**Validação:** a estimativa da Equipe EDN na AWS Pricing Calculator deu **US$ 29,83/mês** (US$ 357,96 em 12 meses) para a nossa solução no mês 36. O modelo deu **US$ 29,79** para o mesmo mês. A diferença de 4 centavos vem do arredondamento da saída para a internet (98 GB na calculadora, 97,7 GB no modelo).

## Premissas

| Item | Valor | Origem |
|---|---|---|
| Arquivos novos por mês | 50.000 | Enunciado do case |
| Tamanho médio | 1 MB | Premissa do grupo ("PDFs pequenos") |
| Volume novo por mês | ~49 GB | Calculado |
| Chamadas de API por mês | 250.000 | Premissa: 50 mil uploads + 100 mil listagens + 100 mil downloads |
| Saída para a internet | ~98 GB/mês | 100 mil downloads de 1 MB |
| Clientes ativos (MAU) | 500 | Premissa (B2B) |
| Retenção | Para sempre, nada é deletado | Enunciado do case |

## Por que o acumulado é muito maior que 12 x o mensal

A calculadora mostra **um mês** e repete esse mês 12 vezes. No case, a base cresce ~49 GB todo mês, porque nada é apagado. Por isso o modelo soma mês a mês: o mês 60 tem 5 vezes mais dados que o mês 12.

## Resultado (US$)

| Cenário | Mês 12 | Mês 36 | Mês 60 | Acumulado 3 anos | Acumulado 5 anos |
|---|---|---|---|---|---|
| A) Tudo em S3 Standard, sem Lifecycle | 25,88 | 52,83 | 79,79 | 1.194 | 2.799 |
| **B) Nossa solução (Lifecycle)** | **25,88** | **29,79** | **31,19** | **935** | **1.668** |
| C) Nossa solução + réplica DR | 29,57 | 34,89 | 37,70 | 1.082 | 1.954 |
| D) Servidor EC2 + disco EBS | 82,62 | 195,12 | 307,62 | 4.071 | 10.161 |

**Leitura:** até o mês 12, A e B custam igual (nada foi arquivado ainda). Depois, A sobe em linha reta e B quase para. No mês 60, B custa **39% de A** e **10% de D**.

**Sensibilidade (arquivo médio de 5 MB, mês 60):** A = US$ 384/mês, B = US$ 130/mês, D = US$ 1.468/mês.

### O que cada cenário inclui

| Item | A | B | C | D |
|---|---|---|---|---|
| Armazenamento | S3 Standard (tudo) | S3 Standard (12 meses) + Deep Archive | B + réplica Deep Archive em us-east-2 (Ohio) | EBS gp3 com 20% de folga + 8 GB de sistema |
| Requisições S3 (PUT/LIST/GET/HEAD) | Sim | Sim | Sim + PUT na réplica | Não usa S3 |
| Transições de Lifecycle | Não | Sim (a partir do mês 13) | Sim | Não |
| API Gateway + Lambda | Sim | Sim | Sim | Não (o servidor faz esse papel) |
| Servidor | Não | Não | Não | EC2 t3.small 24h (US$ 15,18/mês) |
| Cognito, CloudWatch, saída internet | Sim | Sim | Sim | Sim |

O cenário D é um **limite inferior**: não inclui backup (snapshots), balanceador de carga nem uma segunda zona de disponibilidade. Com esses itens, ficaria ainda mais caro.

## Onde está o custo (cenário B, mês 36)

| Item | US$/mês |
|---|---|
| S3 Standard, últimos 12 meses (586 GB) | 13,48 |
| Saída para a internet (98 GB) | 8,82 |
| Transições de Lifecycle (50 mil) | 2,50 |
| CloudWatch (5 alarmes, 1 painel, 1 GB de logs) | 1,75 |
| Deep Archive (1.172 GB + metadados) | 1,41 |
| API Gateway REST (250 mil) | 0,88 |
| Requisições S3 | 0,83 |
| Lambda | 0,15 |
| Cognito Lite (500 MAU) | 0,01 |
| SNS | 0,00 |
| **Total** | **~29,8** |

A saída para a internet é o item que mais cresce com mais clientes. A evolução proposta é colocar o CloudFront na frente dos downloads.

## Controles de custo implementados

- **AWS Budgets** com alerta em 80% do orçamento real e 100% do previsto.
- **Retenção de logs** em 30 dias.
- **Lifecycle** limpa uploads multipart incompletos após 7 dias.
- **Serverless:** sem custo ocioso.

O passo a passo campo a campo para reproduzir os três cenários na calculadora está no guia da Pricing Calculator.
