#!/usr/bin/env python3
"""Monta o kit de um cliente a partir do manifesto.

Uso:
    python3 montador/montar.py manifestos/<cliente>.json [opções]

Opções:
    --rascunho          monta mesmo sem os portões (perfil assinado, reuniões conferidas);
                        o kit sai marcado como RASCUNHO e não pode ir para o GitHub nem virar zip
    --permitir-semente  aceita receita em estado de semente
    --refazer           apaga saida/<slug>/ antes de montar (só dentro de saida/)
    --github            cria o repositório privado operacaoroot/kit-<slug>, cadastra a chave do kit
                        como deploy key com escrita e envia o primeiro commit usando a própria chave
    --zip               gera saida/<slug>.zip, que é o que vai para o cliente (leva a chave)

O montador é determinístico: o mesmo manifesto gera o mesmo kit (a não ser pelo
kit_id, a chave e as datas). Nenhum modelo de IA é chamado aqui.
Só biblioteca padrão, compatível com Python 3.9.
"""
import datetime as dt
import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MODELO = RAIZ / "modelo"
RECEITAS = RAIZ / "receitas"
SAIDA = RAIZ / "saida"
DONO_GITHUB = "operacaoroot"
CONFIG_ROOT = Path.home() / ".config" / "root"

PASTAS_DO_VAULT = {
    "10-Identidade": "quem é, o que faz, voz e vocabulário",
    "30-Organizacao": "pessoas e empresas com quem trabalha",
    "40-Operacao": "como o trabalho é feito e os resultados da frente",
    "50-Projetos": "projetos em andamento",
    "60-Decisoes": "decisões, uma por nota",
    "70-Dados": "números de referência e de onde vêm",
    "90-Metas": "o que quer alcançar e até quando",
}

NIVEL = {
    "guiado": ("Guiado", "Explique cada clique e cada termo novo na primeira vez que aparecer, descreva onde fica na tela e confirme se deu certo antes de seguir."),
    "chat": ("Usuário de chat", "Dê o passo em duas ou três frases, com o porquê em uma delas. Termo técnico só com uma explicação curta."),
    "construtor": ("Construtor", "Vá direto ao comando ou ao pedido. Explique só se perguntarem."),
}
TOM = {"explicado": "explicado", "direto-com-contexto": "direto, com contexto", "direto": "direto"}
FORMATO = {"com-print": "passo a passo dizendo onde clicar", "passo-curto-com-porque": "passo curto com o porquê", "passo-curto": "passo curto"}
INICIATIVA = {
    "sempre": "sugira o próximo passo e melhorias sempre que fizer sentido, no fim da resposta, em uma linha.",
    "as-vezes": "sugira só quando vir algo importante, como um erro que vai se repetir ou uma economia de tempo clara.",
    "quando-pedido": "não sugira nada por conta própria; responda ao que foi pedido.",
}


class Recusa(Exception):
    pass


def ler_json(caminho):
    return json.loads(Path(caminho).read_text(encoding="utf-8"))


def render(texto, ctx):
    def troca(m):
        chave = m.group(1)
        if chave not in ctx:
            raise Recusa("campo {{%s}} usado no modelo e ausente no contexto" % chave)
        return str(ctx[chave])
    return re.sub(r"\{\{([a-z_]+)\}\}", troca, texto)


# ---------------------------------------------------------------- portões

