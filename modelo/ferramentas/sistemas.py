#!/usr/bin/env python3
"""Liga o Claude do kit aos sistemas de trabalho da pessoa (plugins, conectores e credenciais).

Uso (na pasta do kit):
    python3 ferramentas/sistemas.py --conferir [--json]      # o que já está ligado e o que falta
    python3 ferramentas/sistemas.py --gravar-credencial <id> [--trocar]
    python3 ferramentas/sistemas.py --instalar-plugins
    python3 ferramentas/sistemas.py --testar-plugin <plugin>
    python3 ferramentas/sistemas.py --registrar <conector> ok|falhou ["detalhe curto"]

No Windows, troque `python3` por `.venv/Scripts/python`.

O que existe para ligar vem de `.root/sistemas.json`, escrito pela Root na montagem do kit.
Segredo (senha, token) nunca passa pelo chat nem pela linha de comando: `--gravar-credencial`
abre uma janela do sistema (Windows, Mac) em que a própria pessoa digita, grava no arquivo que
o plugin lê (permissão 600) e só diz o NOME do que gravou. Nenhuma saída deste script mostra
valor de credencial. O estado dos testes (sem segredo) fica em `.root/sistemas-estado.json`.
Só biblioteca padrão, compatível com Python 3.9.
"""
import base64
import datetime as dt
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
SISTEMAS = KIT / ".root" / "sistemas.json"
ESTADO = KIT / ".root" / "sistemas-estado.json"
PEDIR_SEGREDO_PS1 = KIT / "instalar" / "pedir-segredo.ps1"


def agora():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def ler_json(caminho, padrao=None):
    try:
        return json.loads(Path(caminho).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return padrao if padrao is not None else {}


def gravar_json(caminho, dados):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_name(caminho.name + ".tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, caminho)


def carregar():
    return ler_json(SISTEMAS)


def expandir(arquivo):
    return Path(os.path.expanduser(str(arquivo)))


def pasta_do_claude():
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or (Path.home() / ".claude"))


# ---------------------------------------------------------------- credenciais (arquivo .env)

LINHA = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$")


def nomes_preenchidos(arquivo):
    """Os NOMES com valor no arquivo .env. Nunca devolve o valor."""
    caminho = expandir(arquivo)
    if not caminho.exists():
        return set()
    cheios = set()
    for linha in caminho.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        m = LINHA.match(linha)
        if not m:
            continue
        valor = m.group(2).strip()
        if valor[:1] in ("'", '"') and valor[-1:] == valor[:1]:
            valor = valor[1:-1]
        if valor:
            cheios.add(m.group(1))
    return cheios


def aspas(valor):
    """Valor entre aspas simples, no formato que o python-dotenv lê (\\ e ' escapados)."""
    return "'" + valor.replace("\\", "\\\\").replace("'", "\\'") + "'"


def escrever_env(arquivo, valores):
    """Junta `valores` ao arquivo: troca as linhas dessas chaves, mantém as outras e termina com
    quebra de linha (sem ela, a próxima linha acrescentada gruda na última). Permissão 600."""
    caminho = expandir(arquivo)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        os.chmod(caminho.parent, 0o700)
    linhas = caminho.read_text(encoding="utf-8-sig", errors="replace").splitlines() if caminho.exists() else []
    feitos = set()
    novas = []
    for linha in linhas:
        m = LINHA.match(linha)
        if m and m.group(1) in valores:
            if m.group(1) not in feitos:
                novas.append("{}={}".format(m.group(1), aspas(valores[m.group(1)])))
                feitos.add(m.group(1))
            continue
        novas.append(linha)
    for nome, valor in valores.items():
        if nome not in feitos:
            novas.append("{}={}".format(nome, aspas(valor)))
    tmp = caminho.with_name(caminho.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(novas).rstrip("\n") + "\n")
    if os.name != "nt":
        os.chmod(tmp, 0o600)
    os.replace(tmp, caminho)


def pedir_segredo(rotulo, titulo):
    """Abre uma janela do sistema para a pessoa digitar o segredo. Devolve o texto ou None."""
    if os.environ.get("KIT_MODO_TESTE") == "1" and "KIT_SEGREDO_PARA_TESTE" in os.environ:
        return os.environ["KIT_SEGREDO_PARA_TESTE"] or None
    sistema = platform.system()
    try:
        if sistema == "Windows":
            env = dict(os.environ, KIT_ROTULO=rotulo, KIT_TITULO=titulo)
            r = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-STA",
                                "-File", str(PEDIR_SEGREDO_PS1)], env=env, capture_output=True, text=True, timeout=600)
            if r.returncode != 0 or not r.stdout.strip():
                return None
            return base64.b64decode(r.stdout.strip()).decode("utf-8")
        if sistema == "Darwin":
            script = ['on run argv',
                      'display dialog (item 1 of argv) default answer "" with hidden answer with title (item 2 of argv) '
                      'buttons {"Cancelar", "Gravar"} default button "Gravar" cancel button "Cancelar"',
                      'return text returned of result', 'end run']
            cmd = ["osascript"]
            for linha in script:
                cmd += ["-e", linha]
            r = subprocess.run(cmd + [rotulo, titulo], capture_output=True, text=True, timeout=600)
            return r.stdout.rstrip("\n") or None if r.returncode == 0 else None
        if shutil.which("zenity"):
            r = subprocess.run(["zenity", "--password", "--title", titulo], capture_output=True, text=True, timeout=600)
            return r.stdout.rstrip("\n") or None if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None
    if sys.stdin.isatty():
        import getpass
        return getpass.getpass(rotulo + ": ") or None
    return None


