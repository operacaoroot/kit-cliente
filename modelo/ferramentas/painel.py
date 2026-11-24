#!/usr/bin/env python3
"""Painel da instalação: a página que mostra à pessoa o que o kit está fazendo no computador dela.

Uso (na pasta do kit; os instaladores chamam sozinhos):
    python3 ferramentas/painel.py iniciar [--abrir]          # começa uma instalação nova no painel
    python3 ferramentas/painel.py etapa <id> <estado> [texto] # estado: andamento, ok, atencao, falhou
    python3 ferramentas/painel.py evento <texto> [--tipo ok|aviso|info]
    python3 ferramentas/painel.py concluir [--abrir] [--sem-rede]  # confere o que ficou pronto e o que falta
    python3 ferramentas/painel.py abrir                      # abre a página no navegador
    python3 ferramentas/painel.py caminho                    # mostra onde a página está

A página é estática (painel/index.html) e abre direto do disco, sem servidor e sem porta: ela lê
`_privado/painel/estado.js`, que este script reescreve a cada mudança. Por isso funciona antes de
qualquer programa estar instalado e continua aberta depois que o instalador fecha.

O painel nunca derruba a instalação: se algo der errado ao gravar, o instalador segue.
Só biblioteca padrão, compatível com Python 3.9.
"""
import datetime as dt
import json
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from urllib.parse import quote, urlencode

KIT = Path(__file__).resolve().parent.parent
PASTA = ESTADO = ESTADO_JS = PAGINA = None


def usar_kit(kit):
    """Aponta o painel para a pasta de um kit (o padrão é o kit onde este arquivo está)."""
    global KIT, PASTA, ESTADO, ESTADO_JS, PAGINA
    KIT = Path(kit).resolve()
    PASTA = KIT / "_privado" / "painel"
    ESTADO = PASTA / "estado.json"
    ESTADO_JS = PASTA / "estado.js"
    PAGINA = KIT / "painel" / "index.html"


usar_kit(KIT)
LIMITE_EVENTOS = 300
ESTADOS = ("pendente", "andamento", "ok", "atencao", "falhou")

ETAPAS = [
    ("basico", "Ferramentas básicas do sistema", "Git, Python e o instalador de programas."),
    ("programas", "Programas do kit", "Claude Code, Obsidian, Node.js, Java e o que o seu perfil pede."),
    ("python", "Python do kit", "O ambiente Python só do kit, com as bibliotecas que as ferramentas usam."),
    ("autonomia", "Claude liberado para trabalhar", "O Claude passa a agir no seu computador sem pedir permissão a cada passo."),
    ("chave", "Kit ligado à Root", "Pela chave que já veio no kit. Não precisa de conta nem de código do GitHub."),
    ("atalho", "Atalhos na Mesa", "Claude do kit e Painel do kit, para abrir com dois cliques."),
    ("conferencia", "Conferência final", "O kit confere o que ficou pronto e lista o que falta."),
]


def agora():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def sistema():
    return {"darwin": "mac", "win32": "windows"}.get(sys.platform, "linux")


def ler_json(caminho, padrao=None):
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return padrao if padrao is not None else {}


def link_claude(mensagem=""):
    return "claude://code/new?" + urlencode({"folder": str(KIT), "q": mensagem}, quote_via=quote)


def link_obsidian():
    return "obsidian://open?" + urlencode({"path": str(KIT / "vault")}, quote_via=quote)


def estado_novo():
    cliente = ler_json(KIT / ".root" / "cliente.json")
    return {
        "versao": 1,
        "nome": cliente.get("nome", ""),
        "pasta": str(KIT),
        "vault": str(KIT / "vault"),
        "sistema": sistema(),
        "fase": "instalando",
        "inicio": agora(),
        "atualizado": agora(),
        "agora": "Começando a preparar o seu computador.",
        "etapas": [{"id": i, "titulo": t, "explica": e, "estado": "pendente", "detalhe": ""} for i, t, e in ETAPAS],
        "eventos": [],
        "conferencia": None,
        "links": {"claude": link_claude(), "obsidian": link_obsidian()},
    }


def carregar():
    estado = ler_json(ESTADO)
    return estado if estado.get("versao") == 1 else None


