#!/usr/bin/env python3
"""Monta o kit de revisão: para quem JÁ tem o Claude instalado e não consegue usar os sistemas.

Uso (na raiz do kit-cliente):
    python3 montador/revisao.py manifestos/revisao-<nome>.json [--zip]

Sai uma pasta por pessoa em saida/revisao-<slug>/ (e o ZIP, com --zip). O kit de revisão não tem
chave, não tem repositório e não instala nada: leva o roteiro (`ferramentas/revisar_sistemas.py`),
a skill `revisar-sistemas`, o bloco `sistemas` e a trava de gravação (regras `ask`). A pessoa abre
a pasta no Claude, escreve "revisar" e manda o `relatorio-revisao.txt` ao responsável.

O manifesto de revisão:
    {"nome": "empresa", "empresa": "Empresa", "responsavel": "Nome", "canal": "WhatsApp com ...",
     "pessoas": [{"slug", "nome", "primeiro_nome", "email", "sistema": "windows"|"mac"}],
     "sistemas": {...}}   # o mesmo bloco do kit (docs/SISTEMAS.md); "{email}" vira o e-mail da pessoa

Determinístico: não chama modelo de IA e não fala com a rede. Só biblioteca padrão, Python 3.9.
"""
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import montar  # noqa: E402
from montar import MODELO, Recusa, SLUG  # noqa: E402

SAIDA = montar.SAIDA
PECAS = (
    "ferramentas/revisar_sistemas.py",
    "ferramentas/sistemas.py",
    "instalar/pedir-segredo.ps1",
    ".claude/skills/revisar-sistemas/SKILL.md",
)
PYTHON = {"windows": "python ", "mac": "python3 "}

LEIA_ME = """# Revisão do Claude com os sistemas da {empresa}

{primeiro_nome}, esta pasta serve para descobrir por que o Claude não está conseguindo usar os
sistemas da {empresa} no seu computador e consertar o que der. Ela não instala nada sozinha e não
grava nada em sistema nenhum.

## Como usar (uns 10 minutos)

1. Extraia o ZIP numa pasta sua, por exemplo em Documentos.
2. Abra essa pasta no Claude: no aplicativo, aba Code, escolha a pasta `{pasta}`. No terminal,
   entre na pasta e rode `claude`.
3. Escreva: **revisar**
4. O Claude confere o Claude Code, o uv, {nomes} e o seu login, um ponto por vez, e explica o que
   cada erro significa. O que for conserto seu, ele faz com você.
5. No fim fica o arquivo `relatorio-revisao.txt` nesta pasta. Mande para {responsavel}
   ({canal}). O relatório não leva senha, chave nem e-mail.

## Três cuidados

- Senha você digita só na janela que o kit abre. Nunca no chat.
- Se aparecer "pendente de aprovação", nada foi gravado. Não peça para o Claude repetir: cada
  repetição cria outra pendência.
- O que o relatório marcar como decisão de {responsavel} fica com {responsavel}.

## Se o Claude disser que não achou o Python

Peça para ele rodar `uv run --no-project ferramentas/revisar_sistemas.py`. Se também não houver
uv, ele confere à mão e escreve o relatório do mesmo jeito. Instalar o uv é o primeiro conserto.
"""

CLAUDE_MD = """# Kit de revisão dos sistemas da {empresa}

Esta pasta é de {nome}, que já usa o Claude e está com dificuldade para usar {nomes}. O
responsável é {responsavel} ({canal}).

## O que fazer aqui

- Na primeira mensagem da conversa, ou quando {primeiro_nome} escrever "revisar", use a skill
  `revisar-sistemas` e siga a ordem dela até o `relatorio-revisao.txt` ficar pronto.
- Quando uma ferramenta de sistema devolver erro, rode
  `python3 ferramentas/revisar_sistemas.py --explicar "<texto do erro>"` antes de tentar de novo.
- Fale em português do Brasil, frases curtas, um ponto por vez.

## O que não fazer

- Não abrir o arquivo de credencial nem pedir senha no chat.
- Não gravar em sistema para "testar". A revisão só lê.
- Não aprovar pendência, não ligar gravação em empresa, não mudar permissão. Isso é decisão de
  {responsavel} e vai no relatório.
- Não enviar o relatório: quem manda é {primeiro_nome}.

## Regras dos sistemas

{regras}
"""


