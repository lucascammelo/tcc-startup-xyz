# Startup XYZ: gestão de documentos para IA

TCC da Escola da Nuvem. Arquitetura serverless na AWS que recebe os documentos dos clientes de um SaaS de IA, isola cada cliente na sua própria "pasta", mantém os arquivos acessíveis por 12 meses e depois move tudo para o S3 Glacier Deep Archive, sem nunca apagar nada.

## Arquitetura

```
Cliente ──1 login──▶ Cognito (token JWT)
   │
   ├──2 pedido + token──▶ API Gateway ──3 valida token──▶ Cognito
   │                          │
   │                          └──4 invoca──▶ Lambda (upload-url | list | download-url)
   │                                              │
   │                                              └──5 assina URL (IAM mínimo)
   │
   └──6 arquivo vai e volta direto, por HTTPS──▶ S3  docs/<id-do-cliente>/arquivo.pdf
                                                  │
                                                  ├──7 Lifecycle 365 dias──▶ Deep Archive
                                                  └──8 Replicação──▶ bucket em us-east-2 (Ohio, Deep Archive)

CloudWatch (logs, 5 alarmes, painel) · SNS (e-mail) · Budgets (orçamento)
```

| Rota | Lambda | O que faz |
|---|---|---|
| `POST /files/upload-url` | `upload` | Gera um POST assinado (5 min, até 10 MB, só PDF/PNG/JPG) para a pasta do cliente |
| `GET /files` | `list` | Lista só os arquivos do cliente, indicando os que já estão arquivados |
| `GET /files/download-url?key=...` | `download` | Gera URL de leitura (5 min) só se a chave for do próprio cliente; 403 caso contrário; 409 se arquivada |

**O ponto central de segurança:** o ID do cliente vem do token validado pelo Cognito (`claims.sub`), nunca de um campo que o cliente envia. Por isso trocar `usuario-123` por `usuario-456` não funciona.

## Estrutura

```
infra/template.base.yaml   template com marcadores para o código
infra/build.py             embute src/*.py no template (limite de 4 KB por função)
infra/template.yaml        GERADO: é este que vai para o CloudFormation
infra/replica.yaml         bucket de réplica (DR), em outra região
src/                       código das 3 Lambdas (Python 3.12)
tests/test_lambdas.py      11 testes com S3 simulado (moto)
scripts/demo.sh            demonstração ponta a ponta para a banca
docs/custos.md             estimativa de custos e roteiro da Pricing Calculator
docs/modelo_custos.py      cálculo dos cenários de custo
docs/defesa.md             roteiro da apresentação e perguntas da banca
```

## Deploy

### Opção A: conta AWS própria (recomendado)

Pré-requisitos: AWS CLI v2 configurada, região `us-east-1`.

```bash
# 1. (opcional, para DR) réplica em outra região
aws cloudformation deploy --region us-east-2 --stack-name startup-xyz-replica \
  --template-file infra/replica.yaml
REPLICA_ARN=$(aws cloudformation describe-stacks --region us-east-2 --stack-name startup-xyz-replica \
  --query "Stacks[0].Outputs[0].OutputValue" --output text)

# 2. stack principal
aws cloudformation deploy --region us-east-1 --stack-name startup-xyz \
  --template-file infra/template.yaml --capabilities CAPABILITY_IAM \
  --parameter-overrides EmailAlertas=seu@email.com OrcamentoMensalUSD=10 ReplicaBucketArn=$REPLICA_ARN
```

Sem réplica, omita `ReplicaBucketArn`. Depois do deploy, confirme a assinatura do SNS no e-mail recebido.

Pelo console: CloudFormation → Create stack → Upload `infra/template.yaml` → preencha os parâmetros → marque "I acknowledge that AWS CloudFormation might create IAM resources".

### Opção B: AWS Academy / Learner Lab

O Learner Lab não deixa criar roles IAM. Informe o ARN da `LabRole` no parâmetro `LabRoleArn` e o template usa essa role no lugar das três roles de menor privilégio. Na apresentação, explique que em produção cada Lambda teria a própria role (o template já faz isso quando `LabRoleArn` fica vazio). Se algum serviço (Budgets, por exemplo) for bloqueado no lab, deixe `EmailAlertas` vazio: isso desliga o Budgets e a assinatura de e-mail. Não use `ReplicaBucketArn` no lab: a replicação exige uma role que o serviço S3 possa assumir, e a LabRole normalmente não permite. Apresente a réplica como desenho e custo calculado.