def conferir_manifesto(m, perfis, rascunho, permitir_semente):
    faltas = []
    c = m.get("cliente", {})
    for campo in ["slug", "nome", "primeiro_nome", "empresa", "cargo", "sistema"]:
        if not c.get(campo):
            faltas.append("cliente.%s" % campo)
    if c.get("slug") and not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", c["slug"]):
        faltas.append("cliente.slug só com minúsculas, números e hífen")
    if c.get("sistema") not in ("mac", "windows", "linux"):
        faltas.append("cliente.sistema deve ser mac, windows ou linux")
    p = m.get("perfil", {})
    if p.get("escolhido") not in perfis["perfis"]:
        faltas.append("perfil.escolhido deve ser um de: " + ", ".join(perfis["perfis"]))
    frente = m.get("frente", [])
    if not 1 <= len(frente) <= 3:
        faltas.append("frente precisa de 1 a 3 receitas")
    for chave in frente:
        arq = RECEITAS / chave / "receita.json"
        if not arq.exists():
            faltas.append("receita inexistente: %s" % chave)
            continue
        if ler_json(arq)["estado"] != "inteira" and not permitir_semente:
            faltas.append("receita %s ainda é semente (use --permitir-semente para testar)" % chave)
    if faltas:
        raise Recusa("manifesto incompleto:\n  - " + "\n  - ".join(faltas))

    portoes = []
    if not p.get("conferido_por"):
        portoes.append("nenhum sócio assinou o perfil (perfil.conferido_por)")
    conf = m.get("conferencia_das_reunioes", {})
    if not conf.get("feita_por"):
        portoes.append("as reuniões ainda não foram conferidas (conferencia_das_reunioes.feita_por)")
    if conf.get("divergencias_em_aberto"):
        portoes.append("há divergência em aberto entre as reuniões e o manifesto")
    sem_prova = [n.get("titulo", "?") for n in m.get("notas_iniciais", []) if not n.get("fonte")]
    if sem_prova:
        portoes.append("nota inicial sem fonte: " + ", ".join(sem_prova))
    if portoes and not rascunho:
        raise Recusa("portão fechado:\n  - " + "\n  - ".join(portoes) + "\nResolva ou monte com --rascunho.")
    return portoes


# ---------------------------------------------------------------- contexto

def montar_contexto(m, perfis, kit_id):
    c, p = m["cliente"], m["perfil"]
    base = perfis["perfis"][p["escolhido"]]
    aj = p.get("ajustes", {}) or {}
    nivel = base["nivel_do_texto"]
    tom = aj.get("tom") or base["tom"]
    formato = aj.get("formato") or base["formato"]
    iniciativa = aj.get("iniciativa_claude") or base["iniciativa_claude"]
    passos_dia = aj.get("passos_por_dia") or base["passos_por_dia"]
    receitas = [ler_json(RECEITAS / k / "receita.json") for k in m["frente"]]
    reunioes = m.get("reunioes", [])
    reunioes_texto = ", ".join("{} de {}".format(r.get("tipo", "reunião"), r.get("data", "?")) for r in reunioes) or "as conversas com a Root"
    restricoes = p.get("restricoes", [])
    catalogo = {s["id"]: s for s in perfis["sinais"]}
    sinais_txt = "\n".join(
        "- {} ({}: \"{}\")".format(catalogo.get(s["id"], {}).get("descricao", s["id"]), s.get("minuto", "?"), s.get("trecho", ""))
        for s in p.get("sinais", [])
    ) or "- Nenhum sinal registrado. O perfil é o padrão até você configurar."
    skills_base = [
        ("perfil-de-interacao", "como falar com a pessoa; ajustar a pedido"),
        ("proximo-passo", "onde a pessoa está e o que vem agora"),
        ("cuidar-do-vault", "notas do Obsidian com cabeçalho e fonte"),
        ("extrair-contexto", "o histórico de IA vira notas com fonte, sem sair da máquina"),
        ("pedir-ajuda", "registra o pedido para a Root"),
        ("fechar-o-dia", "salva, envia o progresso e traz atualizações"),
    ]
    linhas = ["**Base (todo kit tem):**", ""]
    linhas += ["- `{}`: {}".format(n, d) for n, d in skills_base]
    linhas += ["", "**Frente ({}):**".format(", ".join(r["nome"] for r in receitas)), ""]
    for r in receitas:
        for s in r["skills"]:
            linhas.append("- `{}`: da frente \"{}\". {}".format(s, r["nome"], r["dor"]))
    linhas += ["", "Agente: `auditor-de-contexto` (confere o pacote do histórico de IA)."]
    como_pedir = "\n".join("- " + ped for r in receitas for ped in r["como_pedir"])
    comb = m.get("combinado", {})
    kickoff = m.get("kickoff", {})
    return {
        "nome": c["nome"], "primeiro_nome": c["primeiro_nome"], "empresa": c["empresa"], "cargo": c["cargo"],
        "kit_id": kit_id, "hoje": dt.date.today().isoformat(), "versao_modelo": ler_json(MODELO / "passos.json")["versao"],
        "perfil_id": p["escolhido"], "nivel": nivel, "nivel_nome": NIVEL[nivel][0], "nivel_regra": NIVEL[nivel][1],
        "tom": TOM.get(tom, tom), "formato": FORMATO.get(formato, formato), "tom_id": tom, "formato_id": formato,
        "iniciativa": iniciativa, "iniciativa_regra": INICIATIVA[iniciativa],
        "passos_por_dia": passos_dia, "passos_por_dia_texto": "1 passo" if passos_dia == 1 else "{} passos".format(passos_dia), "horario": aj.get("horario") or "no horário que for melhor",
        "como_aprende": aj.get("como_aprende") or "fazendo",
        "data_kickoff": kickoff.get("data", "?"),
        "sinais_texto": sinais_txt,
        "restricoes_lista": "\n".join("- " + r for r in restricoes) or "- Nenhuma restrição registrada.",
        "restricoes_texto": ("\n- **Restrições combinadas:** " + "; ".join(restricoes) + ".") if restricoes else "",
        "lista_de_skills": "\n".join(linhas),
        "como_pedir": como_pedir,
        "frente_nomes": " e ".join(r["nome"] for r in receitas),
        "reunioes_texto": reunioes_texto,
        "canal_de_ajuda": comb.get("canal_de_ajuda", "o canal combinado"),
        "prazo_resposta_horas": comb.get("prazo_resposta_horas", 4),
        "horarios_acompanhamento": ", ".join(comb.get("horarios_acompanhamento", ["08:30", "13:00", "18:00"])),
        "total_passos": len(ler_json(MODELO / "passos.json")["passos"]),
    }, receitas


