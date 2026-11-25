#!/usr/bin/env python3
"""Testes da versão Codex do kit (`agente: codex`). Os critérios estão em docs/KIT-CODEX.md.

Uso (na raiz do kit-cliente):
    KIT_SELO_SEGREDO=teste-local-descartavel python3 testes/testar_codex.py -v

Monta kits Codex de teste numa pasta temporária a partir de uma CÓPIA do manifesto de exemplo
(outro slug, `agente: codex`, bloco `mcp` de teste): nunca toca em saida/ nem no manifesto
publicado. Não usa rede, não instala nada e não precisa do Codex: o `codex` que
`ferramentas/mcp.py` chama aqui é um dublê que só registra os argumentos recebidos.
A prova com o Codex de verdade e um servidor MCP real é testes/validar_codex_real.sh.
Só biblioteca padrão, compatível com Python 3.9.
"""
import http.server
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "montador"))
import montar  # noqa: E402
import atualizar  # noqa: E402

MODELO = RAIZ / "modelo"
MCP_TESTE = {"nome": "exemplo-os", "url": "https://mcp.exemplo.invalid/mcp", "perfil": "leitura",
             "variavel": "EXEMPLO_OS_MCP_TOKEN"}
SKILLS_BASE_CODEX = {"criar-skill", "cuidar-do-vault", "extrair-contexto", "fechar-o-dia", "pedir-ajuda",
                     "perfil-de-interacao", "preparar-ambiente", "proximo-passo", "auditar-contexto"}
SKILLS_DA_FRENTE = {"dossie-de-conta", "escrever-com-a-minha-voz", "revisar-texto"}
TEXTOS = (".md", ".json", ".sh", ".command", ".ps1", ".cmd")
MARCAS_DO_CLAUDE = ("Claude Code", "CLAUDE.md", ".claude/", "Claude do kit", "ao Claude", "pelo Claude",
                    "claude-code", "claude-app", "claude.ai", "claude://")

DUBLE_DO_CODEX = """#!/bin/bash
# Dublê do codex para os testes: registra os argumentos e finge o registro do servidor.
echo "$*" >> "$CODEX_DUBLE_LOG"
case "$1 $2" in
  "mcp add") [ "${CODEX_DUBLE_FALHAR_ADD:-0}" = 1 ] && exit 1; touch "$CODEX_DUBLE_LOG.add"; exit 0 ;;
  "mcp remove") rm -f "$CODEX_DUBLE_LOG.add"; exit 0 ;;
  "mcp get")
    if [ -f "$CODEX_DUBLE_LOG.add" ]; then
      printf '{"name":"%s","enabled":true,"transport":{"type":"streamable_http","url":"%s","bearer_token_env_var":"%s"}}\\n' "$3" "$CODEX_DUBLE_URL" "${CODEX_DUBLE_VAR:-EXEMPLO_OS_MCP_TOKEN}"
      exit 0
    fi
    echo "No MCP server named $3" >&2; exit 1 ;;
esac
exit 0
"""


def py(kit, *args, check=False, env=None, entrada=None):
    r = subprocess.run([sys.executable] + list(args), cwd=str(kit), capture_output=True, text=True,
                       env=env, input=entrada)
    if check and r.returncode != 0:
        raise AssertionError("{} falhou:\n{}{}".format(" ".join(args), r.stdout, r.stderr))
    return r


def manifesto_de_teste(sistema, agente="codex", mcp=MCP_TESTE):
    m = json.loads((RAIZ / "manifestos" / "exemplo-marina-duarte.json").read_text(encoding="utf-8"))
    m["cliente"]["slug"] = "teste-{}-{}".format(agente, sistema)
    m["cliente"]["sistema"] = sistema
    m.pop("entrega", None)
    if agente == "codex":
        m["agente"] = "codex"
        if mcp:
            m["mcp"] = dict(mcp)
    return m


class Kits:
    """Um kit Codex por sistema e um kit Claude de controle, montados uma vez para a suíte."""
    pasta = None
    kits = {}

    @classmethod
    def preparar(cls):
        if cls.pasta:
            return
        cls.pasta = Path(tempfile.mkdtemp(prefix="kit-teste-codex-"))
        montar.SAIDA = cls.pasta / "saida"
        for chave, sistema, agente in (("mac", "mac", "codex"), ("windows", "windows", "codex"), ("claude", "mac", "claude")):
            arq = cls.pasta / ("manifesto-" + chave + ".json")
            arq.write_text(json.dumps(manifesto_de_teste(sistema, agente), ensure_ascii=False), encoding="utf-8")
            with open(os.devnull, "w") as nulo:
                saida_padrao, sys.stdout = sys.stdout, nulo
                try:
                    cls.kits[chave] = montar.montar(str(arq), {"--rascunho", "--permitir-semente"})
                finally:
                    sys.stdout = saida_padrao

    @classmethod
    def limpar(cls):
        if cls.pasta:
            shutil.rmtree(cls.pasta, ignore_errors=True)


