---
name: fechar-o-dia
description: Salva o trabalho do dia, envia o progresso para a Root e traz as atualizações do kit. Use quando a pessoa disser "fechar o dia", "salva tudo", "manda para a Root", "atualiza o kit", ou ao encerrar uma sessão longa.
---

# Fechar o dia

1. Rode `python3 ferramentas/verificar.py --silencioso` para atualizar `.root/progresso.json`.
2. Confira o que vai ser enviado com `git status --short`. **Nunca** envie nada de `entrada/`,
   `_privado/` ou `.root/chave` (o `.gitignore` já barra; se aparecer, pare e avise).
3. Salve: `git add -A && git commit -m "Dia AAAA-MM-DD: <o que foi feito em até 10 palavras>"`.
   Se não houver mudança, pule o commit.
4. Traga as atualizações da Root: `git pull --rebase --autostash`. Se houver conflito, não resolva por conta
   própria: rode `git rebase --abort`, registre um pedido de ajuda (skill `pedir-ajuda`) e siga.
5. Envie: `git push`.
6. Responda no tom do `perfil.md`, em até 3 linhas: o que foi salvo, se chegou atualização do kit
   (e o que mudou, lendo `git log` das mudanças que vieram) e qual é o próximo passo para amanhã.

Se o envio falhar por rede, diga que tudo ficou salvo na máquina e que o envio sai no próximo
fechamento. Se falhar por permissão da chave, registre um pedido de ajuda: a chave pode ter sido
trocada pela Root.
