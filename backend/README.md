Quick FastAPI backend to expose the algorithms package.

Run locally:

```bash
python -m pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Endpoints:
- `GET /health`
- `POST /evaluate` { fen, ply }
- `POST /generate_moves` { fen }
- `POST /order_moves` { fen, moves[], tt_move }
- `POST /search` { fen, max_depth, engine_is_black }
- `POST /tt/clear`