def gravar(estado):
    """Grava o JSON e o JS da página. No Windows o navegador pode estar lendo o arquivo: tenta de novo."""
    estado["atualizado"] = agora()
    PASTA.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(estado, ensure_ascii=False, indent=1)
    # O estado vira JS para a página abrir do disco (file://), onde o navegador não deixa ler JSON.
    script = "window.KIT_PAINEL = " + texto.replace("</", "<\\/") + ";\n"
    for destino, conteudo in ((ESTADO, texto + "\n"), (ESTADO_JS, script)):
        tmp = destino.with_name(destino.name + ".tmp")
        tmp.write_text(conteudo, encoding="utf-8")
        for tentativa in range(10):
            try:
                os.replace(str(tmp), str(destino))
                break
            except PermissionError:
                time.sleep(0.1 * (tentativa + 1))
        else:
            try:
                tmp.unlink()
            except OSError:
                pass


def registrar(texto, tipo="info", estado=None):
    estado = estado or carregar()
    if not estado:
        return None
    estado["eventos"].append({"em": dt.datetime.now().strftime("%H:%M:%S"), "texto": str(texto)[:400], "tipo": tipo})
    estado["eventos"] = estado["eventos"][-LIMITE_EVENTOS:]
    if tipo != "ok":
        estado["agora"] = str(texto)[:400]
    return estado


# ---------------------------------------------------------------- uso por outras ferramentas

def evento(texto, tipo="info"):
    """Para o ambiente.py e outras ferramentas: só escreve durante uma instalação em andamento.

    Depois de concluída, uma conferência avulsa (o Claude rodando ambiente.py semanas depois) não
    reescreve o que a página mostra.
    """
    try:
        estado = carregar()
        if estado and estado.get("fase") == "instalando":
            gravar(registrar(texto, tipo, estado))
    except Exception:  # o painel é só vitrine: nunca derruba a instalação
        pass


def etapa(etapa_id, situacao, detalhe=""):
    try:
        estado = carregar()
        if not estado or estado.get("fase") != "instalando":
            return
        marcar(estado, etapa_id, situacao, detalhe)
        gravar(estado)
    except Exception:
        pass


def marcar(estado, etapa_id, situacao, detalhe=""):
    if situacao not in ESTADOS:
        raise ValueError("estado desconhecido: " + situacao)
    for e in estado["etapas"]:
        if e["id"] == etapa_id:
            e["estado"] = situacao
            if detalhe:
                e["detalhe"] = detalhe
            if situacao == "andamento":
                e["inicio"] = agora()
                registrar("{}: {}".format(e["titulo"], detalhe or "começando"), "info", estado)
            elif situacao in ("ok", "atencao", "falhou"):
                e["fim"] = agora()
                registrar("{}: {}".format(e["titulo"], detalhe or "pronto"),
                          {"ok": "ok", "atencao": "aviso", "falhou": "aviso"}[situacao], estado)
            return
    raise ValueError("etapa desconhecida: " + etapa_id)


# ---------------------------------------------------------------- conferência

def rodar(cmd, timeout=40):
    try:
        r = subprocess.run(cmd, cwd=str(KIT), capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout)
        return r.returncode, (r.stdout or "").strip()
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""


