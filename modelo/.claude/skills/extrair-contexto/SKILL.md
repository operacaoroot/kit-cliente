---
name: extrair-contexto
description: Transforma as exportações do ChatGPT e do Claude da pessoa num pacote de notas com fonte, dentro do vault, sem nada sair da máquina. Use quando ela disser "quero trazer o meu histórico de IA", "extrair contexto", "ler as minhas conversas antigas", ou no passo "contexto" do COMECE-AQUI.
---

# Extrair contexto do ChatGPT e do Claude

A pessoa usa IA no trabalho, e o histórico dessas conversas mostra quem ela é, como trabalha, o
que pede toda semana e onde a IA falha com ela. Esta skill transforma as exportações num pacote de
notas em `vault/_contexto/`, cada afirmação com a fonte.

O pacote serve para três coisas: carregar a base do kit (quem ela é, vocabulário, regras,
projetos), mostrar quais tarefas repetidas a frente do kit pode assumir, e registrar a linha de
base (quanto tempo e quantas idas e vindas cada tarefa custa hoje) para comparar depois.

Antes de começar, leia no vault o que a Root já sabe (`10-Identidade`, `40-Operacao`, `90-Metas`) e
as fontes combinadas no kickoff. **Só leia as fontes que a pessoa autorizou.**

## Regras duras (valem do começo ao fim)

1. **Tudo fica nesta máquina.** Não use busca na web, não suba arquivo e não chame serviço externo
   além do modelo em que você já está rodando.
2. **A exportação original não é tocada.** Leia `entrada/`, nunca escreva nem apague nada lá.
3. **Segredo nunca é copiado.** Chave de API (`sk-`, `sk-ant-`, `sk-or-`, `Bearer`, tokens em
   geral), senha, dado bancário, número de cartão, CPF e RG: conte, anote em qual conversa apareceu
   e substitua por `[SEGREDO:tipo]` em todo arquivo gerado. O valor não aparece na tela nem em arquivo.
4. **Dado comercial de terceiro fica fora.** Nome de empresa cliente pode aparecer. Valor, preço,
   desconto, condição de contrato, dado de fatura e dado pessoal de terceiros (telefone, e-mail,
   documento) não entram. Descreva o padrão ("proposta para rede de varejo") sem o número.
5. **Vida pessoal fica fora.** Saúde, família, finanças pessoais e relacionamentos: conte quantas
   conversas são e não resuma nenhuma.
6. **Nada entra sem fonte.** Toda afirmação leva a fonte no formato
   `[gpt:1a2b3c4d · 2026-03-14 · "título da conversa"]` ou `[cld:1a2b3c4d · ...]`, com os 8 primeiros
   caracteres do id. Marque cada afirmação como **fato** (a pessoa disse com todas as letras),
   **padrão** (aparece em 3 conversas ou mais, e aí cite 3) ou **hipótese** (1 ou 2 ocorrências).
7. **O que a pessoa escreveu vale mais do que o que a IA respondeu.** A resposta da IA só serve
   para identificar a versão final que ela aceitou.
8. **Se o `perfil.md` tiver restrição corporativa**, pergunte antes de ler cada fonte e não leia
   conversa marcada como do cliente da empresa se a pessoa pedir.

## Onde está cada coisa

```
<pasta do kit>/
├── entrada/
│   ├── chatgpt/     ← zip do ChatGPT descompactado
│   └── claude/      ← zip do Claude descompactado
├── _privado/        ← intermediários; nunca sai da máquina (está no .gitignore)
└── vault/_contexto/ ← o pacote
```

O trabalho pesado vai em scripts Python só com a biblioteca padrão (sem `pip install`), guardados em
`_privado/scripts/`. Não carregue os JSON inteiros no contexto: a exportação de uma conta usada há
anos pode ser grande demais.

## Fase 0: conferir a entrada

1. Se `entrada/` estiver vazia, explique no nível do perfil como exportar:
   - ChatGPT: Configurações > Controles de dados > Exportar dados. O link chega por e-mail.
   - Claude: Configurações > Privacidade > Exportar dados.
   Peça para descompactar em `entrada/chatgpt` e `entrada/claude`. Pare até os arquivos chegarem.
