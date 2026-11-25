#!/usr/bin/env python3
"""Revisa a ligação do Claude com os sistemas de trabalho e escreve um relatório curto.

Uso (na pasta do kit):
    python3 ferramentas/revisar_sistemas.py                 # confere tudo e grava relatorio-revisao.txt
    python3 ferramentas/revisar_sistemas.py --sem-teste     # não roda o teste do plugin (sem internet)
    python3 ferramentas/revisar_sistemas.py --json
    python3 ferramentas/revisar_sistemas.py --explicar "<texto do erro que apareceu>"

No Windows, troque `python3` pelo Python que houver (`python`, ou `uv run --no-project`).

Confere, nesta ordem: o Claude Code, o uv, cada plugin (instalado, versão mínima, pasta inteira),
cada credencial (só o NOME dos campos, nunca o valor), o teste de cada plugin e a prova de cada
conector. O que conferir e o que cada erro quer dizer vêm de `.root/sistemas.json`, escrito pela
Root na montagem. O relatório não leva senha, chave nem e-mail. Não chama modelo de IA.
Só biblioteca padrão, compatível com Python 3.9.
"""
import datetime as dt
import json
import os
import platform
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sistemas  # noqa: E402

KIT = sistemas.KIT
RELATORIO = KIT / "relatorio-revisao.txt"
LINK_UV = "https://docs.astral.sh/uv/getting-started/installation/"
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

ERROS_DE_BASE = [
    {"id": "sem-rede", "sinais": ["ConnectError", "getaddrinfo", "Name or service not known", "Temporary failure in name resolution",
                                  "timed out", "CERTIFICATE_VERIFY_FAILED"],
     "significa": "O computador não conseguiu falar com o sistema pela internet.",
     "resolve": "Confira a internet e, em rede de empresa, se há bloqueio ou VPN. Depois rode a revisão de novo.", "quem_resolve": "voce"},
    {"id": "biblioteca", "sinais": ["ModuleNotFoundError", "ImportError", "No module named"],
     "significa": "O servidor do plugin não conseguiu carregar uma biblioteca. Quase sempre é plugin desatualizado.",
     "resolve": "Atualize o plugin, abra uma conversa nova e rode a revisão de novo.", "quem_resolve": "voce"},
]


def responsavel(s):
    return s.get("_responsavel") or "quem entregou o kit"


def versao_de(programa):
    caminho = sistemas.binario(programa)
    if not caminho:
        return None, None
    codigo, texto = sistemas.rodar([caminho, "--version"], timeout=30)
    achado = re.search(r"\d+(\.\d+)+", texto or "")
    return caminho, (achado.group(0) if achado and codigo == 0 else "versão não informada")


def numeros(versao):
    return tuple(int(x) for x in re.findall(r"\d+", str(versao or ""))[:4])


def valores_para_esconder(s):
    """Os valores dos campos de credencial, lidos só para tirar de qualquer texto que saia daqui."""
    esconder = set()
    for c in s.get("credenciais", []):
        for campo in c.get("campos", []):
            if campo.get("valor"):
                esconder.add(str(campo["valor"]))
        caminho = sistemas.expandir(c["arquivo"])
        if not caminho.exists():
            continue
        for linha in caminho.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            m = sistemas.LINHA.match(linha)
            if m:
                valor = m.group(2).strip().strip("'\"")
                if len(valor) >= 4:
                    esconder.add(valor)
    return sorted(esconder, key=len, reverse=True)


def limpar(texto, esconder):
    for valor in esconder:
        texto = texto.replace(valor, "<oculto>")
    return EMAIL.sub("<e-mail>", texto)


def grudados(c):
    """Campos que ficaram na mesma linha de outro (faltou a quebra de linha ao acrescentar)."""
    caminho = sistemas.expandir(c["arquivo"])
    if not caminho.exists():
        return []
    nomes = [campo["nome"] for campo in c["campos"]]
    achados = []
    for linha in caminho.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        m = sistemas.LINHA.match(linha)
        if not m:
            continue
        for nome in nomes:
            if nome != m.group(1) and re.search(re.escape(nome) + r"\s*=", m.group(2)):
                achados.append((nome, m.group(1)))
    return achados


def achar_erro(texto, s):
    baixo = (texto or "").lower()
    for erro in list(s.get("erros") or []) + ERROS_DE_BASE:
        if any(sinal.lower() in baixo for sinal in erro.get("sinais", [])):
            return erro
    return None


def item(iid, nome, situacao, detalhe="", fazer=None, quem="voce"):
    return {"id": iid, "nome": nome, "situacao": situacao, "detalhe": detalhe, "fazer": list(fazer or []), "quem": quem}


