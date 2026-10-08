#!/usr/bin/env python3
"""Isolated loopback Studio UI simulator: synthetic evidence; zero external calls."""
from copy import deepcopy
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import RLock
from urllib.parse import urlsplit, parse_qs
import json

ROOT=Path(__file__).resolve().parents[1]
STATIC=ROOT/'apps/api/app/static'
PORT=8766
PHASES=[f'A{x}' for x in range(1,7)]
LOCK=RLock()
def timestamp(): return datetime.now(timezone.utc).isoformat()

def evidence(phase,revision):
    path='docs/planning/cycle1.md'
    return {'phase_id':phase,'repo_full_name':'simulation/campusconnect-team',
        'commit_sha':('29aabbcc' if revision==1 else '06ddeeff')+'0'*32,
        'coverage':48 if revision==1 else 78,
        'items':[{'ref':'E-1','title':path,'detail':'Synthetic evidence for interface testing',
            'status':'weak' if revision==1 else 'present','quality':'weak' if revision==1 else 'present',
            'source_provenance':'PROJECT_SPECIFIC','phase_scope':'CURRENT_PHASE','equivalent_path':path,
            'scope_reason':'Synthetic test fixture, not real evidence',
            'condition':{'key':'weak' if revision==1 else 'present','label':'Check source','why':'Confirm who verifies work','support':{}}}],
        'artifacts':[{'path':path,'title':path,'summary':'Synthetic planning record; revision '+str(revision),
                      'provenance':'PROJECT_SPECIFIC','quality':'weak' if revision==1 else 'present'}],
        'findings':[{'id':'sim-f1','title':'Verification ownership needs an explicit decision',
            'statement':'Synthetic concern: the snapshot needs an inspectable verification decision.',
            'significance':'A named owner alone cannot demonstrate verification.','category':'accountability',
            'status':'open','provenance':'REVIEW','evidence_refs':['PATH:'+path]}],
        'strengths':[],'semantic_review':{'inspection':{'omitted_artifact_count':0,'inspected_artifact_count':1}}}

def challenge(phase,revision):
    return {'title':'Who can demonstrate that the plan is executable?',
        'lens':'chief_architect','prompt':'What evidence would justify proceeding?',
        'opening_text':f'SIMULATED reviewer (no AI). This is synthetic {phase} repository revision {revision}. What should your team verify before implementation?',
        'level':'developing','reviewer':{'name':'Simulation Reviewer','role':'Synthetic coach','portrait':'/assets/reviewers/maya-chen.svg'},
        'finding':{'id':'sim-f1','title':'Verification ownership needs an explicit decision'},
        'evidence_refs':['PATH:docs/planning/cycle1.md'],
        'noticed':'Synthetic ownership gap','significance':'Verification is not established by a filename.',
        'decision_question':'Which control should be required?'}

