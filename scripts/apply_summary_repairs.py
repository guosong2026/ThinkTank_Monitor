"""Apply reviewed summaries to a NEW database copy, preserving all other data."""
import argparse
import json
from pathlib import Path
import sqlite3


def apply_repairs(source, destination, manifest):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination or destination.exists():
        raise ValueError('输出必须是尚不存在的新文件，不能覆盖原数据库')
    repairs = json.loads(Path(manifest).read_text(encoding='utf-8'))
    before = sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)
    output = sqlite3.connect(destination)
    changed = []
    try:
        before.backup(output)
        with output:
            for item in repairs:
                row = output.execute(
                    'SELECT id, ai_summary FROM reports WHERE url = ?', (item['url'],)
                ).fetchone()
                if row is None:
                    raise ValueError(f"报告URL不存在: {item['id']}")
                if row[1] and row[1].strip():
                    continue
                assert 0 < len(item['summary']) <= 200
                assert item['chinese_title'] and item['keywords']
                output.execute('''UPDATE reports SET ai_chinese_title = ?,
                    ai_keywords = ?, ai_summary = ? WHERE id = ?''', (
                    item['chinese_title'], item['keywords'], item['summary'], row[0],
                ))
                changed.append(row[0])
        assert output.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        # Check every row and field, not only aggregate counts.
        old_rows = before.execute('SELECT * FROM reports ORDER BY id').fetchall()
        new_rows = output.execute('SELECT * FROM reports ORDER BY id').fetchall()
        columns = [r[1] for r in before.execute('PRAGMA table_info(reports)')]
        ai_columns = {'ai_chinese_title', 'ai_keywords', 'ai_summary'}
        assert len(old_rows) == len(new_rows)
        for old, new in zip(old_rows, new_rows):
            for index, column in enumerate(columns):
                if column in ai_columns and old[0] in changed:
                    continue
                assert old[index] == new[index], (old[0], column)
        tables = [r[0] for r in before.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        for table in tables:
            if table == 'reports':
                continue
            quoted = '"' + table.replace('"', '""') + '"'
            assert before.execute(f'SELECT * FROM {quoted} ORDER BY rowid').fetchall() == output.execute(
                f'SELECT * FROM {quoted} ORDER BY rowid'
            ).fetchall(), table
        return changed
    finally:
        output.close()
        before.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('destination')
    parser.add_argument('--manifest', default=str(
        Path(__file__).resolve().parents[1] / 'data/repair_20260916/summaries.json'
    ))
    args = parser.parse_args()
    print('Updated IDs:', apply_repairs(args.source, args.destination, args.manifest))
