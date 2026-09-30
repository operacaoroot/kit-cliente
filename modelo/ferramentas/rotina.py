#!/usr/bin/env python3
"""A rotina que alimenta o vault: junta o que aconteceu no kit e chama o Claude para escrever.

Uso (na pasta do kit; no Windows troque `python3` por `.venv/Scripts/python`):
    python3 ferramentas/rotina.py --estado            # ligada? quando roda? última alimentação
    python3 ferramentas/rotina.py --ligar [--horas 08:00,12:30,17:30] [--sem-envio] [--simular]
    python3 ferramentas/rotina.py --desligar [--simular]
    python3 ferramentas/rotina.py --rodar             # o que o agendador chama: coleta e, se houver novidade, chama o Claude
    python3 ferramentas/rotina.py --coletar           # só a coleta; imprime o caminho do resumo (ou "nada novo")
    python3 ferramentas/rotina.py --concluir <resumo> # marca o resumo como processado

Como funciona, três vezes por dia (padrão 08:00, 12:30 e 17:30, meia hora antes das leituras do
acompanhador da Root), em Mac (launchd), Windows (Agendador de Tarefas, sem abrir janela) e Linux (cron):
1. A coleta (esta ferramenta, sem IA) junta o que aconteceu desde a última alimentação: as conversas
   com o Claude feitas DENTRO da pasta do kit, os commits, os arquivos novos em entregas/, os pedidos
   de ajuda e os arquivos novos em entrada/. Senha, token, chave, cartão, CPF e CNPJ saem mascarados.
   O resumo fica em _privado/rotina/, que nunca sai da máquina.
2. Se houver novidade, o Claude do kit roda sozinho a skill `alimentar-vault`, que escreve o diário
   do dia e atualiza as notas do vault com fonte, marcadas para a pessoa revisar.
3. A rodada salva e envia o vault e o progresso para o repositório do kit (commit "Rotina: ..."),
   que é o reporte que a Root lê. Com --sem-envio, nada sai até a pessoa fechar o dia.

Só biblioteca padrão, compatível com Python 3.9.
"""
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
ROOT_DIR = KIT / ".root"
ESTADO = ROOT_DIR / "rotina.json"
PRIVADO = KIT / "_privado" / "rotina"
SISTEMA = os.environ.get("KIT_SISTEMA") or {"Darwin": "mac", "Windows": "windows"}.get(platform.system(), "linux")
HORAS_PADRAO = ["08:00", "12:30", "17:30"]
SEM_JANELA = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW: rodada agendada não pisca janela
LIMITE_DO_RESUMO = 60000          # caracteres; o que passar disso fica para a próxima rodada
LIMITE_POR_FALA = 1500
LIMITE_POR_ARQUIVO = 3000
TEXTO_LIDO = (".md", ".txt", ".csv")
TEMPO_MAXIMO_DO_CLAUDE = 20 * 60  # segundos

