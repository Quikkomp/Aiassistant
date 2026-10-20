"""Bounded public-URL imports, with DNS validation pinned to the actual socket."""
import http.client
import ipaddress
import re
import socket
import ssl
import time
from html.parser import HTMLParser
from urllib.parse import quote, urljoin, urlsplit, urlunsplit

MAX_BYTES = 8 * 1024 * 1024
MAX_TEXT = 200000


class URLImportError(ValueError):
    pass


def public_address(value):
    address = ipaddress.ip_address(value)
    return (address.is_global and not address.is_multicast and not address.is_reserved
            and not getattr(address, 'ipv4_mapped', None)
            and not getattr(address, 'sixtofour', None)
            and not getattr(address, 'teredo', None))


def target(url):
    if not isinstance(url, str) or len(url) > 2048 or re.search(r'[\x00-\x20\x7f\\]', url):
        raise URLImportError('请输入完整的公开 HTTP/HTTPS 链接。')
    try:
        parts = urlsplit(url)
        host = (parts.hostname or '').encode('idna').decode('ascii').lower()
        port = parts.port or (443 if parts.scheme == 'https' else 80)
        if parts.scheme not in {'http', 'https'} or not host or parts.username is not None or parts.password is not None:
            raise ValueError()
        if port != (443 if parts.scheme == 'https' else 80):
            raise ValueError()
        if '%' in host or host.endswith('.') or len(host) > 253:
            raise ValueError()
        records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        if not records or any(not public_address(row[4][0]) for row in records):
            raise URLImportError('仅支持公开互联网地址，不能导入本机、内网或云服务器内部地址。')
    except URLImportError:
        raise
    except (ValueError, UnicodeError, OSError):
        raise URLImportError('链接无效、端口不受支持或域名无法解析。') from None
    return parts, host, port, records


def remaining(deadline):
    value = deadline - time.monotonic()
    if value <= 0:
        raise URLImportError('链接读取超时，请稍后重试或下载文档后上传。')
    return min(7, value)


def open_public(url, deadline):
    parts, host, port, records = target(url)
    # Do not resolve again after validation; connect only to a validated sockaddr.
    family, socktype, proto, _, address = records[0]
    conn = http.client.HTTPConnection(host, port, timeout=remaining(deadline))
    sock = socket.socket(family, socktype, proto)
    try:
        sock.settimeout(remaining(deadline))
        sock.connect(address)
        if parts.scheme == 'https':
            sock = ssl.create_default_context().wrap_socket(sock, server_hostname=host)
        conn.sock = sock
        path = quote(urlunsplit(('', '', parts.path or '/', parts.query, '')), safe="/%?:=&+;,@!$'()*~-._")
        conn.request('GET', path, headers={'User-Agent': 'WizPractice-MaterialImporter/1.0',
                                         'Accept': 'text/html,text/plain,application/pdf', 'Accept-Encoding': 'identity'})
        response = conn.getresponse()
        if response.status in {301, 302, 303, 307, 308}:
            return {'redirect': response.getheader('Location')}
        if response.status != 200:
            raise URLImportError('网页拒绝访问或不存在，请使用公开资料直链，或下载后上传。')
        media_type = response.headers.get_content_type()
        if media_type not in {'text/html', 'application/xhtml+xml', 'text/plain', 'text/markdown', 'application/pdf'}:
            raise URLImportError('仅支持网页、纯文本、Markdown 和 PDF 直链，不支持该链接的文件类型。')
        if response.getheader('Content-Encoding', 'identity').lower() != 'identity':
            raise URLImportError('该网站返回了不受支持的压缩内容，请下载文件后上传。')
        size = response.getheader('Content-Length')
        if size and (not size.isdigit() or int(size) > MAX_BYTES):
            raise URLImportError('链接内容超过 8 MB，请下载并精简后上传。')
        chunks, count = [], 0
        while True:
            sock.settimeout(remaining(deadline))
            chunk = response.read1(min(65536, MAX_BYTES + 1 - count))
            if not chunk:
                break
            chunks.append(chunk); count += len(chunk)
            if count > MAX_BYTES:
                raise URLImportError('链接内容超过 8 MB，请下载并精简后上传。')
        return {'body': b''.join(chunks), 'type': media_type,
                'charset': response.headers.get_content_charset(), 'host': host}
    finally:
        conn.close()
        sock.close()


class PageText(HTMLParser):
    blocked = {'head', 'script', 'style', 'nav', 'footer', 'header', 'noscript', 'svg', 'form', 'iframe', 'template'}
    breaks = {'p', 'div', 'br', 'li', 'h1', 'h2', 'h3', 'h4', 'tr', 'section', 'article', 'pre'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ignored, self.chunks, self.title, self.in_title = [], [], [], False

    def handle_starttag(self, tag, attrs):
        if tag == 'title':
            self.in_title = True
        if tag in self.blocked:
            self.ignored.append(tag)
        if tag in self.breaks and not self.ignored:
            self.chunks.append('\n')

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False
        if tag in self.ignored:
            self.ignored = self.ignored[:len(self.ignored)-1-self.ignored[::-1].index(tag)]
        if tag in self.breaks and not self.ignored:
            self.chunks.append('\n')

    def handle_data(self, data):
        if self.in_title:
            self.title.append(data)
        if not self.ignored:
            self.chunks.append(data)


def fetch_material(url):
    deadline = time.monotonic() + 25
    try:
        for attempt in range(4):
            result = open_public(url, deadline)
            if 'redirect' not in result:
                break
            if not result['redirect'] or attempt == 3:
                raise URLImportError('链接重定向过多或无效，请提供最终公开链接。')
            next_url = urljoin(url, result['redirect'])
            if urlsplit(url).scheme == 'https' and urlsplit(next_url).scheme != 'https':
                raise URLImportError('不支持从加密链接跳转到非加密地址。')
            url = next_url
        body = result['body']
        if result['type'] == 'application/pdf':
            if not body.startswith(b'%PDF-'):
                raise URLImportError('链接没有返回有效的 PDF 文件。')
            return {'data': body, 'suffix': '.pdf', 'host': result['host']}
        try:
            text = body.decode(result.get('charset') or 'utf-8')
        except (UnicodeError, LookupError):
            text = body.decode('gb18030', errors='replace')
        title = result['host']
        if result['type'] in {'text/html', 'application/xhtml+xml'}:
            parser = PageText(); parser.feed(text)
            text = ''.join(parser.chunks)
            title = ''.join(parser.title).strip()[:200] or title
        text = '\n'.join(line for raw in text.splitlines() if (line := re.sub(r'\s+', ' ', raw).strip()))
        if len(text) < 30:
            raise URLImportError('没有读取到足够正文；该链接可能需要登录或依赖脚本，请下载文档后上传。')
        if len(text) > MAX_TEXT:
            raise URLImportError('正文超过 20 万字符，请精简后上传文档。')
        return {'data': (title+'\n来源：'+url+'\n\n'+text).encode('utf-8'), 'suffix': '.txt', 'host': result['host']}
    except URLImportError:
        raise
    except (OSError, ValueError, http.client.HTTPException):
        raise URLImportError('链接读取失败，请检查地址，或下载资料后通过文档导入。') from None