# ---------------------------------------------------------------- peças

def comece_aqui(ctx, sistema, perfil_id):
    passos = ler_json(MODELO / "passos.json")["passos"]
    nivel = ctx["nivel"]
    abertura = {
        "guiado": "São {} passos. Faça um por dia, no seu tempo. Cada passo diz quanto tempo leva e como saber que deu certo. Se travar, peça ajuda ao Claude do kit: ele registra o pedido e a Root responde.",
        "chat": "São {} passos, cada um com tempo estimado e a prova de que deu certo. O Claude do kit sabe em que passo você está: pergunte \"qual o próximo passo\".",
        "construtor": "{} passos. Prova de cada um em `ferramentas/verificar.py`.",
    }[nivel].format(len(passos))
    out = ["# Comece aqui", "", "Kit de {} · {}".format(ctx["nome"], ctx["hoje"]), "", abertura, ""]
    for i, p in enumerate(passos, 1):
        out.append("## {}. {} (cerca de {} min)".format(i, p["titulo"], p["minutos"]))
        out.append("")
        out.append(p["texto"][nivel])
        out.append("")
        out.append("**Como fazer:** " + p["comando"][sistema])
        out.append("")
        out.append("**Pronto quando:** " + p["prova"] + ".")
        if perfil_id in p.get("ao_vivo_para", []):
            out.append("")
            out.append("Na primeira vez, este passo é feito junto com a Root, numa chamada.")
        out.append("")
    out.append("Kit `{}`".format(ctx["kit_id"]))
    return "\n".join(out) + "\n"


def nota_md(pasta, titulo, kind, corpo, fonte, nome, hoje):
    return "---\nkind: {}\ndono: {}\nvalido_de: {}\nfonte: {}\nrevisar: sim\n---\n\n# {}\n\n{}\n".format(kind, nome, hoje, fonte, titulo, corpo)


def nome_de_arquivo(titulo):
    return re.sub(r'[\\/:*?"<>|]', "-", titulo).strip() + ".md"


