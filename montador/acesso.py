#!/usr/bin/env python3
"""Quem acessa o repositório do kit de um cliente: convidar, ver e encerrar.

Uso:
    python3 montador/acesso.py estado <slug>
    python3 montador/acesso.py convidar <slug> [--usuario <login-do-github>]
    python3 montador/acesso.py encerrar <slug> --motivo "fim do contrato" [--sim]

- convidar: convida o usuário do GitHub do cliente (cliente.github no manifesto, ou --usuario)
  como colaborador com escrita. O GitHub só convida por NOME DE USUÁRIO em repositório de conta
  pessoal (a operacaoroot é conta pessoal); convite por e-mail só existe para organização.
- encerrar: cancela convites, tira os colaboradores, revoga a chave do kit e arquiva o
  repositório. Sem --sim, só mostra o que faria. O kit continua funcionando na máquina do
  cliente com o que já tem, mas para de enviar e de receber.

Usa o token da conta operacaoroot (~/.config/root/github.env). Só biblioteca padrão.
"""
import datetime as dt
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "montador"))
from montar import DONO_GITHUB, Recusa, api  # noqa: E402


def agora():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def manifesto(slug):
    arq = RAIZ / "manifestos" / "{}.json".format(slug)
    if not arq.exists():
        raise Recusa("não achei manifestos/{}.json".format(slug))
    return arq, json.loads(arq.read_text(encoding="utf-8"))


def gravar(arq, m):
    arq.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def repo_de(m):
    repo = m.get("entrega", {}).get("repo") or "{}/kit-{}".format(DONO_GITHUB, m["cliente"]["slug"])
    return repo


def convidar_usuario(repo, usuario):
    """Devolve (situacao, detalhe): 'convidado', 'ja-colaborador' ou 'falhou'."""
    status, corpo = api("PUT", "/repos/{}/collaborators/{}".format(repo, usuario), {"permission": "push"})
    if status == 201:
        return "convidado", "convite {} enviado para @{}".format(corpo.get("id"), usuario)
    if status == 204:
        return "ja-colaborador", "@{} já é colaborador".format(usuario)
    if status == 404:
        return "falhou", "o GitHub não achou o usuário @{} (ou o repositório {})".format(usuario, repo)
    if status == 403:
        return "falhou", ("o token da operacaoroot não pode convidar: no GitHub, Settings > Developer settings > "
                          "Fine-grained tokens > (o token do kit) > Repository permissions > Administration: "
                          "Read and write, e salvar. Depois: montador/acesso.py convidar")
    return "falhou", "{} {}".format(status, corpo.get("message"))


def ver_estado(repo):
    s1, convites = api("GET", "/repos/{}/invitations".format(repo))
    s2, colabs = api("GET", "/repos/{}/collaborators?affiliation=direct".format(repo))
    s3, chaves = api("GET", "/repos/{}/keys".format(repo))
    s4, info = api("GET", "/repos/{}".format(repo))
    if s4 != 200:
        raise Recusa("repositório {} não encontrado ({})".format(repo, s4))
    return {
        "repo": repo,
        "arquivado": info.get("archived", False),
        "convites_pendentes": [{"id": c["id"], "usuario": (c.get("invitee") or {}).get("login"), "criado_em": c.get("created_at")}
                               for c in (convites if s1 == 200 else [])],
        "colaboradores": [c["login"] for c in (colabs if s2 == 200 else []) if c["login"].lower() != DONO_GITHUB],
        "chaves": [{"id": k["id"], "titulo": k.get("title"), "escrita": not k.get("read_only")} for k in (chaves if s3 == 200 else [])],
    }