SEGREDOS = [
    (re.compile(r"sk-(?:ant-|or-)?[A-Za-z0-9_-]{16,}"), "[SEGREDO:chave]"),
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/-]{16,}=*"), "[SEGREDO:token]"),
    (re.compile(r"(?i)\b(senha|password|pass|token|api[_-]?key|secret)\b(\s*[:=]\s*)\S+"), r"\1\2[SEGREDO]"),
    (re.compile(r"\b(?:\d[ .-]?){13,19}\b"), "[SEGREDO:numero-longo]"),
    (re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"), "[SEGREDO:cpf]"),
    (re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b"), "[SEGREDO:cnpj]"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S), "[SEGREDO:chave-privada]"),
]
RUIDO_DO_USUARIO = ("<command-", "<local-command", "<system-reminder", "Caveat:", "[Request interrupted")


# ---------------------------------------------------------------- utilidades

def agora():
    return dt.datetime.now().astimezone()


def iso(d):
    return d.isoformat(timespec="seconds")


def ler_iso(s):
    if not s:
        return None
    try:
        d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        return d.astimezone() if d.tzinfo else d.astimezone()  # sempre no fuso da máquina: é o horário que a pessoa reconhece
    except ValueError:
        return None


def mascarar(texto):
    for padrao, troca in SEGREDOS:
        texto = padrao.sub(troca, texto)
    return texto


def encurtar(texto, limite):
    texto = texto.strip()
    return texto if len(texto) <= limite else texto[:limite].rstrip() + " [...]"


def ler_estado():
    if ESTADO.exists():
        try:
            return json.loads(ESTADO.read_text(encoding="utf-8"))
        except ValueError:
            pass
    return {}


def gravar_estado(estado):
    ROOT_DIR.mkdir(exist_ok=True)
    ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def slug_do_kit():
    arq = ROOT_DIR / "cliente.json"
    if arq.exists():
        try:
            return json.loads(arq.read_text(encoding="utf-8")).get("slug") or "kit"
        except ValueError:
            pass
    return "kit"


def rel(caminho):
    try:
        return Path(caminho).resolve().relative_to(KIT).as_posix()
    except (ValueError, OSError):
        return None


# ---------------------------------------------------------------- conversas com o Claude

def pastas_de_sessoes():
    """As conversas do Claude Code ficam em ~/.claude/projects/<caminho da pasta com não-letras virando '-'>."""
    base = Path(os.environ.get("KIT_CLAUDE_PROJECTS") or (Path.home() / ".claude" / "projects"))
    if not base.exists():
        return []
    caminhos = {str(KIT), os.path.realpath(str(KIT))}
    achadas = [base / re.sub(r"[^A-Za-z0-9]", "-", c) for c in caminhos]
    achadas = [p for p in achadas if p.is_dir()]
    if achadas:
        return sorted(set(achadas))
    for pasta in base.iterdir():  # reserva: a pasta cujo registro diz ter sido aberta no kit
        if not pasta.is_dir():
            continue
        for arq in sorted(pasta.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:1]:
            try:
                with open(arq, encoding="utf-8", errors="ignore") as f:
                    for _, linha in zip(range(50), f):
                        cwd = json.loads(linha).get("cwd") if '"cwd"' in linha else None
                        if cwd and (cwd in caminhos or os.path.realpath(cwd) in caminhos):
                            achadas.append(pasta)
                            break
            except (OSError, ValueError):
                continue
    return achadas


def texto_da_mensagem(conteudo):
    if isinstance(conteudo, str):
        return conteudo, []
    textos, arquivos = [], []
    for parte in conteudo or []:
        if not isinstance(parte, dict):
            continue
        if parte.get("type") == "text":
            textos.append(parte.get("text", ""))
        elif parte.get("type") == "tool_use" and parte.get("name") in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
            caminho = (parte.get("input") or {}).get("file_path") or (parte.get("input") or {}).get("notebook_path")
            if caminho:
                arquivos.append(caminho)
    return "\n".join(textos), arquivos


def conversas_desde(desde):
    sessoes = []
    for pasta in pastas_de_sessoes():
        for arq in sorted(pasta.glob("*.jsonl")):
            if desde and dt.datetime.fromtimestamp(arq.stat().st_mtime).astimezone() <= desde:
                continue
            falas, arquivos, inicio = [], set(), None
            with open(arq, encoding="utf-8", errors="ignore") as f:
                for linha in f:
                    try:
                        o = json.loads(linha)
                    except ValueError:
                        continue
                    quando = ler_iso(o.get("timestamp"))
                    if o.get("type") not in ("user", "assistant") or not quando or (desde and quando <= desde):
                        continue
                    if o.get("isMeta") or o.get("isSidechain"):
                        continue
                    texto, escritos = texto_da_mensagem((o.get("message") or {}).get("content"))
                    for e in escritos:
                        r = rel(e)
                        if r:
                            arquivos.add(r)
                    texto = texto.strip()
                    if not texto or texto.startswith(RUIDO_DO_USUARIO):
                        continue
                    inicio = inicio or quando
                    quem = "Pessoa" if o["type"] == "user" else "Claude"
                    falas.append("- **{}** ({}): {}".format(quem, quando.strftime("%d/%m %H:%M"),
                                                          encurtar(mascarar(texto), LIMITE_POR_FALA).replace("\n", " ")))
            if falas:
                sessoes.append({"id": arq.stem[:8], "inicio": inicio, "falas": falas, "arquivos": sorted(arquivos)})
    return sorted(sessoes, key=lambda s: s["inicio"])


# ---------------------------------------------------------------- o resto do kit

def commits_desde(desde):
    cmd = ["git", "log", "--format=%h%x09%ci%x09%an%x09%s"]
    if desde:
        cmd.append("--since=" + iso(desde))
    try:
        r = subprocess.run(cmd, cwd=str(KIT), capture_output=True, text=True, timeout=30, creationflags=SEM_JANELA)
    except (OSError, subprocess.TimeoutExpired):
        return []
    saida = []
    for linha in (r.stdout or "").splitlines()[:50]:
        partes = linha.split("\t", 3)
        if len(partes) == 4 and partes[2] != "Root (montador de kits)":
            saida.append("- `{}` {} · {}: {}".format(partes[0], partes[1][:16], partes[2], mascarar(partes[3])))
    return saida


def arquivos_novos(pasta, desde, com_conteudo):
    base = KIT / pasta
    if not base.exists():
        return []
    itens = []
    for arq in sorted(base.rglob("*")):
        if not arq.is_file() or arq.name in (".gitkeep", ".DS_Store"):
            continue
        quando = dt.datetime.fromtimestamp(arq.stat().st_mtime).astimezone()
        if desde and quando <= desde:
            continue
        linha = "- `{}` ({})".format(arq.relative_to(KIT).as_posix(), quando.strftime("%d/%m %H:%M"))
        if com_conteudo and arq.suffix.lower() in TEXTO_LIDO:
            texto = arq.read_text(encoding="utf-8", errors="ignore")
            linha += "\n\n  ```\n  " + encurtar(mascarar(texto), LIMITE_POR_ARQUIVO).replace("\n", "\n  ") + "\n  ```"
        itens.append(linha)
    return itens


def coletar():
    """Escreve o resumo do que aconteceu desde a última alimentação. Devolve o caminho, ou None."""
    estado = ler_estado()
    desde = ler_iso(estado.get("ultima_alimentacao"))
    ate = agora()
    sessoes = conversas_desde(desde)
    commits = commits_desde(desde)
    entregas = arquivos_novos("entregas", desde, com_conteudo=True)
    ajuda = arquivos_novos("ajuda", desde, com_conteudo=True)
    entrada = arquivos_novos("entrada", desde, com_conteudo=True)
    if not (sessoes or commits or entregas or ajuda or entrada):
        return None, ate

    partes = ["# Coleta para o vault · {}".format(ate.strftime("%Y-%m-%d %H:%M")), "",
              "Desde: {}. Até: {}. Resumo feito pela rotina do kit, sem IA; segredos mascarados.".format(
                  desde.strftime("%Y-%m-%d %H:%M") if desde else "o começo do kit", ate.strftime("%Y-%m-%d %H:%M")), ""]
    for s in sessoes:
        partes += ["## Conversa `{}` de {}".format(s["id"], s["inicio"].strftime("%d/%m/%Y %H:%M")), ""]
        if s["arquivos"]:
            partes += ["Arquivos que o Claude escreveu: " + ", ".join("`{}`".format(a) for a in s["arquivos"]), ""]
        partes += s["falas"] + [""]
    for titulo, itens in (("Commits", commits), ("Entregas novas ou alteradas", entregas),
                          ("Pedidos de ajuda novos ou respondidos", ajuda),
                          ("Arquivos novos em entrada/ (não copiar para o vault; descrever)", entrada)):
        if itens:
            partes += ["## " + titulo, ""] + itens + [""]
    texto = "\n".join(partes)
    if len(texto) > LIMITE_DO_RESUMO:
        texto = texto[:LIMITE_DO_RESUMO] + "\n\n[Resumo cortado no limite; o resto entra na próxima rodada.]\n"
    PRIVADO.mkdir(parents=True, exist_ok=True)
    destino = PRIVADO / "coleta-{}.md".format(ate.strftime("%Y-%m-%d-%H%M%S"))
    destino.write_text(texto, encoding="utf-8")
    pendentes = estado.get("coletas_pendentes", [])
    pendentes.append({"arquivo": destino.name, "ate": iso(ate)})
    estado["coletas_pendentes"] = pendentes[-10:]
    gravar_estado(estado)
    return destino, ate


def concluir(nome):
    estado = ler_estado()
    nome = Path(nome).name
    pendentes = estado.get("coletas_pendentes", [])
    feita = next((p for p in pendentes if p["arquivo"] == nome), None)
    if not feita:
        print("Não achei a coleta {} entre as pendentes.".format(nome))
        return 1
    estado["ultima_alimentacao"] = feita["ate"]
    estado["coletas_pendentes"] = [p for p in pendentes if p["arquivo"] != nome]
    estado["alimentacoes"] = estado.get("alimentacoes", 0) + 1
    gravar_estado(estado)
    print("Coleta {} processada. Próxima alimentação parte de {}.".format(nome, feita["ate"][:16]))
    return 0


# ---------------------------------------------------------------- rodar (o que o agendador chama)

def claude_bin():
    estado = ler_estado()
    for c in (os.environ.get("KIT_CLAUDE_BIN"), estado.get("claude"), shutil.which("claude"),
              str(Path.home() / ".local" / "bin" / ("claude.exe" if SISTEMA == "windows" else "claude"))):
        if c and Path(c).exists():
            return c
    return None


def python_do_kit():
    if SISTEMA == "windows":
        return ".venv/Scripts/python"
    return "python3"


def git(*args, timeout=120):
    try:
        r = subprocess.run(["git"] + list(args), cwd=str(KIT), capture_output=True, text=True, timeout=timeout,
                           creationflags=SEM_JANELA)
        return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)


