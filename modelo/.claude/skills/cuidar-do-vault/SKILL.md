---
name: cuidar-do-vault
description: Cria, corrige, liga e revisa notas do vault (a base no Obsidian) seguindo o cabeçalho do kit. Use quando a pessoa pedir "me ajuda a revisar as notas", "anota isso", "registra essa decisão", "cria uma nota sobre", "onde está a nota de", ou quando outra skill precisar gravar algo no vault.
---

# Cuidar do vault

O vault fica em `vault/` e abre no Obsidian. É a memória do trabalho da pessoa: quem ela é, como
trabalha, o que decidiu, o que quer. Tudo o que o Claude escreve lá precisa de fonte.

## Cabeçalho obrigatório

```yaml
---
kind: fato            # regra | definicao | dicionario | decisao | fato | nota
dono: <nome da pessoa>
valido_de: AAAA-MM-DD
fonte: <de onde veio: "conversa AAAA-MM-DD", "kickoff AAAA-MM-DD 00:12:40", "arquivo entrada/x.pdf">
revisar: não          # sim quando foi escrito pelo Claude ou pela Root e a pessoa ainda não leu
---
```

Depois do cabeçalho, um `# Título`. Datas sempre absolutas (`2026-10-02`), nunca "semana passada".

## Onde cada coisa entra

| Pasta | Entra |
|---|---|
| `10-Identidade` | quem a pessoa é, o que faz, voz e escrita, vocabulário |
| `30-Organizacao` | pessoas e empresas com quem trabalha (sem telefone, e-mail ou documento) |
| `40-Operacao` | como o trabalho é feito, tarefas que se repetem, resultados da frente |
| `50-Projetos` | uma nota por projeto ativo: o que é, estado, próximo passo |
| `60-Decisoes` | uma nota por decisão, com data no nome: `AAAA-MM-DD - assunto.md` |
| `70-Dados` | números de referência, com a origem |
| `90-Metas` | o que a pessoa quer alcançar, com prazo |
| `_contexto` | o pacote gerado pela extração de contexto (não editar à mão) |

## Revisar as notas com a pessoa

1. Liste as notas com `revisar: sim` (use Grep no vault).
2. Mostre uma por vez: o título, o corpo em até 5 linhas e a fonte.
3. Pergunte se está certo. Se ela corrigir, reescreva com as palavras dela e mantenha a fonte
   original junto com `corrigido por <nome> em AAAA-MM-DD`.
4. Troque para `revisar: não` só depois do OK dela.
5. No fim, rode `python3 ferramentas/verificar.py` para registrar o passo.

## Regras

- Procure antes de criar: se já existe nota do mesmo assunto, atualize.
- O jeito da casa é não apagar: se algo ficou errado, marque `valido_ate: AAAA-MM-DD` e crie a
  nota nova apontando a antiga. Se a pessoa pedir para apagar, apague.
- Ligue notas relacionadas com `[[Nome da nota]]`, e acrescente a nota nova ao índice da pasta.
- Sem segredo, sem dado pessoal de terceiros, sem valor de contrato de cliente.
