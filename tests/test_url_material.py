"""Public URL safety/extraction and per-account ingest; no real network or AI."""
import json
import socket
import sys
import tempfile
import unittest
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from email.message import Message
from pathlib import Path
from urllib.parse import urlsplit
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tmp/exam-test-deps'))
sys.path.insert(0, str(ROOT/'local_chat_site'))
from flask import Flask, session
from auth_store import AuthError
from url_material import target, fetch_material, open_public, URLImportError, MAX_BYTES, public_address
from url_routes import make_url_blueprint


def dns(ip='93.184.216.34', port=443):
    return [(socket.AF_INET6 if ':' in ip else socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, port))]


class URLMaterialTests(unittest.TestCase):
    def test_http10_body_can_be_read_after_connection_close_header(self):
        # Only this isolated transport test bypasses public DNS for a local fixture.
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200);self.send_header('Content-Type','text/plain; charset=utf-8');self.end_headers()
                self.wfile.write(b'Public course notes: gravity, energy, motion and their practical applications.')
            def log_message(self,*args):pass
        server=HTTPServer(('127.0.0.1',0),Handler)
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        try:
            address=dns('127.0.0.1',server.server_port)
            with patch('url_material.target',return_value=(urlsplit('http://example.com/'),'example.com',server.server_port,address)):
                result=fetch_material('http://example.com/')
                self.assertIn(b'gravity, energy',result['data'])
        finally:
            server.shutdown();server.server_close();worker.join(timeout=2)

    def test_blocks_non_public_addresses_and_encoded_hosts(self):
        for ip in ['127.0.0.1','10.0.0.1','169.254.169.254','100.100.100.200','192.168.1.1','0.0.0.0','224.0.0.1','::1','fc00::1','fe80::1','::ffff:127.0.0.1','2002:7f00:1::']:
            self.assertFalse(public_address(ip), ip)
            with patch('url_material.socket.getaddrinfo',return_value=dns(ip)):
                with self.assertRaises(URLImportError): target('https://example.com')
        with patch('url_material.socket.getaddrinfo',return_value=dns()+dns('10.0.0.1')):
            with self.assertRaises(URLImportError): target('https://example.com')

    def test_url_validation_rejects_protocol_credentials_ports_and_controls(self):
        with patch('url_material.socket.getaddrinfo',return_value=dns()):
            for url in ['file:///etc/passwd','ftp://example.com','https://user:pass@example.com','http://example.com:8000','https://example.com\\@127.0.0.1','https://example.com\nX:1','https://example.com./','https://%31%32%37.0.0.1/','x'*2049]:
                with self.assertRaises(URLImportError, msg=url): target(url)

    def test_pins_connection_to_validated_dns_and_verifies_tls(self):
        message=Message();message['Content-Type']='text/plain; charset=utf-8'
        response=MagicMock(status=200,headers=message)
        response.getheader.side_effect=lambda key,default=None:default
        response.read1.side_effect=[b'This is public course text with enough learning content.', b'']
        with patch('url_material.socket.getaddrinfo',return_value=dns()) as resolver, patch('url_material.socket.socket') as sock, patch('url_material.ssl.create_default_context') as tls, patch('url_material.http.client.HTTPConnection') as connection:
            connection.return_value.getresponse.return_value=response
            result=open_public('https://example.com/course',__import__('time').monotonic()+20)
            resolver.assert_called_once()
            sock.return_value.connect.assert_called_once_with(('93.184.216.34',443))
            tls.return_value.wrap_socket.assert_called_once_with(sock.return_value,server_hostname='example.com')
            self.assertIn(b'course', result['body'])
            self.assertEqual(connection.return_value.request.call_args.args[:2], ('GET','/course'))

    def test_redirect_to_private_address_is_checked_again(self):
        response=MagicMock(status=302);response.getheader.return_value='http://127.0.0.1/private'
        with patch('url_material.socket.getaddrinfo',side_effect=lambda host,*a,**k:dns('127.0.0.1' if host=='127.0.0.1' else '93.184.216.34',80)), patch('url_material.socket.socket'), patch('url_material.http.client.HTTPConnection') as connection:
            connection.return_value.getresponse.return_value=response
            with self.assertRaises(URLImportError): fetch_material('http://example.com')
            self.assertEqual(connection.call_count,1)

    def test_extracts_text_and_title_without_scripts_and_navigation(self):
        html='<html><head><title>课程说明</title><script>SECRET_SCRIPT</script></head><body><nav>HIDDEN_NAV</nav><article><h1>课程知识</h1><p>'+'这是用于出题的课程正文，包含详细概念和应用。'*5+'</p></article><footer>HIDDEN_FOOTER</footer></body></html>'
        with patch('url_material.open_public',return_value={'body':html.encode(),'type':'text/html','charset':'utf-8','host':'example.com'}):
            result=fetch_material('https://example.com/course')
            text=result['data'].decode()
            self.assertIn('课程说明',text);self.assertIn('用于出题的课程正文',text)
            for hidden in ['SECRET_SCRIPT','HIDDEN_NAV','HIDDEN_FOOTER','<p>']:self.assertNotIn(hidden,text)

    def test_direct_pdf_and_empty_or_excessive_redirects(self):
        with patch('url_material.open_public',return_value={'body':b'%PDF-1.7 data','type':'application/pdf','host':'example.com'}):
            self.assertEqual(fetch_material('https://example.com/paper')['suffix'],'.pdf')
        for result in [{'body':b'<html><script>load()</script></html>','type':'text/html','host':'example.com'}, {'redirect':'/again'}, {'redirect':'http://example.com/insecure'}]:
            with patch('url_material.open_public',return_value=result):
                with self.assertRaises(URLImportError):fetch_material('https://example.com')

    def test_response_size_and_type_limits(self):
        response=MagicMock(status=200)
        for content_type, length in [('application/zip','1'),('text/plain',str(MAX_BYTES+1))]:
            message=Message();message['Content-Type']=content_type;response.headers=message
            response.getheader.side_effect=lambda key,default=None:length if key=='Content-Length' else default
            with patch('url_material.socket.getaddrinfo',return_value=dns()),patch('url_material.socket.socket'),patch('url_material.ssl.create_default_context'),patch('url_material.http.client.HTTPConnection') as connection:
                connection.return_value.getresponse.return_value=response
                with self.assertRaises(URLImportError):open_public('https://example.com',__import__('time').monotonic()+20)


class URLRouteTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.app=Flask(__name__);self.app.secret_key='test-only'
        self.limiter=MagicMock();self.ingest=MagicMock(return_value='✅ 知识库已更新')
        self.fetcher=MagicMock(return_value={'data':b'Public learning material','suffix':'.txt','host':'example.com'})
        folder=lambda:str(Path(self.temp.name)/session['auth_user_id'])
        files=lambda:list(Path(folder()).glob('*'))
        self.app.register_blueprint(make_url_blueprint(folder,self.ingest,files,self.limiter,self.fetcher))
        self.client=self.app.test_client()

    def tearDown(self):self.temp.cleanup()

    def signin(self,user='teacher'):
        with self.client.session_transaction() as state:state['auth_user_id']=user

    def post(self,**kwargs):return self.client.post('/api/material/import_url',json={'url':'https://example.com/course'},**kwargs)

    def test_requires_login_and_valid_json_origin(self):
        self.assertEqual(self.post().status_code,401);self.signin()
        self.assertEqual(self.post(headers={'Origin':'https://evil.example'}).status_code,403)
        self.assertEqual(self.client.post('/api/material/import_url',json=[]).status_code,400)
        self.assertEqual(self.client.post('/api/material/import_url',data='x'*4097,content_type='application/json').status_code,400)
        self.fetcher.assert_not_called()

    def test_import_calls_original_ingest_and_isolates_users(self):
        names=[]
        for user in ['teacher','student']:
            self.signin(user);res=self.post();self.assertEqual(res.status_code,200)
            filename=res.json['saved'][0];names.append(filename)
            self.assertEqual((Path(self.temp.name)/user/filename).read_bytes(),b'Public learning material')
            self.ingest.assert_called_with(str(Path(self.temp.name)/user))
            self.assertEqual(res.headers['Cache-Control'],'private, no-store')
        self.assertNotEqual(*names)

    def test_fetch_failures_and_rate_limit_do_not_create_material(self):
        self.signin();self.fetcher.side_effect=URLImportError('链接不可用')
        self.assertEqual(self.post().status_code,400);self.ingest.assert_not_called()
        self.limiter.rate.side_effect=AuthError('rate_limited',429,60)
        self.assertEqual(self.post().status_code,429)
        self.assertFalse(list(Path(self.temp.name).glob('*')))

    def test_failed_ingest_reports_saved_file_without_false_success(self):
        self.signin();self.ingest.return_value='⚠️ 当前用户的知识库正在构建中'
        response=self.post();self.assertEqual(response.status_code,409);self.assertEqual(len(response.json['saved']),1)
        self.ingest.side_effect=RuntimeError('private backend data')
        response=self.post();self.assertEqual(response.status_code,503);self.assertNotIn('private backend data',response.text)


if __name__=='__main__':unittest.main()