def conferir_programas():
    itens = []
    caminho, versao = versao_de("claude")
    if caminho:
        itens.append(item("claude", "Claude Code", "ok", versao))
    else:
        itens.append(item("claude", "Claude Code", "aviso",
                          "o comando claude não está no terminal; se você usa só o aplicativo, a versão aparece em Ajuda, Sobre"))
    caminho, versao = versao_de("uv")
    if caminho:
        itens.append(item("uv", "uv", "ok", versao))
    else:
        instalar = {"Windows": "No PowerShell: winget install --id=astral-sh.uv -e", "Darwin": "No Terminal: brew install uv"}.get(
            platform.system(), "Instale pelo site oficial")
        itens.append(item("uv", "uv", "falta", "sem o uv, o servidor do plugin não sobe e as ferramentas do sistema não aparecem",
                          [instalar + " (instruções oficiais: " + LINK_UV + ")", "Feche o Claude inteiro, abra de novo e rode a revisão outra vez"]))
    return itens


def conferir_plugin(p, tem_uv, credenciais_ok, sem_teste, s, esconder):
    chave = "{}@{}".format(p["plugin"], p["marketplace"])
    nome = p.get("nome") or chave
    inst = sistemas.plugins_instalados().get(chave)
    nova_conversa = "Abra uma conversa nova: o plugin só aparece em conversa aberta depois da instalação"
    if not inst:
        return [item("plugin:" + p["plugin"], nome, "falta", "não está instalado neste computador",
                     ["Digite no Claude: /plugin marketplace add " + p["repo"], "Depois: /plugin install " + chave, nova_conversa])]
    pasta = Path(inst.get("caminho") or "")
    script = pasta / p["teste"]["script"] if p.get("teste") else None
    if not inst.get("caminho") or not pasta.is_dir() or (script and not script.exists()):
        return [item("plugin:" + p["plugin"], nome, "falta", "consta como instalado, mas a pasta do plugin está incompleta",
                     ["Digite no Claude: /plugin uninstall " + chave, "Depois: /plugin install " + chave, nova_conversa])]
    minima = p.get("versao_minima")
    if minima and numeros(inst.get("versao")) < numeros(minima):
        return [item("plugin:" + p["plugin"], nome, "falta",
                     "desatualizado: versão {} instalada, a mínima é {}".format(inst.get("versao"), minima),
                     ["Digite no Claude: /plugin marketplace update " + p["marketplace"],
                      "Depois atualize o plugin na tela do /plugin (aba dos instalados) ou, no terminal: claude plugin update " + chave,
                      nova_conversa])]
    itens = [item("plugin:" + p["plugin"], nome, "ok", "versão {}".format(inst.get("versao")))]
    if not p.get("teste"):
        return itens
    tid, tnome = "teste:" + p["plugin"], "teste do " + nome
    if sem_teste:
        return itens + [item(tid, tnome, "aviso", "não rodou (pedido com --sem-teste)")]
    if not tem_uv or not credenciais_ok:
        return itens + [item(tid, tnome, "aviso", "não rodou: resolva antes o que falta acima")]
    codigo, texto = sistemas.rodar([sistemas.binario("uv"), "run", "--script", str(script)] + list(p["teste"].get("args", [])), timeout=300)
    sistemas.registrar("plugin:" + p["plugin"], codigo == 0, "revisão, versão {}".format(inst.get("versao")))
    if codigo == 0:
        return itens + [item(tid, tnome, "ok", "entrou no sistema e respondeu")]
    erro = achar_erro(texto, s)
    if erro:
        return itens + [item(tid, tnome, "falta", erro["significa"], [erro["resolve"]], erro.get("quem_resolve", "voce"))]
    fim = [limpar(linha.strip(), esconder)[:160] for linha in (texto or "").splitlines() if linha.strip()][-6:]
    return itens + [item(tid, tnome, "falta", "falhou com um erro que não está na lista deste kit: " + " | ".join(fim),
                         ["Mande este relatório a {}".format(responsavel(s))], "responsavel")]


def conferir_credencial(c):
    nome = c.get("nome") or c["id"]
    gravar = "Rode ferramentas/sistemas.py --gravar-credencial {} (abre uma janela para a senha; o chat não vê)".format(c["id"])
    colados = grudados(c)
    if colados:
        return item("credencial:" + c["id"], nome, "falta",
                    "linha grudada em {}: {} ficou na mesma linha de {}".format(c["arquivo"], colados[0][0], colados[0][1]),
                    [gravar + ", com --trocar no fim"])
    faltam = sistemas.faltam_da_credencial(c)
    if faltam:
        return item("credencial:" + c["id"], nome, "falta", "em {} falta: {}".format(c["arquivo"], ", ".join(faltam)), [gravar])
    return item("credencial:" + c["id"], nome, "ok", "campos preenchidos em {}".format(c["arquivo"]))


