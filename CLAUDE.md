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

## Kit de exemplo

`manifestos/exemplo-marina-duarte.json` é fictício e está publicado em
`operacaoroot/kit-exemplo-marina-duarte` para teste de ponta a ponta (chave, atualização,
acompanhamento, resposta de ajuda). Pode ser remontado e atualizado à vontade.
