# Roteiro de apresentação e defesa

## Divisão das falas (12 a 14 minutos)

Ajuste conforme o tamanho do grupo. Todos precisam conhecer o projeto inteiro: a banca pode perguntar qualquer coisa a qualquer integrante.

| Integrante | Slides | Tempo |
|---|---|---|
| Aluno 1 | 1 Capa · 2 Problema · 3 Premissa · 4 Requisitos · 5 Visão geral | ~3 min |
| Aluno 2 | 6 Arquitetura · 7 e 8 Serviços · 9 Justificativa · 10 Mapeamento | ~4 min |
| Aluno 3 | 11 Escala · 12 Falhas · 13 Segurança · 14 Custos · 15 Recuperação | ~4 min |
| Aluno 4 | 16 Demonstração · 17 Futuro · 18 Conclusão | ~4 min |

As falas sugeridas estão nas notas do apresentador de cada slide.

## Antes do dia

- [ ] Preencher nome da equipe e integrantes na capa
- [ ] Fazer o deploy e rodar `scripts/demo.sh` do começo ao fim
- [ ] Testar o envio de um arquivo maior que 10 MB e confirmar a recusa
- [ ] Apagar e recriar a stack cronometrando; colocar o tempo real no slide 15
- [ ] Montar a estimativa na Pricing Calculator (`docs/custos.md`) e colocar o link no slide 14
- [ ] Gravar a demo em vídeo como plano B e tirar prints do console
- [ ] Gerar tokens novos logo antes de apresentar (vencem em 60 minutos)

## A premissa que desafiamos (venda desafiadora)

A avaliadora vai olhar com olhar de vendedora. A ideia central do projeto, que deve aparecer cedo:

> A XYZ trata documento antigo como custo de armazenamento. Mas ele é o ativo que vai treinar os próximos modelos. E como nada é apagado, a decisão de onde guardar vira uma curva de custo que nunca para de subir.

O ROI que mostramos não é "quanto custa a solução", e sim "quanto custa não reestruturar": em 5 anos, US$ 10.161 num servidor, US$ 2.799 no S3 sem ciclo de vida, US$ 1.668 na nossa arquitetura. Premissa: 1 MB por arquivo. O modelo foi validado na AWS Pricing Calculator: US$ 29,83/mês no mês 36, contra US$ 29,79 do modelo. Se perguntarem, sejam honestos: o valor absoluto é baixo porque o volume é pequeno; o que importa é o formato da curva, que multiplica com o tamanho dos arquivos e com o crescimento.

## Perguntas prováveis da banca, com respostas

### Arquitetura

**Por que vocês escolheram Lambda e não EC2?**
O tráfego é irregular e a XYZ é uma startup. Com Lambda não há servidor ligado de madrugada nem sistema operacional para atualizar. Um EC2 t3.small custa ~US$ 15/mês só por estar ligado, e seria um ponto único de falha se rodasse em uma AZ só.

**Por que o arquivo não passa pela API?**
O API Gateway aceita no máximo 10 MB por pedido e cobraria o tráfego duas vezes. Com o POST assinado, o arquivo vai direto ao S3. A Lambda só decide se pode e para onde vai.

**Como a arquitetura funciona, em uma frase?**
O Cognito diz quem é o cliente, a Lambda dá uma chave temporária só para a pasta dele, e o S3 guarda tudo e manda o antigo para o arquivo morto.

**Qual seria a alternativa ao Lifecycle?**
S3 Intelligent-Tiering. Descartamos porque o padrão de acesso já é conhecido (12 meses) e o Intelligent-Tiering cobra uma taxa de monitoramento por objeto, que com milhões de arquivos pesa.

### Segurança

**Quem pode acessar os recursos?**
Só clientes criados pelo administrador no Cognito, com senha forte e token de 60 minutos. Cada Lambda tem uma role com uma única permissão (gravar, listar ou ler). Nenhum usuário humano tem chave de acesso no código.

**Como impedem que um cliente veja o arquivo do outro?**
A pasta de cada arquivo é o `sub` do token do Cognito. A Lambda de download só gera link se a chave pedida começar com o `sub` de quem pediu, e recusa `..`. Isso está coberto por testes automatizados e aparece na demo (erro 403).

