#!/usr/bin/env python3
"""Testes dos sistemas de trabalho do kit Claude (plugins, conectores, credenciais) e da conversa conduzida.

Uso (na raiz do kit-cliente):
    KIT_SELO_SEGREDO=teste-local-descartavel python3 testes/testar_sistemas.py -v

Monta kits numa pasta temporária a partir de uma CÓPIA do manifesto de exemplo, com um bloco
`sistemas` fictício. Não usa rede, não instala plugin e não abre janela: a credencial é gravada
no modo de teste (KIT_MODO_TESTE=1), com HOME e CLAUDE_CONFIG_DIR apontando para a pasta temporária.
Só biblioteca padrão, compatível com Python 3.9.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "montador"))
import montar  # noqa: E402

MODELO = RAIZ / "modelo"
SEGREDO_DE_TESTE = "Ab c'd\\e#f\"g ç"

SISTEMAS = {
    "plugins": [{
        "nome": "plugin Exemplo", "marketplace": "exemplo", "repo": "exemplo/plugin-exemplo", "plugin": "exemplo",
        "para_que": "consulta o sistema de exemplo", "teste": {"script": "mcp/servidor.py", "args": ["--selftest"]},
        "servidores": {"exemplo-erp": {"leitura": ["listar_contas"], "escrita": ["incluir_conta", "baixar_conta"]}},
    }],
    "conectores": [{
        "id": "erp", "nome": "ERP Exemplo", "para_que": "o ERP da empresa", "link": "https://claude.ai/directory/connectors/exemplo",
        "ferramenta_de_teste": "erp_listar", "leitura": ["erp_listar"], "escrita": ["erp_executar"],
    }],
    "credenciais": [{
        "id": "erp", "nome": "Login do ERP", "para": "o plugin entra no ERP", "arquivo": "~/.exemplo/credenciais.env",
        "como_recuperar": "use a opção de recuperar a senha na tela do ERP",
        "campos": [
            {"nome": "ERP_EMAIL", "valor": "pessoa@exemplo.com"},
            {"nome": "ERP_ANON_KEY", "valor": "chave-publica", "publico": True},
            {"nome": "ERP_PASSWORD", "segredo": True, "pergunta": "Senha do ERP"},
        ],
    }],
    "regras": ["Prefira o plugin ao conector para gravar."],
}


def manifesto_base(slug, sistema="windows", sistemas=True):
    m = json.loads((RAIZ / "manifestos" / "exemplo-marina-duarte.json").read_text(encoding="utf-8"))
    m["cliente"]["slug"] = slug
    m["cliente"]["sistema"] = sistema
    m["cliente"]["github"] = None
    m.pop("entrega", None)
    if sistemas:
        m["sistemas"] = json.loads(json.dumps(SISTEMAS))
    return m


def montar_kit(pasta, m):
    arq = pasta / (m["cliente"]["slug"] + ".json")
    arq.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    with open(os.devnull, "w") as nulo:
        saida, sys.stdout = sys.stdout, nulo
        try:
            return montar.montar(str(arq), {"--rascunho", "--permitir-semente"})
        finally:
            sys.stdout = saida


class Kits:
    pasta = None
    com = sem = None

    @classmethod
    def preparar(cls):
        if cls.pasta:
            return
        cls.pasta = Path(tempfile.mkdtemp(prefix="kit-sistemas-"))
        montar.SAIDA = cls.pasta / "saida"
        cls.com = montar_kit(cls.pasta, manifesto_base("teste-sistemas-win"))
        cls.sem = montar_kit(cls.pasta, manifesto_base("teste-sem-sistemas-mac", "mac", sistemas=False))

    @classmethod
    def limpar(cls):
        if cls.pasta:
            shutil.rmtree(cls.pasta, ignore_errors=True)


def setUpModule():
    Kits.preparar()


def tearDownModule():
    Kits.limpar()


def ambiente_de_teste(home, segredo=SEGREDO_DE_TESTE):
    env = dict(os.environ, HOME=str(home), USERPROFILE=str(home), CLAUDE_CONFIG_DIR=str(home / ".claude"), KIT_MODO_TESTE="1")
    env["KIT_SEGREDO_PARA_TESTE"] = segredo
    return env


def sistemas_py(kit, env, *args):
    return subprocess.run([sys.executable, "ferramentas/sistemas.py"] + list(args), cwd=str(kit), env=env,
                          capture_output=True, text=True)


class Manifesto(unittest.TestCase):
    def faltas(self, mexer, agente="claude"):
        s = json.loads(json.dumps(SISTEMAS))
        mexer(s)
        return montar.conferir_sistemas(s, agente)

    def test_bloco_valido_passa(self):
        self.assertEqual(montar.conferir_sistemas(SISTEMAS), [])
        self.assertEqual(montar.conferir_sistemas(None), [])

    def test_segredo_nunca_vem_com_valor(self):
        f = self.faltas(lambda s: s["credenciais"][0]["campos"][2].update(valor="123"))
        self.assertTrue(any("é segredo e não leva valor" in x for x in f), f)

    def test_campo_com_cara_de_segredo_precisa_ser_segredo(self):
        f = self.faltas(lambda s: s["credenciais"][0]["campos"].append({"nome": "ERP_TOKEN", "valor": "abc"}))
        self.assertTrue(any("cara de segredo" in x for x in f), f)

    def test_chave_com_valor_so_se_publica(self):
        f = self.faltas(lambda s: s["credenciais"][0]["campos"][1].pop("publico"))
        self.assertTrue(any("só se for pública" in x for x in f), f)

    def test_kit_codex_nao_tem_sistemas(self):
        self.assertTrue(montar.conferir_sistemas(SISTEMAS, "codex"))

    def test_formatos(self):
        self.assertTrue(self.faltas(lambda s: s["plugins"][0].update(repo="sem-barra")))
        self.assertTrue(self.faltas(lambda s: s["credenciais"][0].update(arquivo="/etc/credenciais.env")))
        self.assertTrue(self.faltas(lambda s: s["credenciais"][0].update(arquivo="~/../fora.env")))
        self.assertTrue(self.faltas(lambda s: s["plugins"][0]["teste"].update(script="../fora.py")))
        self.assertTrue(self.faltas(lambda s: s["conectores"][0].update(link="http://inseguro")))
        self.assertTrue(self.faltas(lambda s: s["conectores"][0].update(ferramenta_de_teste="erp_executar")))
        self.assertTrue(self.faltas(lambda s: s["plugins"][0]["servidores"]["exemplo-erp"]["leitura"].append("incluir_conta")))
        self.assertTrue(self.faltas(lambda s: s.update(outro=1)))
        self.assertTrue(self.faltas(lambda s: s.update(plugins=[], conectores=[])))

    def test_manifesto_inteiro_recusa_segredo(self):
        m = manifesto_base("teste-recusa")
        m["sistemas"]["credenciais"][0]["campos"][2]["valor"] = "vazou"
        with self.assertRaises(montar.Recusa):
            montar.conferir_manifesto(m, json.loads((RAIZ / "perfis" / "perfis.json").read_text(encoding="utf-8")), True, True)


class KitComSistemas(unittest.TestCase):
    kit = None

    @classmethod
    def setUpClass(cls):
        cls.kit = Kits.com

    def test_pecas_do_kit(self):
        for rel in ("ferramentas/sistemas.py", "instalar/pedir-segredo.ps1", ".root/sistemas.json",
                    ".claude/skills/comecar/SKILL.md", ".claude/skills/ligar-sistemas/SKILL.md"):
            self.assertTrue((self.kit / rel).exists(), rel)
        nomes = {s["nome"] for s in json.loads((self.kit / "catalogo.json").read_text(encoding="utf-8"))["skills"]}
        self.assertTrue({"comecar", "ligar-sistemas"} <= nomes)

    def test_sistemas_json_sem_segredo(self):
        s = json.loads((self.kit / ".root" / "sistemas.json").read_text(encoding="utf-8"))
        for c in s["credenciais"]:
            for campo in c["campos"]:
                if campo.get("segredo"):
                    self.assertNotIn("valor", campo)
        self.assertIn("_leia", s)

    def test_permissoes(self):
        perm = json.loads((self.kit / ".claude" / "settings.json").read_text(encoding="utf-8"))["permissions"]
        self.assertIn("mcp__plugin_exemplo_exemplo-erp__listar_contas", perm["allow"])
        for nome in ("mcp__plugin_exemplo_exemplo-erp__incluir_conta", "mcp__plugin_exemplo_exemplo-erp__baixar_conta",
                     "mcp__*__erp_executar"):
            self.assertIn(nome, perm["ask"])
        self.assertFalse(set(perm["ask"]) & set(perm["allow"]))
        self.assertIn("Bash", perm["allow"])

    def test_passo_de_sistemas(self):
        passos = json.loads((self.kit / "ferramentas" / "passos.json").read_text(encoding="utf-8"))["passos"]
        ids = [p["id"] for p in passos]
        self.assertEqual(ids[:3], ["instalar", "perfil", "sistemas"])
        texto = json.dumps(passos, ensure_ascii=False)
        self.assertNotIn("so_com", texto)
        self.assertNotIn("texto_windows_sem_github", texto)
        self.assertNotIn("{{", texto)
        self.assertIn("plugin Exemplo e conector ERP Exemplo", texto)
        instalar = passos[0]["texto"]["guiado"]
        self.assertIn("chave", instalar)
        self.assertNotIn("8 letras", instalar)

    def test_textos(self):
        claude = (self.kit / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("## Sistemas de trabalho", claude)
        self.assertIn("skill `comecar`", claude)
        self.assertIn("Prefira o plugin ao conector para gravar.", claude)
        self.assertLess(claude.index("## Autonomia"), claude.index("## Sistemas de trabalho"))
        self.assertIn("## Os sistemas de trabalho", (self.kit / "README.md").read_text(encoding="utf-8"))
        self.assertIn("## Começar\n\n1. Baixe o ZIP", (self.kit / "COMECE-AQUI.md").read_text(encoding="utf-8"))
        for md in self.kit.rglob("*.md"):
            texto = md.read_text(encoding="utf-8")
            self.assertNotIn("{{", texto, md)
            self.assertNotIn("python3 ", texto, md)

    def test_skills_novas_sem_travessao(self):
        for nome in ("comecar", "ligar-sistemas"):
            self.assertNotIn("—", (MODELO / ".claude" / "skills" / nome / "SKILL.md").read_text(encoding="utf-8"), nome)

    def test_powershell_novo_e_ascii(self):
        for nome in ("pedir-segredo.ps1", "agente-claude.ps1", "instalar.ps1"):
            texto = (MODELO / "instalar" / nome).read_bytes()
            self.assertEqual([b for b in texto if b > 127], [], nome)

    def test_atalho_do_windows_abre_o_aplicativo(self):
        ps1 = (self.kit / "instalar" / "agente.ps1").read_text(encoding="ascii")
        self.assertIn("claude://code/new?folder=", ps1)
        self.assertIn("function Agente-Abrir", ps1)
        self.assertIn("Agente-Abrir", (self.kit / "instalar" / "instalar.ps1").read_text(encoding="ascii"))


class KitSemSistemas(unittest.TestCase):
    def test_nada_de_sistemas(self):
        kit = Kits.sem
        self.assertFalse((kit / ".root" / "sistemas.json").exists())
        ids = [p["id"] for p in json.loads((kit / "ferramentas" / "passos.json").read_text(encoding="utf-8"))["passos"]]
        self.assertNotIn("sistemas", ids)
        perm = json.loads((kit / ".claude" / "settings.json").read_text(encoding="utf-8"))["permissions"]
        self.assertNotIn("ask", perm)
        self.assertEqual(perm, json.loads((MODELO / ".claude" / "settings.json").read_text(encoding="utf-8"))["permissions"])
        claude = (kit / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertNotIn("## Sistemas de trabalho", claude)
        self.assertIn("skill `comecar`", claude)
        r = subprocess.run([sys.executable, "ferramentas/verificar.py", "--silencioso", "--sem-rede"], cwd=str(kit),
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)


class Credencial(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="kit-home-"))
        self.kit = Path(tempfile.mkdtemp(prefix="kit-copia-")) / "kit"
        shutil.copytree(Kits.com, self.kit)

    def tearDown(self):
        shutil.rmtree(self.home, ignore_errors=True)
        shutil.rmtree(self.kit.parent, ignore_errors=True)

    def arquivo(self):
        return self.home / ".exemplo" / "credenciais.env"

    def test_grava_junta_e_nao_mostra(self):
        self.arquivo().parent.mkdir(parents=True)
        self.arquivo().write_text("OUTRA_COISA=fica\nERP_EMAIL=antigo@x.com", encoding="utf-8")
        r = sistemas_py(self.kit, ambiente_de_teste(self.home), "--gravar-credencial", "erp")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("Ab c", r.stdout + r.stderr)
        texto = self.arquivo().read_text(encoding="utf-8")
        self.assertTrue(texto.endswith("\n"))
        self.assertIn("OUTRA_COISA=fica", texto)
        self.assertEqual(texto.count("ERP_EMAIL="), 1)
        self.assertIn("ERP_EMAIL='pessoa@exemplo.com'", texto)
        self.assertIn("ERP_PASSWORD=", texto)
        if os.name != "nt":
            self.assertEqual(oct(self.arquivo().stat().st_mode & 0o777), "0o600")
        conferir = sistemas_py(self.kit, ambiente_de_teste(self.home), "--conferir", "--json")
        self.assertNotIn("Ab c", conferir.stdout)
        self.assertNotIn("chave-publica", conferir.stdout)
        self.assertEqual(json.loads(conferir.stdout)["credenciais"][0]["faltam"], [])

    def test_valor_volta_igual_no_formato_do_dotenv(self):
        sys.path.insert(0, str(self.kit / "ferramentas"))
        try:
            import sistemas
        finally:
            sys.path.pop(0)
        alvo = self.home / "c.env"
        sistemas.escrever_env(str(alvo), {"X": SEGREDO_DE_TESTE})
        linha = alvo.read_text(encoding="utf-8").strip()
        valor = linha.split("=", 1)[1]
        self.assertTrue(valor.startswith("'") and valor.endswith("'"))
        lido = valor[1:-1].replace("\\'", "'").replace("\\\\", "\\")
        self.assertEqual(lido, SEGREDO_DE_TESTE)
        self.assertEqual(sistemas.nomes_preenchidos(str(alvo)), {"X"})

    def test_janela_cancelada_grava_so_o_publico(self):
        r = sistemas_py(self.kit, ambiente_de_teste(self.home, segredo=""), "--gravar-credencial", "erp")
        self.assertEqual(r.returncode, 1)
        texto = self.arquivo().read_text(encoding="utf-8")
        self.assertIn("ERP_EMAIL=", texto)
        self.assertNotIn("ERP_PASSWORD", texto)

    def test_credencial_desconhecida(self):
        self.assertEqual(sistemas_py(self.kit, ambiente_de_teste(self.home), "--gravar-credencial", "outra").returncode, 2)
        self.assertEqual(sistemas_py(self.kit, ambiente_de_teste(self.home), "--registrar", "outro", "ok").returncode, 2)

    def test_passo_fecha_quando_tudo_esta_ligado(self):
        env = ambiente_de_teste(self.home)
        verificar = [sys.executable, "ferramentas/verificar.py", "--silencioso", "--sem-rede"]

        def passo():
            subprocess.run(verificar, cwd=str(self.kit), env=env, capture_output=True, text=True, check=True)
            prog = json.loads((self.kit / ".root" / "progresso.json").read_text(encoding="utf-8"))
            return next(p for p in prog["passos"] if p["id"] == "sistemas")

        antes = passo()
        self.assertFalse(antes["feito"])
        self.assertIn("não instalado", antes["detalhe"])
        sistemas_py(self.kit, env, "--gravar-credencial", "erp")
        bins = self.home / ".local" / "bin"  # o plugin precisa do claude e do uv; aqui bastam existir
        bins.mkdir(parents=True)
        for nome in ("claude", "uv"):
            (bins / nome).write_text("")
        plugins = self.home / ".claude" / "plugins"
        plugins.mkdir(parents=True)
        (plugins / "installed_plugins.json").write_text(json.dumps(
            {"version": 2, "plugins": {"exemplo@exemplo": [{"scope": "user", "installPath": str(self.home / "p"), "version": "1.0.0"}]}}))
        estado = {"itens": {"plugin:exemplo": {"ok": True, "em": "2026-11-07T10:00:00-03:00", "detalhe": "teste"}}}
        (self.kit / ".root" / "sistemas-estado.json").write_text(json.dumps(estado))
        self.assertFalse(passo()["feito"])
        self.assertEqual(sistemas_py(self.kit, env, "--registrar", "erp", "ok", "3 empresas").returncode, 0)
        depois = passo()
        self.assertTrue(depois["feito"], depois["detalhe"])
        self.assertIn("plugin Exemplo", depois["detalhe"])


if __name__ == "__main__":
    unittest.main()
