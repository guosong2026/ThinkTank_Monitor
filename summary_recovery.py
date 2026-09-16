"""Bounded, persistent recovery of missing summaries; never sends notifications."""
import logging

from db import DatabaseManager

logger = logging.getLogger(__name__)


def recover_missing_summaries(db_path, summarizer, limit=10):
    """Retry recent missing summaries at most once per six hours per report.

    Oldest attempts go first so permanently blocked URLs cannot starve other work.
    Run before discovery so a new report is not immediately requested twice.
    """
    if not summarizer.is_configured():
        return 0
    recovered = 0
    with DatabaseManager(db_path) as db:
        db.connection.execute('''CREATE TABLE IF NOT EXISTS ai_summary_attempts (
            report_id INTEGER PRIMARY KEY,
            attempts INTEGER NOT NULL DEFAULT 0,
            last_attempt TEXT NOT NULL,
            last_error TEXT NOT NULL DEFAULT ''
        )''')
        rows = db.connection.execute('''
            SELECT r.id, r.url, r.title FROM reports r
            LEFT JOIN ai_summary_attempts a ON a.report_id = r.id
            WHERE (trim(coalesce(r.ai_summary, '')) = ''
                OR trim(coalesce(r.ai_chinese_title, '')) = ''
                OR trim(coalesce(r.ai_keywords, '')) = '')
              AND datetime(r.discovered_time) >= datetime('now', '-60 days')
              AND (a.last_attempt IS NULL OR a.last_attempt <= datetime('now', '-6 hours'))
            ORDER BY coalesce(a.last_attempt, ''), r.discovered_time DESC, r.id DESC
            LIMIT ?
        ''', (max(0, min(int(limit), 50)),)).fetchall()
        for row in rows:
            # Claim before network IO; an interrupted attempt is retried after cooldown.
            claim = db.connection.execute('''
                INSERT INTO ai_summary_attempts(report_id, attempts, last_attempt, last_error)
                VALUES (?, 1, datetime('now'), '摘要生成中或上次执行被中断')
                ON CONFLICT(report_id) DO UPDATE SET attempts = attempts + 1,
                    last_attempt = datetime('now'), last_error = excluded.last_error
                WHERE last_attempt <= datetime('now', '-6 hours')
            ''', (row['id'],))
            db.connection.commit()
            if not claim.rowcount:
                continue
            try:
                result = summarizer.summarize_report(row['url'], row['title'])
                if result and db.update_ai_summary(
                    row['id'], result['chinese_title'], result['keywords'], result['summary']
                ):
                    recovered += 1
                    error = ''
                else:
                    error = getattr(summarizer, 'last_error', '') or '摘要生成或保存失败'
            except Exception as exc:
                error = f'摘要补偿异常: {type(exc).__name__}'
            db.connection.execute(
                'UPDATE ai_summary_attempts SET last_error = ? WHERE report_id = ?',
                (error[:1000], row['id']),
            )
            db.connection.commit()
            if error:
                logger.warning('报告 %s 摘要待补偿: %s', row['id'], error)
        logger.info('摘要补偿完成：检查 %s 篇，补全 %s 篇', len(rows), recovered)
    return recovered