def conferir(sem_rede=False):
    """O que ficou pronto e o que falta, em frases para a pessoa. Não mostra saída de comando."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import ambiente  # noqa: E402  (mesma pasta)
    feito, falta = [], []
    conf = ambiente.conferir(ambiente.perfil_do_kit())
    for app in conf["apps"]:
        if app["instalado"] and app["nivel"] != "opcional":
            feito.append("{} instalado".format(app["nome"]))
        elif not app["instalado"] and app["nivel"] == "obrigatorio":
            falta.append("{} não ficou instalado. Rode o instalador de novo; se repetir, peça ajuda à Root.".format(app["nome"]))
        elif not app["instalado"] and app["nivel"] == "recomendado":
            falta.append("{} (recomendado) ainda não está instalado: {}.".format(app["nome"], app["para_que"]))
    venv = conf["venv"]["detalhe"]
    (feito if conf["venv"]["pronto"] else falta).append(venv[:1].upper() + venv[1:])
    _, remoto = rodar(["git", "remote", "get-url", "origin"])
    ligado = False
    if (KIT / ".root" / "chave").exists() and remoto.startswith("git@") and sem_rede:
        ligado = True
        feito.append("Kit ligado à Root pela chave do kit (conexão não testada)")
    elif (KIT / ".root" / "chave").exists() and remoto.startswith("git@"):
        codigo, _ = rodar(["git", "ls-remote", "--exit-code", "origin", "HEAD"], timeout=30)
        ligado = codigo == 0
        if ligado:
            feito.append("Kit conectado à Root pela chave do kit")
        else:
            falta.append("O kit não conseguiu falar com a Root agora. Confira a internet e rode o instalador de novo.")
    else:
        falta.append("O kit ainda não está ligado à Root. Rode o instalador de novo; se repetir, peça ajuda à Root.")
    pronto = not conf["faltam_obrigatorios"] and conf["venv"]["pronto"] and ligado
    return {"feito": feito, "falta": falta, "pronto": pronto, "conferido_em": agora()}


def iniciar():
    """Começa uma instalação nova no painel (apaga o andamento anterior)."""
    estado = estado_novo()
    gravar(estado)
    return estado


def concluir(sem_rede=False):
    """Roda a conferência, fecha a etapa final e diz se o kit ficou pronto."""
    estado = carregar() or estado_novo()
    marcar(estado, "conferencia", "andamento", "conferindo o computador e a ligação com a Root")
    gravar(estado)
    try:
        estado["conferencia"] = conferir(sem_rede)
    except Exception:  # a página nunca fica parada em "instalando" por causa da conferência
        estado["conferencia"] = {"feito": [], "pronto": False, "conferido_em": agora(),
                                 "falta": ["Não consegui conferir o computador. Peça ao Claude: \"confere o meu computador\"."]}
    pronto = estado["conferencia"]["pronto"]
    estado["fase"] = "pronto" if pronto else "atencao"
    marcar(estado, "conferencia", "ok" if pronto else "atencao",
           "tudo pronto" if pronto else "{} ponto(s) para resolver".format(len(estado["conferencia"]["falta"])))
    estado["agora"] = ("Instalação concluída. Siga os próximos passos abaixo." if pronto
                       else "Instalação concluída com pendências. Veja o que falta abaixo.")
    gravar(estado)
    return estado


# ---------------------------------------------------------------- linha de comando

def abrir():
    if not PAGINA.exists():
        print("A página do painel não está no kit (painel/index.html).")
        return 1
    url = PAGINA.as_uri()
    try:
        if sys.platform == "darwin":
            subprocess.call(["open", url])
        elif sys.platform == "win32":
            os.startfile(str(PAGINA))  # noqa: abre no navegador padrão do Windows
        else:
            webbrowser.open(url)
    except OSError:
        print("Abra no navegador: " + url)
    return 0


def texto_de(args):
    partes = [a for a in args if not a.startswith("--")]
    return " ".join(partes).strip()


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    comando, resto = argv[1], argv[2:]
    tipo = "info"
    if "--tipo" in resto:
        i = resto.index("--tipo")
        tipo = resto[i + 1] if i + 1 < len(resto) else "info"
        resto = resto[:i] + resto[i + 2:]
    try:
        if comando == "iniciar":
            iniciar()
            return abrir() if "--abrir" in resto else 0
        if comando == "concluir":
            concluir("--sem-rede" in resto)
            return abrir() if "--abrir" in resto else 0
        if comando == "caminho":
            print(PAGINA)
            return 0
        if comando == "abrir":
            return abrir()
        estado = carregar() or estado_novo()
        if comando == "etapa":
            if len(resto) < 2:
                raise ValueError("use: etapa <id> <estado> [texto]")
            marcar(estado, resto[0], resto[1], texto_de(resto[2:]))
        elif comando == "evento":
            registrar(texto_de(resto), tipo if tipo in ("ok", "aviso", "info") else "info", estado)
        else:
            print(__doc__)
            return 2
        gravar(estado)
        return 0
    except ValueError as e:
        print("painel: {}".format(e))
        return 2
    except Exception as e:  # o painel nunca derruba o instalador
        print("painel: não consegui atualizar a página ({})".format(type(e).__name__))
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