**Como os dados estão protegidos?**
Em trânsito, só HTTPS: a bucket policy nega qualquer acesso sem TLS. Em repouso, criptografia SSE-S3 (AES-256). Block Public Access ligado nas quatro opções. Links assinados vencem em 5 minutos.

**Por que SSE-S3 e não KMS?**
Não há exigência de chave própria no case, e o KMS cobra por requisição. Se a XYZ precisar de auditoria de uso da chave, a troca é uma linha no template.

**Por que não tem VPC?**
Não existe servidor nosso para isolar. S3, Lambda e API Gateway são gerenciados pela AWS. Uma VPC com NAT Gateway custaria ~US$ 33/mês sem resolver nenhum problema do cliente.

### Custos

**Quais são os recursos mais caros?**
No mês 36: o S3 Standard com os últimos 12 meses de arquivos (~586 GB, US$ 13,48/mês) e a saída para a internet (98 GB, US$ 8,82/mês). Depois vêm as transições de Lifecycle (US$ 2,50), o CloudWatch (US$ 1,75) e o API Gateway (US$ 0,88). Total na calculadora: US$ 29,83/mês.

**Por que a calculadora mostra ~US$ 30 e o slide 3 mostra US$ 1.668?**
A calculadora mostra um mês. O slide 3 soma 60 meses de uma base que cresce todo mês, porque nada é apagado. Validamos o modelo contra a calculadora no mês 36: a diferença foi de 4 centavos.

**Como reduziriam ainda mais?**
Trocar a API REST pela HTTP API (US$ 1 em vez de US$ 3,50 por milhão), abrindo mão da validação de corpo nativa. Colocar o CloudFront na frente dos downloads, porque a saída para a internet (US$ 8,82/mês hoje) é o item que mais cresce com mais clientes. Antecipar o arquivamento se a XYZ aceitar acesso por menos de 12 meses.

**O que acontece com o aumento da demanda?**
O custo sobe linearmente com o uso, sem degraus de servidor. Com 10x os downloads, a saída para a internet passaria de ~US$ 9 para ~US$ 88/mês, e por isso o CloudFront é a primeira evolução de custo. O armazenamento quente fica limitado a 12 meses de arquivos; o resto vai para o Deep Archive, ~23x mais barato por GB. O Budgets avisa antes de estourar o orçamento.

### Escalabilidade

**Como a solução suporta mais usuários?**
Todos os serviços são gerenciados e escalam sozinhos. 10x o volume (500 mil arquivos/mês) dá em média 0,2 envios por segundo.

**Existe algum gargalo?**
Três limites a vigiar: a cota de concorrência de Lambda da conta (contas novas podem ter menos que 1.000), o limite de 50 req/s que nós configuramos na API (ajustável) e 3.500 gravações/s por prefixo no S3 (cada cliente tem o seu prefixo, então isso se distribui).

**O que acontece num pico de acesso?**
Até o limite configurado, tudo responde. Acima dele, a API devolve 429 e protege a conta. O alarme de 4xx avisa se o volume de recusas for alto.

### Recuperação

**O que acontece se um recurso falhar?**
Falha de execução: a API devolve erro, o app repete e o alarme avisa. Falha de AZ: nada muda, os serviços são multi-AZ. Perda de região: os dados estão na réplica em us-east-2 (Ohio).

**Como recuperar os dados?**
Arquivo apagado ou sobrescrito: versão anterior pelo versionamento. Arquivo antigo: restore do Deep Archive. Região perdida: réplica.

**Quanto tempo levaria para restaurar?**
Versão anterior: minutos. Restore do Deep Archive: até 12 horas no modo padrão (48 h no modo bulk, mais barato). Infraestrutura: um novo deploy do template; usem o tempo que vocês mediram no ensaio. A réplica fica em Deep Archive por custo; se a XYZ exigir recuperação rápida, replicar em Standard-IA custaria ~US$ 37/mês no ano 5.

## Regra de ouro

Ao final, a banca precisa conseguir responder:

1. **Qual problema resolvemos?** Guardar 50 mil documentos por mês, para sempre, com cada cliente vendo só os seus.
2. **Como a solução resolve?** Cognito identifica, Lambda autoriza só a pasta certa, S3 guarda e o Lifecycle arquiva.
3. **Por que foi a melhor escolha?** Isolamento provado na demo, sem servidor para cair, e 39% do custo do S3 sem ciclo de vida no ano 5 (10% do custo de um servidor EC2).