2. Liste `entrada/` e descubra o formato de cada exportação antes de escrever qualquer parser. Abra
   as chaves do primeiro registro e confirme, em vez de presumir.
   - **ChatGPT:** costuma vir `conversations.json` (às vezes dividido) e `chat.html`. Cada conversa é
     uma árvore em `mapping`; a versão que valeu é o caminho que sai de `current_node` e sobe até a
     raiz. O modelo usado costuma estar em `metadata.model_slug`.
   - **Claude:** costuma vir `conversations.json`, com as mensagens em `chat_messages` (`sender` =
     `human` ou `assistant`), e os projetos em `projects.json` ou numa pasta `projects/`.
3. Se faltar uma das exportações, siga com a que existe. Se faltarem as duas, passe o prompt do
   **Anexo A**, espere a pessoa colar as respostas e monte o pacote só com elas, com confiança baixa
   e sem a linha de base.
4. As exportações não trazem as instruções personalizadas nem as memórias salvas do ChatGPT, nem as
   instruções dos GPTs criados. Peça, numa mensagem só, que a pessoa cole o que quiser incluir
   (instruções personalizadas, memórias salvas, instruções de GPTs e Projetos, memória do Claude) ou
   responda "pula". O que ela colar vai para `_privado/manual/`.

## Fase 1: inventário, segredos e triagem

1. Normalize as duas fontes em `_privado/normalizado.jsonl`, uma linha por conversa: fonte, id,
   título, criada em, atualizada em, modelo, projeto ou GPT, número de mensagens da pessoa, texto
   das mensagens dela e texto final da IA. Grave já com os segredos mascarados (regra 3).
2. Varra segredos e dados pessoais com expressões regulares e grave `_privado/segredos.md` com tipo,
   quantidade e conversa, sem o valor.
3. Classifique cada conversa pelo título e pela primeira mensagem, usando o que o vault diz sobre o
   trabalho da pessoa: **trabalho atual**, **trabalho anterior**, **marca pessoal e conteúdo**,
   **técnico** (código, agentes, automação), **pessoal** (regra 5) e **outros**.
4. **Pare e mostre** uma tabela com as conversas por grupo e por ferramenta, o período coberto e
   quantos segredos apareceram. Pergunte se ela quer tirar algum grupo ou assunto. Só siga depois
   da resposta.

## Fase 2: leitura

Leia com profundidade os últimos 12 meses. Do período anterior, use só títulos e contagens, a não
ser que o assunto antigo continue vivo. Acima de 2.000 conversas, leia todas as mensagens da pessoa
e só a resposta final da IA nas conversas que for citar.

Procure, nesta ordem:

1. **Quem ela é hoje:** cargo, empresa, o que entrega, para quem e com quem trabalha.
2. **Vocabulário:** siglas e termos da casa e o sentido que ela dá a cada um.
3. **Pessoas e empresas** que aparecem 3 vezes ou mais: nome, papel e relação, sem contato.
4. **Tarefas recorrentes:** o que ela pede à IA com frequência. Para cada uma: quantas vezes, a
   última vez, a ferramenta, quantas idas e vindas até a versão final e para onde a saída vai.
5. **Prompts e instruções que ela já construiu.**
6. **Fontes de dado:** o que ela cola ou anexa e de onde vem. Registre o tipo, nunca o conteúdo.
7. **Voz:** como é o texto final que ela aprova e o que ela manda tirar do texto da IA, com as
   palavras dela. Separe o jeito que ela fala com a IA do texto que ela publica.
8. **Onde a IA falhou:** conversas em que ela corrigiu, repetiu o pedido ou largou no meio, o que
   deu errado e o que ela teve de explicar de novo.
9. **Decisões** declaradas, com data.
10. **Projetos e metas** em andamento.
11. **Como ela divide o trabalho entre o Claude e o ChatGPT.**

## Fase 3: escrever o pacote

Toda nota começa com o cabeçalho do vault (skill `cuidar-do-vault`), com `revisar: sim`,
`fonte: exportação ChatGPT de AAAA-MM-DD + exportação Claude de AAAA-MM-DD` e `confianca: alta |
media | baixa`. Português, data absoluta, frase inteira.

