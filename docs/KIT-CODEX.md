# Kit em versão Codex

O kit de pessoa sai da fábrica em duas versões, escolhidas pelo campo `agente` do manifesto:
`claude` (o padrão, o que sempre existiu) e `codex` (o Codex do ChatGPT como agente do
computador). Esta página define o que a versão Codex entrega, os critérios de aceite e os
testes que provam cada um. A regra é teste antes do código: cada critério abaixo tem um teste
em `testes/testar_codex.py`, escrito antes do montador saber o que é `agente: codex`.

## O que muda quando `agente` é `codex`

| Peça | Kit Claude | Kit Codex |
|---|---|---|
| Programa instalado | Claude Code (`claude.ai/install.sh`) e o aplicativo Claude | Codex CLI (`chatgpt.com/codex/install.sh` no Mac e Linux, winget `OpenAI.Codex` no Windows) |
| Instruções do agente | `CLAUDE.md` | `AGENTS.md` (o Codex lê o arquivo da raiz da pasta) |
| Skills | `.claude/skills/<nome>/SKILL.md` | `.agents/skills/<nome>/SKILL.md`, mesmo `SKILL.md` com `name` e `description`, texto convertido |
| Agente auditor | `.claude/agents/auditor-de-contexto.md` | skill `auditar-contexto` (o Codex não tem subagente de arquivo) |
| Servidor da empresa (MCP) | `mcp.json` por fora do kit | `codex mcp add <nome> --url <url> --bearer-token-env-var <VAR>`, feito pelo instalador; o token mora em `.root/mcp.env`, fora do git |
| Atalho na Mesa | "Claude do kit" (`claude`) | "Codex do kit" (`codex`, carregando o token do MCP) |
| Página guiada de onboarding (Mac) | sim | não: `instalar.command` vai direto ao instalador de terminal |
| `ferramentas/autonomia.py` | sim (libera o Claude) | não entra |
| Conta | Claude individual, 1º mês reembolsado | ChatGPT da empresa; o Codex usa a mesma conta |

O manifesto ganha dois campos:

```json
"agente": "codex",
"mcp": {
  "nome": "exemplo-os",
  "url": "https://mcp.exemplo.com.br/mcp",
  "perfil": "leitura",
  "variavel": "EXEMPLO_OS_MCP_TOKEN"
}
```

`mcp` é opcional e nunca leva o token: o token é digitado na instalação (ou vem da variável
`KIT_MCP_TOKEN`) e fica em `.root/mcp.env`, com permissão 600, ignorado pelo git.

## Critérios de aceite

Cada critério aponta o teste que o prova. "Offline" é teste que roda sem rede, sem Codex e sem
conta; "real" é o que só se prova com o Codex instalado e um servidor MCP de verdade.

| # | Critério | Teste |
|---|---|---|
| C1 | O manifesto aceita `agente: claude` ou `codex` (ausente vale `claude`) e recusa outro valor; `mcp`, quando presente, exige `nome` (slug), `url` (`https://`, ou loopback para teste), `perfil` (`leitura`, `equipe`, `full`) e `variavel` (MAIÚSCULAS) | `Manifesto.*` |
| C2 | O ZIP sai com o instalador do Codex CLI no lugar do Claude Code: `ambiente/apps.json` do kit tem `codex` obrigatório em todo perfil e não tem `claude-code` nem `claude-app`; a parte do instalador que depende do agente mora em `instalar/agente.sh` e `instalar/agente.ps1` (o montador copia só a do Codex: atalho "Codex do kit", comando `codex`, registro do MCP; sem `autonomia.py`), e `instalar.command` vai direto ao terminal | `Instalador.*` |
| C3 | `AGENTS.md` na raiz, renderizado (sem `{{`), com o nome da pessoa, o `kit_id`, a pasta `.agents/skills` e o nome do servidor MCP; sem `CLAUDE.md` | `Instrucoes.*` |
| C4 | As skills de base (menos `validar-onboarding`, que depende da página guiada) e as da frente estão em `.agents/skills/<nome>/SKILL.md`, com `name` igual à pasta e `description`; `auditar-contexto` entra como skill, sem a linha `tools:`; o catálogo bate com as pastas; `skills.py` e `verificar.py` trabalham em `.agents/skills` (ciclo da oficina e prova do passo `primeira-skill`) | `Skills.*` |
| C5 | O servidor MCP vai registrado por `codex mcp add` com token por pessoa: `.root/cliente.json` tem `mcp` sem token; `.gitignore` barra `.root/mcp.env`; `ferramentas/mcp.py --registrar` grava `.root/mcp.env` (600) e chama `codex mcp add <nome> --url <url> --bearer-token-env-var <VAR>`; `--conferir --json` responde sem Codex instalado; `--testar` exige 401 sem token e completa initialize com token; o token nunca aparece em arquivo versionado nem nos argumentos do `codex` | `Mcp.*` |
| C6 | Nada do Claude dentro: sem `.claude/`, `CLAUDE.md`, `autonomia.py`, `onboarding/` e `ferramentas/onboarding.py`; nenhum `.md`, `.json`, `.sh`, `.command` ou `.ps1` do kit cita `Claude`, `.claude`, `claude-code`, `claude-app` ou `claude.ai`. Única exceção: `extrair-contexto` cita a exportação do claude.ai como **fonte de dado** da pessoa (não como agente), no `SKILL.md` e no resumo dela em `catalogo.json`; ali não há `Claude Code`, `CLAUDE.md`, `.claude/` nem `Claude do kit` | `NadaDoClaude.*` |
| C7 | O kit Codex para Windows passa pelas mesmas regras do kit Windows (sem `python3 ` em texto, `.ps1` e `.cmd` em ASCII) e instala o Codex pelo winget | `KitWindowsCodex.*` |
| C8 | O kit Claude não muda: sem `AGENTS.md`, sem `.agents/`, sem `ferramentas/mcp.py`, e a suíte `testar_base.py` continua passando | `KitClaudeIntacto.*` e `testar_base.py` |
| C9 | `para_codex` converte o texto do agente (Claude Code → Codex, `CLAUDE.md` → `AGENTS.md`, `.claude/skills` → `.agents/skills`, "Claude do kit" → "Codex do kit", agente `auditor-de-contexto` → skill `auditar-contexto`, `` `claude` `` → `` `codex` ``) e preserva as frases em que Claude é fonte de dado (exportação, memória, zip) | `Conversao.*` |
| C10 | `atualizar.py` sabe o que levar a um kit Codex: nada de `.claude/`, `autonomia.py` ou página guiada; leva `agente.py`, `mcp.py` e as skills convertidas para `.agents/skills` | `Atualizacao.*` |
| C11 (real) | Numa pasta descartável deste Mac, com `HOME` vazio: o instalador roda, instala o Codex CLI, registra o servidor MCP no `config.toml` desse `HOME`, e `codex mcp get <nome>` o mostra | `testes/validar_codex_real.sh`, registrado abaixo |
| C12 (real) | Contra um servidor FastMCP de verdade (o `servidor.py` do módulo `mcp` do kit da VPS, com token de teste): sem token responde 401; com token aceita; uma chamada de leitura feita pelo Codex (`codex exec`) devolve o resultado da ferramenta e o rastro `logs/mcp/uso.jsonl` registra o rótulo da pessoa | `testes/validar_codex_real.sh`, registrado abaixo |

