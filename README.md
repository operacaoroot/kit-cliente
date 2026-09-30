# kit-cliente

A fábrica dos kits de onboarding da Root e a **base das construções com os clientes** (decisão de
2026-09-29). Cada cliente novo recebe um kit próprio: um repositório que prepara o computador dele
(Mac ou Windows), os passos para começar, o Claude configurado no jeito dele, a base no Obsidian
com o que a Root entendeu das conversas, as ferramentas da primeira frente e uma oficina para ele
criar as próprias ferramentas. A Root acompanha a execução e o desenvolvimento três vezes por dia
sem gastar modelo de IA.

Do começo ao fim: **ambiente** (instalador lê `modelo/ambiente/apps.json`) → **perfil** → **vault** →
**contexto** → **primeira frente** → **primeira ferramenta do cliente** (oficina, teste, uso) →
**fechar o dia** (progresso e catálogo para a Root).

Este repositório é interno. O que vai para o cliente é gerado a partir dele.

## Em 4 comandos

```bash
cp manifestos/_modelo.json manifestos/<slug>.json          # 1. preencher depois do kickoff
python3 perfis/pontuar.py manifestos/<slug>.json --gravar   # 2. proposta de perfil; um sócio assina
python3 montador/montar.py manifestos/<slug>.json --github --zip   # 3. kit, repositório, convite e zip
python3 acompanhador/acompanhar.py                          # 4. acompanhamento (agendado 3x ao dia)
```

O cliente entra no repositório **como colaborador, com a conta dele no GitHub** (mesa de
2026-09-29): ponha o nome de usuário em `cliente.github` no manifesto. Acesso depois da entrega:

```bash
python3 montador/acesso.py estado <slug>                               # quem tem acesso
python3 montador/acesso.py convidar <slug> --usuario <login>           # convidar ou trocar o usuário
python3 montador/acesso.py encerrar <slug> --motivo "..." --sim        # fim do contrato
```

## Onde está cada coisa

| Pasta | O que é |
|---|---|
| `docs/KICKOFF.md` | o roteiro mínimo do kickoff, para o sócio da vez |
| `docs/ARQUITETURA.md` | as etapas, os portões e o que fica com quem |
| `docs/PERFIS.md` | os três perfis e como a pontuação funciona |
| `docs/CHAVE.md` | o acesso ao kit: cliente como colaborador, a chave do kit, encerramento |
| `docs/ACOMPANHAMENTO.md` | o acompanhador, a resposta a pedidos de ajuda e o agendamento |
| `docs/AMBIENTE.md` | o que o kit instala (Git, GitHub CLI, Python, Node, Java, Claude Code, Obsidian...), por perfil, em Mac e Windows, os links oficiais e como testar |
| `docs/DESENVOLVIMENTO.md` | a oficina: como o cliente cria, testa e põe em uso as próprias ferramentas |
| `testes/testar_base.py` | testes da base (catálogo de apps, instaladores, montagem, oficina) |
| `perfis/` | perfis, sinais, pesos, modelos de mensagem e o `pontuar.py` |
| `manifestos/` | um JSON por cliente (`_modelo.json` e um exemplo fictício) |
| `modelo/` | tudo o que vai para o cliente: textos com `{{campos}}`, passos, catálogo de apps (`ambiente/`), skills de base, instaladores, oficina, conferência |
| `receitas/` | o cardápio de frentes: 3 inteiras e 3 sementes |
| `montador/` | `montar.py` (gera e publica) e `atualizar.py` (leva melhorias aos kits entregues) |
| `acompanhador/` | `acompanhar.py`, `responder.py` e `agendar.sh` |

## Regras

- Só biblioteca padrão do Python, compatível com 3.9 (é o Python que vem no Mac). No cliente, o
  instalador cria um Python 3.12 próprio do kit (`.venv`); as ferramentas continuam rodando no 3.9.
- Tudo o que é da Root e dos clientes mora só no GitHub `operacaoroot` e na VPS da Root
  (decisão de 2026-09-29). Nenhum outro servidor, nenhuma conta de fora.
- O montador não chama modelo de IA e recusa kit sem perfil assinado por sócio e sem as reuniões
  conferidas. `--rascunho` existe para mostrar no kickoff e nunca vai para o cliente.
- Kit montado (`saida/`) carrega chave e dado de cliente e nunca entra neste repositório.
- Credenciais: conta `operacaoroot` (`~/.config/root/github.env`) e segredo do selo
  (`~/.config/root/kit.env`). Nenhuma credencial de fora da Root entra aqui.
- Nenhum texto do kit cita outro cliente, projeto anterior ou quem mais a Root atende.
- Texto para o cliente passa pelo checklist de `receitas/kit-de-contexto-e-conteudo/skills/revisar-texto`
  e não leva travessão.
- Mudança nesta fábrica se constrói em homologação local e só entra na `main` depois dos 20 minutos
  da quinta (decisão dos sócios de 29/09/2026, no `root-base`). Conserto de defeito é na hora, avisando.
- Ordem dos kits em 29/09/2026: Douglas, Danilo (MaisQ), depois Lucas Rezende.