def credencial(cid):
    for c in carregar().get("credenciais", []):
        if c["id"] == cid:
            return c
    return None


def faltam_da_credencial(c):
    cheios = nomes_preenchidos(c["arquivo"])
    return [campo["nome"] for campo in c["campos"] if campo["nome"] not in cheios]


def gravar_credencial(cid, trocar=False):
    c = credencial(cid)
    if not c:
        print("Não há credencial '{}' neste kit. As que existem: {}.".format(
            cid, ", ".join(x["id"] for x in carregar().get("credenciais", [])) or "nenhuma"))
        return 2
    cheios = nomes_preenchidos(c["arquivo"])
    valores, gravados = {}, []
    for campo in c["campos"]:
        if not campo.get("segredo"):
            valores[campo["nome"]] = campo["valor"]
            gravados.append(campo["nome"])
    for campo in c["campos"]:
        if not campo.get("segredo") or (campo["nome"] in cheios and not trocar):
            continue
        print("Abrindo uma janela para digitar: {}. Se ela não aparecer, procure na barra de tarefas.".format(
            campo.get("pergunta") or campo["nome"]))
        sys.stdout.flush()
        segredo = pedir_segredo(campo.get("pergunta") or campo["nome"], c.get("nome") or "Kit")
        if not segredo:
            escrever_env(c["arquivo"], valores)
            print("Nada digitado (ou janela cancelada). Gravei só o que não é segredo: {}. "
                  "Rode de novo quando quiser digitar {}.".format(", ".join(gravados), campo["nome"]))
            return 1
        valores[campo["nome"]] = segredo
        gravados.append(campo["nome"] + " (segredo)")
    escrever_env(c["arquivo"], valores)
    faltam = faltam_da_credencial(c)
    print("Gravado em {}: {}.".format(expandir(c["arquivo"]), ", ".join(gravados) or "nada novo"))
    if faltam:
        print("Ainda falta: {}.".format(", ".join(faltam)))
        return 1
    print("Credencial '{}' completa. O valor dos segredos não aparece aqui de propósito.".format(cid))
    return 0


# ---------------------------------------------------------------- plugins

def binario(nome):
    achado = shutil.which(nome)
    if achado:
        return achado
    for pasta in (Path.home() / ".local" / "bin", Path.home() / ".cargo" / "bin"):
        for candidato in (pasta / nome, pasta / (nome + ".exe")):
            if candidato.exists():
                return str(candidato)
    return None


def plugins_instalados():
    """{'plugin@marketplace': {'versao': ..., 'caminho': ...}} lido do registro do Claude Code."""
    dados = ler_json(pasta_do_claude() / "plugins" / "installed_plugins.json")
    saida = {}
    for chave, valor in (dados.get("plugins") or {}).items():
        itens = valor if isinstance(valor, list) else [valor]
        if itens:
            ultimo = itens[-1]
            saida[chave] = {"versao": ultimo.get("version"), "caminho": ultimo.get("installPath")}
    return saida


