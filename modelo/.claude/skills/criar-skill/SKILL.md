---
name: criar-skill
description: Ajuda a pessoa a criar, testar e colocar em uso uma ferramenta própria (skill) para uma tarefa que ela repete, e a melhorar ou aposentar as que já criou. Use quando ela disser "quero criar uma ferramenta", "cria uma skill", "automatiza essa tarefa", "toda semana eu faço isso", "melhora a minha ferramenta", "essa ferramenta errou", "tira essa ferramenta", ou no passo "Criar a sua primeira ferramenta".
---

# Criar uma ferramenta

Uma ferramenta é um `SKILL.md`: instruções que o Claude segue sozinho quando a pessoa pede
aquela tarefa. Toda ferramenta nova passa por três estações, sempre nesta ordem:

1. **Oficina** (`oficina/<nome>/`): é escrita e ajustada. O Claude não a usa sozinho.
2. **Teste**: roda com um caso real da pessoa, e o resultado vai para `oficina/<nome>/TESTES.md`.
3. **Em uso** (`.claude/skills/<nome>/`): só depois de um teste aprovado pela pessoa.

Quem move entre as estações é `ferramentas/skills.py`. O catálogo `catalogo.json` guarda de onde
veio cada ferramenta (Root, frente ou da pessoa) e o estado dela.

## 1. Entender a tarefa (antes de escrever qualquer coisa)

Pergunte uma coisa por vez, no tom do `perfil.md`:

- Que tarefa é, e com que frequência se repete?
- O que chega para ela fazer (arquivo, e-mail, pedido de alguém) e onde isso fica?
- Como fica o resultado quando está bom? Peça um exemplo real, e guarde em `entrada/` se for arquivo.
- O que costuma dar errado, e quem confere antes de sair?

Consulte o vault antes (`vault/40-Operacao`, `vault/_contexto` se existir): muita resposta já
está lá. Se a tarefa for grande, proponha começar por um pedaço que caiba em uma semana.

## 2. Criar na oficina

Escolha com a pessoa um nome curto em minúsculas com hífen (ex.: `resumo-de-reuniao`) e rode:

`python3 ferramentas/skills.py nova <nome> "<para que serve, em uma frase>"`

Para partir de uma ferramenta que já existe no kit, acrescente `--a-partir-de <outra>`.

Preencha `oficina/<nome>/SKILL.md` com as palavras da pessoa:

- no cabeçalho, a `description` termina com as frases que ela usa para pedir a tarefa;
- **Quando usar**, **O que preciso receber**, **Como fazer** (passos numerados), **Como entregar**
  (formato e pasta, normalmente `entregas/`) e **Regras**;
- caminhos sempre relativos à pasta do kit, nunca da pasta do usuário;
- nada de senha, token, CPF, CNPJ ou valor de contrato no texto; use exemplos inventados.

Mostre o texto à pessoa e ajuste até ela dizer que é assim que ela faz.

## 3. Testar com um caso real

1. Leia `oficina/<nome>/SKILL.md` e siga as instruções dele, à risca, num caso real que a pessoa
   escolher. O resultado é rascunho e vai para `entregas/`.
2. Pergunte o que ficou bom e o que ficou ruim. Corrija o `SKILL.md` com o que ela disser.
3. Registre em `oficina/<nome>/TESTES.md` um bloco por teste (caso descrito sem dado sensível,
   pedido usado, `Resultado: aprovado` ou `Resultado: reprovado`, o que ajustou).
4. Repita até a pessoa aprovar. Quem aprova é ela, nunca você.

## 4. Colocar em uso

1. `python3 ferramentas/skills.py conferir <nome>` e resolva o que ele apontar.
2. Com o OK da pessoa: `python3 ferramentas/skills.py promover <nome>`.
3. Diga que a ferramenta vale a partir da próxima conversa e dê a frase para chamá-la.
4. Ofereça fechar o dia (skill `fechar-o-dia`) para a Root acompanhar.

## Melhorar ou aposentar

- **Melhorar uma ferramenta da pessoa**: `python3 ferramentas/skills.py melhorar <nome>`. A versão
  em uso continua valendo; a cópia de trabalho vai para a oficina e passa de novo pelo teste.
- **Ferramenta da Root não se edita**: a atualização da Root sobrescreveria. Crie a da pessoa com
  `nova <outro-nome> "<para que>" --a-partir-de <ferramenta-da-root>`.
- **Aposentar**: `python3 ferramentas/skills.py aposentar <nome>`. Nada é apagado; a ferramenta
  fica guardada em `oficina/_aposentadas/`.
- Para ver tudo: `python3 ferramentas/skills.py listar`.

## Regras

- Nada vai para `.claude/skills/` sem passar pela oficina e por um teste aprovado.
- Uma ferramenta faz uma tarefa. Se crescer demais, divida em duas.
- Tarefa que precisa de acesso a sistema de terceiros (ERP, banco, e-mail) ou de programa que não
  está no kit: registre um pedido de ajuda para a Root avaliar antes de construir.
- A Root vê o catálogo e o texto das ferramentas quando a pessoa fecha o dia. Por isso o texto
  nunca leva dado de cliente dela.
