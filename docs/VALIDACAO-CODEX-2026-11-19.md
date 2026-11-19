# Validação do kit Codex em 19 de novembro de 2026

Base revisada: PR #6, commit d8953a08ab9950b933441f40c8d2bd7e4da22387.
Ambiente: macOS arm64 do operador, com HOME descartável. Git, Obsidian e Docker já existiam no host; isso não foi uma máquina virtual sem aplicativos.

## Correções verificadas

- O teste de conexão passou a exigir `initialize` MCP válido. Antes, erros HTTP e HTML com status 200 recebiam resultado positivo.
- A conferência do registro compara URL e variável do token em JSON. Um registro com variável diferente deixa de parecer pronto.
- Uma falha em `codex mcp add` preserva o token anterior e não apaga o registro existente. Isso não pretende garantir rollback de qualquer falha de disco posterior.
- Instaladores retornam erro quando uma etapa necessária falha ou a instalação continua pendente. O wrapper do Mac conserva o código de saída.
- O ensaio real usa configuração descartável e verifica telemetria, resposta esperada e limpeza. A suíte de regressão dos instaladores entrou na CI.

## Testes automatizados

| Suíte | Testes | Resultado local |
|---|---:|---|
| Codex | 39 | 39 aprovados |
| Base | 33 | 32 aprovados e 1 pulado, sem pwsh |
| Onboarding | 14 | 14 aprovados |
| Resultado dos instaladores | 6 | 5 aprovados e 1 pulado, sem pwsh |

Total: 90 aprovados, 2 pulados. Os defeitos foram reproduzidos antes da correção. A revisão independente reproduziu o registro com variável errada usando Codex real e confirmou as correções de registro e instaladores. Sintaxe Bash, compilação Python e `git diff --check` passaram.

## C11 Instalação e registro em HOME vazio

A instalação corrigida executou em `/tmp/validacao-codex-mlKUQf/home` e terminou em 361 segundos, código 0. Instalou GitHub CLI, uv, Python 3.12.16, Node LTS, Java 21 e Codex CLI 0.170.0 e criou o ambiente Python do kit e o atalho do Codex.

A conferência com rede registrou “computador pronto e kit conectado à Root”. O destino foi o repositório fictício privado `operacaoroot/kit-exemplo-marina-duarte`, por chave temporária somente leitura. O teste não publicou arquivos nem provou envio por Git. A chave temporária foi removida e uma nova consulta à API confirmou zero chaves com o prefixo desta validação.

O Codex encontrou o servidor no HOME de teste. `mcp.env` ficou com permissão 600 e fora do Git; o config.toml guardou somente o nome da variável. O servidor respondeu 401 sem token e completou initialize com HTTP 200 com o token.

O wrapper do ensaio terminou com erro de sintaxe ao avançar para C12 porque seu arquivo foi editado durante a execução. O instalador e C11 já haviam terminado. O erro foi da condução do ensaio e não é apresentado como uma execução combinada aprovada. C12 foi repetido com uma cópia congelada do validador, usando o Codex 0.170.0 instalado por C11.

## Limites da validação

Esta prova é de laboratório, com empresa fictícia e base de uma nota. Não prova Windows real, acesso ao SharePoint da Juma, leitura de proposta real nem aceite de Tarcilla. A configuração do Codex do operador não foi alterada. As cópias temporárias da autenticação foram removidas.

O manifesto Juma/Tarcilla permanece rascunho: sistema do computador, perfil e conta de entrega precisam de conferência. Há prévias separadas para Mac e Windows. Nenhuma foi publicada nem gerou ZIP de entrega.

O primeiro uso da Juma parte do SharePoint, conforme orientação de Pedro em 19/11. Leandro conduz com Tarcilla; Daniel resolve permissão de leitura ou bloqueio de download; Rodrigo coordena bloqueios. E-mail e VPS não são pré-requisitos para ler os arquivos já presentes no SharePoint.

## C12 Primeiro uso pelo Codex real

O ensaio final usou Codex CLI 0.170.0 e o módulo MCP real do kit da VPS, com mcp 1.27.2. Em `/tmp/validacao-codex-psYONr`, `codex exec` retornou 0 e o validador também retornou 0. A resposta e a telemetria comprovaram `base_buscar` e `status` com o rótulo `helena-teste`, perfil `leitura`, ocorrência de `ABACAXI-TESTE`, `total=1` e `status.base.notas=1`.

A cópia congelada do validador rodou com `--sem-instalador --manter --aprovar-leituras-laboratorio`, usando no PATH o Codex 0.170.0 instalado por C11. O modo de aprovação foi restrito às duas ferramentas de leitura da base fictícia, conforme a [configuração MCP oficial](https://learn.chatgpt.com/docs/extend/mcp). O sandbox continuou em leitura. O arquivo temporário de autenticação não existe mais.

C11 e C12 foram aprovados em execuções separadas. Isso demonstra instalação, registro e chamadas do kit no laboratório; não substitui o primeiro uso da Juma no SharePoint.
