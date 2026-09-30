#!/usr/bin/env python3
"""Liga o kit ao repositório dele no GitHub.

Uso (na pasta do kit):
    python3 ferramentas/conectar.py --conferir [--json]   # como o kit está ligado agora
    python3 ferramentas/conectar.py --conectar            # entra com a sua conta do GitHub (colaborador)
    python3 ferramentas/conectar.py --usar-chave          # liga pela chave do kit (sem conta no GitHub)

Há dois jeitos de o kit falar com a Root, e os dois usam o mesmo repositório privado
(operacaoroot/kit-<cliente>):

- Colaborador (o padrão desde 2026-09-29): a pessoa entra no GitHub com a conta dela pelo
  navegador, o convite do repositório é aceito aqui e todo envio sai no nome dela. O GitHub
  registra quem baixou, quem usa e quem enviou.
- Chave do kit: para quem ainda não tem conta no GitHub. O envio sai pela chave do kit, que
  é só deste repositório.

O --conectar precisa de uma janela de terminal, porque o GitHub mostra um código para a
pessoa confirmar no navegador. Nenhuma senha passa por este script.
Só biblioteca padrão, compatível com Python 3.9.
"""
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
ROOT_DIR = KIT / ".root"
CHAVE = ROOT_DIR / "chave"
SISTEMA = {"Darwin": "mac", "Windows": "windows"}.get(platform.system(), "linux")


def garantir_path():
    extras = [str(Path.home() / ".local" / "bin")]
    if SISTEMA == "windows":
        pf = os.environ.get("ProgramFiles", r"C:\Program Files")
        extras += [os.path.join(pf, "GitHub CLI"), os.path.join(pf, "Git", "cmd")]
    atual = os.environ.get("PATH", "").split(os.pathsep)
    for e in extras:
        if e not in atual:
            atual.insert(0, e)
    os.environ["PATH"] = os.pathsep.join(atual)


def rodar(cmd, timeout=60, interativo=False):
    try:
        if interativo:
            return subprocess.run(cmd, cwd=str(KIT)).returncode, ""
        r = subprocess.run(cmd, cwd=str(KIT), capture_output=True, text=True, timeout=timeout)
        return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)


def cliente():
    arq = ROOT_DIR / "cliente.json"
    return json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else {}


def gh(*args, timeout=60):
    return rodar(["gh"] + list(args), timeout=timeout)


def gh_json(*args):
    codigo, saida = gh("api", *args)
    if codigo != 0:
        return None
    try:
        return json.loads(saida)
    except ValueError:
        return None


# ---------------------------------------------------------------- conferir

def estado():
    garantir_path()
    c = cliente()
    repo = c.get("repo", "")
    e = {"repo": repo, "usuario_esperado": c.get("github") or None, "gh_instalado": bool(shutil.which("gh")),
         "logado_como": None, "convite_pendente": False, "pode_enviar": False,
         "remoto": None, "modo": None, "chave_presente": CHAVE.exists()}
    codigo, url = rodar(["git", "remote", "get-url", "origin"])
    e["remoto"] = url if codigo == 0 else None
    if e["gh_instalado"]:
        codigo, _ = gh("auth", "status", "--hostname", "github.com")
        if codigo == 0:
            eu = gh_json("user")
            e["logado_como"] = eu.get("login") if eu else None
            convites = gh_json("user/repository_invitations") or []
            e["convite_pendente"] = any(i.get("repository", {}).get("full_name") == repo for i in convites)
            info = gh_json("repos/" + repo) if repo else None
            e["pode_enviar"] = bool(info and info.get("permissions", {}).get("push"))
    remoto = e["remoto"] or ""
    if remoto.startswith("https://") and e["pode_enviar"]:
        e["modo"] = "colaborador"
    elif remoto.startswith("git@") and e["chave_presente"]:
        e["modo"] = "chave"
    return e


