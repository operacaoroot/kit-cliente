# kit-cliente: instruções para quem trabalha aqui

Fábrica dos kits de onboarding da Root. Leia o `README.md` e `docs/ARQUITETURA.md` antes de mexer.

## Nunca

- Versionar `saida/`, `acompanhador/estado.json` ou `acompanhador/saida/` (têm chave e dado de cliente).
- Citar em `modelo/` ou `receitas/` qualquer cliente, projeto anterior ou outra empresa dos sócios. As
  receitas podem ter nascido em trabalho real, mas o texto é genérico.
- Chamar modelo de IA no montador ou no acompanhador. Os dois são determinísticos de propósito.
- Afrouxar portão do montador para "fazer passar". Perfil sem sócio e reunião sem conferência são
  recusa, e é assim que tem de ser.
- Usar outra conta do GitHub. Tudo é `operacaoroot` via `~/.config/root/github.env`.
- Colocar travessão em texto que vai para o cliente.

## Ao mudar o modelo

- Mexeu em `modelo/`: monte o exemplo (`python3 montador/montar.py manifestos/exemplo-marina-duarte.json --refazer --rascunho`)
  e rode `python3 ferramentas/verificar.py --sem-rede` dentro do kit gerado.
- Mexeu em peça comum (conferência, instaladores, skills de base, permissões): suba a `versao` de
  `modelo/passos.json` e leve aos kits entregues com `python3 montador/atualizar.py --todos "<o que mudou>"`.
- Campo novo em template (`{{campo}}`) precisa existir no contexto de `montar_contexto`; o montador
  recusa campo ausente.
- Receita nova entra como semente (`receita.json` com `estado: semente`) e só vira `inteira` com
  skills, critério de saída e pedidos de exemplo.

## Base das construções com o cliente (29/09/2026)

- O que se instala mora em `modelo/ambiente/apps.json`; mexeu nele, rode `python3 testes/testar_base.py`.
- Instalador de Windows (`.ps1`, `.cmd`) só em ASCII; o teste barra acento.
- App novo entra no `apps.json` com `links` (site e download oficiais, `https://`): o `LINKS.md` do
  kit sai daí. Link de terceiro (tutorial, blog, espelho) nunca entra.
- O cliente é colaborador pelo **nome de usuário** do GitHub; e-mail não serve para convite em
  conta pessoal. Quem mexe em acesso usa `montador/acesso.py`, nunca a tela do GitHub sem registrar
  no manifesto.
- O kit leva a identidade da Root (brand guide v1 em `root-base/10-Identidade/marca`): logo em
  `modelo/marca/` e tema do Obsidian em `modelo/vault/.obsidian/snippets/root.css`.
- Texto de kit Windows não pode ter `python3 `: o montador troca por `.venv/Scripts/python `.
- Skill de base nova é qualquer pasta em `modelo/.claude/skills/` com `SKILL.md`: o montador e o
  `atualizar.py` a levam sozinhos e a registram no `catalogo.json`. No kit Codex ela vai convertida
  para `.agents/skills/` por `para_codex` (montar.py): texto novo que cite o Claude como agente
  precisa passar nessa conversão (`testes/testar_codex.py`).
- `agente: codex` no manifesto monta o kit com o Codex (docs/KIT-CODEX.md). Peça só de um agente
  entra em `SO_DO_CLAUDE` ou `SO_DO_CODEX` no montar.py e na lista do atualizar.py; app ou serviço
  só de um agente leva `agente` no `apps.json`.
- Mudança aqui se constrói em branch `homologacao/...` e entra na `main` depois dos 20 minutos de
  quinta. Conserto de defeito é na hora, avisando.
- Nada deste repositório nem dos kits sai do GitHub `operacaoroot` e da VPS da Root.

## Kit de exemplo

`manifestos/exemplo-marina-duarte.json` é fictício e está publicado em
`operacaoroot/kit-exemplo-marina-duarte` para teste de ponta a ponta (chave, atualização,
acompanhamento, resposta de ajuda). Pode ser remontado e atualizado à vontade.
