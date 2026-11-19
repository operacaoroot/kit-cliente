#!/usr/bin/env python3
"""Liga o Codex do kit ao servidor da empresa (MCP), com um token só desta pessoa.

Uso (na pasta do kit):
    python3 ferramentas/mcp.py --conferir [--json]   # Codex instalado? servidor registrado? token presente?
    python3 ferramentas/mcp.py --registrar           # guarda o token em .root/mcp.env e registra o servidor no Codex
    python3 ferramentas/mcp.py --testar              # chama o servidor de verdade: sem token tem de dar 401; com token, passar

O que o kit sabe do servidor (nome, endereço, perfil e o nome da variável do token) está em
.root/cliente.json, campo `mcp`, posto pela Root na montagem. O token NÃO está lá: ele é digitado
na instalação (ou vem da variável de ambiente KIT_MCP_TOKEN) e fica em .root/mcp.env, com
permissão 600, fora do git. O registro usa o próprio Codex:
    codex mcp add <nome> --url <url> --bearer-token-env-var <VARIAVEL>
que grava em ~/.codex/config.toml só o NOME da variável. O atalho "Codex do kit" carrega o
.root/mcp.env antes de abrir o Codex, e é assim que o token chega ao servidor.
Nenhum token passa por linha de comando nem aparece na tela. Só biblioteca padrão (Python 3.9).
"""
import getpass
import json
import os
import platform
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
ROOT_DIR = KIT / ".root"
ENV = ROOT_DIR / "mcp.env"
SISTEMA = {"Darwin": "mac", "Windows": "windows"}.get(platform.system(), "linux")


