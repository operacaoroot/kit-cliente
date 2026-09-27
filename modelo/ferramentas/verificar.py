#!/usr/bin/env python3
"""Confere cada passo do kit e grava o progresso em .root/progresso.json.

Uso (na pasta do kit):
    python3 ferramentas/verificar.py              # mostra a lista e grava o progresso
    python3 ferramentas/verificar.py --silencioso # só grava; imprime uma linha
    python3 ferramentas/verificar.py --sem-rede   # não testa a conexão com a Root

O progresso é o que a Root acompanha. Ele diz quais passos foram feitos e quando,
nunca o conteúdo do trabalho. Só biblioteca padrão, compatível com Python 3.9.
"""
import datetime as dt
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
ROOT_DIR = KIT / ".root"
PROGRESSO = ROOT_DIR / "progresso.json"
EMAIL_DO_MONTADOR = "kits@operacaoroot.com"


def agora():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def hoje():
    return dt.date.today().isoformat()


def rodar(cmd, timeout=20):
    try:
        r = subprocess.run(cmd, cwd=str(KIT), capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, "", str(e)


def claude_instalado():
    if shutil.which("claude"):
        return True
    casa = Path.home()
    candidatos = [casa / ".local" / "bin" / "claude", casa / ".claude" / "local" / "claude",
                  casa / ".local" / "bin" / "claude.exe", Path("/opt/homebrew/bin/claude"), Path("/usr/local/bin/claude")]
    return any(c.exists() for c in candidatos)


def obsidian_instalado():
    sistema = platform.system()
    if sistema == "Darwin":
        return any(Path(p).exists() for p in ["/Applications/Obsidian.app", str(Path.home() / "Applications/Obsidian.app")])
    if sistema == "Windows":
        local = os.environ.get("LOCALAPPDATA", "")
        return any(Path(p).exists() for p in [
            os.path.join(local, "Obsidian", "Obsidian.exe"),
            os.path.join(local, "Programs", "Obsidian", "Obsidian.exe"),
            r"C:\Program Files\Obsidian\Obsidian.exe",
        ])
    return shutil.which("obsidian") is not None or Path("/var/lib/flatpak/app/md.obsidian.Obsidian").exists()


def checar_instalar(sem_rede):
    faltas = []
    if not shutil.which("git"):
        faltas.append("git não encontrado")
    if not claude_instalado():
        faltas.append("Claude Code não encontrado (comando claude)")
    if not obsidian_instalado():
        faltas.append("Obsidian não encontrado")
    if not (ROOT_DIR / "chave").exists():
        faltas.append("chave do kit ausente em .root/chave")
    if not (KIT / ".git").exists():
        faltas.append("a pasta do kit não é um repositório git")
    if not faltas and not sem_rede:
        codigo, _, erro = rodar(["git", "ls-remote", "--exit-code", "origin", "HEAD"], timeout=25)
        if codigo != 0:
            faltas.append("o kit não conseguiu falar com a Root ({})".format(erro.splitlines()[-1] if erro else "sem resposta"))
    return (not faltas), "; ".join(faltas) or "tudo instalado e conectado"


def cabecalho(texto):
    if not texto.startswith("---"):
        return ""
    fim = texto.find("\n---", 3)
    return texto[3:fim] if fim > 0 else ""


def checar_perfil():
    p = KIT / "perfil.md"
    if not p.exists():
        return False, "perfil.md não existe"
    cab = cabecalho(p.read_text(encoding="utf-8"))
    ok = any(linha.strip().lower() == "confirmado: sim" for linha in cab.splitlines())
    return ok, "perfil confirmado" if ok else "perfil ainda não confirmado"


def checar_vault():
    vault = KIT / "vault"
    pendentes = []
    for nota in vault.rglob("*.md"):
        if "_contexto" in nota.parts or ".obsidian" in nota.parts:
            continue
        cab = cabecalho(nota.read_text(encoding="utf-8", errors="ignore"))
        if any(linha.strip().lower() == "revisar: sim" for linha in cab.splitlines()):
            pendentes.append(nota.relative_to(vault).as_posix())
    if pendentes:
        return False, "{} nota(s) para revisar: {}".format(len(pendentes), ", ".join(pendentes[:3]) + ("..." if len(pendentes) > 3 else ""))
    return True, "todas as notas revisadas"


def checar_contexto():
    base = KIT / "vault" / "_contexto"
    faltam = [n for n in ["00 - LEIA-ME.md", "00 - Auditoria.md"] if not (base / n).exists()]
    return (not faltam), "pacote de contexto e auditoria prontos" if not faltam else "falta: " + ", ".join(faltam)


def checar_primeira_frente():
    entregas = [p for p in (KIT / "entregas").rglob("*") if p.is_file() and p.name != ".gitkeep"]
    avaliacao = KIT / "vault" / "40-Operacao" / "Resultados da frente.md"
    faltas = []
    if not entregas:
        faltas.append("nenhuma entrega em entregas/")
    if not avaliacao.exists():
        faltas.append("sem avaliação em vault/40-Operacao/Resultados da frente.md")
    return (not faltas), "; ".join(faltas) or "{} entrega(s) e avaliação registrada".format(len(entregas))


def ultimo_envio():
    codigo, upstream, _ = rodar(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    if codigo != 0 or not upstream:
        return None
    # conta só envio feito pelo kit; o commit do montador da Root não vale como "fechar o dia"
    codigo, saida, _ = rodar(["git", "log", "-50", "--format=%ae%x09%ci", upstream])
    if codigo != 0:
        return None
    for linha in saida.splitlines():
        email, data = linha.split("\t", 1)
        if email != EMAIL_DO_MONTADOR:
            return data[:10]
    return None


def checar_fechar_o_dia():
    data = ultimo_envio()
    if not data:
        return False, "ainda sem envio para a Root", None
    return data == hoje(), "último envio em {}".format(data), data


def main(argv):
    silencioso = "--silencioso" in argv
    sem_rede = "--sem-rede" in argv
    passos = json.loads((KIT / "ferramentas" / "passos.json").read_text(encoding="utf-8"))["passos"]
    anterior = {}
    if PROGRESSO.exists():
        try:
            anterior = {p["id"]: p for p in json.loads(PROGRESSO.read_text(encoding="utf-8")).get("passos", [])}
        except (ValueError, KeyError):
            anterior = {}

    checagens = {
        "instalar": lambda: checar_instalar(sem_rede),
        "perfil": checar_perfil,
        "vault": checar_vault,
        "contexto": checar_contexto,
        "primeira-frente": checar_primeira_frente,
    }
    resultado, envio = [], None
    for passo in passos:
        pid = passo["id"]
        if pid == "fechar-o-dia":
            ok, detalhe, envio = checar_fechar_o_dia()
            feito = ok or bool(envio)
        else:
            feito, detalhe = checagens[pid]()
            if pid == "instalar" and sem_rede and anterior.get(pid, {}).get("feito"):
                feito = feito or anterior[pid]["feito"]
        antes = anterior.get(pid, {})
        feito_em = antes.get("feito_em") if antes.get("feito") else None
        if feito and not feito_em:
            feito_em = agora()
        resultado.append({"id": pid, "titulo": passo["titulo"], "feito": bool(feito),
                          "feito_em": feito_em if feito else None, "detalhe": detalhe})

    atual = next((p["id"] for p in resultado if not p["feito"]), None)
    cliente = {}
    if (ROOT_DIR / "cliente.json").exists():
        cliente = json.loads((ROOT_DIR / "cliente.json").read_text(encoding="utf-8"))
    progresso = {
        "kit_id": cliente.get("kit_id"),
        "cliente": cliente.get("slug"),
        "atualizado_em": agora(),
        "passo_atual": atual,
        "concluidos_hoje": sum(1 for p in resultado if p["feito_em"] and p["feito_em"][:10] == hoje() and p["id"] != "fechar-o-dia"),
        "ultimo_envio": envio,
        "pedidos_de_ajuda_abertos": contar_ajuda_aberta(),
        "passos": resultado,
    }
    ROOT_DIR.mkdir(exist_ok=True)
    PROGRESSO.write_text(json.dumps(progresso, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    feitos = sum(1 for p in resultado if p["feito"])
    if silencioso:
        print("{} de {} passos feitos. Passo atual: {}.".format(feitos, len(resultado), atual or "todos concluídos"))
        return 0
    cor = sys.stdout.isatty() and platform.system() != "Windows"
    verde, vermelho, fim = ("\033[32m", "\033[31m", "\033[0m") if cor else ("", "", "")
    print("Conferência do kit ({} de {} passos feitos)\n".format(feitos, len(resultado)))
    for i, p in enumerate(resultado, 1):
        marca = verde + "[feito]" + fim if p["feito"] else vermelho + "[falta]" + fim
        print("{} {}. {}: {}".format(marca, i, p["titulo"], p["detalhe"]))
    print("\nPasso atual: {}".format(next((p["titulo"] for p in resultado if p["id"] == atual), "todos concluídos")))
    return 0


def contar_ajuda_aberta():
    n = 0
    for f in (KIT / "ajuda").glob("*.md"):
        cab = cabecalho(f.read_text(encoding="utf-8", errors="ignore"))
        if any(l.strip().lower() == "estado: aberto" for l in cab.splitlines()):
            n += 1
    return n


if __name__ == "__main__":
    sys.exit(main(sys.argv))
