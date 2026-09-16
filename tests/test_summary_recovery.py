from unittest.mock import Mock

from ai_summarizer import AISummarizer
from db import DatabaseManager
from summary_recovery import recover_missing_summaries


def test_recovery_persists_cooldown_and_does_not_change_sent_status(tmp_path):
    path = str(tmp_path / 'reports.db')
    with DatabaseManager(path) as db:
        missing = db.insert_report('Missing', 'https://example.org/missing', 'Example')
        complete = db.insert_report('Complete', 'https://example.org/complete', 'Example')
        db.update_ai_summary(complete, '已有', '关键词', '原有摘要')
        db.mark_report_as_sent(missing)
    ai = Mock()
    ai.is_configured.return_value = True
    ai.summarize_report.return_value = None
    ai.last_error = 'HTTP 403'
    assert recover_missing_summaries(path, ai) == 0
    assert recover_missing_summaries(path, ai) == 0
    assert ai.summarize_report.call_count == 1
    with DatabaseManager(path) as db:
        assert db.connection.execute('SELECT last_error FROM ai_summary_attempts').fetchone()[0] == 'HTTP 403'
        db.connection.execute("UPDATE ai_summary_attempts SET last_attempt = datetime('now', '-7 hours')")
        db.connection.commit()
    ai.summarize_report.return_value = dict(chinese_title='补全', keywords='环境', summary='补全摘要')
    assert recover_missing_summaries(path, ai) == 1
    assert recover_missing_summaries(path, ai) == 0
    with DatabaseManager(path) as db:
        row = db.connection.execute('SELECT * FROM reports WHERE id = ?', (missing,)).fetchone()
        assert row['ai_summary'] == '补全摘要'
        assert row['sent_status'] == 1
        assert db.connection.execute('SELECT ai_summary FROM reports WHERE id = ?', (complete,)).fetchone()[0] == '原有摘要'


def test_recovery_failure_does_not_starve_unattempted_reports(tmp_path):
    path = str(tmp_path / 'reports.db')
    with DatabaseManager(path) as db:
        for n in range(3):
            db.insert_report(f'Report {n}', f'https://example.org/{n}', 'Example')
    ai = Mock()
    ai.summarize_report.return_value = None
    ai.last_error = 'HTTP 403'
    for _ in range(3):
        recover_missing_summaries(path, ai, limit=1)
    assert len({call.args[0] for call in ai.summarize_report.call_args_list}) == 3


def test_truncated_model_output_is_rejected():
    ai = AISummarizer(api_key='test', endpoint='model', request_delay=0)
    response = Mock(ok=True)
    response.json.return_value = {'choices': [{'finish_reason': 'length', 'message': {'content': '{"summary":'}}]}
    ai.session.post = Mock(return_value=response)
    assert ai._call_ark_api('test') is None
    assert '截断' in ai.last_error


def test_challenge_page_is_not_summarized():
    ai = AISummarizer(api_key='test', endpoint='model', request_delay=0)
    response = Mock(headers={'Content-Type': 'text/html'}, content=b'<html><title>Just a moment...</title><body>Verify you are human</body></html>')
    ai.session.get = Mock(return_value=response)
    ai._call_ark_api = Mock()
    assert ai.summarize_report('https://example.org/report', 'Report') is None
    ai._call_ark_api.assert_not_called()
    assert '验证页' in ai.last_error


def test_public_abstract_is_used_instead_of_navigation_or_full_text():
    ai = AISummarizer(api_key='test', endpoint='model', request_delay=0)
    abstract = 'Public abstract about flood resilience and urban transit. ' * 5
    html = f'<html><nav>Menus</nav><main>Article metadata<section id="abstracts">{abstract}</section>Full text requires access</main></html>'
    response = Mock(headers={'Content-Type': 'text/html'}, content=html.encode())
    ai.session.get = Mock(return_value=response)
    assert ai._fetch_page_content('https://example.org/article') == abstract.strip()


def test_monitor_recovers_before_discovery_without_email(monkeypatch, tmp_path):
    from monitor import MultiWebsiteMonitor
    events = []
    monkeypatch.setattr('monitor.recover_missing_summaries', lambda *args: events.append('recover'))
    monitor = MultiWebsiteMonitor([], db_path=str(tmp_path / 'reports.db'), enable_email=False)
    try:
        assert monitor.run_once(send_email=False, delay_between_sites=0) == {}
        assert events == ['recover']
    finally:
        monitor.session.close()


def test_summary_button_preserves_quotes_and_newlines_without_inline_js():
    from pathlib import Path
    from flask import Flask, render_template
    from bs4 import BeautifulSoup
    app = Flask(__name__, template_folder=str(Path(__file__).resolve().parents[1] / 'templates'))
    # Use actual report template and a minimal base so this check needs no app scheduler.
    from jinja2 import ChoiceLoader, DictLoader
    app.jinja_loader = ChoiceLoader([DictLoader({'base.html': '{% block content %}{% endblock %}'}), app.jinja_loader])
    title = 'Farmers\' "choices"'
    summary = '第一行\n第二行的 "引号" 与 apostrophe\'s'
    with app.test_request_context():
        html = render_template('reports.html', reports=[dict(id=1, title='English', url='https://example.org',
            ai_chinese_title=title, ai_summary=summary, ai_keywords='关键词', source_website='Example')])
    button = BeautifulSoup(html, 'html.parser').select_one('.btn-ai-summary')
    assert button['data-ai-title'] == title
    assert button['data-ai-summary'] == summary
    assert not button.has_attr('onclick')