def enviar(registrar):
    """O reporte da rodada: progresso atualizado, commit "Rotina: ...", atualizações da Root e envio."""
    subprocess.run([sys.executable, str(KIT / "ferramentas" / "verificar.py"), "--silencioso", "--sem-rede"],
                   cwd=str(KIT), capture_output=True, creationflags=SEM_JANELA)
    git("add", "-A")
    if git("diff", "--cached", "--quiet")[0] != 0:
        codigo, saida = git("commit", "-q", "-m", "Rotina: vault e progresso ({})".format(agora().strftime("%d/%m %H:%M")))
        if codigo != 0:
            registrar("commit da rotina falhou: " + encurtar(saida, 300))
            return "commit falhou"
    codigo, saida = git("pull", "--rebase", "--autostash", "-q")
    if codigo != 0:
        git("rebase", "--abort")
        registrar("não consegui trazer as atualizações da Root (conflito); o envio fica para o próximo fechamento")
        return "envio pendente (conflito)"
    codigo, saida = git("push", "-q")
    if codigo != 0:
        registrar("envio falhou: " + encurtar(saida, 300))
        return "envio pendente (rede ou acesso)"
    return "enviado"


def rodar():
    PRIVADO.mkdir(parents=True, exist_ok=True)
    log = PRIVADO / "rotina.log"
    inicio = agora()

    def registrar(texto):
        with open(log, "a", encoding="utf-8") as f:
            f.write("{} {}\n".format(iso(agora()), texto))
        print(texto)

    resumo, _ = coletar()
    estado = ler_estado()
    estado["ultima_rodada"] = iso(inicio)
    if not resumo:
        estado["ultimo_resultado"] = "nada novo"
        gravar_estado(estado)
        registrar("nada novo desde a última alimentação")
        if estado.get("enviar", True):
            estado = ler_estado()
            estado["ultimo_envio"] = enviar(registrar)
            gravar_estado(estado)
        return 0
    claude = claude_bin()
    if not claude:
        estado["ultimo_resultado"] = "Claude Code não encontrado"
        gravar_estado(estado)
        registrar("Claude Code não encontrado; a coleta ficou pendente em " + resumo.name)
        return 1
    pedido = ("Use a skill alimentar-vault com a coleta {r}. Ao terminar, rode `{py} ferramentas/rotina.py "
              "--concluir {n}`. Não faça commit nem push.").format(r=resumo.relative_to(KIT).as_posix(), py=python_do_kit(), n=resumo.name)
    ferramentas = ["Read", "Write", "Edit", "Glob", "Grep",
                   "Bash({} ferramentas/rotina.py:*)".format(python_do_kit())]
    cmd = [claude, "-p", pedido, "--permission-mode", "acceptEdits", "--no-session-persistence",
           "--output-format", "text", "--allowedTools"] + ferramentas
    registrar("chamando o Claude para a coleta " + resumo.name)
    try:
        r = subprocess.run(cmd, cwd=str(KIT), capture_output=True, text=True, timeout=TEMPO_MAXIMO_DO_CLAUDE,
                           creationflags=SEM_JANELA)
        codigo, saida = r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        codigo, saida = 124, "tempo esgotado"
    except OSError as e:
        codigo, saida = 1, str(e)
    registrar("Claude terminou com código {}: {}".format(codigo, encurtar(saida, 800).replace("\n", " ")))
    estado = ler_estado()
    processada = all(p["arquivo"] != resumo.name for p in estado.get("coletas_pendentes", []))
    estado["ultimo_resultado"] = "vault alimentado" if (codigo == 0 and processada) else "falhou (ver _privado/rotina/rotina.log)"
    gravar_estado(estado)
    if estado.get("enviar", True):
        estado = ler_estado()
        estado["ultimo_envio"] = enviar(registrar)
        gravar_estado(estado)
    return 0 if codigo == 0 and processada else 1


