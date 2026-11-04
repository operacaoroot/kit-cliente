---
name: preparar-ambiente
description: Confere o computador da pessoa, instala o que falta para o kit funcionar (Git, GitHub CLI, Python, Node.js, Java, Claude Code, Obsidian e os recomendados do perfil) e liga o kit à conta dela no GitHub, explicando cada coisa no jeito dela. Use quando ela disser "confere o meu computador", "o que falta instalar", "instala o Obsidian", "instala o Java", "deu erro na instalação", "liga o kit ao GitHub", "não consigo enviar", "onde baixo o ...", ou quando o passo de instalar estiver vermelho.
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
     sistemas, LibreOffice para PDF sem Word).
3. Se o Python do kit (`.venv`) não estiver pronto, diga que ele é criado no mesmo passo.

## Instalar

Sempre peça o OK antes de instalar e diga quanto tempo costuma levar (de 1 a 5 minutos por item).

- Tudo o que o perfil pede: `python3 ferramentas/ambiente.py --instalar`
- Só um item: `python3 ferramentas/ambiente.py --instalar --so <id>`
- Um opcional: `python3 ferramentas/ambiente.py --instalar --com <id>`
- O Python do kit: `python3 ferramentas/ambiente.py --venv`

Depois de instalar, rode `--conferir` de novo e mostre o que mudou.

## Ligar o kit ao GitHub

O kit fala com a Root pelo repositório privado dele, com a conta da pessoa no GitHub.

1. Rode `python3 ferramentas/conectar.py --conferir --json` e diga como está (colaborador, chave
   ou ainda não ligado).
2. Para ligar pela conta: peça que a pessoa rode, **numa janela de terminal** aberta na pasta do
   kit, `python3 ferramentas/conectar.py --conectar`. O GitHub mostra um código de 8 letras: ela
   tecla Enter, o navegador abre, cola o código e clica em Authorize. O convite do kit é aceito
   sozinho. (Você não consegue fazer esse passo por ela, porque o código é confirmado no navegador.)
3. Se ela ainda não tem conta: o link para criar está em `LINKS.md`. Enquanto isso, o kit segue
   pela chave: `python3 ferramentas/conectar.py --usar-chave`.
4. Se a conta que entrou não é a que a Root convidou, o script avisa: registre um pedido de ajuda.

## Links

Quando a pessoa perguntar onde baixar ou onde ler sobre um programa, use só os endereços de
`LINKS.md` (ou `python3 ferramentas/ambiente.py --links`). Nunca indique link de outra fonte.

## O que costuma dar errado e o que fazer

| Aparece | O que dizer e fazer |
|---|---|
| "falhou" logo depois de instalar | O programa entrou, mas esta janela ainda não o enxerga. Peça para fechar o Claude, abrir de novo e conferir. |
| Mac: janela da Apple pedindo ferramentas de linha de comando | Clicar em Instalar, esperar terminar e rodar o instalador do kit de novo. |
| Mac: "não é possível abrir" o instalador | Ajustes do Sistema, Privacidade e Segurança, "Abrir mesmo assim". |
| Windows: pedido de permissão (tela escurece) | Clicar em Sim. Git, GitHub CLI, Node, Java, Docker e LibreOffice pedem isso uma vez. |
| Mac: `java` diz que não há Java instalado | O Java do kit fica em `~/.local/bin`. Feche e abra o terminal (ou o Claude) e confira de novo. |
| "o kit ainda não está ligado ao GitHub" | Siga "Ligar o kit ao GitHub" acima. |
| Windows: sem winget | Instalar o "Instalador de Aplicativo" pela Microsoft Store e rodar de novo. |
| "abri a página de download" | Esse item não se instala sozinho neste sistema: acompanhe a pessoa na página, um clique por vez no perfil guiado. |
| Docker pedindo reinício ou virtualização | Explique o que o Docker pede e acompanhe a pessoa (reiniciar, ligar a virtualização). Se não resolver, registre um pedido de ajuda (skill `pedir-ajuda`). |

Se o mesmo item falhar duas vezes, registre um pedido de ajuda com o que apareceu na tela.

## Regras

- O catálogo `ambiente/apps.json` é a base. Se a pessoa pedir outro programa, instale pela fonte
  oficial (site do fabricante, winget, Homebrew ou o gerenciador do sistema).
- Configuração do sistema também é dela: mexa quando ela pedir.
- Nunca peça nem digite senha do computador pela pessoa. Quem clica em Sim é ela.
- Se o Claude estiver pedindo permissão a cada passo, rode `python3 ferramentas/autonomia.py`
  e peça para ela fechar e abrir o Claude.
- No fim, rode `python3 ferramentas/verificar.py` para registrar o passo.
