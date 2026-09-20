from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import ScoreEntry, TelemetryEvent
import sqlite3
import json
from typing import List, Dict, Any

app = FastAPI(title='Swarm Telemetry API')

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_PATH = 'swarm_telemetry.db'


def init_database():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Create scores table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL,
            score INTEGER NOT NULL,
            wave INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create telemetry table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            timestamp REAL NOT NULL,
            data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# Auto-initialize database on launch
init_database()


def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    return conn


@app.get('/api/health')
async def health_check():
    return {'status': 'ok'}


@app.get('/api/scores')
async def get_scores():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM scores ORDER BY created_at DESC')
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            'id': row[0],
            'player_name': row[1],
            'score': row[2],
            'wave': row[3],
            'created_at': row[4]
        }
        for row in rows
    ]


@app.post('/api/scores', response_model=ScoreEntry)
async def create_score(score_entry: ScoreEntry):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO scores (player_name, score, wave)
        VALUES (?, ?, ?)
    ''', (score_entry.player_name, score_entry.score, score_entry.wave))
    
    conn.commit()
    conn.close()
    
    return score_entry


@app.get('/api/telemetry')
async def get_telemetry():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM telemetry ORDER BY timestamp DESC LIMIT 100')
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        try:
            d = json.loads(row[3])
        except Exception:
            d = row[3]
        result.append({
            'id': row[0],
            'event_type': row[1],
            'timestamp': row[2],
            'data': d,
            'created_at': row[4]
        })
    return result


@app.post('/api/telemetry', response_model=TelemetryEvent)
async def create_telemetry(telemetry_event: TelemetryEvent):
    conn = get_db_connection()
    cursor = conn.cursor()
    data_str = json.dumps(telemetry_event.data)
    
    cursor.execute('''
        INSERT INTO telemetry (event_type, timestamp, data)
        VALUES (?, ?, ?)
    ''', (telemetry_event.event_type, telemetry_event.timestamp, data_str))
    
    conn.commit()
    conn.close()
    
    return telemetry_event


@app.get('/api/scores/{score_id}')
async def get_score_by_id(score_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM scores WHERE id = ?', (score_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        raise HTTPException(status_code=404, detail='Score not found')
    
    return {
        'id': row[0],
        'player_name': row[1],
        'score': row[2],
        'wave': row[3],
        'created_at': row[4]
    }