class State:
    def __init__(self):self.reset()
    def reset(self):
        self.revision=1;self.session_number=40;self.snapshot_number=80
        self.sessions={};self.snapshots={};self.turns={};self.response_cache={};self.fail_next=False;self.fail_next_response=False;self.api_mutations=0;self.scenario_hint=""
    def prepare_older_review_newer_evidence(self):
        """Synthetic Sam scenario: #41 remains on old FACT; latest A2 evidence is #82."""
        self.reset()
        _,first=self.api('/api/v1/reviews/start','POST',{'phase_id':'A2','mode':'board_review'})
        old=first['session_id']
        self.api(f'/api/v1/reviews/{old}/respond','POST',{'response':'Who verifies our A2 plan?','client_turn_id':'fixture-old-response'})
        self.revision=2
        _,second=self.api('/api/v1/reviews/start','POST',{'phase_id':'A2','mode':'board_review'})
        self.scenario_hint=f'Ready: Review #{old} is older (29aabbcc); Review #{second["session_id"]} is newer (06ddeeff). Open Review History, select #{old}, then Engineering Evidence. Inspect original evidence from the warning.'
        return self.view()
    def prepare_long_conversation(self):
        """Synthetic scroll/readability fixture with an existing A2 session."""
        self.reset()
        _,review=self.api('/api/v1/reviews/start','POST',{'phase_id':'A2','mode':'board_review'})
        sid=review['session_id']
        for i in range(24):
            message=f'Exchange {i+1}: team engineers examine a long synthetic verification discussion. '+('What does the frozen snapshot actually establish? '*17)
            self.turns[sid].extend([{'actor':'student','lens':'student','content':message,'signals':{}},
                {'actor':'reviewer','lens':'chief_architect','content':'SYNTHETIC ONLY: Verify the evidence and explain your decision. '+message,'signals':{}}])
        self.scenario_hint=f'Ready: 24 long exchanges are saved in open Review #{sid}. Choose Review History, reopen #{sid}, read earlier messages, and check your reply area.'
        return self.view()
    def view(self):
        return {'revision':self.revision,'commit':evidence('A2',self.revision)['commit_sha'][:8],
            'sessions':len(self.sessions),'snapshots':len(self.snapshots), 'api_mutations':self.api_mutations,
            'model_calls':0,'failure_queued':self.fail_next,'response_failure_queued':self.fail_next_response, 'scenario_hint':self.scenario_hint}
    def api(self,path,method,body):
        if path=='/health' and method=='GET':return 200,{'environment':'development','semantic_coaching_ready':True,'model':'SYNTHETIC, NO AI','version':'0.18.0'}
        if path=='/api/v1/course' and method=='GET':return 200,{'course':{'judgment_dimensions':[]}}
        if path=='/api/v1/dev/seed' and method=='POST':return 200,{'user_id':1,'team_id':1}
        if path=='/api/v1/onboarding/users/1' and method=='GET':
            return 200,{'user':{'id':1,'name':'Alex Simulation','github_login':'synthetic'},
              'onboarding':{'institutional_identity':True,'team_assigned':True,'github_identity':True,'repository_connected':True},
              'sections':[{'section':{'id':1,'display_name':'Simulation only'},
                'team':{'id':1,'name':'Synthetic Team Vector','project_name':'CampusConnect (synthetic)',
                    'repo_full_name':'simulation/campusconnect-team','team_key':'team-01',
                    'members':[{'name':'Alex Simulation','github_login':'synthetic'}]},
                'repository':{'repo_full_name':'simulation/campusconnect-team'},
                'phase_access':{'phases':[{'phase_id':p,'status':'released'} for p in PHASES],
                    'current_phase':'A2','released':PHASES}}]}
        if path=='/api/v1/reviews' and method=='GET':
            # Exercise the server's stable, bounded history paging contract.
            limit=min(max(int(body.get('limit',12)),1),50)
            offset=min(max(int(body.get('offset',0)),0),10000)
            sessions=list(reversed(list(self.sessions.items())))
            page=sessions[offset:offset+limit]
            return 200,{'has_more':offset+limit<len(sessions),'sessions':[
                {'id':n,'phase_id':s['phase'],'status':s['status'],
                 'started_at':s['started_at'],'mode':s['mode'],'committed':False,'evaluation':{}}
                for n,s in page]}
        if path=='/api/v1/reviews/evidence/current' and method=='GET':
            phase=body.get('phase_id','A2')
            snaps=[v for v in self.snapshots.values() if v['phase']==phase]
            if not snaps:return 200,{'available':False}
            snap=snaps[-1]
            return 200,{'available':True,'snapshot_id':snap['id'],'created_at':snap['created_at'],
                'team':{'name':'Synthetic Team Vector','project_name':'CampusConnect (synthetic)'},
                'evidence':deepcopy(snap['evidence'])}
        if path=='/api/v1/reviews/start' and method=='POST':
            if self.fail_next:
                self.fail_next=False
                return 503,{'detail':'SIMULATED network interruption. The earlier review is unchanged.'}
            phase=body.get('phase_id','A2')
            if phase not in PHASES:return 400,{'detail':'Unsupported synthetic phase'}
            self.api_mutations+=1
            matches=[v for v in self.snapshots.values() if (v['phase'],v['revision'])==(phase,self.revision)]
            reused=bool(matches)
            if reused:snap=matches[0]
            else:
                self.snapshot_number+=1
                snap={'id':self.snapshot_number,'phase':phase,'revision':self.revision,
                    'created_at':timestamp(),'evidence':evidence(phase,self.revision)}
                self.snapshots[snap['id']]=snap
            self.session_number+=1;sid=self.session_number
            c=challenge(phase,self.revision)
            self.sessions[sid]={'phase':phase,'status':'active','mode':body.get('mode','board_review'),
                'snapshot_id':snap['id'],'started_at':timestamp(),'challenge':c}
            self.turns[sid]=[{'actor':'reviewer','lens':'chief_architect','content':c['opening_text'],
                'signals':{'reviewer':c['reviewer']}}]
            return 200,{'session_id':sid,'snapshot_id':snap['id'],'snapshot_created_at':snap['created_at'],
                'evidence_cache_reused':reused,'evidence':deepcopy(snap['evidence']),'challenge':deepcopy(c)}
        if path.startswith('/api/v1/reviews/evidence/') and path.endswith('/artifact') and method=='GET':
            # Return the artifact from the requested FROZEN snapshot, not the
            # simulator's currently selected commit. Later work cannot backfill it.
            parts=path.split('/')
            snap_id=int(parts[5]) if len(parts)>5 and parts[5].isdigit() else None
            snap=self.snapshots.get(snap_id)
            if not snap:return 404,{'detail':'Synthetic frozen snapshot not found'}
            commit=snap['evidence']['commit_sha']
            return 200,{'path':body.get('path',''),'commit_sha':commit,
                'provenance':'PROJECT_SPECIFIC','quality':'synthetic','summary':'Synthetic data only',
                'content':f'SIMULATION ONLY: frozen commit {commit[:8]}. No GitHub source retrieved.\nA synthetic planning record for interface testing.',
                'additional_windows':[],'disclosure_status':'visible','source':'retained_copy',
                'may_be_incomplete':False,'url':''}
        if path.startswith('/api/v1/reviews/'):
            parts=path.split('/');sid=int(parts[4]) if len(parts)>4 and parts[4].isdigit() else None
            if sid not in self.sessions:return 404,{'detail':'Synthetic session not found'}
            s=self.sessions[sid];snap=self.snapshots[s['snapshot_id']]
            if len(parts)==5 and method=='GET':
                return 200,{'session':{'id':sid,'phase_id':s['phase'],'status':s['status'],
                    'mode':s['mode'],'started_at':s['started_at']},
                    'snapshot':{'id':snap['id'],'created_at':snap['created_at']},
                    'evidence':deepcopy(snap['evidence']),
                    'state':{'challenge':deepcopy(s['challenge']),'committed_position':False,
                        'evaluation':{},'reasoning_state':{}},'turns':deepcopy(self.turns[sid])}
            if len(parts)==6 and parts[5]=='complete' and method=='POST':
                self.api_mutations+=1;s['status']='completed';return 200,{'status':'completed','session_id':sid}
            if len(parts)==6 and parts[5]=='respond' and method=='POST':
                if self.fail_next_response:
                    self.fail_next_response=False
                    return 503,{'detail':'SIMULATED reply failure before saving. Your draft should remain available for retry.'}
                # Mirror the real review API's idempotent logical-turn contract so a lost
                # HTTP reply does not teach the wrong recovery behavior.
                turn_id=str(body.get('client_turn_id') or '')
                cache_key=(sid,turn_id) if turn_id else None
                if cache_key and cache_key in self.response_cache:
                    prior=deepcopy(self.response_cache[cache_key]);prior['duplicate']=True
                    return 200,prior
                if s['status']!='active':return 409,{'detail':'Finished synthetic review is read-only.'}
                self.api_mutations+=1
                msg=body.get('response') or 'Synthetic question'
                answer='SIMULATION: This reply is scripted; no model is called. Snapshot '+str(snap['id'])+' remains fixed.'
                self.turns[sid].extend([{'actor':'student','lens':'student','content':msg,'signals':{}},
                    {'actor':'reviewer','lens':'chief_architect','content':answer,'signals':{}}])
                result={'follow_up':{'text':answer,'lens':'chief_architect','reviewer':{'name':'Simulation Reviewer','role':'Synthetic coach','portrait':'/assets/reviewers/maya-chen.svg'},'kind':'synthetic'},'evaluation':{},'reasoning_state':{},'coaching_level':'simulated'}
                if cache_key:self.response_cache[cache_key]=deepcopy(result)
                return 200,result
            return 409,{'detail':'Advanced coaching actions are intentionally not simulated.'}
        return 404,{'detail':'Unknown synthetic route; no real API call was attempted.'}

