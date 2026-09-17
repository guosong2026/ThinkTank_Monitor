"""IISD 与 Land Use Policy：详情页不可读时的内容兜底与摘要来源标记。"""
import json
from unittest.mock import Mock

import requests

from ai_summarizer import AISummarizer
from website_configs import (
    WebsiteConfig, iisd_parser, normalize_listing_date, sciencedirect_rss_parser,
)

IISD_LISTING = '''
<div class="c-listing__items">
  <div class="views-row">
    <article class="c-list-item c-list-item--publication">
      <h3 class="c-list-item__heading">
        <a class="c-list-item__heading-link" href="/publications/report/lithium-mining-chile"
           title="Lithium Mining in Chile"><span class="field field--name-title">Lithium Mining in Chile</span></a>
      </h3>
      <div class="c-list-item__excerpt">
        This case study describes Chile&rsquo;s environmental challenges and associated social issues
        relating to lithium extraction from brine and examines the country&rsquo;s policy measures.
      </div>
      <small class="c-list-item__meta">
        <span class="c-list-item__meta-subtype">Report</span>
        <span class="c-list-item__meta-date">September 15, 2026</span>
      </small>
    </article>
  </div>
  <div class="views-row">
    <article class="c-list-item c-list-item--publication">
      <h3 class="c-list-item__heading">
        <a class="c-list-item__heading-link" href="/publications/guide/handbook-revised-common-investment-area"
           title="Guidance Handbook for the Revised Common Investment Area"><span class="field">Guidance Handbook</span></a>
      </h3>
      <div class="c-list-item__excerpt">
        A practical guide to help member states translate the revised Common Investment Area Agreement
        into national legal and institutional action.
      </div>
      <small class="c-list-item__meta">
        <span class="c-list-item__meta-subtype">Guide</span>
        <span class="c-list-item__meta-date">September 11, 2026</span>
      </small>
    </article>
  </div>
</div>
'''

RSS_FEED = '''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <item>
    <title><![CDATA[Improving landcover data governance in developing countries]]></title>
    <description><![CDATA[<p>Publication date: January 2027</p><p><b>Source:</b> Land Use Policy, Volume 172</p><p><b>Author(s):</b> Xavier G.H. Koenig, Prakash N.K. Deenapanray</p>]]></description>
    <link>https://www.sciencedirect.com/science/article/pii/S0264837726004321?dgcid=rss_sd_all</link>
  </item>
</channel></rss>
'''

SD_URL = 'https://www.sciencedirect.com/science/article/pii/S0264837726004321?dgcid=rss_sd_all'

CHALLENGE_HTML = '<html><title>Just a moment...</title><body>Verify you are human</body></html>'


def fake_response(text='', status=200, content_type='text/html', json_body=None):
    response = Mock()
    response.status_code = status
    response.ok = status < 400
    response.text = text
    response.content = text.encode()
    response.headers = {'Content-Type': content_type}
    response.json = Mock(return_value=json_body or {})
    if status >= 400:
        response.raise_for_status = Mock(side_effect=requests.exceptions.HTTPError(f'{status}'))
    else:
        response.raise_for_status = Mock(return_value=None)
    return response


class RoutingSession:
    """按URL片段返回预置响应，未知URL视为网络失败。"""

    def __init__(self, routes):
        self.routes = routes
        self.requested = []

    def get(self, url, **kwargs):
        self.requested.append(url)
        for fragment, response in self.routes.items():
            if fragment in url:
                return response
        raise requests.exceptions.ConnectionError(url)

    def close(self):
        pass


MODEL_REPLY = json.dumps({
    "chinese_title": "智利锂矿开采",
    "keywords": ["锂矿", "环境治理", "政策"],
    "summary": "该案例研究介绍智利锂矿开采的环境与社会议题及对应政策手段。",
})


def make_summarizer(routes):
    ai = AISummarizer(api_key='test', endpoint='model', request_delay=0)
    ai.session = RoutingSession(routes)
    ai._call_ark_api = Mock(return_value=MODEL_REPLY)
    return ai


def test_listing_date_normalization_is_locale_independent():
    assert normalize_listing_date('September 16, 2026') == '2026-09-16'
    assert normalize_listing_date('Sep 9, 2026') == '2026-09-09'
    assert normalize_listing_date('未标注日期') is None


def test_iisd_parser_extracts_excerpt_type_and_date():
    reports = iisd_parser(IISD_LISTING, 'https://www.iisd.org/publications')
    assert [report['url'] for report in reports] == [
        'https://www.iisd.org/publications/report/lithium-mining-chile',
        'https://www.iisd.org/publications/guide/handbook-revised-common-investment-area',
    ]
    first = reports[0]
    assert first['title'] == 'Lithium Mining in Chile'
    assert first['content_type'] == 'Report'
    assert first['publish_date'] == '2026-09-15'
    assert 'lithium extraction from brine' in first['excerpt']


