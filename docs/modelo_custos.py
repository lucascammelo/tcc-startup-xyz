"""Modelo de custos da Startup XYZ (us-east-1, precos de out/2026, sem Free Tier).

Validado contra a AWS Pricing Calculator: no mes 36 a calculadora deu US$ 29,83/mes
para a nossa solucao e este modelo da o mesmo valor (diferenca de centavos).

Rodar: python3 docs/modelo_custos.py
A calculadora mostra UM mes; este modelo soma mes a mes, porque a base cresce
todo mes (nada e apagado). Por isso o acumulado de 5 anos e muito maior que 12 x o mensal.
"""

# ---------------------------------------------------------------- premissas
ARQ_MES = 50_000            # arquivos novos por mes (enunciado)
MB_MEDIO = 1.0              # tamanho medio por arquivo (premissa do grupo)
DOWNLOADS_MES = 100_000     # downloads por mes (premissa)
LISTAGENS_MES = 100_000     # chamadas de listagem por mes (premissa)
CHAMADAS_API = ARQ_MES + LISTAGENS_MES + DOWNLOADS_MES  # 250 mil

# ---------------------------------------------------------------- precos (US$)
P = dict(
    s3_std=0.023,               # GB-mes, S3 Standard (primeiros 50 TB)
    s3_deep=0.00099,            # GB-mes, Glacier Deep Archive
    put=0.005 / 1000,           # PUT, COPY, POST, LIST (Standard)
    get=0.0004 / 1000,          # GET, HEAD e demais (Standard)
    transicao_deep=0.05 / 1000,  # transicao de Lifecycle para Deep Archive
    put_deep=0.05 / 1000,       # PUT direto em Deep Archive (replica)
    saida_internet=0.09,        # GB, primeiros 10 TB/mes
    entre_regioes=0.01,         # GB, replicacao us-east-1 -> us-east-2 (Ohio); para Oregon seria 0,02
    api_rest=3.50 / 1e6,        # requisicao, API Gateway REST
    ec2_t3small_h=0.0208,       # hora, t3.small Linux on-demand
    ebs_gp3=0.08,               # GB-mes, EBS gp3
)
LAMBDA_MES = 0.15     # valor da calculadora: 250 mil req, 128 MB, 200 ms, x86
COGNITO_MES = 0.01    # valor da calculadora: plano Lite, 500 MAU
CLOUDWATCH_MES = 1.75  # valor da calculadora: 5 alarmes, 1 painel, 1 GB de logs
SNS_MES = 0.00        # valor da calculadora: 50 e-mails

GB_MES = ARQ_MES * MB_MEDIO / 1024          # ~48,8 GB novos por mes
SAIDA_GB = DOWNLOADS_MES * MB_MEDIO / 1024  # ~97,7 GB baixados por mes
# Cada objeto arquivado no Deep Archive tem 40 KB de metadados cobrados:
# 8 KB pelo preco do Standard e 32 KB pelo preco do Deep Archive.
OVH_STD_GB = 8 / 1024 / 1024
OVH_DEEP_GB = 32 / 1024 / 1024


def requisicoes_s3():
    return (ARQ_MES + LISTAGENS_MES) * P["put"] + (2 * DOWNLOADS_MES) * P["get"]  # GET + HEAD


def comum_serverless():
    """Itens iguais nos cenarios A, B e C: API, Lambda, Cognito, CloudWatch, SNS, saida."""
    return (CHAMADAS_API * P["api_rest"] + LAMBDA_MES + COGNITO_MES + CLOUDWATCH_MES + SNS_MES
            + SAIDA_GB * P["saida_internet"])


def cenario_a(m):
    """A) Nossa arquitetura, mas tudo em S3 Standard (sem ciclo de vida)."""
    return GB_MES * m * P["s3_std"] + requisicoes_s3() + comum_serverless()


def cenario_b(m):
    """B) Nossa solucao: 12 meses em Standard, o resto em Deep Archive."""
    quente = GB_MES * min(m, 12)
    frio = GB_MES * max(0, m - 12)
    objs_frios = ARQ_MES * max(0, m - 12)
    c = quente * P["s3_std"] + frio * P["s3_deep"]
    c += objs_frios * (OVH_STD_GB * P["s3_std"] + OVH_DEEP_GB * P["s3_deep"])
    if m > 12:
        c += ARQ_MES * P["transicao_deep"]
    return c + requisicoes_s3() + comum_serverless()


def cenario_c(m):
    """C) Nossa solucao + replica em us-east-2 (Ohio) gravada direto em Deep Archive."""
    objs = ARQ_MES * m
    replica = (GB_MES * m * P["s3_deep"]
               + objs * (OVH_STD_GB * P["s3_std"] + OVH_DEEP_GB * P["s3_deep"])
               + ARQ_MES * P["put_deep"] + GB_MES * P["entre_regioes"])
    return cenario_b(m) + replica


def cenario_d(m):
    """D) Servidor tradicional: 1 EC2 t3.small ligado 24h + disco EBS gp3 com 20% de folga
    + 8 GB de disco do sistema. Mesmo Cognito, CloudWatch e saida para a internet.
    Limite inferior: sem backup (snapshots), sem balanceador e em uma unica AZ."""
    ec2 = P["ec2_t3small_h"] * 730
    ebs = (GB_MES * m * 1.2 + 8) * P["ebs_gp3"]
    return ec2 + ebs + COGNITO_MES + CLOUDWATCH_MES + SAIDA_GB * P["saida_internet"]


CENARIOS = [("A) Tudo em S3 Standard, sem Lifecycle", cenario_a),
            ("B) Nossa solucao (Lifecycle)", cenario_b),
            ("C) Nossa solucao + replica DR", cenario_c),
            ("D) Servidor EC2 + disco EBS", cenario_d)]


def acumulado(f, meses):
    return sum(f(i) for i in range(1, meses + 1))


if __name__ == "__main__":
    print(f"Premissas: {ARQ_MES} arquivos/mes x {MB_MEDIO} MB = {GB_MES:.1f} GB/mes; "
          f"{CHAMADAS_API} chamadas de API/mes; {SAIDA_GB:.1f} GB baixados/mes\n")
    print(f"{'Cenario':40}{'Mes 12':>9}{'Mes 36':>9}{'Mes 60':>9}{'Acum 3a':>10}{'Acum 5a':>10}")
    for nome, f in CENARIOS:
        print(f"{nome:40}{f(12):9.2f}{f(36):9.2f}{f(60):9.2f}"
              f"{acumulado(f, 36):10.0f}{acumulado(f, 60):10.0f}")
    print(f"\nValidacao: cenario B no mes 36 = US$ {cenario_b(36):.2f} (calculadora: US$ 29,83)")
