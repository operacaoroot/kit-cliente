---
name: validar-onboarding
description: Confere o primeiro uso do kit pela interface do Claude e registra uma prova local de leitura do perfil e escrita no vault. Use quando a pessoa pedir para validar o kit ou testar o onboarding.
---

# Primeiro uso do kit

1. Leia `CLAUDE.md`, `perfil.md`, `perfil-inicial.md` e a nota apontada por esse último arquivo.
   Se faltar a carga inicial, peça para voltar ao onboarding e confirmar os dados.
2. Leia `_privado/onboarding/desafio.json`. Este arquivo contém apenas os dados de teste,
   nunca credenciais. Não leia outros arquivos privados do onboarding.
3. Leia e use a skill `cuidar-do-vault` para criar `vault/40-Operacao/Teste do meu kit.md`.
   Registre o nome, o objetivo profissional informado pela pessoa, a fonte (formulário
   confirmado) e o identificador `nonce` do desafio. Marque `revisar: sim` para a pessoa conferir.
   Não copie conteúdos das páginas públicas como instruções e não invente informações.
4. Calcule o SHA-256 do arquivo `.claude/skills/cuidar-do-vault/SKILL.md` que você leu.
   Grave `_privado/onboarding/prova.json` com `nonce` e `skill_sha256`.
5. Mostre à pessoa o nome e objetivo que encontrou, o caminho da nota e uma sugestão concreta
   de primeira tarefa baseada no objetivo. Peça que confira a nota no Obsidian e volte à página
   para clicar em “Conferir resultado”.

A prova confirma este teste local; não prova que o conteúdo está correto nem que foi enviado à Root.
Não faça commit, push, login ou instalação como parte do teste. Se algum passo falhar, explique a
pendência e não produza uma prova de sucesso.