SIM=State()
class Handler(BaseHTTPRequestHandler):
    def log_message(self,fmt,*args):print('SIM',self.command,urlsplit(self.path).path)
    def emit(self,code,data,mime='application/json; charset=utf-8'):
        blob=data if isinstance(data,bytes) else json.dumps(data).encode()
        self.send_response(code)
        for k,v in [('Content-Type',mime),('Content-Length',str(len(blob))),('Cache-Control','no-store'),
                    ('X-Content-Type-Options','nosniff'),('X-Frame-Options','DENY'),
                    ('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'")]:
            self.send_header(k,v)
        self.end_headers();self.wfile.write(blob)
    def dispatch(self):
        parsed=urlsplit(self.path);path=parsed.path
        qs={k:v[0] for k,v in parse_qs(parsed.query).items()}
        if path in ('/','/index.html') and self.command=='GET':
            html=(STATIC/'index.html').read_text().replace('<script src="/assets/studio.js"></script>',
                '<script src="/simulation-controls.js"></script>\n<script src="/assets/studio.js"></script>')
            return self.emit(200,html.encode(),'text/html; charset=utf-8')
        if path in ('/assets/studio.js','/assets/studio.css','/simulation-controls.js') and self.command=='GET':
            file=ROOT/'tools/student_simulation_controls.js' if path=='/simulation-controls.js' else STATIC/path.rsplit('/',1)[-1]
            return self.emit(200,file.read_bytes(),'application/javascript; charset=utf-8' if path.endswith('.js') else 'text/css; charset=utf-8')
        # Only bundled portraits are available in the isolated local simulation.
        if path=='/assets/reviewers/maya-chen.svg' and self.command=='GET':
            return self.emit(200,(STATIC/'reviewers/maya-chen.svg').read_bytes(),'image/svg+xml')
        with LOCK:
            if path=='/__simulation/state' and self.command=='GET':return self.emit(200,SIM.view())
            if path.startswith('/__simulation/') and self.command=='POST':
                if path=='/__simulation/advance':SIM.revision=2;SIM.scenario_hint='Simulated newer commit is available, but the earlier saved snapshot remains frozen. Start another review to capture it.'
                elif path=='/__simulation/older-newer':SIM.prepare_older_review_newer_evidence()
                elif path=='/__simulation/long-conversation':SIM.prepare_long_conversation()
                elif path=='/__simulation/fail-response':SIM.fail_next_response=True;SIM.scenario_hint='The next review response will fail before saving. Type a reply, send, then retry when it fails.'
                elif path=='/__simulation/reset':SIM.reset()
                elif path=='/__simulation/fail-start':SIM.fail_next=True
                elif path=='/__simulation/mixed-history':
                    for number in range(16):
                        _,result=SIM.api('/api/v1/reviews/start','POST',{'phase_id':PHASES[number%6],'mode':'board_review'})
                        if number%3==0:SIM.api(f"/api/v1/reviews/{result['session_id']}/complete",'POST',{})
                else:return self.emit(404,{'detail':'Invalid simulation action'})
                return self.emit(200,SIM.view())
            if path.startswith('/api/') or path=='/health':
                length=int(self.headers.get('Content-Length','0'))
                if length>65536:return self.emit(413,{'detail':'Simulation request too large'})
                try: body=json.loads(self.rfile.read(length)) if length else {}
                except (ValueError,UnicodeDecodeError):return self.emit(400,{'detail':'Invalid JSON'})
                status,response=SIM.api(path,self.command,{**qs,**body})
                return self.emit(status,response)
        return self.emit(404,{'detail':'This local simulator has no external routes.'})
    do_GET=dispatch
    do_POST=dispatch
    do_PUT=dispatch
    do_DELETE=dispatch

def main():
    print(f'SIMULATION ONLY: http://127.0.0.1:{PORT}/ — no GitHub, model, Azure, real database or student data.',flush=True)
    ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()
if __name__=='__main__':main()
