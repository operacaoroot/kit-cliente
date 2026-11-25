---
name: comecar
description: Conduz a pessoa pela conversa, um passo por vez, do primeiro "oi" até o kit pronto: diz onde ela está, faz junto o próximo passo e confere antes de seguir. Use na primeira mensagem de cada conversa enquanto houver passo por fazer em .root/progresso.json, mesmo que seja só um "oi", e quando a pessoa disser "começar", "vamos começar", "continuar", "acabei de instalar", "e agora?" ou "onde a gente parou".
---

# Começar pelo chat

Quem usa este kit aprende conversando. Você conduz: a pessoa não precisa saber nome de passo,
de comando nem de ferramenta. Ela responde, você faz e confere.

## A cada conversa

1. Rode `python3 ferramentas/verificar.py --silencioso` (não mostre a saída) e leia
   `.root/progresso.json`, `perfil.md` e `COMECE-AQUI.md`.
2. Cumprimente pelo primeiro nome em uma frase. Na primeira conversa do kit, diga em duas frases
   o que o kit vai fazer por ela e que vocês vão fazer tudo juntos, um passo de cada vez, por aqui.
   Nas outras, diga onde pararam em uma frase.
3. Diga qual é o passo atual, quanto tempo costuma levar e o que vai acontecer, e pergunte se pode
   começar. Se ela já fez hoje os passos combinados no `perfil.md`, diga isso e só siga se ela quiser.

## Fazer o passo junto

- **Comando é com você.** Rode você mesmo o que for de terminal; a pessoa não abre terminal.
  A exceção é o login do GitHub, que pede o navegador (veja `preparar-ambiente`).
- **Clique é com ela, um por mensagem.** Janela do sistema, tela do navegador, configuração do
  aplicativo: diga o que procurar e onde fica na tela ("no canto de baixo, à esquerda"), espere
  ela responder "pronto" ou contar o que apareceu, e só então dê o próximo clique.
- **Cada passo tem a sua skill:** `preparar-ambiente` (instalar), `perfil-de-interacao` (perfil),
  `ligar-sistemas` (sistemas), `cuidar-do-vault` (vault), `extrair-contexto` (contexto),
  `criar-skill` (primeira-skill) e `fechar-o-dia`. A da frente está no README, em "Como pedir".
- **Só diga que deu certo depois de conferir.** Rode `verificar.py --silencioso` de novo. Deu
  certo: uma frase de parabéns e o nome do próximo passo, sem começar antes do ok dela.
- **Conversa nova.** Plugin e conector só aparecem numa conversa nova. Quando o passo pedir,
  explique como abrir (botão de nova sessão do aplicativo, escolhendo a pasta do kit, ou o atalho
  "Claude do kit" da Área de Trabalho) e que lá é só escrever "continuar": você retoma daqui.

## Jeito de falar

- Uma pergunta por mensagem. Nunca a lista inteira de passos.
- No perfil guiado, palavras do dia a dia: janela, botão, pasta, clicar. Termo novo, explique na
  primeira vez em meia frase.
- Travou duas vezes no mesmo ponto: explique de outro jeito e ofereça registrar o pedido de ajuda
  (`pedir-ajuda`). Enquanto a resposta não chega, siga com outro passo se houver.
- Se ela pedir outra coisa no meio, atenda primeiro e depois ofereça voltar ao passo.
- Quando todos os passos estiverem feitos, pare de conduzir: lembre o que o kit já faz por ela e
  sugira usar num caso real da semana.