def test_website_config_keeps_excerpt_for_summarizer():
    config = WebsiteConfig('IISD', 'https://www.iisd.org/publications', iisd_parser)
    reports = config.get_reports(IISD_LISTING, config.url)
    assert reports and all('excerpt' in report for report in reports)
    assert reports[0]['publish_date'] == '2026-09-15'


def test_sciencedirect_rss_parser_extracts_pii_and_citation():
    reports = sciencedirect_rss_parser(RSS_FEED, 'https://rss.sciencedirect.com/feed')
    assert len(reports) == 1
    report = reports[0]
    assert report['pii'] == 'S0264837726004321'
    assert report['publish_date'] == 'January 2027'
    assert 'Land Use Policy, Volume 172' in report['citation']
    assert 'Xavier G.H. Koenig' in report['citation']


def test_iisd_detail_page_block_uses_listing_excerpt():
    ai = make_summarizer({
        'iisd.org/publications/report/lithium-mining-chile': fake_response(CHALLENGE_HTML),
        'iisd.org/publications': fake_response(IISD_LISTING),
    })
    result = ai.summarize_report(
        'https://www.iisd.org/publications/report/lithium-mining-chile',
        'Lithium Mining in Chile',
        excerpt='This case study describes Chile environmental challenges and associated social '
                'issues relating to lithium extraction from brine.',
    )
    assert result['summary'].endswith('（依据官网列表页简介概括）')
    assert '列表页的简介' in ai._call_ark_api.call_args[0][0]
    assert ai.last_error == ''


def test_iisd_recovery_looks_up_listing_when_no_excerpt_available():
    ai = make_summarizer({
        'iisd.org/publications/report/lithium-mining-chile': fake_response(CHALLENGE_HTML),
        'iisd.org/publications': fake_response(IISD_LISTING),
    })
    result = ai.summarize_report(
        'https://www.iisd.org/publications/report/lithium-mining-chile',
        'Lithium Mining in Chile',
    )
    assert result['summary'].endswith('（依据官网列表页简介概括）')
    assert any(url.endswith('/publications') for url in ai.session.requested)


def test_sciencedirect_falls_back_to_bibliographic_record():
    crossref = {'message': {'items': [{
        'DOI': '10.1016/j.landusepol.2026.108348',
        'title': ['Improving landcover data governance in developing countries'],
        'author': [{'given': 'Xavier G.H.', 'family': 'Koenig'}],
        'container-title': ['Land Use Policy'],
        'volume': '172',
        'published': {'date-parts': [[2026, 9, 16]]},
    }]}}
    ai = make_summarizer({
        'science/article/pii/S0264837726004321': fake_response(CHALLENGE_HTML),
        'api.crossref.org': fake_response(json_body=crossref),
        'api.semanticscholar.org': fake_response(status=404, json_body={'error': 'not found'}),
        'api.openalex.org': fake_response(json_body={}),
    })
    result = ai.summarize_report(SD_URL, 'Improving landcover data governance in developing countries')
    assert result['summary'].endswith('（依据题录信息概括，未获取原文摘要）')
    prompt = ai._call_ark_api.call_args[0][0]
    assert '10.1016/j.landusepol.2026.108348' in prompt
    assert 'Koenig' in prompt


def test_sciencedirect_uses_public_abstract_when_available():
    crossref = {'message': {'items': [{
        'DOI': '10.1016/j.landusepol.2012.12.013',
        'title': ['Assessing cultural ecosystem services'],
        'container-title': ['Land Use Policy'],
        'published': {'date-parts': [[2013, 1, 21]]},
    }]}}
    abstract = 'Community level assessment of cultural ecosystem services in rural landscapes. ' * 3
    ai = make_summarizer({
        'science/article/pii/S0264837726004321': fake_response(CHALLENGE_HTML),
        'api.crossref.org': fake_response(json_body=crossref),
        'api.semanticscholar.org': fake_response(json_body={'title': 'x', 'abstract': abstract}),
    })
    result = ai.summarize_report(SD_URL, 'Assessing cultural ecosystem services')
    assert result['summary'].endswith('（依据公开摘要数据库内容概括）')
    assert abstract[:60] in ai._call_ark_api.call_args[0][0]


def test_source_label_keeps_summary_within_limit():
    ai = AISummarizer(api_key='test', endpoint='model', request_delay=0)
    labeled = ai._apply_source_label('测' * 400, 'citation')
    assert len(labeled) <= 200
    assert labeled.endswith('（依据题录信息概括，未获取原文摘要）')
    assert ai._apply_source_label('原文摘要', 'page') == '原文摘要'


def test_too_short_fallback_context_is_rejected():
    ai = AISummarizer(api_key='test', endpoint='model', request_delay=0)
    ai._fetch_page_content = Mock(return_value=None)
    assert ai._collect_content('https://example.org/report', '太短', None) == (None, None)


def test_unknown_site_challenge_page_is_still_not_summarized():
    ai = make_summarizer({'example.org/report': fake_response(CHALLENGE_HTML)})
    assert ai.summarize_report('https://example.org/report', 'Report') is None
    ai._call_ark_api.assert_not_called()
    assert '验证页' in ai.last_error
