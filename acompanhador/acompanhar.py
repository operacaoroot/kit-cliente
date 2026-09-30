#!/usr/bin/env python3
"""Acompanha os kits entregues e prepara o que a Root precisa fazer. Sem modelo de IA.

Uso:
    python3 acompanhador/acompanhar.py            # todos os kits entregues
    python3 acompanhador/acompanhar.py <slug>     # um kit só
    python3 acompanhador/acompanhar.py --json     # saída em JSON (para o OS ler depois)

Roda três vezes por dia (08:30, 13:00, 18:00; ver acompanhador/agendar.sh). Para cada
manifesto com kit montado, lê o progresso do kit (pelo GitHub quando publicado, pela
pasta local quando não), compara com a rodada anterior e escreve um relatório em
acompanhador/saida/. A mensagem sugerida sai de um modelo de texto no tom do perfil
do cliente, por isso nenhuma chamada de modelo de IA acontece aqui. Nada é enviado
ao cliente: quem manda é o sócio responsável.

Só biblioteca padrão, compatível com Python 3.9.
"""
import base64
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "montador"))
from montar import api  # noqa: E402

ESTADO = RAIZ / "acompanhador" / "estado.json"
SAIDA = RAIZ / "acompanhador" / "saida"


def agora():
    return dt.datetime.now().astimezone()


def parse_iso(s):
    if not s:
        return None
    try:
        d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        return d if d.tzinfo else d.astimezone()
    except ValueError:
        return None


def cabecalho(texto):
    if not texto.startswith("---"):
        return {}
    fim = texto.find("\n---", 3)
    campos = {}
    for linha in texto[3:fim].splitlines():
        if ":" in linha:
            k, v = linha.split(":", 1)
            campos[k.strip()] = v.strip()
    return campos


# ---------------------------------------------------------------- leitura

def ler_do_github(repo):
    dono, nome = repo.split("/")
    status, corpo = api("GET", "/repos/{}/{}/contents/.root/progresso.json".format(dono, nome))
    if status != 200:
        return None, [], [], "progresso ilegível no GitHub ({})".format(status)
    progresso = json.loads(base64.b64decode(corpo["content"]).decode())
    status, commits = api("GET", "/repos/{}/{}/commits?per_page=5".format(dono, nome))
    lista = []
    if status == 200:
        for c in commits:
            lista.append({"sha": c["sha"][:8], "quando": c["commit"]["committer"]["date"], "mensagem": c["commit"]["message"].splitlines()[0],
                          "autor": (c.get("author") or {}).get("login"), "email": c["commit"]["author"].get("email", "")})
    ajuda = []
    status, arquivos = api("GET", "/repos/{}/{}/contents/ajuda".format(dono, nome))
    if status == 200:
        for a in arquivos:
            if not a["name"].endswith(".md"):
                continue
            s2, f = api("GET", "/repos/{}/{}/contents/{}".format(dono, nome, a["path"]))
            if s2 == 200:
                cab = cabecalho(base64.b64decode(f["content"]).decode())
                cab["arquivo"] = a["path"]
                ajuda.append(cab)
    return progresso, lista, ajuda, None


def ler_acesso(repo):
    """Quem está no repositório: convite pendente, colaboradores. Só para kit publicado."""
    s1, convites = api("GET", "/repos/{}/invitations".format(repo))
    s2, colabs = api("GET", "/repos/{}/collaborators?affiliation=direct".format(repo))
    return {
        "convites": [{"usuario": (c.get("invitee") or {}).get("login"), "criado_em": c.get("created_at")} for c in (convites if s1 == 200 else [])],
        "colaboradores": [c["login"] for c in (colabs if s2 == 200 else []) if c["login"].lower() != "operacaoroot"],
    }


