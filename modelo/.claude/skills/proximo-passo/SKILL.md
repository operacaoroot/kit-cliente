---
name: proximo-passo
description: Diz à pessoa onde ela está no kit e qual é o próximo passo, no jeito do perfil dela. Use quando ela perguntar "qual o próximo passo", "onde eu estou", "o que falta", "por onde começo", ao abrir o kit pela primeira vez no dia, ou depois de concluir um passo.
---

# Próximo passo

1. Rode `python3 ferramentas/verificar.py --silencioso`. Ele confere cada passo e atualiza
   `.root/progresso.json`.
2. Leia `.root/progresso.json` e `COMECE-AQUI.md`. O passo atual é o primeiro com `feito: false`.
3. Leia o `perfil.md` e responda no nível, tom e formato dele:
   - **guiado**: diga o nome do passo, quanto tempo leva, e descreva o primeiro clique ou a
     primeira frase a escrever. Não mostre o passo inteiro de uma vez. Pergunte se deu certo
     antes de seguir.
   - **chat**: o passo em duas ou três frases, com o porquê em uma delas.
   - **construtor**: o comando ou o pedido, e a prova de pronto.
4. Se a pessoa já fez os passos de hoje (compare `passos_por_dia` do perfil com os passos
   concluídos hoje no `progresso.json`), diga isso e não empurre o próximo, a não ser que ela peça.
5. Se todos os passos estiverem feitos, diga o que o kit já faz por ela (a frente e os pedidos
   do README) e sugira usar a frente num caso real da semana.

## Quando o verificar acusa vermelho num passo que a pessoa diz ter feito

Mostre a prova que faltou (está em `COMECE-AQUI.md`), em linguagem do perfil, e ajude a
completar. Se não resolver em duas tentativas, ofereça registrar um pedido de ajuda
(skill `pedir-ajuda`).