def imprimir(e):
    print("Repositório do kit: {}".format(e["repo"] or "(sem .root/cliente.json)"))
    if e["modo"] == "colaborador":
        print("Ligado como colaborador: os envios saem no nome de @{}.".format(e["logado_como"]))
    elif e["modo"] == "chave":
        print("Ligado pela chave do kit (sem conta do GitHub).")
    else:
        print("Ainda não ligado. Rode: python3 ferramentas/conectar.py --conectar")
    if e["convite_pendente"]:
        print("Há um convite do kit esperando para ser aceito.")
    if e["usuario_esperado"] and e["logado_como"] and e["usuario_esperado"].lower() != e["logado_como"].lower():
        print("Atenção: o kit foi feito para @{}, mas o GitHub está com @{}.".format(e["usuario_esperado"], e["logado_como"]))


# ---------------------------------------------------------------- ligar

def identidade_git(login=None):
    c = cliente()
    if login:
        eu = gh_json("user") or {}
        rodar(["git", "config", "user.name", eu.get("name") or c.get("nome") or login])
        rodar(["git", "config", "user.email", "{}+{}@users.noreply.github.com".format(eu.get("id", 0), login)])
    else:
        rodar(["git", "config", "user.name", c.get("nome", "Cliente do kit")])
        rodar(["git", "config", "user.email", "kit-{}@kit.operacaoroot.com".format(c.get("slug", "cliente"))])


def conectar():
    garantir_path()
    c = cliente()
    repo = c.get("repo")
    if not repo:
        print("Falta .root/cliente.json. Fale com a Root.")
        return 1
    if not shutil.which("gh"):
        print("O GitHub CLI não está instalado. Rode o instalador do kit ou peça ao Claude: \"confere o meu computador\".")
        return 1
    codigo, _ = gh("auth", "status", "--hostname", "github.com")
    if codigo != 0:
        print("\nVamos entrar no GitHub com a sua conta. Vai aparecer um código de 8 letras:")
        print("tecle Enter, o navegador abre, cole o código e clique em Authorize.\n")
        codigo, _ = rodar(["gh", "auth", "login", "--hostname", "github.com", "--git-protocol", "https", "--web"], interativo=True)
        if codigo != 0:
            print("O login no GitHub não terminou. Dá para rodar de novo, ou seguir pela chave do kit.")
            return 1
    eu = gh_json("user") or {}
    login = eu.get("login")
    esperado = c.get("github")
    if esperado and login and esperado.lower() != login.lower():
        print("Atenção: o kit foi feito para @{} e você entrou como @{}. Sigo, e a Root fica sabendo.".format(esperado, login))
    for convite in gh_json("user/repository_invitations") or []:
        if convite.get("repository", {}).get("full_name") == repo:
            codigo, saida = gh("api", "-X", "PATCH", "user/repository_invitations/{}".format(convite["id"]))
            print("Convite do kit aceito." if codigo == 0 else "Não consegui aceitar o convite: " + saida)
    info = gh_json("repos/" + repo)
    if not (info and info.get("permissions", {}).get("push")):
        print("A conta @{} ainda não tem acesso a {}. Confira com a Root se o convite foi para este usuário.".format(login, repo))
        return 1
    gh("auth", "setup-git", "--hostname", "github.com")
    rodar(["git", "remote", "set-url", "origin", "https://github.com/{}.git".format(repo)])
    rodar(["git", "config", "--unset", "core.sshCommand"])
    identidade_git(login)
    codigo, saida = rodar(["git", "ls-remote", "--exit-code", "origin", "HEAD"], timeout=40)
    if codigo != 0:
        print("Entrei no GitHub, mas o repositório não respondeu: " + (saida.splitlines() or ["sem resposta"])[-1])
        return 1
    print("Kit ligado: os envios saem no nome de @{}.".format(login))
    return 0


def usar_chave():
    c = cliente()
    repo = c.get("repo")
    if not CHAVE.exists():
        print("A chave do kit (.root/chave) não veio junto. Fale com a Root.")
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
    if "--conectar" in argv:
        return conectar()
    if "--usar-chave" in argv:
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