```bash
LAB_ROLE=$(aws iam get-role --role-name LabRole --query Role.Arn --output text)
aws cloudformation deploy --stack-name startup-xyz --template-file infra/template.yaml \
  --parameter-overrides LabRoleArn=$LAB_ROLE
```

### Saídas do stack

`ApiUrl`, `UserPoolId`, `UserPoolClientId`, `BucketName`, `PainelUrl`.

## Demonstração

```bash
export SENHA_DEMO='<SUA_SENHA_DE_TESTE>'   # obrigatório; o script não tem senha embutida
./scripts/demo.sh            # STACK=nome-do-stack AWS_REGION=regiao se mudou o padrão
```

> **Segurança: nenhum dado sensível neste repositório.**
> - A senha dos usuários de teste não fica no código: o script lê da variável `SENHA_DEMO` e para com erro se ela não existir. Use uma senha só de teste (8+ caracteres, com maiúscula, minúscula e número) e nunca faça commit dela.
> - Não há ID de conta AWS, chave de acesso, token nem nome real de bucket nos arquivos. Os buckets recebem um sufixo gerado pelo próprio stack.
> - Os usuários `ana@exemplo.com.br` e `bruno@exemplo.com.br` são fictícios (domínio de exemplo). Apague-os no Cognito depois da apresentação, ou apague o stack (Parte de limpeza abaixo).
> - Credenciais da AWS ficam só na sua máquina ou no CloudShell (`aws configure`), nunca no repositório.

O script cria os clientes Ana e Bruno no Cognito, faz login, envia um PDF de cada, lista os arquivos da Ana, abre o link assinado e mostra a Ana recebendo **403** ao tentar abrir o arquivo do Bruno (e 401 sem login).

**Teste manual pendente na AWS real:** enviar um arquivo maior que 10 MB com o POST assinado e confirmar a recusa do S3 (`EntityTooLarge`). A condição `content-length-range` está na política assinada, mas o simulador local não a aplica.

Para ver o Lifecycle funcionando sem esperar um ano, faça um deploy de teste com `DiasAteArquivamento=1`. A transição acontece em até ~48 h depois do prazo (a AWS processa as regras uma vez por dia).

## Testes locais

```bash
pip install boto3 "moto[s3]" pytest cfn-lint
python3 infra/build.py          # sempre que mudar algo em src/ ou no template base
pytest -v                       # 11 testes das Lambdas
cfn-lint infra/template.yaml infra/replica.yaml
```

## Custos

Resumo em `docs/custos.md`. Com 50 mil arquivos de 1 MB por mês, a solução custa US$ 29,83/mês no mês 36 segundo a AWS Pricing Calculator, e US$ 31,19/mês no ano 5, contra US$ 79,79 com tudo no S3 Standard e US$ 307,62 num servidor EC2 com disco.

## Limpeza

O bucket tem `DeletionPolicy: Retain` de propósito: apagar a stack **não** apaga os documentos. Para remover tudo depois da apresentação:

```bash
aws cloudformation delete-stack --stack-name startup-xyz
# depois, no console do S3: esvaziar o bucket (incluindo versões) e excluí-lo; repetir para a réplica
```

## Mapeamento para a rubrica

| Pilar | Onde está |
|---|---|
| Entendimento do problema | Slides 2 e 3, `docs/defesa.md` |
| Serviços e justificativa | Slides 7 a 9 |
| Atendimento aos requisitos | Slide 10, testes automatizados |
| Arquitetura | Slide 6, `infra/template.yaml` |
| Escalabilidade e resiliência | Slides 11 e 12 |
| Segurança | Slide 13, roles por Lambda, bucket policy, Cognito |
| Custos | Slide 14, `docs/custos.md`, Budgets |
| Replicação e recuperação | Slides 12 e 15, `infra/replica.yaml`, versionamento |
| Diferenciais | CloudFormation, testes, painel, alarmes, Budgets, DR, `scripts/demo.sh` |

## Documentação oficial

- [Amazon S3 Lifecycle](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html)
- [POST assinado no S3](https://docs.aws.amazon.com/AmazonS3/latest/API/sigv4-HTTPPOSTConstructPolicy.html)
- [S3 Replication](https://docs.aws.amazon.com/AmazonS3/latest/userguide/replication.html)
- [API Gateway com Cognito](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-integrate-with-cognito.html)
- [AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)
- [AWS CloudFormation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/Welcome.html)
- [AWS Budgets](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)
