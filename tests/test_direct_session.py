"""Exercise patched upstream queue routing without loading model weights."""
import ast, copy, os, time, unittest
from pathlib import Path
from types import SimpleNamespace

class Store:
 def __init__(self):self.sessions={};self.jobs={}
 def get_session(self,s):return copy.deepcopy(self.sessions.get(s))
 def put_session(self,s,v):self.sessions[s]=copy.deepcopy(v)
 def delete_session(self,s):self.sessions.pop(s,None)
 def patch(self,j,**v):self.jobs.setdefault(j,{}).update(v)

class Request:
 @staticmethod
 def model_validate(p):return SimpleNamespace(**p)

class DirectSessionTest(unittest.TestCase):
 def test_generate_rollback_branch_and_reset(self):
  root=Path(os.environ['NOMAS_TEST_ROOT'])
  tree=ast.parse((root/'apps/seg_ar_web_server.py').read_text())
  fn=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='execute_queue_job')
  for n in ast.walk(fn):
   if isinstance(n,ast.arg):n.annotation=None
   if isinstance(n,ast.FunctionDef):n.returns=None
  namespace={'GenerateRequest':Request,'time':time,'UnsupportedStreamingRollbackError':type('RollbackError',(Exception,),{})}
  exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'queue','exec'),namespace)
  execute=namespace['execute_queue_job'];store=Store();counter=[0];rollbacks=[]
  def generate(req):
   counter[0]+=1
   return {'id':str(counter[0]),'video_url':'test.mp4','frames':49,'fps':24}
  service=SimpleNamespace(generate=generate,rollback_session=lambda sid:rollbacks.append(sid) or {'remaining_segments':1})
  def gen(j,reset=False):execute(service,store,{'id':j,'kind':'generate','payload':{'session_id':'test','preserve_kv_cache':True,'reset_session':reset}})
  gen('anchor',True);gen('left');self.assertEqual(len(store.sessions['test']['result_history']),2)
  execute(service,store,{'id':'undo','kind':'rollback','payload':{'session_id':'test'}})
  self.assertEqual(store.jobs['undo']['status'],'succeeded');self.assertEqual(rollbacks,['test']);self.assertEqual(store.sessions['test']['last_result']['id'],'1')
  gen('right');self.assertEqual([r['id'] for r in store.sessions['test']['result_history']],['1','3'])
  gen('reset',True);self.assertEqual(len(store.sessions['test']['result_history']),1)
if __name__=='__main__':unittest.main()
