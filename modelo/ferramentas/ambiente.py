#!/usr/bin/env python3
"""Confere e prepara o computador para o kit, a partir de ambiente/apps.json.

Uso (na pasta do kit):
    python3 ferramentas/ambiente.py --conferir            # lista o que está e o que falta
    python3 ferramentas/ambiente.py --conferir --json     # o mesmo, em JSON
    python3 ferramentas/ambiente.py --instalar            # instala o obrigatório e o recomendado do perfil
    python3 ferramentas/ambiente.py --instalar --com vscode,docker   # e também estes opcionais
    python3 ferramentas/ambiente.py --instalar --so obsidian         # só estes
    python3 ferramentas/ambiente.py --venv                # cria o Python do kit (.venv) com as bibliotecas
    python3 ferramentas/ambiente.py --listar              # o catálogo, por perfil

No Windows, troque `python3` por `.venv/Scripts/python` (o instalador cria o .venv antes de chamar
este script). O perfil vem de .root/cliente.json; --perfil guiado|chat|construtor sobrescreve.

Pode rodar quantas vezes quiser: o que já está instalado é pulado. Nada que precise de senha de
administrador acontece sem aviso na tela, e nada é enviado para fora da máquina.
Só biblioteca padrão, compatível com Python 3.9.
"""
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
CATALOGO = KIT / "ambiente" / "apps.json"
REQUISITOS = KIT / "ambiente" / "requirements.txt"
VENV = KIT / ".venv"
SISTEMA = {"Darwin": "mac", "Windows": "windows"}.get(platform.system(), "linux")
PERFIS = ("guiado", "chat", "construtor")
NIVEIS = ("obrigatorio", "recomendado", "opcional")
BIBLIOTECAS_DE_PROVA = ("docx", "openpyxl", "pypdf")


# ---------------------------------------------------------------- saída

def passo(t):
    print("\n== " + t, flush=True)


def ok(t):
    print("   ok  " + t, flush=True)


def aviso(t):
    print("   !!  " + t, flush=True)


# ---------------------------------------------------------------- leitura

def catalogo():
    return json.loads(CATALOGO.read_text(encoding="utf-8"))["apps"]


def perfil_do_kit(forcado=None):
    if forcado in PERFIS:
        return forcado
    arq = KIT / ".root" / "cliente.json"
    if arq.exists():
        try:
            p = json.loads(arq.read_text(encoding="utf-8")).get("perfil")
            if p in PERFIS:
                return p
        except ValueError:
            pass
    return "chat"


def expandir(caminho):
    return os.path.expanduser(os.path.expandvars(caminho))


def garantir_path():
    """Os instaladores oficiais põem os binários em ~/.local/bin; o processo atual ainda não sabe."""
    extras = [str(Path.home() / ".local" / "bin")]
    if SISTEMA == "windows":
        extras += [expandir(r"%ProgramFiles%\Git\cmd")]
    atual = os.environ.get("PATH", "").split(os.pathsep)
    for e in extras:
        if e not in atual:
            atual.insert(0, e)
    os.environ["PATH"] = os.pathsep.join(atual)


def uv_bin():
    garantir_path()
    achado = shutil.which("uv")
    if achado:
        return achado
    nome = "uv.exe" if SISTEMA == "windows" else "uv"
    candidato = Path.home() / ".local" / "bin" / nome
    return str(candidato) if candidato.exists() else None


def rodar(cmd, timeout=None, silencioso=False):
    try:
        r = subprocess.run(cmd, cwd=str(KIT), timeout=timeout,
                           capture_output=silencioso, text=True)
        return r.returncode, (r.stdout or "") if silencioso else ""
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)


# ---------------------------------------------------------------- conferir

def pastas_de_apps():
    return [Path("/Applications"), Path.home() / "Applications"]


def winget_disponivel():
    return SISTEMA == "windows" and shutil.which("winget") is not None


