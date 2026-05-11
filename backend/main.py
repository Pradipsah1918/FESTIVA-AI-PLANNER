from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .agents import Orchestrator
from .database import db_cursor, init_db, seed_db
from .rag import answer_query
from .schemas import KnowledgeRequest, PlanRequest

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / 'frontend'

app = FastAPI(title='Festiva Planner AI', version='1.0.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.mount('/static', StaticFiles(directory=FRONTEND_DIR / 'static'), name='static')
orchestrator = Orchestrator()


@app.on_event('startup')
def startup_event():
    init_db()
    seed_db()


@app.get('/')
def serve_index():
    return FileResponse(FRONTEND_DIR / 'index.html')


@app.get('/api/health')
def health():
    return {'status': 'ok'}


@app.post('/api/plan')
def create_plan(payload: PlanRequest):
    output = orchestrator.run(
        event_type=payload.event_type,
        city=payload.city,
        budget=payload.budget,
        preferences=payload.preferences,
        question=payload.question,
    )

    response = {
        'planner': output.planner,
        'optimizer': output.optimizer,
        'researcher': output.researcher,
        'vendors': output.vendors,
    }

    with db_cursor() as cur:
        cur.execute(
            'INSERT INTO generated_plans (event_type, budget, city, preferences, plan_json) VALUES (?, ?, ?, ?, ?)',
            (
                payload.event_type,
                payload.budget,
                payload.city,
                payload.preferences,
                json.dumps(response),
            ),
        )
    return response


@app.post('/api/knowledge')
def knowledge(payload: KnowledgeRequest):
    result = answer_query(payload.question, payload.event_type)
    return {'answer': result.answer, 'sources': result.sources}


@app.get('/api/history')
def history():
    with db_cursor() as cur:
        rows = cur.execute(
            'SELECT id, event_type, budget, city, preferences, created_at FROM generated_plans ORDER BY created_at DESC LIMIT 10'
        ).fetchall()
        return [dict(row) for row in rows]
