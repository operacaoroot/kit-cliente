---
name: dossie-de-conta
description: Monta o dossiê de uma página de uma conta (empresa cliente ou prospect) antes de uma reunião, cruzando fonte pública com o que o vault já sabe, cada afirmação com fonte. Use quando a pessoa pedir "dossiê da <empresa>", "o que eu preciso saber da <empresa>", "prepara a reunião com", "quem é essa empresa", ou para atualizar um dossiê depois da reunião.
---

# Dossiê de conta

Uma página que a pessoa lê em 3 minutos antes de entrar na reunião. Fato com fonte, hipótese
marcada como hipótese, e nada inventado.

## Passo 0: ancorar

1. Leia `vault/40-Operacao/Como eu preparo uma reunião.md`. Se estiver vazia ou com `revisar: sim`,
   pergunte à pessoa, uma pergunta por vez: o que ela precisa saber antes de toda reunião, em que
   ordem lê, e o que costuma faltar. Grave a resposta nessa nota (skill `cuidar-do-vault`).
2. Procure a conta no vault (`Grep` pelo nome da empresa e por apelidos) e em `entregas/dossies/`.
   Se já existe dossiê, a tarefa é atualizar, não refazer.
3. Confirme com a pessoa: nome da empresa, com quem é a reunião, quando, e qual o objetivo dela.

## Passo 1: levantar

Fontes, nesta ordem, parando quando a página estiver cheia:

1. **O que a pessoa já sabe**: vault, conversa atual, arquivos que ela colocar em `entrada/`.
2. **Fonte pública**: site da empresa, página de "sobre" e de produtos, notícias dos últimos 12
   meses, dados públicos de registro (CNPJ, porte, atividade), perfil público das pessoas da
   reunião (cargo e trajetória, nunca contato pessoal).
3. **O setor**: só o que muda a conversa (um concorrente citado, uma regra nova, um movimento de
   mercado com data).

Guarde cada fonte com endereço e data de acesso. Se o `perfil.md` tiver restrição corporativa,
não cole nada da empresa da pessoa em busca externa.

## Passo 2: escrever

Arquivo `entregas/dossies/AAAA-MM-DD - <empresa>.md`, nesta ordem (a menos que a nota "Como eu
preparo uma reunião" diga outra):

1. **Em uma frase**: quem é a empresa e por que esta reunião importa.
2. **A empresa**: o que faz, porte, onde atua, momento atual. Cada linha com fonte.
3. **Quem vai estar na sala**: nome, cargo, trajetória em uma linha, o que provavelmente importa
   para essa pessoa (marcado como hipótese).
4. **O que já aconteceu entre nós**: histórico que está no vault, com data.
5. **Hipóteses de dor e de oportunidade**: no máximo 3, cada uma com o fato que a sustenta.
6. **Perguntas para fazer**: 3 a 5, específicas desta conta.
7. **Cuidado com**: o que pode dar errado na conversa (tema sensível, concorrente atual, notícia ruim).
8. **Fontes**: lista numerada com endereço e data.

Marque cada afirmação como **fato** (fonte diz com todas as letras) ou **hipótese** (dedução sua).
Sem fonte, escreva `[a confirmar]`. Máximo de uma página: corte o que não muda a conversa.

## Passo 3: entregar e aprender

1. Mostre o dossiê em até 10 linhas de resumo no tom do `perfil.md` e diga onde está o arquivo.
2. Pergunte o que ficou faltando ou sobrando e ajuste.
3. Depois da reunião, se a pessoa contar como foi, acrescente "O que aconteceu na reunião" com a
   data e crie ou atualize a nota da empresa em `vault/30-Organizacao/`.

{{registrar_resultado}}
