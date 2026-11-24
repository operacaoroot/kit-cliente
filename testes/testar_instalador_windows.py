#!/usr/bin/env python3
"""Executa o instalador real em Windows, com dependencias externas simuladas.

PowerShell, Python, Git, ACL, painel e escrita dos atalhos sao reais. Downloads,
programas do catalogo, autenticacao e rede sao dubles: nao homologa instalacao
limpa nem contas de clientes. Nao requer tokens ou chaves reais.
KIT_TEST_SHELL escolhe powershell (5.1) ou pwsh (7).
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import parse_qs, urlparse
import venv

RAIZ = Path(__file__).resolve().parent.parent
SHELL = shutil.which(os.environ.get("KIT_TEST_SHELL", "powershell"))

FERRAMENTA = r'''
import json, os, sys
from pathlib import Path
KIT = Path(__file__).resolve().parent.parent
FALHA = os.environ.get('KIT_TEST_FALHA', '')
def perfil_do_kit():
    return 'chat'
def conferir(perfil):
    instalado = FALHA not in ('ambiente:--instalar', 'ambiente:--conferir')
    return {'apps': [{'nome': 'Obsidian', 'instalado': instalado,
                     'nivel': 'obrigatorio', 'para_que': 'notas'}],
            'venv': {'pronto': True, 'detalhe': 'Python do kit pronto'},
            'faltam_obrigatorios': [] if instalado else ['obsidian']}
if __name__ == '__main__':
    nome = Path(__file__).stem
    etapa = nome + (':' + sys.argv[1] if len(sys.argv) > 1 else '')
    with (KIT / 'chamadas.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps([nome] + sys.argv[1:]) + '\n')
    if nome == 'verificar' and FALHA != 'progresso-ausente':
        progresso = KIT / '.root/progresso.json'
        if FALHA == 'progresso-invalido':
            progresso.write_text('{', encoding='utf-8')
        else:
            pronto = FALHA not in ('instalar-pendente', 'mcp:--registrar')
            progresso.write_text(json.dumps({'passos': [
                {'id': 'instalar', 'feito': pronto},
                {'id': 'perfil', 'feito': False},
                {'id': 'contexto', 'feito': False}]}), encoding='utf-8')
    sys.exit(1 if FALHA == etapa else 0)
'''

# O painel real pede o navegador e confere o remoto. Interceptamos apenas essas
# fronteiras no Python filho; arquivos, parser, processos e git local sao reais.
HOOK = r'''
import json, os, subprocess
from pathlib import Path
KIT = Path(os.environ['KIT_TEST_ROOT'])
real_run = subprocess.run
def run(cmd, *args, **kwargs):
    if isinstance(cmd, (list, tuple)) and cmd:
        exe = Path(str(cmd[0])).stem.lower()
        if exe == 'gh':
            (KIT / 'gh-foi-chamado').write_text('erro')
            raise RuntimeError('o cliente nao deve usar gh')
        if exe == 'git' and 'ls-remote' in cmd:
            falha = os.environ.get('KIT_TEST_FALHA') == 'rede'
            return subprocess.CompletedProcess(cmd, 1 if falha else 0,
                '' if falha else '0' * 40 + '\tHEAD\n', '')
    return real_run(cmd, *args, **kwargs)
subprocess.run = run
def abrir(path, *args, **kwargs):
    with (KIT / 'navegador.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps(str(path)) + '\n')
os.startfile = abrir
'''

WRAPPER = r'''
$ErrorActionPreference = 'Stop'
function global:Read-Host { return '' }
function global:Invoke-RestMethod { throw 'Download inesperado no teste isolado' }
function global:Start-Process {
    param($FilePath)
    $FilePath | ConvertTo-Json -Compress | Add-Content -Encoding UTF8 (Join-Path $env:KIT_TEST_ROOT 'aplicativo.jsonl')
}
function global:Test-Path {
    param($Path)
    if ($Path -eq 'Registry::HKEY_CLASSES_ROOT\claude') { return $env:KIT_TEST_CLAUDE_APP -eq '1' }
    Microsoft.PowerShell.Management\Test-Path $Path
}
function global:uv {
    if (($args[0] -eq 'python' -and $env:KIT_TEST_FALHA -eq 'uv:python') -or
        ($args[0] -eq 'pip' -and $env:KIT_TEST_FALHA -eq 'uv:pip')) {
        $global:LASTEXITCODE = 1
    } else { $global:LASTEXITCODE = 0 }
}
& (Join-Path $env:KIT_TEST_ROOT 'instalar\instalar.ps1')
exit $LASTEXITCODE
'''


@unittest.skipUnless(os.name == 'nt' and SHELL, 'requer Windows e PowerShell nativos')
class InstaladorWindows(unittest.TestCase):
    def setUp(self):
        desktop = subprocess.check_output([SHELL, '-NoProfile', '-Command',
            '[Environment]::GetFolderPath("Desktop", "Create")'], text=True).strip()
        self.assertTrue(desktop, 'o usuario do teste precisa de uma Area de Trabalho')
        self.desktop = Path(desktop)
        self.atalhos_antes = {self.desktop / nome:
            (self.desktop / nome).read_bytes() if (self.desktop / nome).exists() else None
            for nome in ('Claude do kit.cmd', 'Claude do kit.url', 'Codex do kit.cmd', 'Painel do kit.url')}
        self.addCleanup(self.restaurar_atalhos)

    def restaurar_atalhos(self):
        for caminho, conteudo in self.atalhos_antes.items():
            if conteudo is not None:
                caminho.write_bytes(conteudo)
            elif caminho.exists():
                caminho.unlink()

    def executar(self, agente='codex', falha='', app=False):
        pasta = tempfile.TemporaryDirectory(prefix='kit-windows-')
        self.addCleanup(pasta.cleanup)
        kit = Path(pasta.name) / 'kit com espacos'
        for nome in ('instalar', 'ferramentas', '.root', 'ambiente', 'hooks', 'vault'):
            (kit / nome).mkdir(parents=True, exist_ok=True)
        for nome in ('instalar.ps1', 'instalar.cmd'):
            shutil.copy2(RAIZ / 'modelo/instalar' / nome, kit / 'instalar' / nome)
        shutil.copy2(RAIZ / 'modelo/instalar' / ('agente-' + agente + '.ps1'),
                     kit / 'instalar/agente.ps1')
        for nome in ('painel.py', 'conectar.py'):
            shutil.copy2(RAIZ / 'modelo/ferramentas' / nome, kit / 'ferramentas' / nome)
        shutil.copytree(RAIZ / 'modelo/painel', kit / 'painel')
        for nome in ('ambiente', 'autonomia', 'mcp', 'verificar'):
            (kit / 'ferramentas' / (nome + '.py')).write_text(FERRAMENTA, encoding='utf-8')
        cliente = {'nome': 'Pessoa ficticia', 'agente': agente, 'slug': 'teste-windows',
                   'repo': 'operacaoroot/kit-teste-windows', 'mcp': {'nome': 'teste'}}
        (kit / '.root/cliente.json').write_text(json.dumps(cliente), encoding='utf-8')
        if falha != 'sem-chave':
            # Texto propositalmente invalido, sem acesso a qualquer repositorio.
            (kit / '.root/chave').write_text('chave ficticia sem acesso\n', encoding='ascii')
        (kit / 'ambiente/requirements.txt').write_text('', encoding='ascii')
        (kit / 'hooks/sitecustomize.py').write_text(HOOK, encoding='utf-8')
        (kit / 'executar.ps1').write_text(WRAPPER, encoding='ascii')
        venv.create(kit / '.venv', with_pip=False)
        for comando in (['git', 'init', '-q'],
                        ['git', 'remote', 'add', 'origin', 'https://github.com/operacaoroot/kit-teste-windows.git']):
            subprocess.run(comando, cwd=kit, check=True, capture_output=True)
        env = dict(os.environ, KIT_TEST_ROOT=str(kit), KIT_TEST_FALHA=falha,
                   PYTHONPATH=str(kit / 'hooks'), PYTHONUTF8='1', KIT_TEST_CLAUDE_APP='1' if app else '0')
        processo = subprocess.run([SHELL, '-NoProfile', '-NonInteractive', '-ExecutionPolicy',
                                  'Bypass', '-File', str(kit / 'executar.ps1')],
                                 env=env, capture_output=True, text=True, encoding='utf-8',
                                 errors='replace', timeout=90)
        arq = kit / '_privado/painel/estado.json'
        estado = json.loads(arq.read_text(encoding='utf-8')) if arq.exists() else None
        if os.environ.get('KIT_TEST_REPORT'):
            destino = Path(os.environ['KIT_TEST_REPORT'])
            destino.mkdir(exist_ok=True)
            nome = agente + '-' + (falha or 'sucesso').replace(':', '-')
            if app:
                nome += '-app'
            (destino / (nome + '.json')).write_text(json.dumps(
                {'agente': agente, 'cenario': falha or 'sucesso', 'exit_code': processo.returncode,
                 'painel': estado, 'dependencias': 'simuladas'}, ensure_ascii=False, indent=2), encoding='utf-8')
            (destino / (nome + '.txt')).write_text(processo.stdout + processo.stderr, encoding='utf-8')
        self.assertFalse((kit / 'gh-foi-chamado').exists())
        return kit, processo, estado

    def test_sintaxe_de_todos_os_scripts(self):
        for arquivo in (RAIZ / 'modelo/instalar').glob('*.ps1'):
            with self.subTest(arquivo=arquivo.name):
                comando = ("$t=$null;$e=$null;[void][System.Management.Automation.Language.Parser]::ParseFile("
                           "'{}',[ref]$t,[ref]$e);if($e.Count){{$e;exit 1}}".format(str(arquivo).replace("'", "''")))
                r = subprocess.run([SHELL, '-NoProfile', '-Command', comando], capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_sucesso_dos_dois_agentes_sem_exigir_onboarding_completo(self):
        for agente in ('claude', 'codex'):
            with self.subTest(agente=agente):
                kit, r, estado = self.executar(agente)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertEqual(estado['fase'], 'pronto')
                self.assertEqual(estado['agente'], agente)
                self.assertEqual(estado['sistema'], 'windows')
                self.assertEqual(bool(estado['links']['claude']), agente == 'claude')
                abertas = (kit / 'navegador.jsonl').read_text(encoding='utf-8').splitlines()
                self.assertEqual(len(abertas), 1, 'o painel deve abrir uma unica vez')
                self.assertEqual(Path(json.loads(abertas[0])), kit / 'painel/index.html')
                remoto = subprocess.check_output(['git', 'remote', 'get-url', 'origin'], cwd=kit, text=True)
                self.assertEqual(remoto.strip(), 'git@github.com:operacaoroot/kit-teste-windows.git')
                self.assertIn('.root/chave', subprocess.check_output(
                    ['git', 'config', 'core.sshCommand'], cwd=kit, text=True).replace('\\', '/'))
                self.conferir_atalhos(kit, agente)

    def test_claude_com_aplicativo_abre_a_conversa_na_pasta_do_kit(self):
        kit, r, estado = self.executar(agente='claude', app=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(estado['fase'], 'pronto')
        atalho = (self.desktop / 'Claude do kit.url').read_text(encoding='ascii')
        link = next(linha[4:] for linha in atalho.splitlines() if linha.startswith('URL='))
        self.assertTrue(link.startswith('claude://code/new?'))
        parametros = parse_qs(urlparse(link).query)
        self.assertEqual(parametros['folder'], [str(kit)])
        self.assertIn('acabei de instalar', parametros['q'][0])
        self.assertFalse((self.desktop / 'Claude do kit.cmd').exists())
        abertas = (kit / 'aplicativo.jsonl').read_text(encoding='utf-8-sig').splitlines()
        self.assertEqual([json.loads(linha) for linha in abertas], [link])

    def conferir_atalhos(self, kit, agente):
        pasta = self.desktop
        atalho = pasta / (agente.title() + ' do kit.cmd')
        self.assertIn(str(kit), atalho.read_text(encoding='ascii'))
        pagina = pasta / 'Painel do kit.url'
        self.assertIn('URL=' + (kit / 'painel/index.html').as_uri(), pagina.read_text(encoding='ascii'))
        atalho.unlink()
        pagina.unlink()

    def test_falhas_antes_do_painel_nao_dao_sucesso(self):
        for falha in ('uv:python', 'uv:pip'):
            with self.subTest(falha=falha):
                _, r, estado = self.executar(falha=falha)
                self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertIsNone(estado)

    def test_falhas_depois_do_painel_encerram_com_pendencias(self):
        for falha in ('ambiente:--instalar', 'sem-chave', 'ambiente:--conferir',
                      'verificar', 'instalar-pendente', 'progresso-ausente',
                      'progresso-invalido', 'mcp:--registrar'):
            with self.subTest(falha=falha):
                _, r, estado = self.executar(falha=falha)
                self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertIsNotNone(estado)
                self.assertEqual(estado['fase'], 'atencao')
                self.assertFalse(estado['conferencia']['pronto'])
                self.assertTrue(estado['conferencia']['falta'])

    def test_falha_na_preparacao_do_claude(self):
        _, r, estado = self.executar(agente='claude', falha='autonomia')
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(estado['fase'], 'atencao')
        etapa = next(x for x in estado['etapas'] if x['id'] == 'autonomia')
        self.assertEqual(etapa['estado'], 'falhou')


if __name__ == '__main__':
    if os.name != 'nt' or not SHELL:
        print('Use Windows nativo e KIT_TEST_SHELL=powershell ou pwsh.', file=sys.stderr)
        sys.exit(2)
    unittest.main()
