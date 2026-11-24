#!/usr/bin/env python3
"""Leva as peças comuns do modelo para kits já entregues.

Uso:
    python3 montador/atualizar.py <slug> [<slug> ...] "o que mudou, em uma frase"
    python3 montador/atualizar.py --todos "o que mudou, em uma frase"

Atualiza só o que é igual em todo kit: as ferramentas (conferência, ambiente, oficina),
o catálogo de apps, os instaladores, as skills de base, o agente auditor, as permissões
do Claude (liberadas: o kit não bloqueia nada) e o .gitignore. No catalogo.json refaz as linhas da Root e da frente e mantém
as do cliente. Nunca toca no que é do cliente: CLAUDE.md, README.md, COMECE-AQUI.md,
perfil.md, vault/, entregas/, ajuda/, oficina/<ferramentas>, as skills que ele criou e
as skills da frente. O cliente recebe a atualização
quando fechar o dia (git pull --rebase pela chave do kit).

Trabalha num clone temporário do repositório do kit, feito com o token da conta
operacaoroot, e envia um commit por kit. Só biblioteca padrão.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "montador"))
from montar import MODELO, RECEITAS, Recusa, gerar_links, montar_catalogo, para_windows, rodar, skills_de_base, token_github  # noqa: E402

ARQUIVOS = [
    ("ferramentas/verificar.py", "ferramentas/verificar.py"),
    ("ferramentas/ambiente.py", "ferramentas/ambiente.py"),
    ("ferramentas/skills.py", "ferramentas/skills.py"),
    ("ferramentas/conectar.py", "ferramentas/conectar.py"),
    ("ferramentas/autonomia.py", "ferramentas/autonomia.py"),
    ("ferramentas/painel.py", "ferramentas/painel.py"),
    ("painel/index.html", "painel/index.html"),
    ("painel/painel.css", "painel/painel.css"),
    ("painel/painel.js", "painel/painel.js"),
    ("painel/primeiros-passos.js", "painel/primeiros-passos.js"),
    ("marca/root-logo.png", "marca/root-logo.png"),
    ("vault/.obsidian/snippets/root.css", "vault/.obsidian/snippets/root.css"),
    ("ambiente/apps.json", "ambiente/apps.json"),
    ("ambiente/requirements.txt", "ambiente/requirements.txt"),
    ("oficina/LEIA-ME.md", "oficina/LEIA-ME.md"),
    ("instalar/instalar.cmd", "instalar/instalar.cmd"),
    ("passos.json", "ferramentas/passos.json"),
    ("instalar/instalar.sh", "instalar/instalar.sh"),
    ("instalar/instalar.command", "instalar/instalar.command"),
    ("instalar/instalar.ps1", "instalar/instalar.ps1"),
    (".claude/settings.json", ".claude/settings.json"),
    (".claude/agents/auditor-de-contexto.md", ".claude/agents/auditor-de-contexto.md"),
    (".gitignore", ".gitignore"),
]


def atualizar(slug, motivo):
    m = json.loads((RAIZ / "manifestos" / "{}.json".format(slug)).read_text(encoding="utf-8"))
    ent = m.get("entrega", {})
    if not ent.get("publicado"):
        raise Recusa("{} não está publicado no GitHub".format(slug))
    kit_id, windows = ent["kit_id"], m["cliente"]["sistema"] == "windows"
    with tempfile.TemporaryDirectory() as tmp:
        url = "https://x-access-token:{}@github.com/{}.git".format(token_github(), ent["repo"])
        rodar(["git", "clone", "-q", url, "kit"], tmp)
        kit = Path(tmp) / "kit"
        for origem, destino in ARQUIVOS:
            alvo = kit / destino
            alvo.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(MODELO / origem, alvo)
        for s in skills_de_base():
            alvo = kit / ".claude" / "skills" / s
            if alvo.exists():
                shutil.rmtree(alvo)
            shutil.copytree(MODELO / ".claude" / "skills" / s, alvo)
        (kit / "LINKS.md").write_text(gerar_links(m["cliente"]["sistema"], m["perfil"]["escolhido"]), encoding="utf-8")
        versao = json.loads((MODELO / "passos.json").read_text(encoding="utf-8"))["versao"]
        arq_cat = kit / "catalogo.json"
        existente = json.loads(arq_cat.read_text(encoding="utf-8")) if arq_cat.exists() else None
        receitas = [json.loads((RECEITAS / k / "receita.json").read_text(encoding="utf-8")) for k in m.get("frente", [])]
        arq_cat.write_text(json.dumps(montar_catalogo(receitas, versao, existente), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for md in list((kit / ".claude").rglob("*.md")):
            texto = md.read_text(encoding="utf-8").rstrip()
            if kit_id not in texto:
                texto += "\n\n<!-- {} -->".format(kit_id)
            if windows:
                texto = para_windows(texto)
            md.write_text(texto + "\n", encoding="utf-8")
        rodar(["git", "config", "user.name", "Root (montador de kits)"], kit)
        rodar(["git", "config", "user.email", "kits@operacaoroot.com"], kit)
        rodar(["git", "add", "-A"], kit)
        mudou = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=str(kit)).returncode != 0
        if not mudou:
            print("{}: já estava em dia".format(slug))
            return
        rodar(["git", "commit", "-q", "-m", "Atualização do kit (modelo {}): {}".format(versao, motivo)], kit)
        rodar(["git", "push", "-q", "origin", "HEAD"], kit)
        print("{}: atualização enviada ({})".format(slug, motivo))


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    motivo = argv[-1]
    if argv[1] == "--todos":
        slugs = []
        for arq in sorted((RAIZ / "manifestos").glob("*.json")):
            if arq.name.startswith("_"):
                continue
            if json.loads(arq.read_text(encoding="utf-8")).get("entrega", {}).get("publicado"):
                slugs.append(arq.stem)
    else:
        slugs = argv[1:-1]
    falhas = 0
    for s in slugs:
        try:
            atualizar(s, motivo)
        except Recusa as e:
            falhas += 1
            print("{}: RECUSADO: {}".format(s, e))
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