def cmd_estado(slug):
    _, m = manifesto(slug)
    e = ver_estado(repo_de(m))
    print("Repositório: {}{}".format(e["repo"], " (ARQUIVADO)" if e["arquivado"] else ""))
    print("Colaboradores: {}".format(", ".join("@" + c for c in e["colaboradores"]) or "nenhum"))
    for c in e["convites_pendentes"]:
        print("Convite pendente: @{} desde {}".format(c["usuario"], c["criado_em"]))
    for k in e["chaves"]:
        print("Chave do kit: {} ({})".format(k["titulo"], "escrita" if k["escrita"] else "leitura"))
    return 0


def cmd_convidar(slug, usuario=None):
    arq, m = manifesto(slug)
    usuario = usuario or m["cliente"].get("github")
    if not usuario:
        raise Recusa("o manifesto não tem cliente.github; passe --usuario <login>")
    if not m.get("entrega", {}).get("publicado"):
        raise Recusa("o kit de {} ainda não foi publicado (montar.py --github)".format(slug))
    situacao, detalhe = convidar_usuario(repo_de(m), usuario)
    print(detalhe)
    if situacao != "falhou":
        m["cliente"]["github"] = usuario
        m.setdefault("entrega", {})["colaborador"] = {"usuario": usuario, "situacao": situacao, "em": agora()}
        gravar(arq, m)
    return 0 if situacao != "falhou" else 1


def cmd_encerrar(slug, motivo, confirmado):
    arq, m = manifesto(slug)
    repo = repo_de(m)
    e = ver_estado(repo)
    plano = ["cancelar convite de @{}".format(c["usuario"]) for c in e["convites_pendentes"]]
    plano += ["tirar o colaborador @{}".format(c) for c in e["colaboradores"]]
    plano += ["revogar a chave '{}'".format(k["titulo"]) for k in e["chaves"]]
    plano += ["arquivar {}".format(repo)] if not e["arquivado"] else []
    if not plano:
        print("Nada a fazer: {} já está encerrado.".format(repo))
        return 0
    print("Encerrar o kit de {} ({}):".format(m["cliente"]["nome"], motivo))
    for p in plano:
        print("  - " + p)
    if not confirmado:
        print("\nNada foi feito. Rode de novo com --sim para executar.")
        return 0
    falhas = []
    for c in e["convites_pendentes"]:
        s, _ = api("DELETE", "/repos/{}/invitations/{}".format(repo, c["id"]))
        if s != 204:
            falhas.append("convite {}".format(c["id"]))
    for c in e["colaboradores"]:
        s, _ = api("DELETE", "/repos/{}/collaborators/{}".format(repo, c))
        if s != 204:
            falhas.append("colaborador @{}".format(c))
    for k in e["chaves"]:
        s, _ = api("DELETE", "/repos/{}/keys/{}".format(repo, k["id"]))
        if s != 204:
            falhas.append("chave {}".format(k["id"]))
    if not e["arquivado"]:
        s, _ = api("PATCH", "/repos/{}".format(repo), {"archived": True})
        if s != 200:
            falhas.append("arquivar" + (" (o token precisa de Administration: Read and write)" if s == 403 else ""))
    m.setdefault("entrega", {})["encerrado"] = {"em": agora(), "motivo": motivo, "falhas": falhas}
    gravar(arq, m)
    print("Encerrado." if not falhas else "Encerrado com falhas em: " + ", ".join(falhas))
    return 0 if not falhas else 1


def valor(argv, nome):
    return argv[argv.index(nome) + 1] if nome in argv and argv.index(nome) + 1 < len(argv) else None


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    acao, slug = argv[1], argv[2]
    try:
        if acao == "estado":
            return cmd_estado(slug)
        if acao == "convidar":
            return cmd_convidar(slug, valor(argv, "--usuario"))
        if acao == "encerrar":
            motivo = valor(argv, "--motivo")
            if not motivo:
                raise Recusa("diga o motivo: --motivo \"fim do contrato\"")
            return cmd_encerrar(slug, motivo, "--sim" in argv)
    except Recusa as e:
        print("RECUSADO:", e)
        return 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
