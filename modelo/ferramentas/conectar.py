#!/usr/bin/env python3
"""Liga o kit ao repositório dele no GitHub, pela chave que vem no kit.

Uso (na pasta do kit):
    python3 ferramentas/conectar.py --conferir [--json]   # como o kit está ligado agora
    python3 ferramentas/conectar.py --usar-chave          # liga pela chave do kit

O kit fala com a Root por um repositório privado (operacaoroot/kit-<cliente>) usando a chave do
kit (.root/chave), que vem dentro do ZIP e só abre este repositório. A pessoa não precisa de conta
no GitHub, não faz login e não digita código nenhum.

Até novembro de 2026 havia um segundo jeito, entrar com a conta da pessoa pelo GitHub CLI, que
mostrava um código de 8 letras para confirmar no navegador. Na instalação esse código não aparecia
para a pessoa e a instalação travava, então ele saiu. `--conectar` continua aceito para não quebrar
instruções antigas e agora faz o mesmo que `--usar-chave`. Kits antigos ligados pela conta
(remoto https) continuam funcionando; para não depender de login, rode `--usar-chave`.

Nenhuma senha passa por este script. Só biblioteca padrão, compatível com Python 3.9.
"""
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
ROOT_DIR = KIT / ".root"
CHAVE = ROOT_DIR / "chave"
SISTEMA = {"Darwin": "mac", "Windows": "windows"}.get(platform.system(), "linux")


def rodar(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, cwd=str(KIT), capture_output=True, text=True, timeout=timeout)
        return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)


def cliente():
    arq = ROOT_DIR / "cliente.json"
    return json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else {}


# ---------------------------------------------------------------- conferir

def estado():
    """Como o kit está ligado, sem rede: lido do git local e da pasta .root."""
    c = cliente()
    e = {"repo": c.get("repo", ""), "remoto": None, "modo": None, "chave_presente": CHAVE.exists()}
    codigo, url = rodar(["git", "remote", "get-url", "origin"])
    e["remoto"] = url if codigo == 0 else None
    remoto = e["remoto"] or ""
    if remoto.startswith("git@") and e["chave_presente"]:
        e["modo"] = "chave"
    elif remoto.startswith("https://"):
        e["modo"] = "colaborador"  # kit antigo, ligado pela conta da pessoa
    return e


def imprimir(e):
    print("Repositório do kit: {}".format(e["repo"] or "(sem .root/cliente.json)"))
    if e["modo"] == "chave":
        print("Ligado pela chave do kit. Não precisa de conta nem de login no GitHub.")
    elif e["modo"] == "colaborador":
        print("Ligado pela conta do GitHub (jeito antigo). Para não depender de login, rode: "
              "python3 ferramentas/conectar.py --usar-chave")
    else:
        print("Ainda não ligado. Rode: python3 ferramentas/conectar.py --usar-chave")


# ---------------------------------------------------------------- ligar

def identidade_git():
    c = cliente()
    rodar(["git", "config", "user.name", c.get("nome", "Cliente do kit")])
    rodar(["git", "config", "user.email", "kit-{}@kit.operacaoroot.com".format(c.get("slug", "cliente"))])


def usar_chave():
    c = cliente()
    repo = c.get("repo")
    if not CHAVE.exists():
        print("A chave do kit (.root/chave) não veio junto. Extraia o ZIP inteiro de novo; se faltar, fale com a Root.")
        return 1
    if SISTEMA == "windows":
        rodar(["icacls", str(CHAVE), "/inheritance:r", "/grant:r", "{}:(R)".format(os.environ.get("USERNAME", ""))])
        caminho = str(CHAVE).replace("\\", "/")
    else:
        os.chmod(str(CHAVE), 0o600)
        caminho = str(CHAVE)
    rodar(["git", "config", "core.sshCommand",
           'ssh -i "{}" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new'.format(caminho)])
    if repo:
        rodar(["git", "remote", "set-url", "origin", "git@github.com:{}.git".format(repo)])
    identidade_git()
    print("Kit ligado pela chave do kit.")
    return 0


def main(argv):
    if "--usar-chave" in argv or "--conectar" in argv:
        return usar_chave()
    if "--conferir" in argv:
        e = estado()
        if "--json" in argv:
            print(json.dumps(e, ensure_ascii=False, indent=2))
        else:
            imprimir(e)
        return 0 if e["modo"] else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