def marketplaces_conhecidos():
    return set(ler_json(pasta_do_claude() / "plugins" / "known_marketplaces.json"))


def rodar(cmd, timeout=600):
    try:
        r = subprocess.run(cmd, cwd=str(KIT), capture_output=True, text=True, timeout=timeout)
        return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()
    except (OSError, subprocess.TimeoutExpired) as erro:
        return 1, str(erro)


def instalar_plugins():
    claude = binario("claude")
    if not claude:
        print("Não achei o Claude Code (comando claude) neste computador. Rode o instalador do kit de novo.")
        return 1
    falhas = 0
    for p in carregar().get("plugins", []):
        chave = "{}@{}".format(p["plugin"], p["marketplace"])
        if p["marketplace"] not in marketplaces_conhecidos():
            codigo, texto = rodar([claude, "plugin", "marketplace", "add", p["repo"]])
            print("Loja de plugins {} ({}): {}".format(p["marketplace"], p["repo"], "adicionada" if codigo == 0 else "falhou"))
            if codigo != 0:
                print(texto[-800:])
                falhas += 1
                continue
        else:
            rodar([claude, "plugin", "marketplace", "update", p["marketplace"]])
        if chave in plugins_instalados():
            codigo, texto = rodar([claude, "plugin", "update", chave])
            print("{}: já instalado (versão {}); atualização conferida.".format(p.get("nome") or chave, plugins_instalados()[chave]["versao"]))
            continue
        codigo, texto = rodar([claude, "plugin", "install", chave, "--scope", "user"])
        instalado = chave in plugins_instalados()
        print("{}: {}".format(p.get("nome") or chave, "instalado" if instalado else "não instalou"))
        if not instalado:
            print(texto[-800:])
            falhas += 1
    if not falhas:
        print("Para o Claude enxergar o plugin, é preciso abrir uma conversa nova nesta pasta.")
    return 1 if falhas else 0


def testar_plugin(nome):
    p = next((x for x in carregar().get("plugins", []) if nome in (x["plugin"], "{}@{}".format(x["plugin"], x["marketplace"]))), None)
    if not p:
        print("Plugin '{}' não está neste kit.".format(nome))
        return 2
    chave = "{}@{}".format(p["plugin"], p["marketplace"])
    inst = plugins_instalados().get(chave)
    if not inst or not inst.get("caminho"):
        print("{} ainda não está instalado. Rode --instalar-plugins.".format(chave))
        return 1
    teste = p.get("teste")
    if not teste:
        print("{} não tem teste de linha de comando; confira numa conversa nova.".format(chave))
        return 0
    uv = binario("uv")
    if not uv:
        print("Falta o uv neste computador (o plugin precisa dele). Rode o instalador do kit de novo.")
        return 1
    script = Path(inst["caminho"]) / teste["script"]
    codigo, texto = rodar([uv, "run", "--script", str(script)] + list(teste.get("args", [])), timeout=300)
    print(texto[-3000:])
    registrar("plugin:" + p["plugin"], codigo == 0, "teste do plugin, versão {}".format(inst.get("versao")))
    print("\nResultado do teste: {}".format("OK" if codigo == 0 else "FALHOU"))
    return 0 if codigo == 0 else 1


# ---------------------------------------------------------------- estado e conferência

def registrar(item, ok, detalhe=""):
    estado = ler_json(ESTADO, {"itens": {}})
    estado.setdefault("itens", {})[item] = {"ok": bool(ok), "em": agora(), "detalhe": str(detalhe)[:200]}
    gravar_json(ESTADO, estado)


