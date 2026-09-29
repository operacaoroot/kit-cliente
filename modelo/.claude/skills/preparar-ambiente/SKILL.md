---
name: preparar-ambiente
description: Confere o computador da pessoa e instala o que falta para o kit funcionar (git, Python, Claude Code, Obsidian e os recomendados do perfil), explicando cada coisa no jeito dela. Use quando ela disser "confere o meu computador", "o que falta instalar", "instala o Obsidian", "deu erro na instalação", "quero o VS Code", "quero o Docker", ou quando o passo de instalar estiver vermelho.
---

# Preparar o ambiente

O catálogo do que o kit usa está em `ambiente/apps.json`, e quem confere e instala é
`ferramentas/ambiente.py`. Esta skill conversa com a pessoa; o script faz o trabalho.

## Conferir

1. Rode `python3 ferramentas/ambiente.py --conferir --json`.
2. Explique o resultado no tom do `perfil.md`, sem jargão para o perfil guiado:
   - o que está pronto, em uma linha;
   - o que falta dos **obrigatórios**, cada um com o "para que" do catálogo;
   - os **recomendados** que faltam, oferecendo instalar;
   - os **opcionais** só se a pessoa perguntar ou se a tarefa dela pedir (Docker para testar
     sistemas, LibreOffice para PDF sem Word, Node para ferramenta em JavaScript).
3. Se o Python do kit (`.venv`) não estiver pronto, diga que ele é criado no mesmo passo.

## Instalar

Sempre peça o OK antes de instalar e diga quanto tempo costuma levar (de 1 a 5 minutos por item).

- Tudo o que o perfil pede: `python3 ferramentas/ambiente.py --instalar`
- Só um item: `python3 ferramentas/ambiente.py --instalar --so <id>`
- Um opcional: `python3 ferramentas/ambiente.py --instalar --com <id>`
- O Python do kit: `python3 ferramentas/ambiente.py --venv`

Depois de instalar, rode `--conferir` de novo e mostre o que mudou.

## O que costuma dar errado e o que fazer

| Aparece | O que dizer e fazer |
|---|---|
| "falhou" logo depois de instalar | O programa entrou, mas esta janela ainda não o enxerga. Peça para fechar o Claude, abrir de novo e conferir. |
| Mac: janela da Apple pedindo ferramentas de linha de comando | Clicar em Instalar, esperar terminar e rodar o instalador do kit de novo. |
| Mac: "não é possível abrir" o instalador | Ajustes do Sistema, Privacidade e Segurança, "Abrir mesmo assim". |
| Windows: pedido de permissão (tela escurece) | Clicar em Sim. Git, Node, Docker e LibreOffice pedem isso uma vez. |
| Windows: sem winget | Instalar o "Instalador de Aplicativo" pela Microsoft Store e rodar de novo. |
| "abri a página de download" | Esse item não se instala sozinho neste sistema: acompanhe a pessoa na página, um clique por vez no perfil guiado. |
| Docker pedindo reinício ou virtualização | Não resolva por conta própria: registre um pedido de ajuda (skill `pedir-ajuda`). |

Se o mesmo item falhar duas vezes, registre um pedido de ajuda com o que apareceu na tela.

## Regras

- Não instale nada que não esteja em `ambiente/apps.json`. Se a pessoa pedir outro programa,
  diga que vai registrar o pedido para a Root avaliar (skill `pedir-ajuda`).
- Nunca peça nem digite senha do computador pela pessoa. Quem clica em Sim é ela.
- Não mexa em configuração do sistema além do que o instalador faz.
- No fim, rode `python3 ferramentas/verificar.py` para registrar o passo.
