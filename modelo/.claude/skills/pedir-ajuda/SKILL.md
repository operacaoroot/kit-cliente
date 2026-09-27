---
name: pedir-ajuda
description: Registra um pedido de ajuda para a Root quando a pessoa trava, algo dá erro ou ela tem uma dúvida que o kit não resolve. Use quando ela disser "preciso de ajuda", "não funcionou", "travei", "chama a Root", ou quando o mesmo passo falhar duas vezes.
---

# Pedir ajuda

A Root lê os pedidos três vezes por dia (os horários estão no `CLAUDE.md`). O pedido chega quando o
kit é enviado, por isso esta skill termina fechando o envio.

1. Pergunte, se ainda não estiver claro: o que ela tentou fazer, o que apareceu na tela e em qual
   passo. Uma pergunta por vez, no tom do `perfil.md`.
2. Crie `ajuda/AAAA-MM-DD-HHMM.md`:

   ```markdown
   ---
   estado: aberto
   passo: <id do passo em .root/progresso.json>
   aberto_em: AAAA-MM-DDTHH:MM
   assunto: <até 8 palavras>
   ---

   # <assunto>

   ## O que tentou
   ## O que aconteceu
   ## O que já foi tentado para resolver
   ```

   Descreva o erro com as palavras da tela. **Não copie** senha, chave, token, dado de cliente
   ou conteúdo de documento: descreva o tipo ("um PDF de proposta"), nunca o conteúdo.
3. Envie o pedido: `git add ajuda/ && git commit -m "Pedido de ajuda: <assunto>" && git push`.
   Se o push falhar, diga à pessoa que o pedido ficou salvo e que ela pode mandar o print pelo
   canal de ajuda combinado (está no `CLAUDE.md`).
4. Diga quando a Root costuma responder e ofereça seguir com outro passo enquanto isso.

Quando a Root responder, ela grava a resposta no mesmo arquivo e muda `estado` para
`respondido`. Ao abrir o kit, se houver pedido respondido que a pessoa ainda não viu, mostre a
resposta primeiro.