# ---------------------------------------------------------------- ligar e desligar

def rotulo():
    return "com.operacaoroot.kit-{}.vault".format(slug_do_kit())


def nome_da_tarefa_windows():
    return "Root kit {} - rotina do vault".format(slug_do_kit())


def horas_validas(texto):
    horas = []
    for h in (texto or "").split(","):
        m = re.fullmatch(r"([01]?\d|2[0-3]):([0-5]\d)", h.strip())
        if not m:
            raise SystemExit("horário inválido: {!r}; use HH:MM separados por vírgula, por exemplo 08:00,12:30,17:30".format(h))
        horas.append((int(m.group(1)), int(m.group(2))))
    if not 1 <= len(horas) <= 6:
        raise SystemExit("use de 1 a 6 horários por dia")
    return sorted(set(horas))


def plist_mac(horas):
    py = sys.executable
    path = ":".join([str(Path.home() / ".local" / "bin"), "/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin"])
    return """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>{rotulo}</string>
  <key>ProgramArguments</key>
  <array><string>{py}</string><string>{script}</string><string>--rodar</string></array>
  <key>WorkingDirectory</key><string>{kit}</string>
  <key>StartCalendarInterval</key>
  <array>
{intervalos}
  </array>
  <key>EnvironmentVariables</key>
  <dict><key>PATH</key><string>{path}</string></dict>
  <key>StandardOutPath</key><string>{log}</string>
  <key>StandardErrorPath</key><string>{log}</string>
</dict>
</plist>
""".format(rotulo=rotulo(), py=py, script=Path(__file__).resolve(), kit=KIT, path=path,
           intervalos="\n".join("    <dict><key>Hour</key><integer>{}</integer><key>Minute</key><integer>{}</integer></dict>".format(h, m)
                                for h, m in horas),
           log=PRIVADO / "agendador.log")


