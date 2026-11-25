# Ambiente do cliente

O que o kit instala no computador do cliente, em Mac e em Windows, e como. A fonte única é
`modelo/ambiente/apps.json`: os instaladores, a conferência e a skill `preparar-ambiente` leem
dele. Mudou o catálogo, mudou tudo junto.

## O que entra, por perfil

| App | Para quê | Guiado | Chat | Construtor | Mac | Windows |
|---|---|---|---|---|---|---|
| Git | guardar o trabalho e falar com a Root | obrigatório | obrigatório | obrigatório | ferramentas da Apple | winget `Git.Git` (pede Sim) |
| GitHub CLI | opcional desde 2026-11-24: o kit liga pela chave, sem login (ver CHAVE.md) | opcional | opcional | opcional | release oficial em `~/.local`, sem admin | winget `GitHub.cli` (pede Sim) |
| uv | instalar o Python sem administrador | obrigatório | obrigatório | obrigatório | script oficial | script oficial |
| Python 3.12 | conferência e ferramentas | obrigatório | obrigatório | obrigatório | `uv python install` | `uv python install` |
| Node.js LTS | conectores do Claude (MCP) e ferramentas em JavaScript | obrigatório | obrigatório | obrigatório | nodejs.org em `~/.local`, sem admin | winget `OpenJS.NodeJS.LTS` (pede Sim) |
| Java 21 (Temurin) | ferramentas e conectores em Java | obrigatório | obrigatório | obrigatório | Adoptium em `~/.local`, sem admin | winget `EclipseAdoptium.Temurin.21.JDK` (pede Sim) |
| Claude Code | o Claude do kit | obrigatório | obrigatório | obrigatório | script oficial | script oficial |
| Obsidian | a base (vault) | obrigatório | obrigatório | obrigatório | dmg do GitHub, sem admin | winget |
| Claude (app) | Claude em janela, aba Code | recomendado | recomendado | opcional | página de download | winget |
| VS Code | ver e editar arquivos | opcional | recomendado | recomendado | zip oficial, sem admin | winget, escopo do usuário |
| Docker Desktop | homologação local | opcional | opcional | recomendado | página de download | winget (pede Sim) |
| LibreOffice | PDF sem Word | opcional | opcional | opcional | página de download | winget (pede Sim) |

Cada app tem no catálogo os **links oficiais** (site, download e ajuda). O catálogo também guarda
os **serviços** que o cliente usa (conta do Claude, conta do GitHub, convite, exportação do
histórico do ChatGPT e do Claude, documentação). O montador gera o `LINKS.md` do kit a partir
daí, e `python3 ferramentas/ambiente.py --links` lista tudo no terminal.

Além dos apps, o instalador cria o **Python do kit** (`.venv`, fora do git) com as bibliotecas de
`modelo/ambiente/requirements.txt`: python-docx, openpyxl, pypdf, pillow, requests, python-dotenv.

Opcional só entra a pedido: `--com node,docker` no Mac e `-Com node,docker` no Windows, ou
"instala o Docker" para o Claude do kit.

## Como o instalador trabalha

- **Mac:** `instalar/instalar.command` (dois cliques) chama `instalar.sh`. Sem as ferramentas de
  linha de comando da Apple, abre a janela da Apple e para: a pessoa instala e roda de novo. Com
  elas (git e o Python do sistema), `ferramentas/ambiente.py --instalar` faz o resto.
- **Windows:** `instalar\instalar.cmd` (dois cliques) chama `instalar.ps1` com
  `-ExecutionPolicy Bypass`. O PowerShell instala Git, uv, Python 3.12 e o `.venv`, e então chama
  o mesmo `ambiente.py` com o Python do kit. Daí em diante a lógica é uma só nos dois sistemas.
- Cada app tem **duas tentativas** automáticas: o erro mais comum numa máquina nova é o download
  cair no meio. E download que para sem cair (menos de 1 KB/s por 60 s) é abortado e retomado do
  ponto em que parou: sem isso o `curl` espera para sempre (visto em 2026-09-29).