def revisar(sem_teste=False):
    s = sistemas.carregar()
    if not s:
        return {"tem_sistemas": False, "itens": [], "tudo_certo": True, "responsavel": responsavel(s)}
    esconder = valores_para_esconder(s)
    itens = conferir_programas()
    tem_uv = any(i["id"] == "uv" and i["situacao"] == "ok" for i in itens)
    credenciais = [conferir_credencial(c) for c in s.get("credenciais", [])]
    itens += credenciais
    credenciais_ok = all(c["situacao"] == "ok" for c in credenciais)
    for p in s.get("plugins", []):
        itens += conferir_plugin(p, tem_uv, credenciais_ok, sem_teste, s, esconder)
    estado = sistemas.ler_json(sistemas.ESTADO, {"itens": {}}).get("itens", {})
    for c in s.get("conectores", []):
        prova = estado.get("conector:" + c["id"], {})
        if prova.get("ok"):
            itens.append(item("conector:" + c["id"], "conector " + c["nome"], "ok", "provado numa conversa em " + str(prova.get("em", ""))[:10]))
        else:
            itens.append(item("conector:" + c["id"], "conector " + c["nome"], "aviso",
                              "só dá para provar na conversa: peça ao Claude para usar a ferramenta {}".format(c.get("ferramenta_de_teste"))))
    for i in itens:
        i["detalhe"] = limpar(i["detalhe"], esconder)
    return {"tem_sistemas": True, "itens": itens, "tudo_certo": not any(i["situacao"] == "falta" for i in itens),
            "responsavel": responsavel(s), "quando": dt.datetime.now().astimezone().strftime("%d/%m/%Y %H:%M"),
            "computador": "{} {}".format(platform.system(), platform.release())}


def texto_do_relatorio(r):
    if not r["tem_sistemas"]:
        return "Este kit não tem sistemas de trabalho para revisar.\n"
    linhas = ["Revisão dos sistemas, {} ({})".format(r["quando"], r["computador"]), ""]
    for i in r["itens"]:
        linhas.append("[{}] {}{}".format(i["situacao"], i["nome"], ": " + i["detalhe"] if i["detalhe"] else ""))
    faltas = [i for i in r["itens"] if i["situacao"] == "falta"]
    linhas.append("")
    if not faltas:
        linhas.append("Resultado: Tudo certo no que dá para conferir por aqui.")
    else:
        linhas.append("Resultado: {} ponto(s) a resolver.".format(len(faltas)))
    seus = [passo for i in faltas if i["quem"] == "voce" for passo in i["fazer"]]
    if seus:
        linhas += ["", "O que você faz:"] + ["  {}. {}".format(n, passo) for n, passo in enumerate(seus, 1)]
    dele = [i for i in faltas if i["quem"] == "responsavel"]
    if dele:
        linhas += ["", "Para {} decidir ou resolver:".format(r["responsavel"])]
        linhas += ["  - {}: {}".format(i["nome"], " ".join(i["fazer"])) for i in dele]
    linhas += ["", "Mande este arquivo a {}. Ele não leva senha, chave nem e-mail.".format(r["responsavel"])]
    return "\n".join(linhas) + "\n"


def explicar(texto):
    s = sistemas.carregar()
    erro = achar_erro(texto, s)
    if not erro:
        print("Esse erro não está na lista deste kit. Copie o texto do erro (sem senha) e mande a {} "
              "junto com o relatorio-revisao.txt.".format(responsavel(s)))
        return 1
    quem = responsavel(s) if erro.get("quem_resolve") == "responsavel" else "você"
    print("O que significa: {}\nComo resolve: {}\nQuem resolve: {}".format(erro["significa"], erro["resolve"], quem))
    return 0


def main(argv):
    if "--explicar" in argv:
        i = argv.index("--explicar")
        if i + 1 >= len(argv):
            print('Uso: --explicar "<texto do erro>"')
            return 2
        return explicar(" ".join(argv[i + 1:]))
    r = revisar(sem_teste="--sem-teste" in argv)
    if "--json" in argv:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0 if r["tudo_certo"] else 1
    texto = texto_do_relatorio(r)
    if r["tem_sistemas"]:
        RELATORIO.write_text(texto, encoding="utf-8")
        texto += "\nRelatório gravado em {}.\n".format(RELATORIO.name)
    sys.stdout.write(texto)
    return 0 if r["tudo_certo"] else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv))