def garantir_path():
    """O instalador deixa o codex em ~/.local/bin; o processo atual pode ainda não saber.
    Entra no FIM do PATH, para um codex já escolhido pela pessoa continuar valendo."""
    extras = [str(Path.home() / ".local" / "bin")]
    if SISTEMA == "windows":
        extras.append(os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Links"))
    atual = os.environ.get("PATH", "").split(os.pathsep)
    for e in extras:
        if e and e not in atual:
            atual.append(e)
    os.environ["PATH"] = os.pathsep.join(atual)


def configuracao():
    arq = ROOT_DIR / "cliente.json"
    if not arq.exists():
        return None
    return json.loads(arq.read_text(encoding="utf-8")).get("mcp") or None


def codex_bin():
    garantir_path()
    return shutil.which("codex")


def rodar_codex(*args, timeout=60):
    codex = codex_bin()
    if not codex:
        return 1, ""
    try:
        r = subprocess.run([codex] + list(args), cwd=str(KIT), capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)


def ler_token(variavel):
    if not ENV.exists():
        return None
    for linha in ENV.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha.startswith("export "):
            linha = linha[7:]
        if linha.startswith(variavel + "="):
            return linha.split("=", 1)[1].strip().strip('"').strip("'") or None
    return None


def gravar_token(variavel, token):
    ROOT_DIR.mkdir(exist_ok=True)
    conteudo = ("{}={}\n" if SISTEMA == "windows" else "export {}={}\n").format(variavel, token)
    tmp = ENV.with_name("mcp.env.tmp")
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(conteudo)
    os.replace(str(tmp), str(ENV))
    if SISTEMA != "windows":
        os.chmod(str(ENV), 0o600)


def registrado(cfg):
    codigo, saida = rodar_codex("mcp", "get", cfg["nome"], "--json")
    if codigo != 0:
        return False
    try:
        servidor = json.loads(saida)
        transporte = servidor.get("transport", {})
        return (servidor.get("enabled", True) is True
                and transporte.get("type") == "streamable_http"
                and transporte.get("url") == cfg["url"]
                and transporte.get("bearer_token_env_var") == cfg["variavel"])
    except (ValueError, AttributeError):
        return False


def estado():
    cfg = configuracao()
    if not cfg:
        return {"mcp": None}
    codex = codex_bin()
    e = {"nome": cfg["nome"], "url": cfg["url"], "perfil": cfg.get("perfil"), "variavel": cfg["variavel"],
         "codex_instalado": bool(codex), "registrado": bool(codex) and registrado(cfg),
         "token_presente": bool(ler_token(cfg["variavel"]))}
    e["pronto"] = e["codex_instalado"] and e["registrado"] and e["token_presente"]
    return e


def pedir_token(cfg):
    token = os.environ.get("KIT_MCP_TOKEN", "").strip()
    if token:
        return token, "da variável KIT_MCP_TOKEN"
    token = ler_token(cfg["variavel"])
    if token:
        return token, "do .root/mcp.env que já existia"
    if sys.stdin.isatty():
        print("Cole o token do servidor {} que a Root entregou a você (ele não aparece na tela):".format(cfg["nome"]))
        token = getpass.getpass("token: ").strip()
        if token:
            return token, "digitado agora"
    return None, None


def registrar():
    cfg = configuracao()
    if not cfg:
        print("Este kit não tem servidor MCP da empresa; nada a registrar.")
        return 2
    token, origem = pedir_token(cfg)
    if not token:
        print("Sem token. Rode de novo numa janela de terminal para digitá-lo, ou passe pela variável KIT_MCP_TOKEN.")
        return 1
    if not codex_bin():
        gravar_token(cfg["variavel"], token)
        print("Token guardado em .root/mcp.env ({}), fora do git.".format(origem))
        print("O codex ainda não está instalado neste computador: rode o instalador do kit e depois "
              "python3 ferramentas/mcp.py --registrar de novo.")
        return 1
    codigo, saida = rodar_codex("mcp", "add", cfg["nome"], "--url", cfg["url"], "--bearer-token-env-var", cfg["variavel"])
    if codigo != 0:
        print("O codex não registrou o servidor {}:\n{}".format(cfg["nome"], saida.strip()))
        return 1
    gravar_token(cfg["variavel"], token)
    print("Token guardado em .root/mcp.env ({}), fora do git.".format(origem))
    e = estado()
    print("Servidor {} registrado no Codex ({}), perfil {}. Token pela variável {}.".format(
        cfg["nome"], cfg["url"], cfg.get("perfil", "?"), cfg["variavel"]))
    if not e["pronto"]:
        print("Ainda falta: " + ", ".join(k for k in ("codex_instalado", "registrado", "token_presente") if not e[k]))
        return 1
    print("Abra o Codex pelo atalho \"Codex do kit\": ele carrega o token antes de abrir.")
    return 0


def status_http(url, token):
    """Testa initialize: um HTTP de erro ou uma página HTML não provam um MCP disponível."""
    dados = json.dumps({"jsonrpc": "2.0", "id": "kit-health", "method": "initialize",
                       "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                                  "clientInfo": {"name": "kit-root", "version": "1.0"}}}).encode()
    req = urllib.request.Request(url, data=dados, headers={
        "Accept": "application/json, text/event-stream", "Content-Type": "application/json",
        "User-Agent": "kit-root/1.0"})
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            if r.status != 200:
                return r.status, False
            if "text/event-stream" in r.headers.get("Content-Type", ""):
                partes = []
                for _ in range(128):
                    linha = r.readline(65537).decode("utf-8").rstrip("\r\n")
                    if linha.startswith("data:"):
                        partes.append(linha[5:].lstrip())
                    elif not linha and partes:
                        break
                corpo = "\n".join(partes)
            else:
                corpo = r.read(65537).decode("utf-8")
            try:
                resposta = json.loads(corpo)
                resultado = resposta.get("result", {})
                valido = (resposta.get("jsonrpc") == "2.0" and resposta.get("id") == "kit-health"
                          and not resposta.get("error") and isinstance(resultado, dict)
                          and bool(resultado.get("protocolVersion"))
                          and isinstance(resultado.get("capabilities"), dict)
                          and isinstance(resultado.get("serverInfo"), dict))
                return r.status, valido
            except (ValueError, AttributeError):
                return r.status, False
    except urllib.error.HTTPError as e:
        return e.code, False
    except (urllib.error.URLError, OSError, UnicodeError):
        return None, False


def testar():
    cfg = configuracao()
    if not cfg:
        print("Este kit não tem servidor MCP da empresa; nada a testar.")
        return 2
    token = ler_token(cfg["variavel"])
    if not token:
        print("Sem token em .root/mcp.env: rode python3 ferramentas/mcp.py --registrar antes.")
        return 1
    sem, _ = status_http(cfg["url"], None)
    com, aceito = status_http(cfg["url"], token)
    print("Servidor {} em {}".format(cfg["nome"], cfg["url"]))
    print("  sem token: {} (esperado 401)".format("HTTP {}".format(sem) if sem else "sem resposta"))
    print("  com token: {} ({})".format("HTTP {}".format(com) if com else "sem resposta", "initialize válido" if aceito else "initialize falhou"))
    if sem != 401:
        print("O servidor deveria recusar sem token. Avise a Root.")
        return 1
    if not aceito:
        print("O servidor não completou initialize. Confira o endereço, a disponibilidade e o token com a Root.")
        return 1
    print("Contrato ok: o servidor exige token e completou initialize com o seu.")
    return 0


def main(argv):
    if "--registrar" in argv:
        return registrar()
    if "--testar" in argv:
        return testar()
    if "--conferir" in argv:
        e = estado()
        if "--json" in argv:
            print(json.dumps(e, ensure_ascii=False, indent=2))
        elif e.get("mcp", 1) is None:
            print("Este kit não tem servidor MCP da empresa.")
        else:
            print("Servidor {} ({}), perfil {}".format(e["nome"], e["url"], e["perfil"]))
            for chave, rotulo in (("codex_instalado", "codex instalado"), ("registrado", "servidor registrado no Codex"),
                                  ("token_presente", "token em .root/mcp.env")):
                print("  [{}] {}".format("ok" if e[chave] else "falta", rotulo))
        return 0 if e.get("pronto") or e.get("mcp", 1) is None else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