def checar(app):
    spec = app.get(SISTEMA, {}).get("checar", {})
    garantir_path()
    if spec.get("comando") and shutil.which(spec["comando"]):
        return True
    for c in spec.get("caminhos", []):
        if Path(expandir(c)).exists():
            return True
    for nome in spec.get("apps", []):
        if any((p / nome).exists() for p in pastas_de_apps()):
            return True
    if spec.get("uv_python"):
        uv = uv_bin()
        if uv:
            codigo, _ = rodar([uv, "python", "find", spec["uv_python"]], timeout=60, silencioso=True)
            return codigo == 0
        return False
    wid = app.get(SISTEMA, {}).get("instalar", {}).get("winget")
    if wid and winget_disponivel():
        codigo, _ = rodar(["winget", "list", "--id", wid, "-e", "--accept-source-agreements"], timeout=90, silencioso=True)
        return codigo == 0
    return False


def python_do_venv():
    if SISTEMA == "windows":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def checar_venv():
    py = python_do_venv()
    if not py.exists():
        return False, "o Python do kit (.venv) ainda não foi criado"
    teste = "import " + ", ".join(BIBLIOTECAS_DE_PROVA)
    codigo, _ = rodar([str(py), "-c", teste], timeout=60, silencioso=True)
    if codigo != 0:
        return False, "o Python do kit existe, mas faltam bibliotecas"
    return True, "Python do kit pronto, com as bibliotecas"


def conferir(perfil):
    linhas = []
    for app in catalogo():
        nivel = app["perfis"].get(perfil, "opcional")
        linhas.append({"id": app["id"], "nome": app["nome"], "para_que": app["para_que"],
                       "nivel": nivel, "instalado": checar(app)})
    venv_ok, venv_txt = checar_venv()
    return {"sistema": SISTEMA, "perfil": perfil, "apps": linhas,
            "venv": {"pronto": venv_ok, "detalhe": venv_txt},
            "faltam_obrigatorios": [l["id"] for l in linhas if l["nivel"] == "obrigatorio" and not l["instalado"]]}


# ---------------------------------------------------------------- instalar