def setUpModule():
    Kits.preparar()


def tearDownModule():
    Kits.limpar()


def textos_do_kit(kit):
    for arq in kit.rglob("*"):
        if not arq.is_file() or ".git" in arq.parts or ".venv" in arq.parts:
            continue
        if arq.suffix in TEXTOS:
            yield arq.relative_to(kit).as_posix(), arq.read_text(encoding="utf-8", errors="ignore")


# ---------------------------------------------------------------- C1

class Manifesto(unittest.TestCase):
    def conferir(self, m):
        perfis = json.loads((RAIZ / "perfis" / "perfis.json").read_text(encoding="utf-8"))
        return montar.conferir_manifesto(m, perfis, rascunho=True, permitir_semente=True)

    def test_agente_ausente_vale_claude(self):
        m = manifesto_de_teste("mac", agente="claude")
        self.conferir(m)
        self.assertEqual(montar.agente_do(m), "claude")

    def test_agente_codex_aceito(self):
        m = manifesto_de_teste("mac")
        self.conferir(m)
        self.assertEqual(montar.agente_do(m), "codex")

    def test_agente_desconhecido_recusado(self):
        m = manifesto_de_teste("mac")
        m["agente"] = "gemini"
        with self.assertRaises(montar.Recusa) as cm:
            self.conferir(m)
        self.assertIn("agente", str(cm.exception))

    def test_mcp_valido(self):
        self.conferir(manifesto_de_teste("mac"))
        loopback = dict(MCP_TESTE, url="http://127.0.0.1:8765/mcp")
        self.conferir(manifesto_de_teste("mac", mcp=loopback))
        self.conferir(manifesto_de_teste("mac", mcp=None))

    def test_mcp_invalido_recusado(self):
        errados = [
            dict(MCP_TESTE, nome="Exemplo OS"),
            dict(MCP_TESTE, url="http://mcp.exemplo.com.br/mcp"),
            dict(MCP_TESTE, url="mcp.exemplo.com.br/mcp"),
            dict(MCP_TESTE, perfil="admin"),
            dict(MCP_TESTE, variavel="token"),
            {k: v for k, v in MCP_TESTE.items() if k != "nome"},
            dict(MCP_TESTE, token="abc123"),
        ]
        for errado in errados:
            with self.assertRaises(montar.Recusa, msg=json.dumps(errado)) as cm:
                self.conferir(manifesto_de_teste("mac", mcp=errado))
            self.assertIn("mcp", str(cm.exception))


# ---------------------------------------------------------------- C2

