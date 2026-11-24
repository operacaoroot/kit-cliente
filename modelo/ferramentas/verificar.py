#!/usr/bin/env python3
"""Confere cada passo do kit e grava o progresso em .root/progresso.json.

Uso (na pasta do kit):
    python3 ferramentas/verificar.py              # mostra a lista e grava o progresso
    python3 ferramentas/verificar.py --silencioso # só grava; imprime uma linha
    python3 ferramentas/verificar.py --sem-rede   # não testa a conexão com a Root

No Windows, troque `python3` por `.venv/Scripts/python`.
O progresso é o que a Root acompanha. Ele diz quais passos foram feitos e quando,
nunca o conteúdo do trabalho. Só biblioteca padrão, compatível com Python 3.9.
"""
import datetime as dt
import json
import platform
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import agente  # noqa: E402  (mesma pasta; qual agente trabalha neste kit)
import ambiente  # noqa: E402  (mesma pasta; lê ambiente/apps.json)
import conectar  # noqa: E402  (mesma pasta; como o kit fala com o GitHub)

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


def checar_instalar(sem_rede):
    faltas = []
    conf = ambiente.conferir(ambiente.perfil_do_kit())
    nomes = {a["id"]: a["nome"] for a in conf["apps"]}
    for app_id in conf["faltam_obrigatorios"]:
        faltas.append("{} não encontrado".format(nomes.get(app_id, app_id)))
    if not conf["venv"]["pronto"]:
        faltas.append(conf["venv"]["detalhe"])
    if sem_rede:
        if not (ROOT_DIR / "chave").exists() and acesso_resumido()["modo"] != "colaborador":
            faltas.append("sem conta do GitHub ligada e sem a chave do kit em .root/chave")
    elif not conectar.estado()["modo"]:
        faltas.append("o kit ainda não está ligado à Root (peça ao {}: \"liga o kit à Root\")".format(agente.NOME))
    if not (KIT / ".git").exists():
        faltas.append("a pasta do kit não é um repositório git")
    if cliente_do_kit().get("mcp"):
        import mcp as servidor_mcp  # noqa: E402  (mesma pasta; o servidor da empresa, só no kit Codex)
        e = servidor_mcp.estado()
        if not e["pronto"]:
            faltas.append("o {} ainda não está ligado ao servidor da empresa (rode python3 ferramentas/mcp.py --registrar)".format(agente.NOME))
    if not faltas and not sem_rede:
        codigo, _, erro = rodar(["git", "ls-remote", "--exit-code", "origin", "HEAD"], timeout=25)
        if codigo != 0:
            faltas.append("o kit não conseguiu falar com a Root ({})".format(motivo_da_rede(erro)))
    pronto = "computador pronto (conexão com a Root não testada)" if sem_rede else "computador pronto e kit conectado à Root"
    return (not faltas), "; ".join(faltas) or pronto


def motivo_da_rede(erro):
    e = (erro or "").lower()
    if "permission denied" in e or "could not read from remote" in e or "not found" in e:
        return "a chave do kit não foi aceita ou o repositório não existe; peça ajuda à Root"
    if "timed out" in e or "could not resolve" in e or "network" in e:
        return "sem conexão com a internet agora; tente de novo mais tarde"
    linhas = [l for l in (erro or "").splitlines() if l.strip()]
    return linhas[0] if linhas else "sem resposta"


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


def checar_primeira_skill():
    arq = KIT / "catalogo.json"
    if not arq.exists():
        return False, "o kit ainda não tem catalogo.json"
    try:
        skills = json.loads(arq.read_text(encoding="utf-8")).get("skills", [])
    except ValueError:
        return False, "o catalogo.json está ilegível"
    suas = [s for s in skills if s.get("origem") == "cliente"]
    prontas = []
    for s in suas:
        testes = agente.PASTA_SKILLS / s["nome"] / "TESTES.md"
        if s.get("estado") == "ativa" and testes.exists() and "aprovado" in testes.read_text(encoding="utf-8", errors="ignore").lower():
            prontas.append(s["nome"])
    if prontas:
        return True, "{} ferramenta(s) sua(s) em uso: {}".format(len(prontas), ", ".join(prontas))
    em_teste = [s["nome"] for s in suas if s.get("estado") == "homologacao"]
    if em_teste:
        return False, "em teste na oficina: {}".format(", ".join(em_teste))
    return False, "nenhuma ferramenta criada ainda"


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
        "primeira-skill": checar_primeira_skill,
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
        "acesso": acesso_resumido(),
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


def cliente_do_kit():
    arq = ROOT_DIR / "cliente.json"
    try:
        return json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else {}
    except ValueError:
        return {}


def acesso_resumido():
    """Como o kit fala com o GitHub, sem rede: lido do git local. Vai para a Root no progresso."""
    codigo, url, _ = rodar(["git", "remote", "get-url", "origin"])
    url = url if codigo == 0 else ""
    codigo, email, _ = rodar(["git", "config", "user.email"])
    modo = "colaborador" if url.startswith("https://") else ("chave" if url.startswith("git@") else None)
    login = None
    if modo == "colaborador" and email.endswith("@users.noreply.github.com"):
        login = email.split("@")[0].split("+")[-1]
    return {"modo": modo, "login": login}


def contar_ajuda_aberta():
    n = 0
    for f in (KIT / "ajuda").glob("*.md"):
        cab = cabecalho(f.read_text(encoding="utf-8", errors="ignore"))
        if any(l.strip().lower() == "estado: aberto" for l in cab.splitlines()):
            n += 1
    return n


if __name__ == "__main__":
    sys.exit(main(sys.argv))
