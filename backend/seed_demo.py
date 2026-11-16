"""Insert optional synthetic demonstration records (safe to rerun)."""
from fastapi.testclient import TestClient
from main import app

SEEDS = [{'room': 'general', 'author': 'Alex', 'body': 'Welcome to PulseChat!'}, {'room': 'general', 'author': 'Jordan', 'body': 'Good to be here.'}]
client=TestClient(app)
if client.get('/api/items').json():
    print('Existing records found; skipping seed.')
else:
    for record in SEEDS:
        result=client.post('/api/items',json=record)
        result.raise_for_status()
    print('Added',len(SEEDS),'synthetic sample records.')