def conferir():
    s = carregar()
    estado = ler_json(ESTADO, {"itens": {}}).get("itens", {})
    instalados = plugins_instalados()
    res = {"tem_sistemas": bool(s), "plugins": [], "credenciais": [], "conectores": [], "faltas": []}
    for c in s.get("credenciais", []):
        faltam = faltam_da_credencial(c)
        res["credenciais"].append({"id": c["id"], "nome": c.get("nome"), "arquivo": str(expandir(c["arquivo"])), "faltam": faltam})
        if faltam:
            res["faltas"].append("credencial {}: falta {} (rode --gravar-credencial {})".format(c["id"], ", ".join(faltam), c["id"]))
    for p in s.get("plugins", []):
        chave = "{}@{}".format(p["plugin"], p["marketplace"])
        inst = instalados.get(chave)
        teste = estado.get("plugin:" + p["plugin"], {})
        res["plugins"].append({"plugin": chave, "nome": p.get("nome"), "instalado": bool(inst),
                               "versao": (inst or {}).get("versao"), "teste_ok": teste.get("ok"), "testado_em": teste.get("em")})
        if not inst:
            res["faltas"].append("plugin {} não instalado (rode --instalar-plugins)".format(chave))
        elif p.get("teste") and not teste.get("ok"):
            res["faltas"].append("plugin {} instalado e ainda sem teste aprovado (rode --testar-plugin {})".format(chave, p["plugin"]))
    for c in s.get("conectores", []):
        teste = estado.get("conector:" + c["id"], {})
        res["conectores"].append({"id": c["id"], "nome": c.get("nome"), "teste_ok": teste.get("ok"), "testado_em": teste.get("em")})
        if not teste.get("ok"):
            res["faltas"].append("conector {} ainda sem teste aprovado numa conversa (ferramenta {})".format(c["nome"], c.get("ferramenta_de_teste")))
    if s.get("plugins"):
        res["programas"] = {"claude": bool(binario("claude")), "uv": bool(binario("uv"))}
        for nome, achou in res["programas"].items():
            if not achou:
                res["faltas"].append("programa {} não encontrado".format(nome))
    res["pronto"] = res["tem_sistemas"] and not res["faltas"]
    return res


def pronto():
    """Para o verificar.py: (feito, detalhe)."""
    r = conferir()
    if not r["tem_sistemas"]:
        return True, "este kit não tem sistemas para ligar"
    if r["pronto"]:
        nomes = [p["nome"] or p["plugin"] for p in r["plugins"]] + [c["nome"] for c in r["conectores"]]
        return True, "ligados e testados: " + ", ".join(nomes)
    return False, "; ".join(r["faltas"])


def imprimir(r):
    if not r["tem_sistemas"]:
        print("Este kit não tem sistemas de trabalho para ligar.")
        return
    for c in r["credenciais"]:
        print("[{}] credencial {} ({}){}".format("ok" if not c["faltam"] else "falta", c["nome"] or c["id"], c["arquivo"],
                                                 "" if not c["faltam"] else ": falta " + ", ".join(c["faltam"])))
    for p in r["plugins"]:
        situacao = "falta" if not p["instalado"] else ("ok" if p["teste_ok"] else "testar")
        print("[{}] {}{}".format(situacao, p["nome"] or p["plugin"], " versão " + str(p["versao"]) if p["versao"] else ""))
    for c in r["conectores"]:
        print("[{}] conector {}".format("ok" if c["teste_ok"] else "falta", c["nome"]))
    print("\n" + ("Tudo ligado e testado." if r["pronto"] else "Falta: " + "; ".join(r["faltas"])))


def main(argv):
    if "--conferir" in argv:
        r = conferir()
        if "--json" in argv:
            print(json.dumps(r, ensure_ascii=False, indent=2))
        else:
            imprimir(r)
        return 0 if r["pronto"] or not r["tem_sistemas"] else 1
    if "--gravar-credencial" in argv:
        i = argv.index("--gravar-credencial")
        if i + 1 >= len(argv):
            print("Diga qual credencial: --gravar-credencial <id>")
            return 2
        return gravar_credencial(argv[i + 1], trocar="--trocar" in argv)
    if "--instalar-plugins" in argv:
        return instalar_plugins()
    if "--testar-plugin" in argv:
        i = argv.index("--testar-plugin")
        return testar_plugin(argv[i + 1]) if i + 1 < len(argv) else 2
    if "--registrar" in argv:
        i = argv.index("--registrar")
        if i + 2 >= len(argv) or argv[i + 2] not in ("ok", "falhou"):
            print('Uso: --registrar <conector> ok|falhou ["detalhe"]')
            return 2
        conector = argv[i + 1]
        if conector not in {c["id"] for c in carregar().get("conectores", [])}:
            print("Conector '{}' não está neste kit.".format(conector))
            return 2
        registrar("conector:" + conector, argv[i + 2] == "ok", argv[i + 3] if i + 3 < len(argv) else "")
        print("Registrado: conector {} {}.".format(conector, argv[i + 2]))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