def comando_windows(horas):
    py = str(KIT / ".venv" / "Scripts" / "pythonw.exe")  # sem janela preta três vezes ao dia
    script = str(Path(__file__).resolve())
    return ("$a = New-ScheduledTaskAction -Execute '{py}' -Argument '\"{script}\" --rodar' -WorkingDirectory '{kit}'; "
            "$t = @({gatilhos}); "
            "$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries; "
            "Register-ScheduledTask -TaskName '{nome}' -Action $a -Trigger $t -Settings $s -Force | Out-Null").format(
                py=py.replace("'", "''"), script=script.replace("'", "''"), kit=str(KIT).replace("'", "''"),
                gatilhos=", ".join("(New-ScheduledTaskTrigger -Daily -At '{:02d}:{:02d}')".format(h, m) for h, m in horas),
                nome=nome_da_tarefa_windows())


def linhas_cron(horas):
    return ["{m} {h} * * * cd '{kit}' && '{py}' '{script}' --rodar >> '{log}' 2>&1 # {rotulo}".format(
        m=m, h=h, kit=KIT, py=sys.executable, script=Path(__file__).resolve(), log=PRIVADO / "agendador.log", rotulo=rotulo())
        for h, m in horas]


def ligar(horas_texto, simular, enviar_reporte=True):
    horas = horas_validas(horas_texto)
    texto_horas = ", ".join("{:02d}:{:02d}".format(h, m) for h, m in horas)
    claude = claude_bin()
    if not claude and not simular:
        print("Não achei o Claude Code nesta máquina. Rode a conferência do computador antes de ligar a rotina.")
        return 1
    PRIVADO.mkdir(parents=True, exist_ok=True)
    if SISTEMA == "mac":
        destino = Path.home() / "Library" / "LaunchAgents" / (rotulo() + ".plist")
        conteudo = plist_mac(horas)
        if simular:
            print("Gravaria {} com:\n{}".format(destino, conteudo))
            return 0
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(conteudo, encoding="utf-8")
        uid = str(os.getuid())
        subprocess.run(["launchctl", "bootout", "gui/" + uid, str(destino)], capture_output=True)
        r = subprocess.run(["launchctl", "bootstrap", "gui/" + uid, str(destino)], capture_output=True, text=True)
        if r.returncode != 0:
            print("O Mac não aceitou o agendamento: " + (r.stderr or r.stdout).strip())
            return 1
    elif SISTEMA == "windows":
        cmd = comando_windows(horas)
        if simular:
            print("Rodaria no PowerShell:\n" + cmd)
            return 0
        r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd], capture_output=True, text=True,
                           creationflags=SEM_JANELA)
        if r.returncode != 0:
            print("O Windows não aceitou o agendamento: " + (r.stderr or r.stdout).strip())
            return 1
    else:
        linhas = linhas_cron(horas)
        if simular:
            print("Acrescentaria ao crontab:\n" + "\n".join(linhas))
            return 0
        atual = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
        novo = "\n".join(l for l in atual.splitlines() if rotulo() not in l) + "\n" + "\n".join(linhas) + "\n"
        subprocess.run(["crontab", "-"], input=novo.lstrip("\n"), text=True, check=True)
    estado = ler_estado()
    estado.update({"ligada": True, "horas": ["{:02d}:{:02d}".format(h, m) for h, m in horas], "claude": claude,
                   "enviar": enviar_reporte, "ligada_em": iso(agora())})
    estado.pop("hora", None)
    gravar_estado(estado)
    print("Rotina do vault ligada: todo dia às {}. Se o computador estiver desligado ou dormindo, ela roda quando ele voltar.".format(texto_horas))
    if not enviar_reporte:
        print("Sem envio automático: o que a rotina escrever vai para a Root quando você fechar o dia.")
    return 0


