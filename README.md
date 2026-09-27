# kit-cliente

A fábrica dos kits de onboarding da Root. Cada cliente novo recebe um kit próprio: um repositório
com os passos para começar, o Claude configurado no jeito dele, a base no Obsidian com o que a Root
entendeu das conversas e as ferramentas da primeira frente. A Root acompanha a execução três vezes
por dia sem gastar modelo de IA.

Este repositório é interno. O que vai para o cliente é gerado a partir dele.

## Em 4 comandos

```bash
cp manifestos/_modelo.json manifestos/<slug>.json          # 1. preencher depois do kickoff
python3 perfis/pontuar.py manifestos/<slug>.json --gravar   # 2. proposta de perfil; um sócio assina
python3 montador/montar.py manifestos/<slug>.json --github --zip   # 3. kit, repositório e zip
python3 acompanhador/acompanhar.py                          # 4. acompanhamento (agendado 3x ao dia)
```

## Onde está cada coisa

| Pasta | O que é |
|---|---|
| `docs/KICKOFF.md` | o roteiro mínimo do kickoff, para o sócio da vez |
| `docs/ARQUITETURA.md` | as etapas, os portões e o que fica com quem |
| `docs/PERFIS.md` | os três perfis e como a pontuação funciona |
| `docs/CHAVE.md` | a chave do kit: envio sem conta, atualização, identificação, revogação |
| `docs/ACOMPANHAMENTO.md` | o acompanhador, a resposta a pedidos de ajuda e o agendamento |
| `perfis/` | perfis, sinais, pesos, modelos de mensagem e o `pontuar.py` |
| `manifestos/` | um JSON por cliente (`_modelo.json` e um exemplo fictício) |
| `modelo/` | tudo o que vai para o cliente: textos com `{{campos}}`, passos, skills de base, instaladores, conferência |
| `receitas/` | o cardápio de frentes: 3 inteiras e 3 sementes |
| `montador/` | `montar.py` (gera e publica) e `atualizar.py` (leva melhorias aos kits entregues) |
| `acompanhador/` | `acompanhar.py`, `responder.py` e `agendar.sh` |

## Regras

- Só biblioteca padrão do Python, compatível com 3.9 (é o Python que vem no Mac).
- O montador não chama modelo de IA e recusa kit sem perfil assinado por sócio e sem as reuniões
  conferidas. `--rascunho` existe para mostrar no kickoff e nunca vai para o cliente.
- Kit montado (`saida/`) carrega chave e dado de cliente e nunca entra neste repositório.
- Credenciais: conta `operacaoroot` (`~/.config/root/github.env`) e segredo do selo
  (`~/.config/root/kit.env`). Nenhuma credencial de fora da Root entra aqui.
- Nenhum texto do kit cita outro cliente, projeto anterior ou quem mais a Root atende.
- Texto para o cliente passa pelo checklist de `receitas/kit-de-contexto-e-conteudo/skills/revisar-texto`
  e não leva travessão.
