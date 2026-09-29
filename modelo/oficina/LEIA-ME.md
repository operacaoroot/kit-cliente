# Oficina

Aqui nascem as ferramentas que você cria no kit. Enquanto uma ferramenta está na oficina, o
Claude não a usa sozinho: ela é escrita, testada com um caso real seu e registrada no
`TESTES.md` dela. Quando você aprova, o Claude a coloca em uso (`.claude/skills/`).

Para começar, diga ao Claude: "quero criar uma ferramenta".

- `oficina/<nome>/SKILL.md`: as instruções da ferramenta.
- `oficina/<nome>/TESTES.md`: os testes, um bloco por teste.
- `oficina/_aposentadas/`: versões antigas e ferramentas aposentadas. Nada é apagado.

A lista de todas as ferramentas do kit, com o estado de cada uma, está em `catalogo.json`.