def desligar(simular):
    if SISTEMA == "mac":
        destino = Path.home() / "Library" / "LaunchAgents" / (rotulo() + ".plist")
        if simular:
            print("Tiraria {}".format(destino))
            return 0
        subprocess.run(["launchctl", "bootout", "gui/" + str(os.getuid()), str(destino)], capture_output=True)
        if destino.exists():
            destino.unlink()
    elif SISTEMA == "windows":
        cmd = "Unregister-ScheduledTask -TaskName '{}' -Confirm:$false".format(nome_da_tarefa_windows())
        if simular:
            print("Rodaria no PowerShell:\n" + cmd)
            return 0
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd], capture_output=True,
                       creationflags=SEM_JANELA)
    else:
        if simular:
            print("Tiraria do crontab a linha marcada com " + rotulo())
            return 0
        atual = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
        subprocess.run(["crontab", "-"], input="\n".join(l for l in atual.splitlines() if rotulo() not in l) + "\n", text=True)
    estado = ler_estado()
    estado.update({"ligada": False, "desligada_em": iso(agora())})
    gravar_estado(estado)
    print("Rotina do vault desligada. O vault continua como está; nada foi apagado.")
    return 0


def notas_da_rotina_para_revisar():
    n = 0
    for nota in (KIT / "vault").rglob("*.md"):
        texto = nota.read_text(encoding="utf-8", errors="ignore")
        if texto.startswith("---"):
            cab = texto[3:texto.find("\n---", 3)].lower()
            if "origem: rotina" in cab and "revisar: sim" in cab:
                n += 1
    return n