class Instalador(unittest.TestCase):
    def setUp(self):
        self.kit = Kits.kits["mac"]
        self.apps = json.loads((self.kit / "ambiente" / "apps.json").read_text(encoding="utf-8"))

    def test_catalogo_do_kit_troca_claude_por_codex(self):
        ids = {a["id"] for a in self.apps["apps"]}
        self.assertIn("codex", ids)
        self.assertNotIn("claude-code", ids)
        self.assertNotIn("claude-app", ids)
        codex = next(a for a in self.apps["apps"] if a["id"] == "codex")
        self.assertEqual(set(codex["perfis"].values()), {"obrigatorio"})
        self.assertEqual(codex["mac"]["instalar"], {"tipo": "script", "url": "https://chatgpt.com/codex/install.sh"})
        self.assertEqual(codex["linux"]["instalar"]["url"], "https://chatgpt.com/codex/install.sh")
        self.assertEqual(codex["windows"]["instalar"]["winget"], "OpenAI.Codex")
        self.assertEqual(codex["mac"]["checar"]["comando"], "codex")
        self.assertTrue(codex["links"]["site"].startswith("https://"))
        self.assertTrue(codex["links"]["download"].startswith("https://"))

    def test_catalogo_do_modelo_marca_o_agente_de_cada_app(self):
        dados = json.loads((MODELO / "ambiente" / "apps.json").read_text(encoding="utf-8"))
        por_id = {a["id"]: a for a in dados["apps"]}
        self.assertEqual(por_id["claude-code"]["agente"], "claude")
        self.assertEqual(por_id["claude-app"]["agente"], "claude")
        self.assertEqual(por_id["codex"]["agente"], "codex")
        for a in dados["apps"]:
            self.assertIn(a.get("agente", "todos"), ("claude", "codex", "todos"), a["id"])
        for s in dados["servicos"]:
            self.assertIn(s.get("agente", "todos"), ("claude", "codex", "todos"), s["nome"])
        self.assertTrue(any(s.get("agente") == "codex" for s in dados["servicos"]))

    def test_instalador_sh_leva_so_a_parte_do_codex(self):
        principal = (self.kit / "instalar" / "instalar.sh").read_text(encoding="utf-8")
        self.assertIn('. "$KIT/instalar/agente.sh"', principal)
        for funcao in ("agente_preparar", "agente_ligar", "agente_atalho"):
            self.assertIn(funcao, principal)
        parte = (self.kit / "instalar" / "agente.sh").read_text(encoding="utf-8")
        self.assertIn("Codex do kit", parte)
        self.assertIn("ferramentas/mcp.py --registrar", parte)
        self.assertIn(".root/mcp.env", parte)
        self.assertIn("exec codex", parte)
        self.assertNotIn("autonomia", parte)
        for sobra in ("agente-claude.sh", "agente-codex.sh", "agente-claude.ps1", "agente-codex.ps1"):
            self.assertFalse((self.kit / "instalar" / sobra).exists(), sobra)
        self.assertFalse((self.kit / "ferramentas" / "autonomia.py").exists())
        for nome in ("instalar.sh", "instalar.command", "agente.sh"):
            r = subprocess.run(["bash", "-n", str(self.kit / "instalar" / nome)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_instalar_command_vai_direto_ao_terminal_no_codex(self):
        texto = (self.kit / "instalar" / "instalar.command").read_text(encoding="utf-8")
        self.assertIn("onboarding.py", texto, "a página guiada fica atrás da checagem do agente")
        self.assertIn('"$AGENTE" = "claude"', texto)
        self.assertIn('bash "$DIR/instalar.sh"', texto)
        self.assertFalse((self.kit / "ferramentas" / "onboarding.py").exists())

    def test_ps1_leva_so_a_parte_do_codex(self):
        for nome in ("instalar.ps1", "agente.ps1"):
            dados = (self.kit / "instalar" / nome).read_bytes()
            self.assertEqual([b for b in dados if b > 127], [], "{} tem caractere fora do ASCII".format(nome))
        principal = (self.kit / "instalar" / "instalar.ps1").read_bytes().decode("ascii")
        self.assertIn('. (Join-Path $PSScriptRoot "agente.ps1")', principal)
        parte = (self.kit / "instalar" / "agente.ps1").read_bytes().decode("ascii")
        self.assertIn("Codex do kit", parte)
        self.assertIn("mcp.py --registrar", parte)
        self.assertNotIn("autonomia", parte)

    def test_links_do_kit_sem_claude_e_com_codex(self):
        links = (self.kit / "LINKS.md").read_text(encoding="utf-8")
        self.assertIn("[Codex", links)
        self.assertNotIn("Claude", links)
        self.assertIn("ChatGPT", links)

    def test_ambiente_conferir_lista_o_codex(self):
        conf = json.loads(py(self.kit, "ferramentas/ambiente.py", "--conferir", "--json").stdout)
        ids = [a["id"] for a in conf["apps"]]
        self.assertIn("codex", ids)
        self.assertNotIn("claude-code", ids)
        self.assertEqual(len(ids), 11)


# ---------------------------------------------------------------- C3

class Instrucoes(unittest.TestCase):
    def setUp(self):
        self.kit = Kits.kits["mac"]

    def test_agents_md_renderizado(self):
        arq = self.kit / "AGENTS.md"
        self.assertTrue(arq.exists())
        self.assertFalse((self.kit / "CLAUDE.md").exists())
        texto = arq.read_text(encoding="utf-8")
        self.assertNotIn("{{", texto)
        cliente = json.loads((self.kit / ".root" / "cliente.json").read_text(encoding="utf-8"))
        for esperado in ("Marina Duarte", cliente["kit_id"], ".agents/skills", MCP_TESTE["nome"], "Codex"):
            self.assertIn(esperado, texto, esperado)
        self.assertIn("Codex", texto.splitlines()[0])

    def test_readme_perfil_e_vault_falam_do_codex(self):
        for rel in ("README.md", "perfil.md", "vault/00 - Comece aqui.md", "COMECE-AQUI.md", "oficina/LEIA-ME.md"):
            texto = (self.kit / rel).read_text(encoding="utf-8")
            self.assertIn("Codex", texto, rel)
            self.assertNotIn("{{", texto, rel)
        self.assertIn("Codex do kit", (self.kit / "COMECE-AQUI.md").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- C4

class Skills(unittest.TestCase):
    def setUp(self):
        self.kit = Kits.kits["mac"]
        self.pasta = self.kit / ".agents" / "skills"

    def test_pastas_e_cabecalhos(self):
        self.assertTrue(self.pasta.is_dir())
        pastas = {p.name for p in self.pasta.iterdir() if p.is_dir()}
        self.assertEqual(pastas, SKILLS_BASE_CODEX | SKILLS_DA_FRENTE)
        kit_id = json.loads((self.kit / ".root" / "cliente.json").read_text(encoding="utf-8"))["kit_id"]
        for nome in pastas:
            texto = (self.pasta / nome / "SKILL.md").read_text(encoding="utf-8")
            self.assertRegex(texto, r"(?m)^name: " + re.escape(nome) + r"$", nome)
            self.assertRegex(texto, r"(?m)^description: \S", nome)
            self.assertNotRegex(texto, r"(?m)^tools:", nome)
            self.assertIn("<!-- {} -->".format(kit_id), texto, nome)

    def test_catalogo_bate_com_as_pastas(self):
        cat = json.loads((self.kit / "catalogo.json").read_text(encoding="utf-8"))
        nomes = {s["nome"] for s in cat["skills"] if s["estado"] == "ativa"}
        self.assertEqual(nomes, {p.name for p in self.pasta.iterdir() if p.is_dir()})
        self.assertEqual({s["origem"] for s in cat["skills"]}, {"root", "frente"})
        self.assertEqual(py(self.kit, "ferramentas/skills.py", "listar").returncode, 0)
        for s in cat["skills"]:
            if s["nome"] != "extrair-contexto":  # o resumo dela cita a exportação do claude.ai como fonte de dado
                self.assertNotIn("Claude", s["resumo"], s["nome"])

    def test_oficina_promove_para_agents_skills(self):
        kit = Kits.pasta / "oficina-codex"
        if kit.exists():
            shutil.rmtree(kit)
        shutil.copytree(self.kit, kit)
        py(kit, "ferramentas/skills.py", "nova", "resumo-da-semana", "Resume as reuniões da semana em decisões e pendências", check=True)
        pasta = kit / "oficina" / "resumo-da-semana"
        (pasta / "SKILL.md").write_text(
            "---\nname: resumo-da-semana\ndescription: Resume as reuniões da semana num quadro de decisões e pendências. "
            "Use quando a pessoa pedir o resumo da semana.\n---\n\n# Resumo da semana\n\n## Quando usar\n\n"
            "Na sexta, com as atas da semana em entrada/atas.\n\n## Como fazer\n\n1. Ler cada ata.\n"
            "2. Separar decisão de pendência.\n3. Montar o quadro.\n\n## Como entregar\n\n"
            "entregas/AAAA-MM-DD - resumo.md, sempre rascunho.\n", encoding="utf-8")
        (pasta / "TESTES.md").write_text(
            "# Testes\n\n## Teste 1 · 2026-11-04\n\n- Caso: atas da semana de um time comercial\n"
            "- Pedido: resumo da semana\n- Resultado: aprovado\n- O que ajustou: nada\n", encoding="utf-8")
        py(kit, "ferramentas/skills.py", "conferir", "resumo-da-semana", check=True)
        py(kit, "ferramentas/skills.py", "promover", "resumo-da-semana", check=True)
        self.assertTrue((kit / ".agents" / "skills" / "resumo-da-semana" / "SKILL.md").exists())
        self.assertFalse((kit / ".claude").exists())
        py(kit, "ferramentas/verificar.py", "--silencioso", "--sem-rede", check=True)
        prog = {p["id"]: p for p in json.loads((kit / ".root" / "progresso.json").read_text(encoding="utf-8"))["passos"]}
        self.assertTrue(prog["primeira-skill"]["feito"], prog["primeira-skill"]["detalhe"])
        self.assertEqual(py(kit, "ferramentas/skills.py", "listar").returncode, 0)

    def test_verificar_cobra_o_registro_do_mcp(self):
        py(self.kit, "ferramentas/verificar.py", "--silencioso", "--sem-rede", check=True)
        prog = json.loads((self.kit / ".root" / "progresso.json").read_text(encoding="utf-8"))
        self.assertEqual(len(prog["passos"]), 7)
        instalar = next(p for p in prog["passos"] if p["id"] == "instalar")
        self.assertFalse(instalar["feito"])
        self.assertIn("mcp.py --registrar", instalar["detalhe"])

    def test_texto_das_skills_fala_do_codex(self):
        for nome in SKILLS_BASE_CODEX | SKILLS_DA_FRENTE:
            texto = (self.pasta / nome / "SKILL.md").read_text(encoding="utf-8")
            for marca in MARCAS_DO_CLAUDE:
                self.assertNotIn(marca, texto, "{}: {}".format(nome, marca))
        extrair = (self.pasta / "extrair-contexto" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("skill `auditar-contexto`", extrair)
        self.assertNotIn("auditor-de-contexto", extrair)
        self.assertIn("Claude: Configurações > Privacidade > Exportar dados", extrair,
                      "a exportação do claude.ai continua como fonte de dado da pessoa")
        auditar = (self.pasta / "auditar-contexto" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("00 - Auditoria.md", auditar)


# ---------------------------------------------------------------- C5

class Mcp(unittest.TestCase):
    """ferramentas/mcp.py: registro no Codex por `codex mcp add`, token fora do git."""

    @classmethod
    def setUpClass(cls):
        cls.duble = Kits.pasta / "duble-codex"
        cls.duble.mkdir(exist_ok=True)
        arq = cls.duble / "codex"
        arq.write_text(DUBLE_DO_CODEX, encoding="utf-8")
        arq.chmod(0o755)

    def setUp(self):
        self.kit = Kits.pasta / "mcp-{}".format(self._testMethodName)
        if self.kit.exists():
            shutil.rmtree(self.kit)
        shutil.copytree(Kits.kits["mac"], self.kit)
        self.casa = self.kit / "casa-vazia"
        self.casa.mkdir()
        self.log = self.kit / "codex-duble.log"
        self.token = "tk-teste-" + os.urandom(8).hex()

    def env(self, com_codex=True, token=True):
        e = {"PATH": (str(self.duble) + ":" if com_codex else "") + "/usr/bin:/bin",
             "HOME": str(self.casa), "CODEX_DUBLE_LOG": str(self.log), "CODEX_DUBLE_URL": MCP_TESTE["url"],
             "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "KIT_SELO_SEGREDO": "teste"}
        if token:
            e["KIT_MCP_TOKEN"] = self.token
        return e

    def conferir(self, **kw):
        r = py(self.kit, "ferramentas/mcp.py", "--conferir", "--json", env=self.env(**kw))
        return json.loads(r.stdout)

    def test_cliente_json_tem_mcp_sem_token(self):
        texto = (self.kit / ".root" / "cliente.json").read_text(encoding="utf-8")
        cliente = json.loads(texto)
        self.assertEqual(cliente["agente"], "codex")
        self.assertEqual(cliente["mcp"], MCP_TESTE)
        self.assertEqual(set(cliente["mcp"]), {"nome", "url", "perfil", "variavel"}, "só o NOME da variável, nunca o token")
        self.assertNotIn("token", {k.lower() for k in cliente} | {k.lower() for k in cliente["mcp"]})

    def test_gitignore_barra_o_env_do_mcp(self):
        self.assertIn(".root/mcp.env", (self.kit / ".gitignore").read_text(encoding="utf-8"))
        (self.kit / ".root" / "mcp.env").write_text("export X=y\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=str(self.kit), check=True, capture_output=True)
        r = subprocess.run(["git", "ls-files"], cwd=str(self.kit), capture_output=True, text=True)
        self.assertNotIn(".root/mcp.env", r.stdout.splitlines())

    def test_conferir_sem_codex_instalado(self):
        e = self.conferir(com_codex=False, token=False)
        self.assertEqual(e["nome"], MCP_TESTE["nome"])
        self.assertEqual(e["url"], MCP_TESTE["url"])
        self.assertEqual(e["variavel"], MCP_TESTE["variavel"])
        self.assertFalse(e["codex_instalado"])
        self.assertFalse(e["registrado"])
        self.assertFalse(e["token_presente"])
        self.assertFalse(e["pronto"])

    def test_registrar_grava_o_token_e_chama_codex_mcp_add(self):
        r = py(self.kit, "ferramentas/mcp.py", "--registrar", env=self.env())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        env_arq = self.kit / ".root" / "mcp.env"
        self.assertTrue(env_arq.exists())
        self.assertEqual(stat.S_IMODE(env_arq.stat().st_mode), 0o600)
        self.assertEqual(env_arq.read_text(encoding="utf-8").strip(), "export {}={}".format(MCP_TESTE["variavel"], self.token))
        chamadas = self.log.read_text(encoding="utf-8").splitlines()
        self.assertIn("mcp add {} --url {} --bearer-token-env-var {}".format(MCP_TESTE["nome"], MCP_TESTE["url"], MCP_TESTE["variavel"]), chamadas)
        self.assertNotIn(self.token, self.log.read_text(encoding="utf-8"), "o token não passa na linha de comando")
        self.assertNotIn(self.token, r.stdout + r.stderr, "o token não aparece na tela")
        e = self.conferir()
        self.assertTrue(e["codex_instalado"] and e["registrado"] and e["token_presente"] and e["pronto"], e)
        subprocess.run(["git", "add", "-A"], cwd=str(self.kit), check=True, capture_output=True)
        versionados = subprocess.run(["git", "ls-files"], cwd=str(self.kit), capture_output=True, text=True).stdout.splitlines()
        self.assertNotIn(".root/mcp.env", versionados)
        for rel in versionados:
            if (self.kit / rel).suffix in TEXTOS + (".py",):
                self.assertNotIn(self.token, (self.kit / rel).read_text(encoding="utf-8", errors="ignore"), rel)

    def test_registrar_de_novo_nao_duplica(self):
        py(self.kit, "ferramentas/mcp.py", "--registrar", env=self.env(), check=True)
        py(self.kit, "ferramentas/mcp.py", "--registrar", env=self.env(), check=True)
        chamadas = self.log.read_text(encoding="utf-8").splitlines()
        self.assertEqual(sum(1 for c in chamadas if c.startswith("mcp add ")), 2)
        self.assertNotIn("mcp remove {}".format(MCP_TESTE["nome"]), chamadas)
        self.assertTrue(self.conferir()["pronto"])

    def test_sem_token_e_sem_terminal_falha_sem_gravar(self):
        r = py(self.kit, "ferramentas/mcp.py", "--registrar", env=self.env(token=False), entrada="")
        self.assertEqual(r.returncode, 1)
        self.assertFalse((self.kit / ".root" / "mcp.env").exists())
        self.assertIn("KIT_MCP_TOKEN", r.stdout + r.stderr)

    def test_sem_codex_o_registro_avisa_e_guarda_o_token(self):
        r = py(self.kit, "ferramentas/mcp.py", "--registrar", env=self.env(com_codex=False))
        self.assertEqual(r.returncode, 1)
        self.assertTrue((self.kit / ".root" / "mcp.env").exists())
        self.assertIn("codex", (r.stdout + r.stderr).lower())

    def test_falha_de_registro_preserva_token_e_servidor(self):
        py(self.kit, "ferramentas/mcp.py", "--registrar", env=self.env(), check=True)
        anterior = (self.kit / ".root/mcp.env").read_bytes()
        e = self.env()
        e.update(KIT_MCP_TOKEN="outro-token", CODEX_DUBLE_FALHAR_ADD="1")
        r = py(self.kit, "ferramentas/mcp.py", "--registrar", env=e)
        self.assertEqual(r.returncode, 1)
        self.assertEqual((self.kit / ".root/mcp.env").read_bytes(), anterior)
        self.assertTrue(self.conferir()["pronto"])

    def test_registro_com_variavel_errada_nao_esta_pronto(self):
        py(self.kit, "ferramentas/mcp.py", "--registrar", env=self.env(), check=True)
        env = self.env()
        env["CODEX_DUBLE_VAR"] = "OUTRO_TOKEN"
        r = py(self.kit, "ferramentas/mcp.py", "--conferir", "--json", env=env)
        self.assertEqual(r.returncode, 1)
        self.assertFalse(json.loads(r.stdout)["pronto"])

    def test_testar_contrato_http(self):
        token = self.token
        resposta = {"codigo": 200, "valida": True, "sse": False}

        class Servidor(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                if self.headers.get("Authorization") != "Bearer " + token:
                    self.send_response(401)
                    self.end_headers()
                    return
                self.send_response(resposta["codigo"])
                self.send_header("Content-Type", "text/event-stream" if resposta["sse"] else "application/json")
                self.end_headers()
                resultado = {"jsonrpc": "2.0", "id": "kit-health", "result": {
                    "protocolVersion": "2025-03-26", "capabilities": {},
                    "serverInfo": {"name": "teste", "version": "1"}}}
                corpo = json.dumps(resultado) if resposta["valida"] else '<html>erro</html>'
                if resposta["sse"]:
                    corpo = 'event: message\ndata: ' + corpo + '\n\n'
                self.wfile.write(corpo.encode())

            do_GET = do_POST

            def log_message(self, *a):
                pass

        srv = http.server.HTTPServer(("127.0.0.1", 0), Servidor)
        th = threading.Thread(target=srv.serve_forever, daemon=True)
        th.start()
        try:
            cliente_arq = self.kit / ".root" / "cliente.json"
            cliente = json.loads(cliente_arq.read_text(encoding="utf-8"))
            cliente["mcp"]["url"] = "http://127.0.0.1:{}/mcp".format(srv.server_port)
            cliente_arq.write_text(json.dumps(cliente, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (self.kit / ".root" / "mcp.env").write_text("export {}={}\n".format(MCP_TESTE["variavel"], token), encoding="utf-8")
            for codigo, valida, sse, esperado in [(200, True, False, 0), (200, True, True, 0),
                    (200, False, False, 1), (400, True, False, 1), (404, True, False, 1),
                    (406, True, False, 1), (500, True, False, 1), (503, True, False, 1)]:
                with self.subTest(codigo=codigo, valida=valida, sse=sse):
                    resposta.update(codigo=codigo, valida=valida, sse=sse)
                    r = py(self.kit, "ferramentas/mcp.py", "--testar", env=self.env(token=False))
                    self.assertEqual(r.returncode, esperado, r.stdout + r.stderr)
                    self.assertIn("401", r.stdout)
            resposta.update(codigo=200, valida=True, sse=False)
            (self.kit / ".root" / "mcp.env").write_text("export {}=errado\n".format(MCP_TESTE["variavel"]), encoding="utf-8")
            r = py(self.kit, "ferramentas/mcp.py", "--testar", env=self.env(token=False))
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        finally:
            srv.shutdown()
            srv.server_close()


# ---------------------------------------------------------------- C6

class NadaDoClaude(unittest.TestCase):
    def setUp(self):
        self.kit = Kits.kits["mac"]

    def test_sem_arquivos_do_claude(self):
        for rel in (".claude", "CLAUDE.md", "ferramentas/autonomia.py", "onboarding", "ferramentas/onboarding.py",
                    "ferramentas/fontes_publicas.py"):
            self.assertFalse((self.kit / rel).exists(), rel)

    def test_textos_sem_claude(self):
        # Única exceção: extrair-contexto cita a exportação do claude.ai como fonte de dado da pessoa,
        # no SKILL.md e no resumo dela dentro do catalogo.json.
        for rel, texto in textos_do_kit(self.kit):
            if rel == ".agents/skills/extrair-contexto/SKILL.md":
                continue
            if rel == "catalogo.json":
                skills = json.loads(texto)["skills"]
                texto = json.dumps([s for s in skills if s["nome"] != "extrair-contexto"], ensure_ascii=False)
            self.assertNotRegex(texto, r"\bClaude\b", rel)
            for marca in (".claude", "claude-code", "claude-app", "claude.ai", "claude://"):
                self.assertNotIn(marca, texto, "{}: {}".format(rel, marca))

    def test_python_das_ferramentas_sem_caminho_do_claude(self):
        for arq in (self.kit / "ferramentas").glob("*.py"):
            texto = arq.read_text(encoding="utf-8")
            if arq.name != "agente.py":
                self.assertNotIn('".claude"', texto, arq.name)
                self.assertNotIn("'.claude'", texto, arq.name)
            for marca in ("Claude Code", "claude.ai", "CLAUDE.md"):
                self.assertNotIn(marca, texto, "{}: {}".format(arq.name, marca))

    def test_passos_convertidos(self):
        texto = (self.kit / "ferramentas" / "passos.json").read_text(encoding="utf-8")
        self.assertNotIn("Claude", texto)
        self.assertIn("Codex", texto)
        self.assertEqual(len(json.loads(texto)["passos"]), 7)


# ---------------------------------------------------------------- C7

class KitWindowsCodex(unittest.TestCase):
    def setUp(self):
        self.kit = Kits.kits["windows"]

    def test_regras_do_windows_valem_no_codex(self):
        for md in self.kit.rglob("*.md"):
            self.assertNotIn("python3 ", md.read_text(encoding="utf-8"), md.relative_to(self.kit).as_posix())
        skill = (self.kit / ".agents" / "skills" / "proximo-passo" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn(".venv/Scripts/python ferramentas/verificar.py", skill)
        self.assertIn("instalar\\instalar.cmd", (self.kit / "COMECE-AQUI.md").read_text(encoding="utf-8"))
        for nome in ("instalar.ps1", "instalar.cmd"):
            dados = (self.kit / "instalar" / nome).read_bytes()
            self.assertEqual([b for b in dados if b > 127], [], nome)
        apps = json.loads((self.kit / "ambiente" / "apps.json").read_text(encoding="utf-8"))["apps"]
        codex = next(a for a in apps if a["id"] == "codex")
        self.assertEqual(codex["windows"]["instalar"]["winget"], "OpenAI.Codex")
        self.assertFalse((self.kit / "CLAUDE.md").exists())
        self.assertTrue((self.kit / "AGENTS.md").exists())


# ---------------------------------------------------------------- C8

class KitClaudeIntacto(unittest.TestCase):
    def setUp(self):
        self.kit = Kits.kits["claude"]

    def test_kit_claude_nao_ganha_nada_do_codex(self):
        for rel in ("AGENTS.md", ".agents", "ferramentas/mcp.py"):
            self.assertFalse((self.kit / rel).exists(), rel)
        for rel in ("CLAUDE.md", ".claude/skills/validar-onboarding/SKILL.md", ".claude/agents/auditor-de-contexto.md",
                    ".claude/settings.json", "ferramentas/autonomia.py", "ferramentas/onboarding.py", "ferramentas/agente.py"):
            self.assertTrue((self.kit / rel).exists(), rel)
        ids = {a["id"] for a in json.loads((self.kit / "ambiente" / "apps.json").read_text(encoding="utf-8"))["apps"]}
        self.assertIn("claude-code", ids)
        self.assertNotIn("codex", ids)
        self.assertNotIn("Codex", (self.kit / "LINKS.md").read_text(encoding="utf-8"))
        self.assertNotIn("Codex", (self.kit / "README.md").read_text(encoding="utf-8"))
        cliente = json.loads((self.kit / ".root" / "cliente.json").read_text(encoding="utf-8"))
        self.assertEqual(cliente["agente"], "claude")
        self.assertNotIn("mcp", cliente)
        conf = json.loads(py(self.kit, "ferramentas/ambiente.py", "--conferir", "--json").stdout)
        self.assertEqual(len(conf["apps"]), 12)


# ---------------------------------------------------------------- C9

class Conversao(unittest.TestCase):
    def test_para_codex(self):
        casos = [
            ("abra o Claude Code na pasta", "abra o Codex na pasta"),
            ("leia `CLAUDE.md` antes", "leia `AGENTS.md` antes"),
            ("vai para `.claude/skills/` depois", "vai para `.agents/skills/` depois"),
            ("o atalho \"Claude do kit\"", "o atalho \"Codex do kit\""),
            ("Chame o agente `auditor-de-contexto` para a auditoria", "Use a skill `auditar-contexto` para a auditoria"),
            ("rode `claude` dentro da pasta", "rode `codex` dentro da pasta"),
            ("peça ao Claude: \"confere\"", "peça ao Codex: \"confere\""),
            ("O Claude lê o perfil", "O Codex lê o perfil"),
            ("pela interface do Claude", "pela interface do Codex"),
        ]
        for antes, depois in casos:
            self.assertEqual(montar.para_codex(antes), depois)
        preservados = [
            "as exportações do ChatGPT e do Claude da pessoa",
            "zip do Claude descompactado",
            "Claude: Configurações > Privacidade > Exportar dados",
            "memória do Claude) ou responda",
            "entre o Claude e o ChatGPT",
            "exportação Claude de AAAA-MM-DD",
            "`Claude e ChatGPT.md`",
            "entrada/claude",
            "iniciativa_claude: sempre",
        ]
        for texto in preservados:
            self.assertEqual(montar.para_codex(texto), texto)

    def test_catalogo_por_agente(self):
        codex = {s["nome"]: s for s in montar.montar_catalogo([], "1.4.0", None, agente="codex")["skills"]}
        self.assertIn("auditar-contexto", codex)
        self.assertNotIn("validar-onboarding", codex)
        self.assertEqual(codex["auditar-contexto"]["origem"], "root")
        self.assertNotIn("Claude", codex["criar-skill"]["resumo"])
        claude = {s["nome"] for s in montar.montar_catalogo([], "1.4.0")["skills"]}
        self.assertIn("validar-onboarding", claude)
        self.assertNotIn("auditar-contexto", claude)


# ---------------------------------------------------------------- C10

class Atualizacao(unittest.TestCase):
    def test_arquivos_comuns_por_agente(self):
        codex = dict(atualizar.arquivos_comuns("codex"))
        claude = dict(atualizar.arquivos_comuns("claude"))
        self.assertFalse([d for d in codex.values() if d.startswith(".claude/")])
        self.assertNotIn("ferramentas/autonomia.py", codex.values())
        for comum in ("ferramentas/agente.py", "ferramentas/mcp.py", "ferramentas/skills.py", "instalar/instalar.command",
                      "instalar/agente.sh", "instalar/agente.ps1"):
            self.assertIn(comum, codex.values(), comum)
        self.assertEqual(codex["instalar/agente-codex.sh"], "instalar/agente.sh")
        self.assertEqual(claude["instalar/agente-claude.sh"], "instalar/agente.sh")
        # as permissões do kit Claude saem do manifesto (settings_do_kit), não de cópia do modelo
        self.assertNotIn(".claude/settings.json", claude.values())
        self.assertIs(atualizar.settings_do_kit, montar.settings_do_kit)
        self.assertIn("ferramentas/autonomia.py", claude.values())
        self.assertNotIn("ferramentas/mcp.py", claude.values())
        self.assertIn("ferramentas/agente.py", claude.values())

    def test_skills_de_base_por_agente(self):
        codex = set(montar.skills_de_base("codex"))
        self.assertIn("auditar-contexto", codex)
        self.assertNotIn("validar-onboarding", codex)
        self.assertEqual(montar.raiz_das_skills("codex"), ".agents")
        self.assertEqual(montar.raiz_das_skills("claude"), ".claude")


if __name__ == "__main__":
    unittest.main()
