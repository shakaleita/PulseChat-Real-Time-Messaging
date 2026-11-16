import importlib,os,sys,tempfile
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
temp = tempfile.mkdtemp(prefix='portfolio-test-')
os.environ['APP_DB']=str(Path(temp)/'test.db')
if 'main' in sys.modules: del sys.modules['main']
from main import app
client=TestClient(app)

def test_health():
    r=client.get('/api/health')
    assert r.status_code==200 and r.json()['ok']

def test_initial_list():
    r=client.get('/api/items')
    assert r.status_code==200 and isinstance(r.json(),list)

def test_summary():
    r=client.get('/api/summary')
    assert r.status_code==200 and isinstance(r.json(),list)


# v0.3 regression tests
def test_room_directory_and_search_isolation():
    import uuid
    rid='qa-'+uuid.uuid4().hex[:8]
    r=client.post('/api/items',json={'room':rid,'author':'Example','body':'Orbital project update'})
    assert r.status_code==201
    assert any(x['room']==rid for x in client.get('/api/rooms').json())
    assert client.get('/api/messages/search',params={'room':rid,'q':'Orbital'}).json()[0]['id']==r.json()['id']
    assert client.get('/api/messages/search',params={'room':'other','q':'Orbital'}).json()==[]
    assert client.get('/api/messages/search',params={'room':rid,'q':'%'}).json()==[]