def resumo_do_estado():
    e = ler_estado()
    return {"ligada": bool(e.get("ligada")), "horas": e.get("horas") or ([e["hora"]] if e.get("hora") else []),
            "envia": e.get("enviar", True), "ultimo_envio": e.get("ultimo_envio"), "ultima_alimentacao": e.get("ultima_alimentacao"),
            "ultima_rodada": e.get("ultima_rodada"), "ultimo_resultado": e.get("ultimo_resultado"),
            "coletas_pendentes": len(e.get("coletas_pendentes", [])), "notas_para_revisar": notas_da_rotina_para_revisar()}


def mostrar_estado(como_json):
    r = resumo_do_estado()
    if como_json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0
    print("Rotina do vault: {}".format("ligada, todo dia às " + ", ".join(r["horas"]) if r["ligada"] else "desligada"))
    if r["ligada"]:
        print("Envio automático do reporte: {}".format("sim" if r["envia"] else "não (vai quando você fechar o dia)"))
    print("Última alimentação: {}".format((r["ultima_alimentacao"] or "nenhuma ainda")[:16].replace("T", " ")))
    if r["ultima_rodada"]:
        print("Última rodada: {} ({}{})".format(r["ultima_rodada"][:16].replace("T", " "), r["ultimo_resultado"],
                                                 ", " + r["ultimo_envio"] if r["ultimo_envio"] else ""))
    print("Notas escritas pela rotina esperando a sua revisão: {}".format(r["notas_para_revisar"]))
    if r["coletas_pendentes"]:
        print("Coletas ainda não processadas: {}".format(r["coletas_pendentes"]))
    return 0


def valor(argv, nome, padrao=None):
    if nome in argv:
        i = argv.index(nome)
        if i + 1 < len(argv):
            return argv[i + 1]
    return padrao


def main(argv):
    if sys.stdout is None or sys.stderr is None:  # pythonw.exe (rodada agendada no Windows) não tem console
        PRIVADO.mkdir(parents=True, exist_ok=True)
        saida = open(PRIVADO / "agendador.log", "a", encoding="utf-8")
        sys.stdout = sys.stdout or saida
        sys.stderr = sys.stderr or saida
    if "--estado" in argv:
        return mostrar_estado("--json" in argv)
    if "--ligar" in argv:
        padrao = ",".join(ler_estado().get("horas") or HORAS_PADRAO)
        return ligar(valor(argv, "--horas", valor(argv, "--hora", padrao)), "--simular" in argv, "--sem-envio" not in argv)
    if "--desligar" in argv:
        return desligar("--simular" in argv)
    if "--rodar" in argv:
        return rodar()
    if "--coletar" in argv:
        resumo, _ = coletar()
        print(resumo.relative_to(KIT).as_posix() if resumo else "nada novo")
        return 0
    if "--concluir" in argv:
        nome = valor(argv, "--concluir")
        if not nome:
            print("informe o arquivo da coleta")
            return 2
        return concluir(nome)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