def escrever_vault(destino, m, receitas, ctx):
    vault = destino / "vault"
    notas = []
    for n in m.get("notas_iniciais", []):
        notas.append((n["pasta"], n["titulo"], n.get("kind", "nota"), n["corpo"], n["fonte"]))
    for r in receitas:
        for n in r.get("notas_do_vault", []):
            notas.append((n["pasta"], n["titulo"], n.get("kind", "nota"), n["corpo"], "receita {} do kit".format(r["chave"])))
    por_pasta = {p: [] for p in PASTAS_DO_VAULT}
    for pasta, titulo, kind, corpo, fonte in notas:
        if pasta not in PASTAS_DO_VAULT:
            raise Recusa("nota '{}' em pasta desconhecida: {}".format(titulo, pasta))
        (vault / pasta).mkdir(parents=True, exist_ok=True)
        (vault / pasta / nome_de_arquivo(titulo)).write_text(
            nota_md(pasta, titulo, kind, corpo, fonte, ctx["nome"], ctx["hoje"]), encoding="utf-8")
        por_pasta[pasta].append(titulo)
    for pasta, descricao in PASTAS_DO_VAULT.items():
        (vault / pasta).mkdir(parents=True, exist_ok=True)
        itens = "\n".join("- [[{}/{}]]".format(pasta, t) for t in por_pasta[pasta]) or "- (ainda vazia)"
        (vault / pasta / "Índice.md").write_text(
            "---\nkind: nota\ndono: {}\nvalido_de: {}\nfonte: montador do kit\nrevisar: não\n---\n\n# {}\n\nGuarda {}.\n\n{}\n".format(
                ctx["nome"], ctx["hoje"], pasta, descricao, itens), encoding="utf-8")
    indice = "\n".join("- [[{}/{}]] (revisar)".format(p, t) for p in PASTAS_DO_VAULT for t in por_pasta[p]) or "- Nenhuma nota ainda."
    return indice


def assinar(dados):
    segredo = os.environ.get("KIT_SELO_SEGREDO")
    arq = CONFIG_ROOT / "kit.env"
    if not segredo and arq.exists():
        for linha in arq.read_text().splitlines():
            if linha.startswith("KIT_SELO_SEGREDO="):
                segredo = linha.split("=", 1)[1].strip()
    if not segredo:
        segredo = uuid.uuid4().hex + uuid.uuid4().hex
        CONFIG_ROOT.mkdir(parents=True, exist_ok=True)
        with open(arq, "a") as f:
            f.write("# Segredo do selo dos kits de cliente (montador e acompanhador). Nunca versionar.\nKIT_SELO_SEGREDO=%s\n" % segredo)
        os.chmod(arq, 0o600)
        print("Segredo do selo criado em", arq)
    canon = json.dumps(dados, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hmac.new(segredo.encode(), canon.encode(), hashlib.sha256).hexdigest()


def rodar(cmd, cwd, env=None):
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, env=env)
    if r.returncode != 0:
        msg = "falhou: {}\n{}".format(" ".join(cmd), (r.stderr or r.stdout).strip())
        raise Recusa(re.sub(r"x-access-token:[^@\s]+@", "x-access-token:***@", msg))
    return r.stdout.strip()


# ---------------------------------------------------------------- GitHub

def token_github():
    tok = os.environ.get("ROOT_GITHUB_TOKEN")
    arq = CONFIG_ROOT / "github.env"
    if not tok and arq.exists():
        for linha in arq.read_text().splitlines():
            linha = linha.strip()
            if linha.startswith("export "):
                linha = linha[7:]
            if linha.startswith("ROOT_GITHUB_TOKEN="):
                tok = linha.split("=", 1)[1].strip().strip('"').strip("'")
    if not tok:
        raise Recusa("sem ROOT_GITHUB_TOKEN (conta operacaoroot) em ~/.config/root/github.env")
    return tok


