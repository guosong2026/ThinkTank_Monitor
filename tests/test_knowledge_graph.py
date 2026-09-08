from datetime import datetime

from db import DatabaseManager
from knowledge_graph import KnowledgeGraphBuilder


class FakeKeywordSummarizer:
    def __init__(self):
        self.calls = 0

    def is_configured(self):
        return True

    def extract_keywords_from_summary(self, title, summary, candidate_count=20,
                                      excluded_keywords=None):
        self.calls += 1
        return [
            "2026", "九月", "报告", "文章", "气候变迁", "城市治理",
            "能源转型", "碳中和", "生态系统", "住房政策", "公平转型",
            "绿色金融", "公共交通", "生物多样性",
        ]


def _insert_summarized_report(db, title="Climate report"):
    report_id = db.insert_report(title, f"https://example.com/{title}", "Test")
    assert report_id is not None
    assert db.update_ai_summary(report_id, "气候报告", "气候，政策，城市", "这是一份已有的AI总结。")
    return report_id


def test_graph_uses_ten_normalized_ai_keywords_and_persists_cache(tmp_path):
    db_path = tmp_path / "reports.db"
    with DatabaseManager(str(db_path)) as db:
        report_id = _insert_summarized_report(db)

    summarizer = FakeKeywordSummarizer()
    builder = KnowledgeGraphBuilder(db_path=str(db_path), ai_summarizer=summarizer)
    assert len(builder.load_reports_from_db(months=2)) == 1
    builder.process_reports(top_k_keywords=10, global_top_n=50)

    keywords = builder.report_keywords[report_id]
    assert len(keywords) == 10
    assert "气候变化" in keywords
    assert not {"2026", "九月", "报告", "文章"}.intersection(keywords)
    assert summarizer.calls == 1

    cached_summarizer = FakeKeywordSummarizer()
    cached_builder = KnowledgeGraphBuilder(db_path=str(db_path), ai_summarizer=cached_summarizer)
    cached_builder.load_reports_from_db(months=2)
    cached_builder.process_reports(top_k_keywords=5, global_top_n=50)
    assert cached_summarizer.calls == 0
    assert cached_builder.report_keywords[report_id] == keywords[:5]


def test_graph_only_loads_summarized_reports_from_previous_two_calendar_months(tmp_path):
    db_path = tmp_path / "reports.db"
    with DatabaseManager(str(db_path)) as db:
        recent_id = _insert_summarized_report(db, "Recent")
        old_id = _insert_summarized_report(db, "Old")
        missing_id = db.insert_report("Missing", "https://example.com/missing", "Test")
        db.connection.execute(
            "UPDATE reports SET discovered_time = ? WHERE id = ?",
            ("2026-06-30T12:00:00", old_id),
        )
        db.connection.execute(
            "UPDATE reports SET discovered_time = ? WHERE id IN (?, ?)",
            ("2026-09-08T12:00:00", recent_id, missing_id),
        )
        db.connection.commit()

    builder = KnowledgeGraphBuilder(db_path=str(db_path), ai_summarizer=FakeKeywordSummarizer())
    reports = builder.load_reports_from_db(months=2, now=datetime(2026, 9, 8, 12, 0, 0))
    assert [report["id"] for report in reports] == [recent_id]
