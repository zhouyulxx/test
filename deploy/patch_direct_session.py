"""Preserve direct structured-prompt session history for native KV rollback."""
from pathlib import Path

def patch_direct_sessions(root):
 p=Path(root)/'apps/seg_ar_web_server.py';s=p.read_text()
 if 'StreetView direct-session history' in s:return
 old='''                    result = {
                        **result,
                        "prompt_enhanced": True,
                        "pe_request_id": pe_request_id,
                    }
                store.patch(
'''
 new=old.replace('                store.patch(\n','''                elif request.preserve_kv_cache and request.session_id:
                    # StreetView direct-session history: PE is optional, KV is not.
                    sid = str(request.session_id)
                    direct = None if request.reset_session else store.get_session(sid)
                    if direct and not direct.get("direct_generation"):
                        raise ValueError("Cannot mix direct and PE session histories")
                    history = list((direct or {}).get("result_history") or [])
                    history.append(dict(result))
                    store.put_session(sid, {
                        "session_id": sid, "direct_generation": True,
                        "result_history": history, "last_result": dict(result),
                        "updated_at": time.time(),
                    })
                store.patch(
''')
 assert s.count(old)==1;s=s.replace(old,new)
 old='''                cache_result = self.rollback_session(session_id)
                result_history.pop()
'''
 new=old+'''                if session.get("direct_generation"):
                    previous = result_history[-1] if result_history else {}
                    if result_history:
                        session.update(result_history=result_history, last_result=previous, updated_at=time.time())
                        store.put_session(session_id, session)
                    else:
                        store.delete_session(session_id)
                    result = {**cache_result, "session_id": session_id,
                              "video_url": previous.get("video_url"),
                              "frames": int(previous.get("frames", 0)),
                              "fps": int(previous.get("fps", 24))}
                    store.patch(job_id, status="succeeded", result=result, **result, error=None)
                    return
'''
 assert s.count(old)==1;s=s.replace(old,new);compile(s,str(p),'exec');p.write_text(s)
 print('Direct prompt history and rollback patched')
if __name__=='__main__':
 import sys
 patch_direct_sessions(sys.argv[1] if len(sys.argv)>1 else '/Hy-Nomas')
