import json
import logging
import sqlite3

import pytest

from ai_summarizer import AISummarizer
from db import DatabaseManager
from monitor_service import MonitorService


def test_ai_result_parser_accepts_json_and_legacy_multiline():
    summarizer = AISummarizer(api_key="test", endpoint="model", request_delay=0)

    parsed_json = summarizer._parse_result(
        '```json\n{"chinese_title":"气候报告","keywords":["气候","能源","政策"],'
        '"summary":"这是一份测试总结。"}\n```'
    )
    assert parsed_json == {
        "chinese_title": "气候报告",
        "keywords": "气候，能源，政策",
        "summary": "这是一份测试总结。",
    }

    parsed_legacy = summarizer._parse_result(
        "标题：气候报告\n关键词：气候, 能源, 政策\n总结：第一句。\n第二句。"
    )
    assert parsed_legacy["summary"] == "第一句。 第二句。"


def test_database_defaults_to_six_hours(tmp_path):
    db_path = tmp_path / "reports.db"
    with DatabaseManager(str(db_path)) as db:
        assert db.get_setting("check_interval_hours") == "6"


def test_database_migrates_old_two_hour_default_once(tmp_path):
    db_path = tmp_path / "old.db"
    connection = sqlite3.connect(db_path)
    connection.execute(
        "CREATE TABLE settings (id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT UNIQUE, "
        "value TEXT, updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    connection.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?)",
        ("check_interval_hours", "2"),
    )
    connection.commit()
    connection.close()

    with DatabaseManager(str(db_path)) as db:
        assert db.get_setting("check_interval_hours") == "6"
        assert db.get_setting("check_interval_migrated_to_6") == "1"
        db.set_setting("check_interval_hours", "2")

    # 迁移标记存在后，尊重用户后来手动设置的2小时。
    with DatabaseManager(str(db_path)) as db:
        assert db.get_setting("check_interval_hours") == "2"


def test_scheduler_uses_six_hour_default(tmp_path, monkeypatch):
    service = MonitorService(str(tmp_path / "scheduler.db"))
    monkeypatch.setattr(service, "_create_monitor", lambda: object())
    monkeypatch.setattr(service, "_run_once_with_email", lambda: {})
    try:
        assert service.start_monitoring() is True
        job = service.scheduler.get_job(service.job_id)
        assert job.trigger.interval.total_seconds() == 6 * 3600
    finally:
        service.shutdown()


def test_ai_config_is_persisted_masked_and_reloads_monitor(tmp_path):
    service = MonitorService(str(tmp_path / "service.db"))
    service.monitor = object()

    assert service.update_ai_config(
        api_key="secret-api-key-1234",
        endpoint="doubao-test-model",
        base_url="https://ark.cn-beijing.volces.com/api/v3/",
    )
    config = service.get_ai_config()

    assert service.monitor is None
    assert config["configured"] is True
    assert config["api_key_masked"] == "••••••••1234"
    assert "secret-api-key" not in json.dumps(config, ensure_ascii=False)
    assert config["base_url"] == "https://ark.cn-beijing.volces.com/api/v3"


def test_ai_api_key_is_not_written_to_logs(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    service = MonitorService(str(tmp_path / "logs.db"))
    secret = "must-never-appear-in-logs"
    service.update_ai_config(
        api_key=secret,
        endpoint="doubao-test-model",
        base_url="https://ark.cn-beijing.volces.com/api/v3",
    )
    assert secret not in caplog.text
    assert "***已脱敏***" in caplog.text


def test_ai_config_rejects_non_volcengine_base_url(tmp_path):
    service = MonitorService(str(tmp_path / "service.db"))
    with pytest.raises(ValueError, match="火山引擎官方HTTPS地址"):
        service.update_ai_config(
            api_key="secret",
            endpoint="model",
            base_url="https://example.com/api/v3",
        )


def test_ai_config_http_endpoints_do_not_expose_key(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "api.db"))
    import app as app_module

    app_module.monitor_service = MonitorService(str(tmp_path / "api.db"))
    client = app_module.app.test_client()

    response = client.post(
        "/api/ai-config",
        json={
            "api_key": "route-secret-key-9876",
            "endpoint": "doubao-route-model",
            "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        },
    )
    assert response.status_code == 200
    assert b"route-secret-key" not in response.data

    response = client.get("/api/ai-config")
    assert response.status_code == 200
    assert response.get_json()["config"]["api_key_masked"] == "••••••••9876"
    assert b"route-secret-key" not in response.data