def ler_do_local(pasta):
    pasta = Path(pasta)
    arq = pasta / ".root" / "progresso.json"
    if not arq.exists():
        return None, [], [], "sem .root/progresso.json em {}".format(pasta)
    progresso = json.loads(arq.read_text(encoding="utf-8"))
    r = subprocess.run(["git", "log", "-5", "--format=%h%x09%cI%x09%s"], cwd=str(pasta), capture_output=True, text=True)
    lista = []
    for linha in (r.stdout or "").splitlines():
        sha, quando, msg = linha.split("\t", 2)
        lista.append({"sha": sha, "quando": quando, "mensagem": msg})
    ajuda = []
    for f in sorted((pasta / "ajuda").glob("*.md")):
        cab = cabecalho(f.read_text(encoding="utf-8", errors="ignore"))
        cab["arquivo"] = "ajuda/" + f.name
        ajuda.append(cab)
    return progresso, lista, ajuda, None


def ler_catalogo(fonte, ent):
    """Só as ferramentas criadas pelo cliente: é o que mostra o kit sendo desenvolvido por ele."""
    try:
        if fonte == "github":
            dono, nome = ent["repo"].split("/")
            status, corpo = api("GET", "/repos/{}/{}/contents/catalogo.json".format(dono, nome))
            if status != 200:
                return []
            cat = json.loads(base64.b64decode(corpo["content"]).decode())
        else:
            arq = Path(ent.get("local", "")) / "catalogo.json"
            if not arq.exists():
                return []
            cat = json.loads(arq.read_text(encoding="utf-8"))
    except (ValueError, KeyError):
        return []
    return [{"nome": s["nome"], "estado": s.get("estado"), "versao": s.get("versao")}
            for s in cat.get("skills", []) if s.get("origem") == "cliente"]


# ---------------------------------------------------------------- análise

