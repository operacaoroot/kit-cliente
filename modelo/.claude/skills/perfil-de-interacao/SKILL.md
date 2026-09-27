---
name: perfil-de-interacao
description: Configura e ajusta como o Claude atende a pessoa dona deste kit (tom, nível de explicação, formato, ritmo, iniciativa). Use no primeiro uso do kit, quando o perfil.md estiver com "confirmado: não", e sempre que a pessoa pedir para mudar o jeito de falar ("fala mais curto", "explica melhor", "para de sugerir", "vamos configurar o meu perfil").
---

# Perfil de interação

O `perfil.md` na raiz do kit diz como atender a pessoa. A Root preencheu a partir do kickoff;
esta skill confirma com ela e mantém o arquivo vivo.

## Primeira configuração (perfil com `confirmado: não`)

1. Leia o `perfil.md` inteiro, inclusive a seção "O que entendemos na conversa".
2. Mostre à pessoa, em até 6 linhas, o que a Root entendeu: nível, tom, formato, ritmo e
   iniciativa, cada um com a frase da conversa que sustenta a escolha quando houver.
3. Faça **uma pergunta por vez**, e só as que a pessoa não respondeu na conversa. Ofereça as
   opções em linguagem simples, nunca o nome técnico do campo:
   - "Quando eu te explicar algo, você prefere: passo a passo com onde clicar, o passo com uma
     frase do porquê, ou só o comando?" (nivel e formato)
   - "Prefere que eu fale de um jeito mais explicado ou mais direto?" (tom)
   - "Quantos passos por dia cabem na sua rotina, e em que horário?" (passos_por_dia, horario)
   - "Quer que eu sugira coisas por conta própria sempre, só quando for importante, ou só quando
     você pedir?" (iniciativa_claude)
   - "Você aprende melhor fazendo, lendo ou vendo alguém fazer?" (como_aprende)
4. Grave as respostas no cabeçalho do `perfil.md` com os valores permitidos (estão na seção "O que
   cada campo quer dizer") e troque `confirmado: não` por `confirmado: sim`.
5. Rode `python3 ferramentas/verificar.py` para registrar o passo.
6. Responda já no novo jeito, em uma frase, dizendo qual é o próximo passo.

## Ajuste depois

Quando a pessoa pedir mudança ("mais curto", "com mais detalhe", "me lembra menos"):

1. Mude só o campo correspondente no `perfil.md`.
2. Acrescente uma linha em "Histórico de ajustes" no fim do arquivo (crie a seção se não existir):
   `- AAAA-MM-DD: <campo> de <antes> para <depois>, a pedido.`
3. Confirme em uma frase o que mudou e siga a conversa no novo jeito.

## Sugestão de ajuste (só se `iniciativa_claude` não for `quando-pedido`)

Se a pessoa travar duas vezes no mesmo ponto, ou pedir para repetir uma explicação, ofereça uma
vez: "Quer que eu passe a explicar com mais detalhe?". Se ela disser não, não ofereça de novo
naquela semana. Nunca mude o perfil sem o sim dela.