## O que fica fora desta versão

- A página guiada de onboarding do Mac (`onboarding/`, `ferramentas/onboarding.py`) é toda
  construída em volta do aplicativo Claude (`claude://` e a conta Claude). No kit Codex o
  `instalar.command` vai direto ao instalador de terminal, como no Windows.
- `autonomia.py` grava `~/.claude/settings.json`; não há equivalente para o Codex no kit. A
  aprovação de comandos fica a cargo da pessoa no próprio Codex.
- `.claude/settings.json` (permissões) não tem equivalente de projeto no Codex; não é gerado.
- O registro do MCP é global na conta do Codex da máquina (`~/.codex/config.toml`), pelo
  próprio `codex mcp add`; o nome do servidor vem do manifesto e precisa ser único na máquina.

## Validação real

O procedimento atualizado e seus limites estão abaixo. A evidência de cada execução fica em `evidencia.md` na pasta temporária indicada pelo validador.

### Revalidação de 19 de novembro de 2026

A correção passa a exigir uma resposta MCP `initialize` válida: HTTP 400, 404, 406,
500 e uma página HTML com HTTP 200 deixam de contar como conexão pronta. O registro
confere o endereço e o nome da variável de token em `codex mcp get --json`. Repetir
`mcp add` atualiza o registro; não é mais necessário apagá-lo antes. Se o comando
falhar, o token anterior fica preservado.

Os instaladores agora retornam erro quando a preparação, a conexão ou a etapa
`instalar` continuam pendentes. Os demais passos do onboarding podem continuar
abertos. O atalho de instalação do Mac preserva esse código de saída.

O ensaio de laboratório usa o repositório fictício privado já existente. Ele cria
uma chave de deploy temporária somente leitura e a remove ao terminar:

```bash
KIT_REPO_TESTE=operacaoroot/kit-exemplo-marina-duarte \
INSTALAR_SO=git,gh,uv,python,node,java,codex \
KIT_SELO_SEGREDO=teste-local-descartavel \
bash testes/validar_codex_real.sh --manter --aprovar-leituras-laboratorio
```

`--aprovar-leituras-laboratorio` autoriza somente `base_buscar` e `status` do MCP
local da base fictícia. Mantém `sandbox=read-only`, usa configuração descartável
e não altera a configuração pessoal. O servidor atual não declara `readOnlyHint`;
sem essa autorização específica, o Codex pode recusar as chamadas no modo sem
interação. A opção por ferramenta está documentada em
[Model Context Protocol](https://learn.chatgpt.com/docs/extend/mcp).

O resultado exige as duas chamadas no rastro da pessoa e o conteúdo esperado:
`ABACAXI-TESTE`, uma ocorrência na busca e uma nota no status. A autenticação
copiada para o ensaio é apagada no encerramento. `--sem-instalador` e `--sem-exec`
produzem validações parciais, identificadas no relatório.

Esse laboratório não comprova Windows real, acesso ao SharePoint nem aceite da
pessoa no ambiente do cliente. As permissões de SharePoint e o primeiro uso com
um documento real continuam sendo verificados na entrega de cada cliente.