def api(metodo, caminho, corpo=None):
    req = urllib.request.Request("https://api.github.com" + caminho, method=metodo,
                                 data=json.dumps(corpo).encode() if corpo is not None else None)
    req.add_header("Authorization", "Bearer " + token_github())
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            txt = r.read().decode()
            return r.status, (json.loads(txt) if txt else {})
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def publicar_no_github(destino, slug, nome):
    repo = "kit-" + slug
    status, _ = api("GET", "/repos/{}/{}".format(DONO_GITHUB, repo))
    if status == 200:
        raise Recusa("o repositório {}/{} já existe; não sobrescrevo kit publicado".format(DONO_GITHUB, repo))
    status, corpo = api("POST", "/user/repos", {
        "name": repo, "private": True, "auto_init": False,
        "description": "Kit de {} (Root). Privado.".format(nome),
        "has_issues": False, "has_wiki": False, "has_projects": False})
    if status not in (201,):
        raise Recusa("não criei o repositório: {} {}".format(status, corpo.get("message")))
    pub = (destino / ".root" / "chave.pub").read_text().strip()
    status, corpo = api("POST", "/repos/{}/{}/keys".format(DONO_GITHUB, repo),
                        {"title": "chave do kit ({})".format(slug), "key": pub, "read_only": False})
    if status != 201:
        raise Recusa("não cadastrei a chave do kit: {} {}".format(status, corpo.get("message")))
    env = dict(os.environ)
    env["GIT_SSH_COMMAND"] = 'ssh -i "{}" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new'.format(destino / ".root" / "chave")
    rodar(["git", "push", "-u", "origin", "main"], destino, env)
    return "{}/{}".format(DONO_GITHUB, repo)


# ---------------------------------------------------------------- montagem

