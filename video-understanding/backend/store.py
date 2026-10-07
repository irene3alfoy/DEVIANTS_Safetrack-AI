import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from .config import DATA

@contextmanager
def connection():
    db = sqlite3.connect(DATA / 'video.sqlite', timeout=30)
    db.row_factory = sqlite3.Row
    try:
        yield db
        db.commit()
    finally:
        db.close()

def init():
    with connection() as db:
        db.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS videos (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events (video_id TEXT, id TEXT, payload TEXT, PRIMARY KEY(video_id,id));
        CREATE TABLE IF NOT EXISTS entities (video_id TEXT, id TEXT, payload TEXT, PRIMARY KEY(video_id,id));
        CREATE TABLE IF NOT EXISTS relationships (video_id TEXT, payload TEXT);
        CREATE TABLE IF NOT EXISTS questions (id INTEGER PRIMARY KEY, video_id TEXT, payload TEXT);
        ''')
        # Interrupted jobs never masquerade as active or completed after a restart.
        for row in db.execute('SELECT id,payload FROM videos').fetchall():
            item = json.loads(row['payload'])
            if item['status'] in ('queued', 'processing'):
                item.update(status='failed', stage='Interrupted', error='The server restarted during analysis. Please analyze again.')
                db.execute('UPDATE videos SET payload=? WHERE id=?', (json.dumps(item), row['id']))

def save_video(item):
    with connection() as db:
        db.execute('INSERT OR REPLACE INTO videos VALUES (?,?)', (item['id'], json.dumps(item)))

def video(video_id):
    with connection() as db:
        row = db.execute('SELECT payload FROM videos WHERE id=?', (video_id,)).fetchone()
    if row is None:
        raise KeyError(video_id)
    return json.loads(row['payload'])

def update(video_id, **values):
    item = video(video_id)
    item.update(values)
    save_video(item)
    return item

def records(table, video_id):
    if table not in ('events', 'entities', 'relationships', 'questions'):
        raise ValueError('Invalid table')
    with connection() as db:
        rows = db.execute(f'SELECT payload FROM {table} WHERE video_id=? ORDER BY rowid', (video_id,)).fetchall()
    return [json.loads(row['payload']) for row in rows]

def save_results(video_id, events, entities, relationships):
    with connection() as db:
        for table, items in [('events', events), ('entities', entities), ('relationships', relationships)]:
            db.execute(f'DELETE FROM {table} WHERE video_id=?', (video_id,))
            for item in items:
                if table == 'relationships':
                    db.execute('INSERT INTO relationships VALUES (?,?)', (video_id, json.dumps(item)))
                else:
                    db.execute(f'INSERT INTO {table} VALUES (?,?,?)', (video_id, item['id'], json.dumps(item)))

def save_question(video_id, question, answer):
    item = {'question': question, **answer, 'created_at': datetime.now(timezone.utc).isoformat()}
    with connection() as db:
        db.execute('INSERT INTO questions(video_id,payload) VALUES (?,?)', (video_id, json.dumps(item)))
    return item