def conferir(m):
    faltas = []
    for campo in ("nome", "empresa", "responsavel", "canal"):
        if not isinstance(m.get(campo), str) or not m[campo].strip():
            faltas.append(campo)
    if m.get("nome") and not re.fullmatch(SLUG, str(m["nome"])):
        faltas.append("nome só com minúsculas, números e hífen")
    pessoas = m.get("pessoas")
    if not isinstance(pessoas, list) or not pessoas:
        faltas.append("pessoas: pelo menos uma")
        pessoas = []
    slugs = set()
    for i, p in enumerate(pessoas):
        onde = "pessoas[{}]".format(i)
        for campo in ("slug", "nome", "primeiro_nome", "email", "sistema"):
            if not isinstance(p.get(campo), str) or not p[campo].strip():
                faltas.append("{}.{}".format(onde, campo))
        if p.get("slug") and (not re.fullmatch(SLUG, p["slug"]) or p["slug"] in slugs):
            faltas.append("{}.slug só com minúsculas, números e hífen, sem repetir".format(onde))
        slugs.add(p.get("slug"))
        if p.get("email") and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", p["email"]):
            faltas.append("{}.email".format(onde))
        if p.get("sistema") and p["sistema"] not in PYTHON:
            faltas.append("{}.sistema é windows ou mac".format(onde))
    if not m.get("sistemas"):
        faltas.append("sistemas (o mesmo bloco do kit, docs/SISTEMAS.md)")
    elif pessoas and not faltas:
        faltas += montar.conferir_sistemas(sistemas_da_pessoa(m, pessoas[0]))
    if faltas:
        raise Recusa("manifesto de revisão incompleto:\n  - " + "\n  - ".join(faltas))


def sistemas_da_pessoa(m, pessoa):
    return json.loads(json.dumps(m["sistemas"], ensure_ascii=False).replace("{email}", pessoa["email"]))


def texto_para(sistema, texto):
    return texto if sistema == "mac" else texto.replace("python3 ", PYTHON[sistema])


def montar_kit(m, pessoa):
    destino = SAIDA / "revisao-{}".format(pessoa["slug"])
    if destino.exists():
        if SAIDA.resolve() not in destino.resolve().parents:
            raise Recusa("só apago dentro de saida/")
        shutil.rmtree(destino)
    pseudo = {"sistemas": sistemas_da_pessoa(m, pessoa), "combinado": {"responsavel_root": m["responsavel"]}}
    for rel in PECAS:
        alvo = destino / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        if rel.endswith(".md"):
            alvo.write_text(texto_para(pessoa["sistema"], (MODELO / rel).read_text(encoding="utf-8")), encoding="utf-8")
        else:
            shutil.copy2(MODELO / rel, alvo)
    leitura, escrita = montar.ferramentas_de_sistema(pseudo)
    (destino / ".claude" / "settings.json").write_text(
        json.dumps({"permissions": {"allow": leitura, "ask": escrita, "deny": []}}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (destino / ".root").mkdir(exist_ok=True)
    (destino / ".root" / "sistemas.json").write_text(
        json.dumps(montar.sistemas_do_kit(pseudo), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ctx = {"empresa": m["empresa"], "responsavel": m["responsavel"], "canal": m["canal"], "nome": pessoa["nome"],
           "primeiro_nome": pessoa["primeiro_nome"], "pasta": destino.name, "nomes": montar.nomes_dos_sistemas(pseudo["sistemas"]),
           "regras": "\n".join("- " + r for r in pseudo["sistemas"].get("regras") or ["Gravação só depois da prévia e do sim da pessoa."])}
    for nome, modelo in (("LEIA-ME.md", LEIA_ME), ("CLAUDE.md", CLAUDE_MD)):
        (destino / nome).write_text(texto_para(pessoa["sistema"], modelo.format(**ctx)), encoding="utf-8")
    return destino


def zipar(destino):
    arquivo = destino.with_suffix(".zip")
    with zipfile.ZipFile(arquivo, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(destino.rglob("*")):
            if p.is_file() and p.name not in (".DS_Store", "relatorio-revisao.txt", "sistemas-estado.json"):
                z.write(p, "{}/{}".format(destino.name, p.relative_to(destino).as_posix()))
    return arquivo


def montar_revisao(caminho, opcoes):
    m = json.loads(Path(caminho).read_text(encoding="utf-8"))
    conferir(m)
    kits = []
    for pessoa in m["pessoas"]:
        faltas = montar.conferir_sistemas(sistemas_da_pessoa(m, pessoa))
        if faltas:
            raise Recusa("sistemas de {}:\n  - ".format(pessoa["slug"]) + "\n  - ".join(faltas))
        destino = montar_kit(m, pessoa)
        kits.append(destino)
        print("Kit de revisão: {}".format(destino))
        if "--zip" in opcoes:
            print("  zip: {} (sem chave; pode ir pelo canal de sempre)".format(zipar(destino)))
    return kits


def main(argv):
    if len(argv) < 2 or argv[1].startswith("--"):
        print(__doc__)
        return 2
    try:
        montar_revisao(argv[1], set(argv[2:]))
    except Recusa as e:
        print("RECUSADO:", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