- No Mac, Node, Java e GitHub CLI vão para `~/.local/share/kit-root/` com os executáveis ligados
  em `~/.local/bin`: nenhum pede senha. O Java é conferido rodando `java -version`, porque o Mac
  tem um `/usr/bin/java` que existe mesmo sem Java instalado.
- O que não se instala sozinho vira **página de download aberta** e aviso na tela.
- Nada pede conta de fora da Root; nada guarda dado fora da máquina do cliente.

## Regras de quem mexe aqui

- `.ps1` e `.cmd` em **ASCII puro** (o PowerShell 5.1 lê sem BOM como ANSI e acento quebra o
  script) e o `.cmd` com fim de linha do Windows. `testes/testar_base.py` confere.
- Windows: o Claude Code roda os comandos no Git Bash, onde não existe `python3`. O montador troca
  `python3 ` por `.venv/Scripts/python ` em todo texto do kit Windows, e as permissões do Claude
  liberam as duas formas.
- JSON gerado por script: UTF-8 sem BOM.
- App novo entra no `apps.json` com `checar` e `instalar` para mac, windows e linux, e o `id` do
  winget conferido no repositório oficial (`microsoft/winget-pkgs`).
- Nada de acesso remoto (AnyDesk e afins) no catálogo: o suporte ao vivo é por chamada com tela
  compartilhada, e a máquina do cliente não ganha porta aberta.

## Testar

```bash
python3 testes/testar_base.py -v                       # catálogo, instaladores, montagem, oficina
PWSH=/caminho/do/pwsh python3 testes/testar_base.py    # inclui a sintaxe do instalar.ps1
```

Teste real no Mac sem mexer no seu usuário: monte um kit de teste numa pasta temporária e rode o
instalador com uma pasta pessoal vazia:

```bash
env -i HOME=/tmp/casa-vazia PATH=/usr/bin:/bin:/usr/sbin:/sbin TERM=xterm bash instalar/instalar.sh
```

Teste real no Windows: máquina ou usuário limpo, dois cliques em `instalar\instalar.cmd`.

## Resultado dos testes

| Data | Onde | Resultado |
|---|---|---|
| 2026-09-29 | Mac M1, pasta pessoal vazia | git, uv, Python 3.12, `.venv` com as bibliotecas e chave ok; Claude Code caiu por tempo esgotado no download; atalho falhou sem a pasta Mesa. Os dois viraram correção (segunda tentativa e criação da pasta). |
| 2026-09-29 | Mac M1, pasta pessoal vazia, perfil construtor, código corrigido | tudo pronto em 1 min 22 s: git, uv 0.12.20, Python 3.12.14, Claude Code 2.1.285 (abre), `.venv` com as 6 bibliotecas, chave ligada, atalho na Mesa. Só o teste de rede falha, porque o kit de teste não existe no GitHub. |
| 2026-09-29 | PowerShell 7.6.6 (Mac) | `instalar.ps1` sem erro de sintaxe |
| 2026-09-29 | Mac M1, pasta pessoal vazia, só `--so gh,node,java` | GitHub CLI 2.101.0, Node.js v24.21.0 (npm 11.19.0) e Java 21.0.12.1 com javac, todos em `~/.local`, sem senha. O primeiro teste achou dois defeitos, corrigidos: o download do Node parou em 12 MB e o `curl` esperou quase 2 h (agora aborta abaixo de 1 KB/s por 60 s e retoma), e um Java 8 do sistema passava como Java 21 (agora a conferência exige a versão 21). |
| 2026-09-29 | links do catálogo (35) | 30 respondem 200; claude.ai, github.com/signup e help.openai.com respondem 403 a acesso automatizado (proteção contra robô), as páginas existem |
| pendente | Windows real | a fazer pelos sócios |