def montar(caminho_manifesto, opcoes):
    perfis = ler_json(RAIZ / "perfis" / "perfis.json")
    m = ler_json(caminho_manifesto)
    rascunho = "--rascunho" in opcoes
    portoes = conferir_manifesto(m, perfis, rascunho, "--permitir-semente" in opcoes)
    if rascunho and ("--github" in opcoes or "--zip" in opcoes):
        raise Recusa("kit em rascunho não vai para o GitHub nem vira zip")
    slug, sistema = m["cliente"]["slug"], m["cliente"]["sistema"]
    destino = SAIDA / slug
    if destino.exists():
        if "--refazer" not in opcoes:
            raise Recusa("{} já existe; use --refazer".format(destino))
        shutil.rmtree(destino)
    kit_id = "kit-" + uuid.uuid4().hex[:12]
    ctx, receitas = montar_contexto(m, perfis, kit_id)

    ignorar = shutil.ignore_patterns("*.tmpl", "passos.json", ".DS_Store", "__pycache__")
    shutil.copytree(MODELO, destino, ignore=ignorar)
    shutil.copy2(MODELO / "passos.json", destino / "ferramentas" / "passos.json")
    for tmpl in MODELO.rglob("*.tmpl"):
        rel = tmpl.relative_to(MODELO).with_suffix("")
        (destino / rel).parent.mkdir(parents=True, exist_ok=True)
        if rel.name == "00 - Comece aqui.md":
            continue
        (destino / rel).write_text(render(tmpl.read_text(encoding="utf-8"), ctx), encoding="utf-8")

    registrar = (RECEITAS / "_comum" / "registrar-resultado.md").read_text(encoding="utf-8")
    for r in receitas:
        for s in r["skills"]:
            origem = RECEITAS / r["chave"] / "skills" / s
            alvo = destino / ".claude" / "skills" / s
            shutil.copytree(origem, alvo)
            skill_md = alvo / "SKILL.md"
            skill_md.write_text(skill_md.read_text(encoding="utf-8").replace("{{registrar_resultado}}", registrar), encoding="utf-8")

    ctx["indice_notas"] = escrever_vault(destino, m, receitas, ctx)
    comece_tmpl = (MODELO / "vault" / "00 - Comece aqui.md.tmpl").read_text(encoding="utf-8")
    (destino / "vault" / "00 - Comece aqui.md").write_text(render(comece_tmpl, ctx), encoding="utf-8")
    (destino / "COMECE-AQUI.md").write_text(comece_aqui(ctx, sistema, m["perfil"]["escolhido"]), encoding="utf-8")

    for skill_md in (destino / ".claude").rglob("*.md"):
        skill_md.write_text(skill_md.read_text(encoding="utf-8").rstrip() + "\n\n<!-- {} -->\n".format(kit_id), encoding="utf-8")

    if sistema == "windows":
        for arq in list(destino.rglob("*.md")):
            arq.write_text(arq.read_text(encoding="utf-8").replace("python3 ferramentas/", "py ferramentas/"), encoding="utf-8")

    if rascunho:
        aviso = "> **RASCUNHO**: montado com portão aberto ({}). Não entregar ao cliente.\n\n".format("; ".join(portoes))
        for nome in ["README.md", "COMECE-AQUI.md"]:
            arq = destino / nome
            arq.write_text(aviso + arq.read_text(encoding="utf-8"), encoding="utf-8")

    emitido = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    ident = {"kit_id": kit_id, "slug": slug, "nome": m["cliente"]["nome"], "emitido_em": emitido}
    cliente = dict(ident)
    cliente.update({
        "modelo": ctx["versao_modelo"], "perfil": m["perfil"]["escolhido"], "frente": m["frente"],
        "repo": "{}/kit-{}".format(DONO_GITHUB, slug), "rascunho": rascunho,
        "selo": assinar(ident),
        "aviso": "Kit pessoal montado pela Root para {}. A chave em .root/chave é deste kit e só dele.".format(m["cliente"]["nome"]),
    })
    (destino / ".root").mkdir(exist_ok=True)
    (destino / ".root" / "cliente.json").write_text(json.dumps(cliente, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rodar(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "{} ({})".format(kit_id, slug), "-f", str(destino / ".root" / "chave")], destino)
    rodar(["git", "init", "-q", "-b", "main"], destino)
    rodar(["git", "config", "user.name", "Root (montador de kits)"], destino)
    rodar(["git", "config", "user.email", "kits@operacaoroot.com"], destino)
    rodar(["python3", "ferramentas/verificar.py", "--silencioso", "--sem-rede"], destino)
    rodar(["git", "add", "-A"], destino)
    versionados = rodar(["git", "ls-files"], destino).splitlines()
    if any(v.startswith(".root/chave") for v in versionados):
        raise Recusa("a chave entrou no git; o .gitignore do modelo está quebrado")
    rodar(["git", "commit", "-q", "-m", "Kit de {} montado pela Root ({})".format(m["cliente"]["nome"], kit_id)], destino)
    rodar(["git", "remote", "add", "origin", "git@github.com:{}/kit-{}.git".format(DONO_GITHUB, slug)], destino)

    repo = None
    if "--github" in opcoes:
        repo = publicar_no_github(destino, slug, m["cliente"]["nome"])
    zip_path = None
    if "--zip" in opcoes:
        zip_path = shutil.make_archive(str(SAIDA / slug), "zip", root_dir=str(SAIDA), base_dir=slug)

    m.setdefault("entrega", {})
    m["entrega"].update({"kit_id": kit_id, "montado_em": emitido, "local": str(destino),
                         "repo": "{}/kit-{}".format(DONO_GITHUB, slug), "publicado": bool(repo),
                         "zip": zip_path, "rascunho": rascunho})
    Path(caminho_manifesto).write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("Kit montado: {}".format(destino))
    print("  kit_id: {} · perfil: {} · frente: {}".format(kit_id, m["perfil"]["escolhido"], ", ".join(m["frente"])))
    print("  arquivos versionados: {}".format(len(versionados)))
    if rascunho:
        print("  RASCUNHO: " + "; ".join(portoes))
    if repo:
        print("  publicado em github.com/{} com a chave do kit".format(repo))
    if zip_path:
        print("  zip para o cliente: {} (leva a chave; mandar por canal privado)".format(zip_path))
    return destino


def main(argv):
    if len(argv) < 2 or argv[1].startswith("--"):
        print(__doc__)
        return 2
    try:
        montar(argv[1], set(argv[2:]))
    except Recusa as e:
        print("RECUSADO:", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
