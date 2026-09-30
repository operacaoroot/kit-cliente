"""Leitura limitada de URLs públicas fornecidas pela pessoa, sem cookies ou login."""
import http.client
import ipaddress
import socket
import ssl
from html.parser import HTMLParser
from urllib.parse import urlsplit, urljoin, urlunsplit
from urllib.robotparser import RobotFileParser

AGENTE = 'RootOnboarding/1.0'
LIMITE = 512_000


def validar_url(url):
    if not isinstance(url, str) or len(url) > 2048 or any(ord(c) < 33 for c in url):
        raise ValueError('Informe um endereço público completo, começando por https://.')
    p = urlsplit(url)
    if p.scheme not in ('https', 'http') or not p.hostname or p.username or p.password:
        raise ValueError('Use um endereço HTTP(S) público, sem senha no link.')
    if p.port not in (None, 80 if p.scheme == 'http' else 443):
        raise ValueError('Porta não permitida.')
    if p.query:
        raise ValueError('Remova os parâmetros depois de ? do endereço antes de coletar.')
    return urlunsplit((p.scheme, p.netloc, p.path or '/', '', ''))


def endereco_publico(host, port):
    infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    ips = [i[4][0] for i in infos]
    if not ips or any((not ipaddress.ip_address(ip).is_global or ipaddress.ip_address(ip).is_multicast) for ip in ips):
        raise ValueError('A coleta só acessa endereços públicos da internet.')
    return ips[0]


def requisitar(url):
    """Resolve uma vez e conecta ao IP validado; TLS verifica o hostname original."""
    url = validar_url(url)
    p = urlsplit(url)
    port = p.port or (443 if p.scheme == 'https' else 80)
    ip = endereco_publico(p.hostname, port)
    conn = http.client.HTTPConnection(p.hostname, port, timeout=12)
    sock = socket.create_connection((ip, port), timeout=12)
    try:
        if p.scheme == 'https':
            sock = ssl.create_default_context().wrap_socket(sock, server_hostname=p.hostname)
        conn.sock = sock
        conn.request('GET', p.path or '/', headers={'User-Agent': AGENTE, 'Accept': 'text/html,text/plain', 'Accept-Encoding': 'identity'})
        res = conn.getresponse()
        body = res.read(LIMITE + 1)
        if len(body) > LIMITE:
            raise ValueError('Página muito grande. Cole somente o trecho relevante.')
        return res.status, dict((k.lower(), v) for k, v in res.getheaders()), body
    finally:
        conn.close()
        sock.close()


class TextoHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.oculto = 0
        self.partes = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript', 'svg'):
            self.oculto += 1

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript', 'svg'):
            self.oculto = max(0, self.oculto - 1)

    def handle_data(self, data):
        if not self.oculto and data.strip():
            self.partes.append(data.strip())


def coletar(url):
    """Sem navegação recursiva; robots e destino revalidados em cada redirecionamento."""
    url = validar_url(url)
    for _ in range(4):
        p = urlsplit(url)
        robots_url = urlunsplit((p.scheme, p.netloc, '/robots.txt', '', ''))
        status, _, body = requisitar(robots_url)
        if status == 200:
            robots = RobotFileParser()
            robots.parse(body.decode('utf-8', errors='replace').splitlines())
            if not robots.can_fetch(AGENTE, url):
                raise ValueError('O site não permite coleta automática. Cole um trecho que você pode usar.')
        elif status not in (404, 410):
            raise ValueError('Não foi possível conferir a permissão de coleta do site. Cole o conteúdo manualmente.')
        status, headers, body = requisitar(url)
        if status in (301, 302, 303, 307, 308):
            url = validar_url(urljoin(url, headers.get('location', '')))
            continue
        if status != 200:
            raise ValueError('Página indisponível ou exige login (HTTP {}). Cole o conteúdo manualmente.'.format(status))
        tipo = headers.get('content-type', '').lower()
        if not ('text/html' in tipo or 'text/plain' in tipo):
            raise ValueError('Este endereço não é uma página de texto.')
        texto = body.decode('utf-8', errors='replace')
        if 'text/html' in tipo:
            parser = TextoHTML()
            parser.feed(texto)
            texto = '\n'.join(parser.partes)
        if len(texto.strip()) < 80:
            raise ValueError('Pouco conteúdo público disponível. Cole a apresentação ou biografia manualmente.')
        return {'url_final': url, 'texto': texto[:12000]}
    raise ValueError('Muitos redirecionamentos. Informe o endereço final da página.')