def baixar(url, destino):
    """Download grande em rede lenta: o curl retoma e repete sozinho; o urllib é a reserva."""
    if shutil.which("curl"):
        codigo, _ = rodar(["curl", "-fL", "--retry", "5", "--retry-delay", "5", "--retry-all-errors",
                           "--connect-timeout", "30", "-C", "-", "-sS", "-o", str(destino), url])
        if codigo == 0 and Path(destino).exists() and Path(destino).stat().st_size > 0:
            return
    req = urllib.request.Request(url, headers={"User-Agent": "kit-root/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r, open(destino, "wb") as f:
        shutil.copyfileobj(r, f, length=1024 * 1024)


def pasta_de_destino_mac():
    if os.access("/Applications", os.W_OK):
        return Path("/Applications")
    destino = Path.home() / "Applications"
    destino.mkdir(exist_ok=True)
    return destino


def copiar_app_mac(origem, nome_app):
    destino = pasta_de_destino_mac() / nome_app
    if destino.exists():
        return destino
    codigo, _ = rodar(["ditto", str(origem), str(destino)])
    if codigo != 0:
        raise RuntimeError("não consegui copiar {} para {}".format(nome_app, destino.parent))
    return destino


def dmg_do_github(repo):
    url = "https://api.github.com/repos/{}/releases?per_page=10".format(repo)
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "kit-root/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        releases = json.loads(r.read().decode())
    for rel in releases:
        if rel.get("draft") or rel.get("prerelease"):
            continue
        for a in rel.get("assets", []):
            if a["name"].endswith(".dmg"):
                return a["browser_download_url"], rel.get("tag_name", "")
    raise RuntimeError("nenhuma versão com instalador para Mac em {}".format(repo))


def instalar_dmg_github(inst):
    url, versao = dmg_do_github(inst["repo"])
    print("   baixando {} {}...".format(inst["app"], versao), flush=True)
    with tempfile.TemporaryDirectory() as tmp:
        dmg = Path(tmp) / "instalador.dmg"
        montagem = Path(tmp) / "volume"
        baixar(url, dmg)
        codigo, _ = rodar(["hdiutil", "attach", "-nobrowse", "-readonly", "-quiet", "-mountpoint", str(montagem), str(dmg)])
        if codigo != 0:
            raise RuntimeError("não consegui abrir o instalador do {}".format(inst["app"]))
        try:
            return copiar_app_mac(montagem / inst["app"], inst["app"])
        finally:
            rodar(["hdiutil", "detach", "-quiet", str(montagem)])


def instalar_zip_app(inst):
    print("   baixando {}...".format(inst["app"]), flush=True)
    with tempfile.TemporaryDirectory() as tmp:
        arq = Path(tmp) / "app.zip"
        baixar(inst["url"], arq)
        pasta = Path(tmp) / "extraido"
        codigo, _ = rodar(["ditto", "-x", "-k", str(arq), str(pasta)])
        if codigo != 0:
            raise RuntimeError("não consegui abrir o pacote do {}".format(inst["app"]))
        return copiar_app_mac(pasta / inst["app"], inst["app"])


def abrir_pagina(url):
    try:
        if SISTEMA == "windows":
            os.startfile(url)  # noqa: attr existe só no Windows
        elif SISTEMA == "mac":
            subprocess.run(["open", url])
        else:
            subprocess.run(["xdg-open", url])
    except OSError:
        pass


def executar(app, inst, tipo):
    """Roda o instalador de um app. Devolve None quando rodou, ou 'manual'/'falhou'."""
    if SISTEMA == "windows" and inst.get("winget") and winget_disponivel():
        if inst.get("admin"):
            aviso("o Windows vai pedir permissão para instalar o {}: clique em Sim".format(app["nome"]))
        cmd = ["winget", "install", "--id", inst["winget"], "-e", "--silent",
               "--accept-package-agreements", "--accept-source-agreements"]
        if inst.get("escopo") == "user":
            cmd += ["--scope", "user"]
        rodar(cmd)
    elif tipo == "xcode-clt":
        rodar(["xcode-select", "--install"])
        aviso("uma janela da Apple vai abrir: clique em Instalar, espere terminar e rode o instalador de novo")
        return "manual"
    elif tipo == "script" and SISTEMA == "windows":
        rodar(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
               "Invoke-RestMethod {} | Invoke-Expression".format(inst["url"])])
    elif tipo == "script":
        rodar(["bash", "-c", "curl -fsSL {} | bash".format(inst["url"])])
    elif tipo == "uv-python":
        uv = uv_bin()
        if not uv:
            aviso("o Python depende do uv, que ainda não está instalado")
            return "falhou"
        rodar([uv, "python", "install", inst["versao"]])
    elif tipo == "dmg-github":
        instalar_dmg_github(inst)
    elif tipo == "zip-app":
        instalar_zip_app(inst)
    elif tipo == "pagina" or (SISTEMA == "windows" and inst.get("winget")):
        url = inst.get("url") or "https://apps.microsoft.com/detail/9NBLGGH4NNS1"
        abrir_pagina(url)
        aviso("abri a página de download do {}: instale por lá e rode de novo".format(app["nome"]))
        return "manual"
    else:
        aviso("não sei instalar o {} neste sistema".format(app["nome"]))
        return "falhou"
    return None


def instalar_app(app, tentativas=2):
    """Devolve 'instalado', 'manual' (depende da pessoa) ou 'falhou'.

    Download que cai no meio (rede lenta, tempo esgotado) é o erro mais comum na primeira
    instalação: por isso cada app tem uma segunda tentativa automática antes de desistir.
    """
    inst = app.get(SISTEMA, {}).get("instalar", {})
    tipo = inst.get("tipo")
    for tentativa in range(1, tentativas + 1):
        try:
            estado = executar(app, inst, tipo)
        except (OSError, RuntimeError, ValueError) as e:
            aviso("{}: {}".format(app["nome"], e))
            estado = None
        if estado == "manual":
            return "manual"
        garantir_path()
        if checar(app):
            return "instalado"
        if estado == "falhou" or tentativa == tentativas:
            return "falhou"
        aviso("o {} não terminou de instalar; tentando de novo".format(app["nome"]))
    return "falhou"


def escolher(perfil, com, so):
    apps = catalogo()
    ids = {a["id"] for a in apps}
    for pedido in list(com) + list(so):
        if pedido not in ids:
            raise SystemExit("app desconhecido: {} (veja --listar)".format(pedido))
    if so:
        return [a for a in apps if a["id"] in so]
    return [a for a in apps if a["perfis"].get(perfil) in ("obrigatorio", "recomendado") or a["id"] in com]


def instalar(perfil, com, so):
    passo("Preparando o computador (perfil {}, {})".format(perfil, SISTEMA))
    resultado = {}
    for app in escolher(perfil, com, so):
        if checar(app):
            ok("{} já está instalado".format(app["nome"]))
            resultado[app["id"]] = "instalado"
            continue
        print("   ..  instalando {}: {}".format(app["nome"], app["para_que"]), flush=True)
        estado = instalar_app(app)
        resultado[app["id"]] = estado
        if estado == "instalado":
            ok("{} instalado".format(app["nome"]))
        elif estado == "falhou":
            aviso("{} não ficou instalado. Feche esta janela, abra de novo e rode outra vez; se repetir, peça ajuda à Root.".format(app["nome"]))
        if app["id"] == "git" and estado == "manual":
            break  # sem git e sem as ferramentas da Apple nada mais anda; a pessoa roda de novo depois
    faltam = [a["nome"] for a in catalogo() if a["perfis"].get(perfil) == "obrigatorio" and resultado.get(a["id"]) not in ("instalado", None)]
    return 1 if faltam else 0


def criar_venv():
    passo("Criando o Python do kit (.venv)")
    uv = uv_bin()
    if not uv:
        aviso("o uv não está instalado; rode o instalador do kit primeiro")
        return 1
    if not python_do_venv().exists():
        codigo, _ = rodar([uv, "venv", "--python", "3.12", str(VENV)])
        if codigo != 0:
            aviso("não consegui criar o .venv")
            return 1
    codigo, _ = rodar([uv, "pip", "install", "--quiet", "--python", str(python_do_venv()), "-r", str(REQUISITOS)])
    pronto, texto = checar_venv()
    (ok if pronto else aviso)(texto)
    return 0 if pronto and codigo == 0 else 1


# ---------------------------------------------------------------- relatório

def imprimir(conf):
    print("Computador: {} · perfil {}\n".format(conf["sistema"], conf["perfil"]))
    for nivel in NIVEIS:
        grupo = [a for a in conf["apps"] if a["nivel"] == nivel]
        if not grupo:
            continue
        print({"obrigatorio": "Obrigatórios", "recomendado": "Recomendados", "opcional": "Opcionais"}[nivel])
        for a in grupo:
            marca = "[ok]   " if a["instalado"] else ("[falta]" if nivel != "opcional" else "[-]    ")
            print("  {} {}: {}".format(marca, a["nome"], a["para_que"]))
        print()
    print(("[ok]    " if conf["venv"]["pronto"] else "[falta] ") + conf["venv"]["detalhe"])
    if conf["faltam_obrigatorios"]:
        print("\nFalta instalar: {}. Rode o instalador do kit ou peça ao Claude: \"confere o meu computador\".".format(
            ", ".join(conf["faltam_obrigatorios"])))


def listar():
    for app in catalogo():
        niveis = ", ".join("{} {}".format(p, app["perfis"][p]) for p in PERFIS)
        print("{:<12} {} ({})\n             {}".format(app["id"], app["nome"], niveis, app["para_que"]))


def valor(argv, nome):
    if nome in argv:
        i = argv.index(nome)
        if i + 1 < len(argv):
            return [x.strip() for x in argv[i + 1].split(",") if x.strip()]
    return []


def main(argv):
    forcado = (valor(argv, "--perfil") or [None])[0]
    perfil = perfil_do_kit(forcado)
    if "--listar" in argv:
        listar()
        return 0
    if "--venv" in argv:
        return criar_venv()
    if "--instalar" in argv:
        return instalar(perfil, valor(argv, "--com"), valor(argv, "--so"))
    if "--conferir" in argv:
        conf = conferir(perfil)
        if "--json" in argv:
            print(json.dumps(conf, ensure_ascii=False, indent=2))
        else:
            imprimir(conf)
        return 1 if conf["faltam_obrigatorios"] else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
