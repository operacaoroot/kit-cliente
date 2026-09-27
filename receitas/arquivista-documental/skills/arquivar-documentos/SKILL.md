---
name: arquivar-documentos
description: Classifica, renomeia no padrão da casa e propõe o destino de documentos, sem mover nada sem aprovação. Também levanta o padrão de nomes que a casa já usa e ajuda a achar documento. Use quando pedirem "organiza esses documentos", "qual o nosso padrão de nome", "arquiva isso", "onde está o documento de".
---

# Arquivar documentos

O arquivo original é sempre da pessoa. Esta skill **propõe**; mover ou renomear na pasta dela só
acontece depois do sim, arquivo por arquivo ou em lote aprovado.

## Primeiro uso: levantar o padrão que já existe

1. Pergunte qual pasta é a "boa" (a que está mais organizada) e liste até 300 nomes de arquivo dela,
   só os nomes, sem abrir o conteúdo.
2. Descubra o padrão que a casa já usa sem saber: ordem dos pedaços (data, cliente, tipo, versão),
   separador, formato de data, abreviações. Conte quantos arquivos seguem cada variação.
3. Proponha o padrão em uma linha, com 3 exemplos reais, e as pastas-destino por assunto. Mostre
   a porcentagem de arquivos que já seguem o padrão: é a linha de base.
4. Com o OK da pessoa, grave em `vault/40-Operacao/Padrão de nomes e pastas.md` (skill
   `cuidar-do-vault`).

## Arquivar

1. Leia `vault/40-Operacao/Padrão de nomes e pastas.md`.
2. Para cada arquivo em `entrada/` (ou na pasta que a pessoa indicar): abra só o necessário para
   classificar (título, primeira página, cabeçalho), identifique tipo, cliente ou assunto e data do
   documento (não a data do arquivo).
3. Monte a tabela em `entregas/arquivamento/AAAA-MM-DD.md`:

   | Nome atual | Tipo | Cliente/assunto | Data do documento | Nome proposto | Destino | Confiança |
   |---|---|---|---|---|---|---|

   Confiança baixa quando o conteúdo não diz o cliente ou a data com todas as letras. Esses ficam
   para a pessoa decidir e nunca entram no lote automático.
4. Mostre a tabela e peça o OK. Só então copie (não mova) cada arquivo para o destino com o nome
   novo, confira que a cópia abriu e pergunte se pode apagar o original.
5. Nunca sobrescreva arquivo existente: se o nome já existe no destino, acrescente `-v2`.

## Achar documento

Procure pelo padrão (cliente, tipo, data) antes de abrir arquivos. Diga onde está e por que acha
que é aquele. Se não achar, diga o que procurou.

{{registrar_resultado}}
