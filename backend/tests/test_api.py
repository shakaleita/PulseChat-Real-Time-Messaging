import importlib,os,sys,tempfile
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
temp = tempfile.mkdtemp(prefix='portfolio-test-')
os.environ['APP_DB']=str(Path(temp)/'test.db')
os.environ['OWNER_SETUP_TOKEN']='test-only-setup-token-1234567890123'
if 'main' in sys.modules: del sys.modules['main']
from main import app
client=TestClient(app)
assert client.post('/api/auth/register',json={'username':'qaowner','password':'DemoPassword123!','setup_token':'test-only-setup-token-1234567890123'}).status_code==201
assert client.post('/api/auth/login',json={'username':'qaowner','password':'DemoPassword123!'}).status_code==200

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



def test_v05_message_limits_and_room_statistics():
    assert client.post('/api/items',json={'room':'general','author':'Engineer','body':'x'*2001}).status_code==422
    assert client.post('/api/items',json={'room':'general','author':'Engineer','body':'Hello'}).status_code==201
    stats=client.get('/api/rooms/general/stats').json()
    assert stats['messages']>=1 and stats['authors']>=1

def test_v05_authentication():
    with TestClient(app) as anonymous:
        assert anonymous.get('/api/items').status_code==401
        assert anonymous.post('/api/auth/register',json={'username':'intruder','password':'DemoPassword123!','setup_token':'bad'}).status_code==403

# v0.6 request-origin and owner audit regression
def test_v06_audit_record_and_cross_site_guard():
    attempted=client.post('/api/__audit_probe_404')
    assert attempted.status_code==404
    audit=client.get('/api/auth/audit')
    assert audit.status_code==200
    assert any(row['method']=='POST' and row['path']=='/api/__audit_probe_404'
               and row['status_code']==404 for row in audit.json())
    assert client.get('/api/auth/audit',params={'limit':201}).status_code==422
    blocked=client.post('/api/__audit_probe_404',headers={'sec-fetch-site':'cross-site'})
    assert blocked.status_code==403

def test_room_names_are_canonical_and_search_is_bounded():
    assert client.post('/api/items',json={'room':'../../other','author':'QA','body':'Rejected'}).status_code==422
    assert client.get('/api/items',params={'room':'../unsafe'}).status_code==422
    assert client.get('/api/rooms/invalid.room/stats').status_code==422
    assert client.get('/api/messages/search',params={'room':'general','q':'X'*201}).status_code==422
    assert client.post('/api/items',json={'room':'project-alpha_1','author':'QA','body':'Allowed'}).status_code==201
