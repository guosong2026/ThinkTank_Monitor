import gzip
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from check_websites import check_website, main
from monitor import MultiWebsiteMonitor
from scraper import WebsiteScraper
from website_configs import WebsiteConfig, biodiversity_council_parser, sciencedirect_rss_parser


def test_fetch_negotiates_decodable_compression():
    html = b'<html><h2><a href="/report/climate">Climate monitoring report</a></h2></html>'

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            # A server may select Brotli whenever the client advertises it.
            brotli = 'br' in self.headers.get('Accept-Encoding', '').split(', ')
            body = b'unsupported brotli data' if brotli else gzip.compress(html)
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Encoding', 'br' if brotli else 'gzip')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f'http://127.0.0.1:{server.server_port}/'
    monitor = MultiWebsiteMonitor([], enable_email=False)
    scraper = WebsiteScraper(url)
    scraper.proxy = None
    try:
        assert monitor._fetch_page(url) == html.decode()
        assert scraper.fetch_page(url) == html.decode()
    finally:
        monitor.session.close()
        scraper.session.close()
        server.shutdown()
        server.server_close()
        thread.join()


def test_rss_tracking_does_not_hide_articles():
    config = WebsiteConfig('Land Use Policy', 'https://rss.sciencedirect.com/feed', sciencedirect_rss_parser)
    rss = '''<rss><channel><item><title>Land policy and farming incentives</title>
    <link>https://www.sciencedirect.com/science/article/pii/S0264837726004230?dgcid=rss_sd_all</link>
    </item></channel></rss>'''
    assert len(config.get_reports(rss, config.url)) == 1
    assert not config._is_report_link('https://example.org/rss', 'Subscribe to our feed')
    assert sciencedirect_rss_parser('<broken', config.url) == []


def test_biodiversity_more_than_six_resources():
    html = ''.join(f'<a href="/resources/report-{i}">Biodiversity assessment number {i}</a>' for i in range(8))
    config = WebsiteConfig('Biodiversity Council', 'https://biodiversitycouncil.org.au/resources', biodiversity_council_parser)
    assert len(config.get_reports(html, config.url)) == 6


def test_listing_page_is_not_a_report():
    url = 'https://example.org/library/'
    config = WebsiteConfig('Example', url, lambda *_: [
        dict(title='Publications', url=url + '?page=2'),
        dict(title='Climate policy assessment', url=url + 'climate'),
    ])
    assert [r['url'] for r in config.get_reports('html', url)] == [url + 'climate']


@pytest.mark.parametrize('html,parser,status', [
    (None, lambda *_: [], 'fetch_failed'),
    ('<html></html>', lambda *_: [], 'empty'),
    ('<html></html>', lambda *_: 1 / 0, 'parse_error'),
])
def test_health_check_does_not_report_false_success(monkeypatch, html, parser, status):
    monkeypatch.setattr(MultiWebsiteMonitor, '_fetch_page', lambda *_: html)
    assert check_website(WebsiteConfig('Example', 'https://example.org/', parser))['status'] == status


def test_health_check_exit_code_and_json(monkeypatch, tmp_path):
    import check_websites
    import json
    config = WebsiteConfig('Example', 'https://example.org/')
    monkeypatch.setattr(check_websites, 'get_all_websites', lambda: [config])
    monkeypatch.setattr(check_websites, 'check_website', lambda _: dict(
        name='Example', status='empty', status_code=200, reports_found=0))
    output = tmp_path / 'health.json'
    assert main(['--json', str(output)]) == 1
    assert json.loads(output.read_text(encoding='utf-8'))['passed'] == 0