| Arquivo em `vault/_contexto/` | kind | O que tem |
|---|---|---|
| `00 - LEIA-ME.md` | nota | o que o pacote tem, os números do inventário, o que ficou de fora e por quê, o que revisar |
| `Quem é.md` | fato | trajetória, papel atual, o que entrega e para quem |
| `Voz e escrita.md` | regra | traços da escrita com exemplos, vícios que ela manda tirar (nas palavras dela), 5 trechos aprovados |
| `Dicionário.md` | dicionario | termo, significado para ela, exemplo e fonte |
| `Pessoas e empresas.md` | fato | nome, papel, relação e última menção |
| `Tarefas recorrentes.md` | nota | as 15 tarefas mais frequentes (colunas abaixo) |
| `Prompts e instruções.md` | nota | instruções e pedidos longos que ela reusa, limpos de dado sensível |
| `Onde a IA falhou.md` | nota | os 10 casos mais claros: pedido, o que deu errado, contexto que faltou, o que o kit precisa ter |
| `Claude e ChatGPT.md` | nota | para que ela usa cada um e o motivo |
| `Projeto - <nome>.md` | nota | uma por projeto ativo: o que é, estado, próximo passo citado |
| `AAAA-MM-DD - <decisão>.md` | decisao | só decisão declarada, uma por nota |
| `Uso de IA - linha de base.md` | fato | os números da linha de base (abaixo) |
| `Fontes de dado.md` | fato | tipo de fonte, de onde vem, para qual tarefa e com que frequência |
| `Metas.md` | fato | metas declaradas, com prazo e fonte |

**Colunas de `Tarefas recorrentes`:** tarefa · vezes nos últimos 12 meses · última vez · ferramenta ·
idas e vindas (mediana) · tempo de conversa (mediana) · para onde vai a saída · trecho de um pedido.

**`Uso de IA - linha de base`:** conversas por mês e por ferramenta nos últimos 12 meses; mediana de
mensagens da pessoa por conversa; porcentagem de conversas com retrabalho (corrigiu ou repetiu o
pedido 2 vezes ou mais), explicando a regra usada; os 10 temas com mais volume; a coluna de tempo das
tarefas recorrentes. Deixe escrito que "tempo de conversa" é o intervalo entre a primeira e a última
mensagem, e não hora trabalhada.

Quando o histórico não disser nada sobre um assunto, escreva "sem dado no histórico" em vez de
completar por dedução.

## Fase 4: conferir e entregar

1. Rode a varredura de segredos de novo em `vault/_contexto/`. Se achar algo, corrija antes de terminar.
2. Confira que toda afirmação tem fonte e marca (fato, padrão ou hipótese).
3. Chame o agente `auditor-de-contexto` para a auditoria (ele grava `vault/_contexto/00 - Auditoria.md`).
4. Diga à pessoa, em até 10 linhas e no tom do perfil: quantas notas saíram, os 3 achados que mais
   chamaram atenção, o que ficou de fora e o que ela precisa revisar. Lembre que `_privado/` e
   `entrada/` nunca saem da máquina.
5. Rode `python3 ferramentas/verificar.py` para registrar o passo.

## Anexo A: prompt para colar dentro do ChatGPT e do Claude

Serve para trazer o que está na memória de cada ferramenta, que a exportação não inclui, e como
plano B quando a conta for corporativa e não permitir exportar.

```
Quero levar o que você sabe sobre mim para outro sistema. Com base na sua memória e no nosso
histórico de conversas, escreva em tópicos:

1. quem eu sou e o que faço hoje;
2. as empresas, pessoas e projetos que aparecem com frequência;
3. as tarefas que eu mais te peço e como eu gosto da saída;
4. as correções que eu costumo fazer no seu texto;
5. os termos e siglas que eu uso e o que significam;
6. as decisões e preferências que eu já te disse.

Para cada item, diga se veio da memória salva ou de uma conversa, e marque o que é inferência sua.
Se não souber, escreva "não sei" em vez de completar. Não inclua senha, chave, valor de contrato
nem dado pessoal de terceiros.
```
