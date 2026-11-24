# Arquitetura

## As etapas, na ordem

| # | Etapa | Quem | Entrada | Saída | Portão |
|---|---|---|---|---|---|
| 1 | Conferência das reuniões | sócio (depois o leitor de ata do OS) | atas do Granola | manifesto com dores, fontes e notas, tudo com minuto | `conferencia_das_reunioes.feita_por` |
| 2 | Kickoff | sócio em rodízio | rascunho do kit | sinais de perfil, fontes prioritárias, frente | roteiro mínimo cumprido |
| 3 | Pontuação do perfil | `perfis/pontuar.py` | sinais com minuto | proposta com porcentagem | sócio assina `perfil.conferido_por` |
| 4 | Montagem | `montador/montar.py` | manifesto | kit, repositório privado, convite ao cliente, zip | recusa sem os portões acima |
| 5 | Execução | cliente, com o Claude do kit | kit | commits de progresso | prova de cada passo em `verificar.py` |
| 5a | Ambiente | instalador + skill `preparar-ambiente` | `ambiente/apps.json` | computador pronto, `.venv`, kit ligado ao GitHub | obrigatórios instalados (`ambiente.py --conferir`) e `conectar.py --conferir` |
| 5b | Desenvolvimento do cliente | cliente, com a skill `criar-skill` | tarefa que se repete | ferramenta em `.claude/skills/` e no `catalogo.json` | teste aprovado + `skills.py conferir` |
| 6 | Extração de contexto | skill `extrair-contexto` na máquina do cliente | exportações do ChatGPT e do Claude | `vault/_contexto/` com fonte | auditoria pelo agente `auditor-de-contexto` |
| 7 | Acompanhamento | `acompanhador/acompanhar.py` 3x ao dia | progresso no GitHub | relatório e mensagem sugerida | sócio revisa antes de mandar |

A extração de contexto acontece **depois** do kickoff, dentro do kit, e só nas fontes que o
cliente autorizou no kickoff. É por isso que o mapa de fontes vem antes.

## Uma fonte só: o manifesto

`manifestos/<slug>.json` descreve o cliente: perfil, fontes, frente, notas, combinado. Tudo o que
o kit tem sai dele. Cada campo que veio de conversa carrega o minuto. O montador é determinístico
e não chama modelo de IA: o mesmo manifesto gera o mesmo kit (fora `kit_id`, chave e datas).

## O que vai para o cliente

```
kit-<slug>/
├── README.md, COMECE-AQUI.md, CLAUDE.md, perfil.md   ← gerados do manifesto
├── .claude/skills/   8 de base + até 3 receitas da frente + as do cliente
├── catalogo.json     cada ferramenta: origem (root, frente, cliente), estado, versão
├── oficina/          ferramentas do cliente em teste; _aposentadas/ guarda o que saiu
├── ambiente/         apps.json (o que se instala) e requirements.txt (.venv)
├── .claude/agents/   auditor-de-contexto
├── .claude/settings.json   permissões liberadas, sem bloqueio (ferramentas/autonomia.py tira o pedido de permissão)
├── vault/            Obsidian com as notas da conversa (revisar: sim)
├── ferramentas/      verificar.py, ambiente.py, skills.py, conectar.py, painel.py + passos.json
├── painel/           Painel do kit: a página que mostra a instalação, o que falta e os próximos passos (PAINEL.md)
├── instalar/         .command (Mac), .cmd + .ps1 (Windows), .sh
├── LINKS.md          links oficiais dos programas, das contas e da ajuda (gerado do catálogo)
├── marca/            o logo da Root; o vault abre com o tema da Root (snippet do Obsidian)
├── entregas/  ajuda/  (entrada/ e _privado/ nunca saem da máquina)
└── .root/            cliente.json (selo), progresso.json, chave (fora do git)
```

## O que fica na Root

- **Este repositório** (`operacaoroot/kit-cliente`): perfis, receitas, montador, acompanhador e
  manifestos.
- **O segredo do selo** em `~/.config/root/kit.env`.
- **O token da conta operacaoroot** em `~/.config/root/github.env`, usado para criar os
  repositórios, cadastrar chaves, atualizar kits e ler o progresso.

A parte que dá trabalho para reproduzir (montador, cardápio, pesos de perfil, acompanhamento e as
atualizações) fica do lado da Root. O kit do cliente leva os dados dele e skills que dependem desses
dados. Ver `CHAVE.md`.

## Atualizar kits entregues

`python3 montador/atualizar.py --todos "o que mudou"` leva a conferência, os instaladores, as skills
de base e as permissões para todos os kits publicados, sem tocar no que é do cliente. O cliente
recebe quando fechar o dia.

## O que ainda não existe

- Leitor de ata preenchendo o manifesto sozinho (hoje é o sócio; o leitor do OS é o dono natural).
- Acompanhamento dentro do ROOT OS (hoje é relatório em markdown; o `--json` já é o formato que a
  bancada do OS vai ler).
- Calibração dos pesos: depende de 10 a 15 clientes com o comportamento medido.
- As três receitas-semente (conciliação, painel de vendas, minuta) virarem inteiras.
- **A esteira em kanban no OS** lendo o `--json` do acompanhador (29/09/2026): checklists do
  cartão marcados pela automação, estações mudadas pelo agente, humano só onde precisar. Vem
  depois de o kit estar completo e plug and play no Git; o OS do cliente vem depois disso.