def analisar(m, perfis, anterior):
    ent = m.get("entrega", {})
    fonte = "github" if ent.get("publicado") else "local"
    if fonte == "github":
        progresso, commits, ajuda, erro = ler_do_github(ent["repo"])
    else:
        progresso, commits, ajuda, erro = ler_do_local(ent.get("local", ""))
    slug = m["cliente"]["slug"]
    r = {"slug": slug, "nome": m["cliente"]["nome"], "fonte": fonte, "erro": erro, "alertas": [], "eventos": []}
    if erro:
        r["alertas"].append(erro)
        return r
    if fonte == "github":
        acesso = ler_acesso(ent["repo"])
        esperado = (m["cliente"].get("github") or "").lower()
        for c in acesso["convites"]:
            criado = parse_iso(c.get("criado_em"))
            horas = int((agora() - criado).total_seconds() // 3600) if criado else 0
            if horas >= 24:
                r["alertas"].append("convite do GitHub para @{} sem aceitar há {}h".format(c["usuario"], horas))
        autores = sorted({c["autor"] for c in commits if c.get("autor") and c["autor"].lower() != "operacaoroot"})
        estranhos = [a for a in autores if esperado and a.lower() != esperado]
        if estranhos:
            r["alertas"].append("envio por conta que não é a do cliente: {}".format(", ".join("@" + a for a in estranhos)))
        modo = (progresso.get("acesso") or {}).get("modo")
        r["acesso"] = {"colaboradores": acesso["colaboradores"], "convites": [c["usuario"] for c in acesso["convites"]],
                       "autores": autores, "modo": modo}
        if esperado and modo == "chave":
            r["eventos"].append("ainda enviando pela chave do kit, sem a conta do GitHub")

    base = perfis["perfis"][m["perfil"]["escolhido"]]
    tom = (m["perfil"].get("ajustes") or {}).get("tom") or base["tom"]
    passos = progresso["passos"]
    feitos = [p for p in passos if p["feito"]]
    r.update({
        "kit_id": progresso.get("kit_id"),
        "feitos": len(feitos), "total": len(passos),
        "passo_atual": next((p["titulo"] for p in passos if not p["feito"]), None),
        "ultimo_envio": progresso.get("ultimo_envio"),
        "ultimo_commit": commits[0] if commits else None,
    })

    # selo: o kit_id que o repositório diz ter precisa ser o que a Root emitiu
    if progresso.get("kit_id") and progresso["kit_id"] != ent.get("kit_id"):
        r["alertas"].append("kit_id do repositório ({}) diferente do emitido ({})".format(progresso["kit_id"], ent.get("kit_id")))

    marcos = [parse_iso(p["feito_em"]) for p in feitos if p.get("feito_em")]
    referencia = max(marcos) if marcos else parse_iso(ent.get("montado_em"))
    dias = (agora() - referencia).days if referencia else 0
    r["dias_sem_avanco"] = dias
    if r["passo_atual"] and dias >= base["dias_sem_avanco_para_alerta"]:
        r["alertas"].append("parado há {} dias no passo \"{}\" (limite do perfil: {})".format(dias, r["passo_atual"], base["dias_sem_avanco_para_alerta"]))

    prazo_h = m.get("combinado", {}).get("prazo_resposta_horas", 4)
    abertas = [a for a in ajuda if a.get("estado") == "aberto"]
    for a in abertas:
        aberto = parse_iso(a.get("aberto_em"))
        horas = int((agora() - aberto).total_seconds() // 3600) if aberto else None
        a["horas_em_aberto"] = horas
        if horas is not None and horas >= prazo_h:
            r["alertas"].append("pedido de ajuda \"{}\" aberto há {}h (prazo {}h)".format(a.get("assunto", "?"), horas, prazo_h))
    r["ajuda_aberta"] = abertas

    antes = anterior.get(slug, {})
    feitos_antes = set(antes.get("feitos_ids", []))
    novos = [p for p in feitos if p["id"] not in feitos_antes]
    for p in novos:
        r["eventos"].append("concluiu \"{}\"".format(p["titulo"]))
    ferramentas = ler_catalogo(fonte, ent)
    r["ferramentas_do_cliente"] = ferramentas
    vistas = antes.get("ferramentas", {})
    rotulo = {"homologacao": "em teste na oficina", "ativa": "em uso", "aposentada": "aposentada"}
    for f in ferramentas:
        marca = "{}@{}".format(f["estado"], f["versao"])
        if f["nome"] not in vistas:
            r["eventos"].append("criou a ferramenta \"{}\" ({})".format(f["nome"], rotulo.get(f["estado"], f["estado"])))
        elif vistas[f["nome"]] != marca:
            r["eventos"].append("ferramenta \"{}\" agora {} (versão {})".format(f["nome"], rotulo.get(f["estado"], f["estado"]), f["versao"]))
    ajudas_antes = set(antes.get("ajudas", []))
    for a in abertas:
        if a["arquivo"] not in ajudas_antes:
            r["eventos"].append("novo pedido de ajuda: \"{}\"".format(a.get("assunto", "?")))
    r["_estado"] = {"feitos_ids": [p["id"] for p in feitos], "ajudas": [a["arquivo"] for a in abertas],
                    "ferramentas": {f["nome"]: "{}@{}".format(f["estado"], f["versao"]) for f in ferramentas},
                    "visto_em": agora().isoformat(timespec="seconds")}

    modelos = perfis["mensagens"].get(tom, perfis["mensagens"]["direto-com-contexto"])
    campos = {"nome": m["cliente"]["primeiro_nome"], "passo": r["passo_atual"] or "", "dias": dias,
              "prazo": "{} horas".format(prazo_h), "minutos": ""}
    if abertas:
        campos["assunto"] = abertas[0].get("assunto", "o seu pedido")
        r["mensagem_sugerida"] = modelos["ajuda"].format(**campos)
    elif r["passo_atual"] and dias >= base["dias_sem_avanco_para_alerta"]:
        r["mensagem_sugerida"] = modelos["parado"].format(**campos)
    elif novos and r["passo_atual"]:
        passos_json = json.loads((RAIZ / "modelo" / "passos.json").read_text(encoding="utf-8"))["passos"]
        prox = next((p for p in passos_json if p["titulo"] == r["passo_atual"]), None)
        campos.update({"passo": novos[-1]["titulo"], "proximo": r["passo_atual"], "minutos": prox["minutos"] if prox else "alguns"})
        r["mensagem_sugerida"] = modelos["avancou"].format(**campos)
    else:
        r["mensagem_sugerida"] = None
    return r


# ---------------------------------------------------------------- relatório

def relatorio_md(resultados):
    t = agora()
    out = ["# Acompanhamento dos kits · {}".format(t.strftime("%Y-%m-%d %H:%M")), ""]
    if not resultados:
        out.append("Nenhum kit entregue ainda.")
        return "\n".join(out) + "\n"
    atencao = [r for r in resultados if r["alertas"]]
    out.append("{} kit(s) acompanhado(s), {} pedindo atenção.".format(len(resultados), len(atencao)))
    out.append("")
    out.append("| Cliente | Passos | Passo atual | Dias sem avanço | Ajuda aberta | Último envio |")
    out.append("|---|---|---|---|---|---|")
    for r in resultados:
        if r.get("erro"):
            out.append("| {} | ? | {} | ? | ? | ? |".format(r["nome"], r["erro"]))
            continue
        out.append("| {} | {}/{} | {} | {} | {} | {} |".format(
            r["nome"], r["feitos"], r["total"], r["passo_atual"] or "todos feitos",
            r["dias_sem_avanco"], len(r["ajuda_aberta"]), r["ultimo_envio"] or "nunca"))
    for r in resultados:
        out += ["", "## {}".format(r["nome"])]
        if r["eventos"]:
            out.append("Desde a última rodada: " + "; ".join(r["eventos"]) + ".")
        for a in r["alertas"]:
            out.append("- ATENÇÃO: " + a)
        fs = r.get("ferramentas_do_cliente", [])
        if fs:
            em_uso = sum(1 for f in fs if f["estado"] == "ativa")
            em_teste = sum(1 for f in fs if f["estado"] == "homologacao")
            out.append("- Ferramentas criadas pelo cliente: {} em uso, {} em teste ({}).".format(
                em_uso, em_teste, ", ".join(f["nome"] for f in fs if f["estado"] != "aposentada")))
        for a in r.get("ajuda_aberta", []):
            out.append("- Pedido aberto: \"{}\" ({}, {}h)".format(a.get("assunto", "?"), a["arquivo"], a.get("horas_em_aberto", "?")))
        ac = r.get("acesso")
        if ac:
            quem = ", ".join("@" + c for c in ac["colaboradores"]) or "nenhum colaborador ainda"
            pend = "; convite pendente para " + ", ".join("@" + c for c in ac["convites"]) if ac["convites"] else ""
            out.append("- Acesso: {}{} · ligado por {}".format(quem, pend, ac["modo"] or "?"))
        if r.get("mensagem_sugerida"):
            out += ["", "Mensagem sugerida (revisar antes de mandar):", "", "> " + r["mensagem_sugerida"]]
        if not r["eventos"] and not r["alertas"]:
            out.append("Sem novidade e sem alerta.")
    return "\n".join(out) + "\n"


def main(argv):
    perfis = json.loads((RAIZ / "perfis" / "perfis.json").read_text(encoding="utf-8"))
    anterior = json.loads(ESTADO.read_text(encoding="utf-8")) if ESTADO.exists() else {}
    filtro = [a for a in argv[1:] if not a.startswith("--")]
    resultados = []
    for arq in sorted((RAIZ / "manifestos").glob("*.json")):
        if arq.name.startswith("_"):
            continue
        m = json.loads(arq.read_text(encoding="utf-8"))
        if not m.get("entrega", {}).get("kit_id") or m["entrega"].get("rascunho"):
            continue
        if filtro and m["cliente"]["slug"] not in filtro:
            continue
        resultados.append(analisar(m, perfis, anterior))

    for r in resultados:
        if "_estado" in r:
            anterior[r["slug"]] = r.pop("_estado")
    ESTADO.write_text(json.dumps(anterior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if "--json" in argv:
        print(json.dumps(resultados, ensure_ascii=False, indent=2, default=str))
        return 0
    texto = relatorio_md(resultados)
    SAIDA.mkdir(parents=True, exist_ok=True)
    destino = SAIDA / (agora().strftime("%Y-%m-%d-%H%M") + ".md")
    destino.write_text(texto, encoding="utf-8")
    print(texto)
    print("Relatório gravado em", destino)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
