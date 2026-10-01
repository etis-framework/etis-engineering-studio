let sessionId=null,currentEvidence=null,reviewSnapshotId=null,engineeringSnapshotId=null,artifactRequestId=0,finishingReview=false,reviewExitIntent=null,currentPhase='A1',demoContext=null,currentView='studio',interactionMode='decision',currentChallenge=null,currentReviewer=null,committed=false,semanticReady=false,pending=false,courseModel=null,appRole='student',studentContext=null,selectedSectionId=null,instructorSectionContextId=undefined,reviewMode='board',requestedFindingId=null,selectedFindingIds=new Set(),healthState=null,authenticatedUser=null,engineeringEvidenceData=null,activeEvidenceLens=null,pendingEntryContext=null,composerContext=null,artifactContext=null,csrfToken=null,currentInstructorTeamId=null,currentInstructorReviewSessionId=null,navigationReady=false,restoringNavigation=false;
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
let repositoryActionError='',repositoryActionErrorTeamId=null,repositoryEditorOpen=false;

const nativeFetch=window.fetch.bind(window);
window.fetch=(input,init={})=>{
  const inputRequest=typeof Request!=='undefined'&&input instanceof Request?input:null;
  const method=String(init.method||inputRequest?.method||'GET').toUpperCase();
  const appOrigin=new URL(document.baseURI).origin;
  const url=new URL(inputRequest?.url||String(input),document.baseURI);
  const unsafe=['POST','PUT','PATCH','DELETE'].includes(method);

  if(csrfToken&&unsafe&&url.origin===appOrigin){
    const headers=new Headers(init.headers||inputRequest?.headers||undefined);
    if(!headers.has('X-CSRF-Token'))headers.set('X-CSRF-Token',csrfToken);
    init={...init,headers};
  }

  return nativeFetch(input,init);
};
const els={phase:$('#phase'),newReview:$('#newReview'),send:$('#send'),response:$('#response'),decision:$('#decision'),transcript:$('#transcript'),evidenceList:$('#evidenceList'),repo:$('#repoFullName')};
window.addEventListener('error',e=>{console.error('Studio UI error',e.error||e.message);const w=$('#uiRuntimeWarning');if(w){w.classList.remove('hidden');$('#uiRuntimeWarningText').textContent='The Review Room encountered a browser error. Refresh the page; if it repeats, report the time and what you clicked.'}});
window.addEventListener('unhandledrejection',e=>{console.error('Studio promise error',e.reason);const w=$('#uiRuntimeWarning');if(w){w.classList.remove('hidden');$('#uiRuntimeWarningText').textContent='The Review Room could not complete an action. Your review evidence is preserved; refresh and resume the session if needed.'}});
window.addEventListener('offline',()=>{const w=$('#uiRuntimeWarning');if(w){w.classList.remove('hidden');$('#uiRuntimeWarningText').textContent='You appear to be offline. Your current draft remains in the browser; reconnect before sending or changing course data.'}});window.addEventListener('online',()=>{const w=$('#uiRuntimeWarning');if(w&&$('#uiRuntimeWarningText')?.textContent.includes('offline'))w.classList.add('hidden')});
const githubSetupStorageKey='etis:github-setup-complete';
const githubSetupChannelName='etis-github-setup';
async function handleGitHubSetupComplete(){if(appRole!=='student'||!authenticatedUser?.id)return;try{await loadStudentContext(authenticatedUser.id);toast('GitHub authorization complete. Verify the exact repository when you are ready.')}catch(e){console.error('Could not refresh GitHub authorization state',e)}}
window.addEventListener('storage',event=>{if(event.key===githubSetupStorageKey&&event.newValue)handleGitHubSetupComplete()});
if('BroadcastChannel' in window){const githubSetupChannel=new BroadcastChannel(githubSetupChannelName);githubSetupChannel.addEventListener('message',event=>{const message=event.data||{};if(message.type==='github-setup-complete'){handleGitHubSetupComplete();return}if(message.type==='github-setup-return-request'&&message.request_id){try{window.focus()}catch(_e){}window.setTimeout(()=>{githubSetupChannel.postMessage({type:'github-setup-return-ack',request_id:message.request_id,focused:document.hasFocus()})},75)}})}

const phaseQuestions={
 A1:'Can the team operate with visible ownership, workflow discipline, AI governance, and repository structure before serious implementation begins?',
 A2:'Can the team convert requirements into visible, realistic, traceable, manageable work before implementation accelerates?',
 A3:'Can another engineering team inspect and challenge the architecture before construction accelerates?',
 A4:'Is implementation controlled, reviewable, traceable, tested, and safe enough to merge?',
 A5:'Can the team defend a stable Cycle 1 release using repository evidence rather than presentation claims?',
 A6:'Can the team defend the final system as operationally mature, governable, supportable, and responsibly releasable?'
};
const phaseDimensions={A1:['Business Value','Evidence','Accountability','AI Governance','Uncertainty'],A2:['Scope','Cost & Time','Traceability','Risk','Commitment Realism'],A3:['Architecture','Boundaries','Data','Governance','Tradeoffs'],A4:['Controlled Change','Review','CI/CD','Testing','Dependencies'],A5:['Release','Validation','Defects','Residual Risk','Traceability'],A6:['Operations','Observability','Recovery','Governance','Stewardship']};
const lensLabels={chief_architect:'Chief Architect',evidence_auditor:'Evidence Auditor',red_team:'Red Team Reviewer',delivery:'Delivery & Planning Lead',system:'System'};
const postureMeanings={'':'Choose only when the discussion reaches a decision. You can change this as your reasoning develops.',approve:'Continue: proceed without a material restriction.',approve_with_conditions:'Continue with conditions: proceed only with explicit controls, ownership, and closure evidence.',defer:'Hold / defer: wait for evidence or uncertainty reduction.',reject:'Reject this path: the proposed course is not acceptable.',constrain:'Constrain: reduce scope, authority, exposure, or blast radius.',request_evidence:'Request evidence: the claim cannot yet support a responsible decision.',escalate:'Escalate: the decision exceeds the team’s authority, expertise, or risk tolerance.'};
const helpTopics={
 general:{title:'How the senior review board works',body:`<p>This room is an engineering apprenticeship. The reviewers use the frozen repository evidence and current phase contract, then coach you through a small number of high-value engineering decisions.</p><ol><li><b>Talk naturally.</b> Tentative answers, questions, disagreement, and “I don’t know” are all valid.</li><li><b>Ask for help.</b> Productive struggle becomes direct teaching when you are stuck.</li><li><b>Challenge the reviewer.</b> If the board missed evidence, point it out.</li><li><b>Use guidance as a reference.</b> Related ETIS and LMU/COICP material appears in the right rail.</li><li><b>Own the judgment.</b> The board can teach the concept; you still decide what your team should do.</li></ol>`},
 'first-review':{title:'What happens when I begin?',body:`<p>The Studio freezes the repository state, distinguishes starter-kit scaffold from team evidence, evaluates the current phase contract, identifies strengths, ranks a few meaningful findings, and selects one conversation to begin.</p><p>A strong repository will still receive a judgment challenge. A review is not a missing-file checklist.</p>`},
 'decision-posture':{title:'How to use your current recommendation',body:`<p>Your current recommendation is where you are leaning <b>right now</b> when the discussion reaches a real engineering decision. It is optional, it is not a quiz answer, and you can change it as evidence or reasoning develops.</p><p>Selecting one helps the reviewer test the consequences, conditions, ownership, and evidence behind that direction. It does <b>not</b> formally commit the recommendation; <b>State My Recommendation</b> is the later action for a position you are prepared to defend.</p>`},
 'evidence-rail':{title:'How to use the evidence rail',body:`<p><b>Present</b> means current team evidence supports the location. <b>Scaffold</b> means the artifact is still identical to the official COMP 330 starter kit. <b>Weak</b> means evidence exists but may still be incomplete. <b>Missing</b> means the snapshot did not locate expected evidence.</p><p>FACT observations describe the snapshot. REVIEW findings are engineering interpretations and can be challenged.</p>`},
 'semantic-required':{title:'Natural reviewer coaching is not configured',body:`<p>Configure <code>OPENAI_API_KEY</code> and <code>OPENAI_MODEL</code> in your local <code>.env</code>, restart the API, and verify the badge says <b>Semantic coaching</b>.</p>`},
 'evidence-map':{title:'How to use Engineering Evidence',body:`<p>This page is your team’s living evidence workspace for the current phase. Start with what is working, then explore professional lenses, current evidence, findings, and traceability signals.</p><p><b>File names are not the goal.</b> The Studio looks for engineering meaning, including equivalent evidence in another file or GitHub workflow surface. Future starter-kit scaffold stays out of current-phase judgment by default.</p><p>When something is unclear, use <b>Ask the Board</b> or <b>Focused Review</b>. You can ask for an honest senior-engineer opinion before you change an artifact.</p>`},
 'staff-general':{title:'Teaching-staff quick guide',body:`<p>The instructor and TA surfaces summarize shared team evidence, student review progress, findings, and AI usage without turning activity counts into grades.</p><ol><li><b>Command Center</b> shows which teams may need attention.</li><li><b>Teams / Evidence</b> lets you inspect the frozen engineering record and current findings.</li><li><b>Reviews</b> shows review activity and status; individual coaching remains private from teammates.</li><li><b>Students</b> manages roster/team assignments when your role permits it.</li><li><b>Semester Setup</b> is restricted to course administration roles.</li></ol><p>TA and Reviewer roles are intentionally read-oriented. If something is unclear, inspect the evidence first and escalate administrative changes to the Instructor/Course Owner.</p>`}
};
function toast(msg){const t=$('#toast');t.textContent=msg;t.classList.remove('hidden');setTimeout(()=>t.classList.add('hidden'),3000)}
function draftKey(){const uid=studentContext?.user?.id||demoContext?.user_id||'anon';return `etis:draft:${uid}:${sessionId||'launcher'}:${currentPhase}`}
function saveDraft(){try{sessionStorage.setItem(draftKey(),JSON.stringify({text:els.response?.value||'',context:composerContext||null,ts:Date.now()}))}catch(_){}}
function clearDraft(){try{sessionStorage.removeItem(draftKey())}catch(_){}}
function restoreDraft(){try{const raw=sessionStorage.getItem(draftKey());if(!raw)return;const d=JSON.parse(raw);if(d?.text&&!els.response.value){els.response.value=d.text;if(d.context)setComposerContext(d.context);updateDraftHint();toast('Your unsent draft was restored.')}}catch(_){}}
function initials(name){return String(name||'?').split(/\s+/).map(x=>x[0]).join('').slice(0,2).toUpperCase()}
function escapeHtml(v){const d=document.createElement('div');d.textContent=String(v??'');return d.innerHTML}
function roleLabel(role){return({course_owner:'Course Owner',instructor:'Instructor',ta:'Teaching Assistant',reviewer:'Reviewer',developer:'Development Instructor'})[role]||'Teaching Staff'}
function instructorSectionStorageKey(){const uid=authenticatedUser?.id||authenticatedUser?.user_id||'current';return `etis:instructor-section:${uid}`}
function currentInstructorSectionId(){if(instructorSectionContextId!==undefined)return instructorSectionContextId;try{const raw=sessionStorage.getItem(instructorSectionStorageKey());instructorSectionContextId=raw&&/^\d+$/.test(raw)?Number(raw):null}catch(_){instructorSectionContextId=null}return instructorSectionContextId}
function instructorSectionQuery(){const id=currentInstructorSectionId();return id?`?section_id=${id}`:''}
function teamIdentifierLabel(key){const value=String(key||'').trim();const match=value.match(/^team[-_\s]?0*(\d+)$/i);if(match)return `Team ${String(Number(match[1])).padStart(2,'0')}`;return value?`Team ID ${value}`:'Team ID not assigned'}
function reloadInstructorContextView(){if(currentView==='instructor')return loadInstructor();if(currentView==='instructorTeams')return loadInstructorTeams();if(currentView==='instructorStudents')return loadInstructorStudents();if(currentView==='instructorReviews')return loadInstructorReviews();if(currentView==='instructorEvidence')return loadInstructorEvidence();if(currentView==='instructorUsage')return loadInstructorUsage();if(currentView==='semesterSetup')return loadSemesterSetup()}
function setInstructorSectionContext(value,{reload=true}={}){const parsed=value===''||value==null?null:Number(value);instructorSectionContextId=Number.isFinite(parsed)?parsed:null;try{sessionStorage.setItem(instructorSectionStorageKey(),instructorSectionContextId==null?'':String(instructorSectionContextId))}catch(_){}$$('[data-instructor-section-selector]').forEach(sel=>{const target=instructorSectionContextId==null?'':String(instructorSectionContextId);if([...sel.options].some(o=>o.value===target))sel.value=target});if(navigationReady&&!restoringNavigation)recordNavigationState({replace:true});if(reload)reloadInstructorContextView()}
function syncInstructorSectionControls(sections){const valid=new Set((sections||[]).map(s=>Number(s.id)));if(currentInstructorSectionId()!=null&&!valid.has(Number(currentInstructorSectionId())))setInstructorSectionContext(null,{reload:false});const options='<option value="">All sections</option>'+(sections||[]).map(s=>`<option value="${s.id}">${escapeHtml(s.display_name)}${s.term?.status==='archived'?' · Archived':''}</option>`).join('');$$('[data-instructor-section-selector]').forEach(sel=>{sel.innerHTML=options;sel.value=currentInstructorSectionId()==null?'':String(currentInstructorSectionId());sel.onchange=()=>setInstructorSectionContext(sel.value)});return sections}
function currentPhaseAccess(){
  return studentContext?.sections?.[0]?.phase_access||null;
}
function currentPhaseIsReleased(){
  const access=currentPhaseAccess();
  if(!access)return false;
  return (access.released||[]).includes(currentPhase);
}
function studentReviewReadiness(){
  if(appRole!=='student'||!studentContext)return {ready:true,code:'ready',title:'',detail:'',action:null,eyebrow:''};
  const ob=studentContext.onboarding||{},sc=studentContext.sections?.[0],repo=sc?.repository,team=sc?.team;
  if(!ob.team_assigned)return {ready:false,code:'team',title:'Team assignment required',detail:'Your instructor must assign you to a team before the Studio can use team repository evidence.',action:null,eyebrow:'SETUP WAITING ON INSTRUCTOR'};
  if(!ob.github_identity)return {ready:false,code:'github',title:'Finish GitHub setup before your first review',detail:ob.repository_connected?'Connect your GitHub identity before starting a review.':'Connect your GitHub account for COMP 330. GitHub may reuse the account already signed in to this browser, so confirm the account before authorizing.',action:'github',eyebrow:'ACTION REQUIRED'};
  if(!ob.repository_connected){
    if(repo?.owner_type==='User'&&repo.owner_is_current_user)return {ready:false,code:'repository',title:"Action required — complete your team's repository connection",detail:`Your team nominated ${repo.repo_full_name||'a repository'} and GitHub identifies your linked account as its owner. Open My Team for the two-step authorization and verification flow.`,action:'myteam',eyebrow:'ACTION REQUIRED'};
    if(repo?.owner_type==='User'){
      const member=repositoryOwnerTeamMember(team,repo);
      return {ready:false,code:'repository',title:'Waiting for repository owner',detail:member?`${member.name} (@${repo.owner_login}) must complete the repository connection. No action is required from you unless the repository is wrong.`:`The team is waiting for @${repo.owner_login||'the repository owner'}. Open My Team to see exactly who needs to act and what to do if the account or repository is wrong.`,action:'myteam',eyebrow:'TEAM SETUP IN PROGRESS'};
    }
    if(repo?.organization_approval_required)return {ready:false,code:'repository',title:'Repository access pending organization approval',detail:`GitHub organization authorization for @${repo.owner_login||'the repository organization'} must complete before the team can verify this repository. Open My Team for the request and verification steps.`,action:'myteam',eyebrow:'TEAM SETUP IN PROGRESS'};
    if(repo)return {ready:false,code:'repository',title:'Repository owner still needs to be confirmed',detail:'The candidate is saved but is not trusted evidence. Open My Team to retry owner detection or choose a different repository.',action:'myteam',eyebrow:'ACTION REQUIRED'};
    return {ready:false,code:'repository',title:'Nominate your team repository',detail:"Open My Team and paste the HTTPS GitHub repository URL for your team's actual working repository. The .git suffix is optional. Nomination alone does not make the repository trusted evidence.",action:'myteam',eyebrow:'ACTION REQUIRED'};
  }
  if(!currentPhaseIsReleased())return {ready:false,code:'phase',title:`${currentPhase} has not been released yet`,detail:'Your instructor controls phase release for this section. You can review the phase question now, but a formal review cannot start until the phase is released.',action:null,eyebrow:'REVIEW NOT YET AVAILABLE'};
  return {ready:true,code:'ready',title:'Review setup complete',detail:'GitHub identity, team repository, and current phase are ready.',action:null,eyebrow:''};
}
function renderStudentReadiness(){
  const box=$('#studentReadiness');
  if(!box)return;
  const readiness=studentReviewReadiness();
  if(appRole!=='student'||readiness.ready){box.classList.add('hidden');box.innerHTML='';return}
  const primary=readiness.action==='github'
    ? '<a href="/auth/github/link" class="secondary link-button setup-required-action">Connect GitHub identity →</a>'
    : readiness.action==='myteam'
      ? '<button type="button" id="openReadinessMyTeam" class="secondary setup-required-action">Open My Team →</button>'
      : '';
  box.innerHTML=`<div><span class="eyebrow">${escapeHtml(readiness.eyebrow||'SETUP REQUIRED')}</span><b>${escapeHtml(readiness.title)}</b><span>${escapeHtml(readiness.detail)}</span></div><div class="readiness-actions">${primary}</div>`;
  box.classList.remove('hidden');
  const open=$('#openReadinessMyTeam');
  if(open)open.onclick=()=>switchView('myteam');
}
function setIdentity(view){const box=$('#userIdentity');if(appRole==='instructor'){const u=authenticatedUser||{display_name:'William O\'Connell',role:'course_owner'};box.innerHTML=`<div class="avatar instructor-avatar">${initials(u.display_name)}</div><div><b>${escapeHtml(u.display_name)}</b><small>${escapeHtml(roleLabel(u.role))}</small></div>`;return}const u=studentContext?.user||{name:authenticatedUser?.display_name||'Alex Rivera'},team=studentContext?.sections?.[0]?.team;box.innerHTML=`<div class="avatar">${initials(u.name)}</div><div><b>${escapeHtml(u.name)}</b><small>${escapeHtml(team?.name||'COMP 330 Student')} · ${escapeHtml(u.github_login?'GitHub linked':'GitHub not linked')}</small></div>`}
const viewTitles={studio:'Engineering Review Room',evidence:'Engineering Evidence',history:'Review History',myteam:'My Team',instructor:'Instructor Command Center',instructorTeams:'Teams',instructorStudents:'Students',instructorReviews:'Reviews',instructorEvidence:'Engineering Evidence',instructorUsage:'AI Usage & Cost',semesterSetup:'Semester Setup',accessSettings:'Settings & Access'};
const studentViews=new Set(['studio','evidence','history','myteam']),instructorViews=new Set(['instructor','instructorTeams','instructorStudents','instructorReviews','instructorEvidence','instructorUsage','semesterSetup','accessSettings']);
function viewAllowedForRole(view){return appRole==='instructor'?instructorViews.has(view):studentViews.has(view)}
function navigationState(){const state={view:currentView};if(appRole==='instructor'){const section=currentInstructorSectionId();state.section=section||null;if(currentView==='instructor'&&currentInstructorTeamId)state.team=currentInstructorTeamId;if(currentView==='instructorReviews'&&currentInstructorReviewSessionId)state.review=currentInstructorReviewSessionId}else if(currentView==='studio'&&sessionId)state.session=sessionId;return state}
function navigationUrl(state){const url=new URL(window.location.href);['view','section','team','review','session','signed_out'].forEach(k=>url.searchParams.delete(k));url.searchParams.set('view',state.view);if(state.section)url.searchParams.set('section',String(state.section));if(state.team)url.searchParams.set('team',String(state.team));if(state.review)url.searchParams.set('review',String(state.review));if(state.session)url.searchParams.set('session',String(state.session));return `${url.pathname}${url.search}${url.hash}`}
function sameNavigationState(a,b){return JSON.stringify(a||{})===JSON.stringify(b||{})}
function recordNavigationState({replace=false}={}){if(!navigationReady||restoringNavigation)return;const state=navigationState(),wrapped={etisNavigation:state};if(!replace&&sameNavigationState(window.history.state?.etisNavigation,state))return;window.history[replace?'replaceState':'pushState'](wrapped,'',navigationUrl(state))}
function navigationStateFromLocation(){const q=new URLSearchParams(window.location.search),state={view:q.get('view')||currentView};for(const key of ['section','team','review','session']){const raw=q.get(key);if(raw&&/^\d+$/.test(raw))state[key]=Number(raw)}return state}
async function restoreNavigationState(state){restoringNavigation=true;try{const fallback=appRole==='instructor'?'instructor':'studio',view=viewAllowedForRole(state?.view)?state.view:fallback;if(appRole==='instructor'&&Object.prototype.hasOwnProperty.call(state||{},'section'))setInstructorSectionContext(state.section||null,{reload:false});currentInstructorTeamId=appRole==='instructor'&&view==='instructor'&&state?.team?Number(state.team):null;currentInstructorReviewSessionId=appRole==='instructor'&&view==='instructorReviews'&&state?.review?Number(state.review):null;if(appRole!=='instructor'&&state?.session&&view==='studio'){await resumeSession(Number(state.session),{history:false});return}if(view==='instructorReviews'&&!currentInstructorReviewSessionId){const detail=$('#reviewOpsDetail');if(detail){detail.classList.add('hidden');detail.innerHTML=''}}switchView(view,{history:false,scroll:false});if(appRole==='instructor'&&view==='instructor'&&currentInstructorTeamId)await loadTeamDetail(currentInstructorTeamId,{focus:false,history:false});if(appRole==='instructor'&&view==='instructorReviews'&&currentInstructorReviewSessionId)await loadInstructorReviewDetail(currentInstructorReviewSessionId,{history:false});}finally{restoringNavigation=false}}
async function initializeBrowserNavigation(){const persisted=window.history.state?.etisNavigation,state=persisted||navigationStateFromLocation();if(appRole==='instructor'&&!persisted&&!Object.prototype.hasOwnProperty.call(state,'section'))state.section=currentInstructorSectionId();await restoreNavigationState(state);navigationReady=true;recordNavigationState({replace:true})}
window.addEventListener('popstate',event=>{if(!navigationReady)return;restoreNavigationState(event.state?.etisNavigation||navigationStateFromLocation()).catch(e=>console.error('Could not restore Studio navigation',e))});
function switchView(view,opts={}){if(!viewAllowedForRole(view))return;const changed=currentView!==view;currentView=view;if(view!=='instructor')currentInstructorTeamId=null;if(view!=='instructorReviews')currentInstructorReviewSessionId=null;$$('.nav').forEach(x=>x.classList.toggle('active',x.dataset.view===view));$$('.view').forEach(x=>x.classList.remove('active-view'));const target=$('#'+view);if(target)target.classList.add('active-view');$('#viewTitle').textContent=viewTitles[view]||'Engineering Studio';setIdentity(view);if(view==='evidence')loadEngineeringEvidence();if(view==='history')loadHistoryPage();if(view==='myteam')renderMyTeam();if(view==='instructor')loadInstructor();if(view==='instructorTeams')loadInstructorTeams();if(view==='instructorStudents')loadInstructorStudents();if(view==='instructorReviews')loadInstructorReviews();if(view==='instructorEvidence')loadInstructorEvidence();if(view==='instructorUsage')loadInstructorUsage();if(view==='semesterSetup')loadSemesterSetup();if(view==='accessSettings')loadAccessSettings();if(opts.history!==false&&changed)recordNavigationState();if(opts.scroll!==false)requestAnimationFrame(()=>window.scrollTo({top:0,left:0,behavior:'auto'}));}
function canManageSectionUi(){return !authenticatedUser||['course_owner','instructor','developer'].includes(authenticatedUser.role)}
function safeErrorMessage(e,fallback='That action could not be completed.'){const msg=String(e?.message||e||'').trim();if(!msg)return fallback;if(/failed to fetch|networkerror|network request failed/i.test(msg))return 'The Studio cannot reach a required service right now. Your current work is preserved; check your connection and try again.';if(/403|not assigned|not authorized|permission/i.test(msg))return 'You do not have permission for that action in this section.';if(/404|not found/i.test(msg))return 'The requested item is no longer available in this context. Refresh the view and try again.';return msg}
async function jsonRequest(url,opts={},fallback='That action could not be completed.'){try{const r=await fetch(url,opts);let body={};try{body=await r.json()}catch(_e){}if(!r.ok)throw new Error(body.detail||`${r.status} ${r.statusText}`);return body}catch(e){throw new Error(safeErrorMessage(e,fallback))}}
function opsError(target,msg,retry){const box=$(target);if(!box)return;box.innerHTML=`<div class="ops-error"><b>Could not load this view.</b><p>${escapeHtml(msg)}</p>${retry?'<button class="secondary compact" data-retry="1">Retry</button>':''}</div>`;if(retry)box.querySelector('[data-retry]')?.addEventListener('click',retry)}
async function withBusy(control,label,fn){if(!control||control.disabled)return;const original=control.textContent;control.disabled=true;control.setAttribute('aria-busy','true');if(label)control.textContent=label;try{return await fn()}catch(e){toast(safeErrorMessage(e));throw e}finally{control.disabled=false;control.removeAttribute('aria-busy');control.textContent=original}}
function currentFindingById(fid){const sources=currentView==='evidence'?[engineeringEvidenceData,currentEvidence]:[currentEvidence,engineeringEvidenceData];for(const source of sources){const match=(source?.findings||[]).find(f=>String(f.id)===String(fid));if(match)return match}return null}
function actualArtifact(path){if(!path)return null;const all=(currentView==='evidence'?engineeringEvidenceData?.artifacts:currentEvidence?.artifacts)||[];return all.find(a=>String(a.path)===String(path))||null}
function evidenceActualPath(item){return item?.equivalent_path||item?.title||''}
function artifactForEvidence(item){return actualArtifact(evidenceActualPath(item))}
function setComposerContext(ctx){composerContext=ctx||null;const box=$('#composerContext');if(!box)return;if(!ctx){box.classList.add('hidden');box.innerHTML='';return}const kind=ctx.kind==='finding'?'Finding':'Evidence';box.innerHTML=`<div><span class="composer-context-kind">${escapeHtml(kind)} in this question</span><b>${escapeHtml(ctx.label||ctx.path||ctx.id||kind)}</b>${ctx.detail?`<small>${escapeHtml(ctx.detail)}</small>`:''}</div><button type="button" id="clearComposerContext" class="text-button">Clear</button>`;box.classList.remove('hidden');$('#clearComposerContext').onclick=()=>setComposerContext(null)}
function contextRefs(){if(!composerContext)return[];if(composerContext.kind==='finding')return [`FINDING:${composerContext.id}`,...(composerContext.evidence_refs||[])];if(composerContext.kind==='evidence')return [`PATH:${composerContext.path}`];return[]}
async function showArtifact(path,label='Evidence'){
  const art=actualArtifact(path);
  if(!art){toast('That exact artifact is not present in this frozen snapshot.');return}
  const snapshotId=currentView==='evidence'?engineeringSnapshotId:reviewSnapshotId;
  const evidence=currentView==='evidence'?engineeringEvidenceData:currentEvidence;
  const relatedFinding=(evidence?.findings||[]).find(f=>(f.evidence_refs||[]).includes(`PATH:${path}`));
  const requestId=++artifactRequestId;
  artifactContext={kind:'evidence',path:art.path,label:label||art.path,detail:art.summary||''};
  $('#artifactOverlayTitle').textContent=label||art.path;
  $('#artifactOverlayMeta').innerHTML=`<b>${escapeHtml(art.path)}</b><span>Loading the frozen review copy…</span>`;
  $('#artifactOverlayExcerpt').textContent='Loading inspected content…';
  $('#artifactConditionNote').textContent='A file being present does not by itself support the engineering claim. Check its actual content and discuss Maya’s interpretation.';
  $('#artifactContentNote').textContent='';
  $('#artifactExternalLink').classList.add('hidden');
  $('#artifactGithubNote').classList.add('hidden');
  $('#artifactOverlay').classList.remove('hidden');
  if(!snapshotId){$('#artifactOverlayExcerpt').textContent='This snapshot has no retrievable artifact copy. The short excerpt is not a complete inspection.';return}
  try{
    const detail=await jsonRequest(`/api/v1/reviews/evidence/${snapshotId}/artifact?path=${encodeURIComponent(path)}`,{},'The frozen artifact could not be opened.');
    if(requestId!==artifactRequestId||!artifactContext||artifactContext.path!==path)return;
    $('#artifactOverlayMeta').innerHTML=`<b>${escapeHtml(detail.path)}</b><span>Snapshot ${escapeHtml(String(detail.commit_sha||'').slice(0,8))} · ${escapeHtml(detail.provenance)} · ${escapeHtml(detail.quality)}</span>`;
    $('#artifactConditionNote').textContent=`File observation: ${detail.summary||'This artifact was found in the frozen snapshot.'}${relatedFinding?` Reviewer concern: ${relatedFinding.statement||relatedFinding.title}`:''} Check the content before accepting or challenging that interpretation.`;
    const later=(detail.additional_windows||[]).filter(w=>w.content).map(w=>`\n\n— Frozen excerpt, characters ${w.start}–${w.end} —\n${w.content}`).join('');
    $('#artifactOverlayExcerpt').textContent=(detail.content||'No inspectable text was stored for this artifact.')+later;
    $('#artifactContentNote').textContent=detail.disclosure_status==='quarantined'
      ?'Content is withheld by the sensitive-file policy. Ask your reviewer about the evidence without pasting secrets.'
      :detail.source==='compact_excerpt'
        ?'Only a compact excerpt is available from this older or non-text snapshot. This cannot establish what the entire file contains.'
        :detail.may_be_incomplete
          ?'Frozen review copy: up to the first 8,000 characters, plus labelled selected later excerpts when available. Other sections may be uninspected; do not infer whole-file absence.'
          :'Frozen review copy retained for this snapshot. Redactions are shown where required.';
    const link=$('#artifactExternalLink');
    if(detail.disclosure_status!=='quarantined'&&/^https:\/\/github\.com\//.test(detail.url||'')){
      link.href=detail.url;link.classList.remove('hidden');$('#artifactGithubNote').classList.remove('hidden');
    }
  }catch(e){
    if(requestId!==artifactRequestId)return;
    $('#artifactOverlayExcerpt').textContent='The frozen content could not be loaded. Try again; the GitHub link may require a separate sign-in.';
    $('#artifactContentNote').textContent=safeErrorMessage(e);
  }
}
function closeArtifact(){artifactRequestId++;$('#artifactOverlay').classList.add('hidden');artifactContext=null}
function newReviewHome(message='Choose the kind of senior review you want to start.',allowActive=false){if(sessionId&&document.body.classList.contains('review-session-active')&&!allowActive){openReviewExit('new');return}if(pending||finishingReview){toast('Wait for the current reviewer response to finish first.');return}findingPickerRequestId++;saveDraft();sessionId=null;committed=false;document.body.classList.remove('review-session-active');els.phase.disabled=false;selectedFindingIds.clear();requestedFindingId=null;pendingEntryContext=null;setComposerContext(null);reviewMode='board';updateReviewModeSummary();$$('.review-choice').forEach(b=>{const yes=b.dataset.reviewMode==='board';b.classList.toggle('selected',yes);b.setAttribute('aria-pressed',String(yes))});$('#focusedReviewPanel').classList.add('hidden');$('#findingReviewPanel').classList.add('hidden');$('#reviewFocus').value='';els.response.value='';updateDraftHint();$('#reviewSessionPurpose').classList.add('hidden');$('#reviewHomeButton').classList.add('hidden');resetReview(message);els.newReview.onclick=startReviewAction;switchView('studio');requestAnimationFrame(()=>window.scrollTo({top:0,behavior:'auto'}))}
function prepareEntryContext(ctx){pendingEntryContext=ctx;try{sessionStorage.setItem('etis.pendingReviewContext',JSON.stringify(ctx))}catch(e){} }
function clearEntryContext(){pendingEntryContext=null;try{sessionStorage.removeItem('etis.pendingReviewContext')}catch(e){}}
let pendingReviewStartRequest=null;
function reviewStartRequestKey(){return 'etis.pendingReviewStart'}
function reviewStartPayload(body){const copy={...body};delete copy.client_request_id;return copy}
function reviewStartRequestId(body){
  const serialized=JSON.stringify(reviewStartPayload(body));

  if(
    pendingReviewStartRequest?.payload===serialized
    && pendingReviewStartRequest?.id
  ){
    return pendingReviewStartRequest.id;
  }

  try{
    const raw=sessionStorage.getItem(reviewStartRequestKey());
    if(raw){
      const saved=JSON.parse(raw);
      if(saved?.payload===serialized&&saved?.id){
        pendingReviewStartRequest=saved;
        return saved.id;
      }
    }
  }catch(_){}

  const saved={id:turnId(),payload:serialized,ts:Date.now()};
  pendingReviewStartRequest=saved;

  try{
    sessionStorage.setItem(
      reviewStartRequestKey(),
      JSON.stringify(saved)
    );
  }catch(_){}

  return saved.id;
}
function clearReviewStartRequest(){
  pendingReviewStartRequest=null;
  try{sessionStorage.removeItem(reviewStartRequestKey())}catch(_){}
}

let pendingReviewMutation=null;
function reviewMutationRequestKey(){return 'etis.pendingReviewMutation'}
function reviewMutationPayload(body){
  const copy={...body};
  delete copy.client_turn_id;
  return copy;
}
function persistReviewMutation(saved){
  pendingReviewMutation=saved;
  try{
    sessionStorage.setItem(
      reviewMutationRequestKey(),
      JSON.stringify(saved)
    );
  }catch(_){}
}
function reviewMutationRequest(operation,activeSessionId,body){
  const payload=JSON.stringify({
    operation,
    session_id:activeSessionId,
    payload:reviewMutationPayload(body),
  });

  if(
    pendingReviewMutation?.payload===payload
    && pendingReviewMutation?.id
  ){
    return pendingReviewMutation;
  }

  try{
    const raw=sessionStorage.getItem(reviewMutationRequestKey());
    if(raw){
      const saved=JSON.parse(raw);
      if(saved?.payload===payload&&saved?.id){
        pendingReviewMutation=saved;
        return saved;
      }
    }
  }catch(_){}

  const saved={
    id:turnId(),
    payload,
    rendered:false,
    ts:Date.now(),
  };
  persistReviewMutation(saved);
  return saved;
}
function markReviewMutationRendered(saved){
  saved.rendered=true;
  persistReviewMutation(saved);
}
function clearReviewMutation(saved=null){
  if(
    saved
    && pendingReviewMutation?.id
    && pendingReviewMutation.id!==saved.id
  ){
    return;
  }

  pendingReviewMutation=null;

  try{
    sessionStorage.removeItem(reviewMutationRequestKey())
  }catch(_){}
}

function applyRoleShell(){const instructor=appRole==='instructor';$('#studentNav').classList.toggle('hidden',instructor);$('#instructorNav').classList.toggle('hidden',!instructor);if(instructor){const limited=authenticatedUser&&['ta','reviewer'].includes(authenticatedUser.role);$$('#instructorNav .nav').forEach(n=>{if(['semesterSetup','accessSettings'].includes(n.dataset.view))n.classList.toggle('hidden',limited)})}setIdentity(currentView);if(instructor&&!String(currentView).startsWith('instructor')&&!['semesterSetup','accessSettings'].includes(currentView))switchView('instructor');if(!instructor&&(String(currentView).startsWith('instructor')||['semesterSetup','accessSettings'].includes(currentView)))switchView('studio')}
$$('.nav').forEach(b=>b.onclick=()=>switchView(b.dataset.view));
function openHelp(topic='general'){const h=helpTopics[topic]||helpTopics.general;$('#helpTitle').textContent=h.title;$('#helpContent').innerHTML=h.body;$('#helpOverlay').classList.remove('hidden')}
$('#helpButton').onclick=()=>openHelp(appRole==='instructor'?'staff-general':'general');$('#quickHelp').onclick=()=>openHelp(appRole==='instructor'?'staff-general':'general');$('#closeHelp').onclick=()=>$('#helpOverlay').classList.add('hidden');$('#helpOverlay').onclick=e=>{if(e.target.id==='helpOverlay')$('#helpOverlay').classList.add('hidden')};$$('[data-help-topic]').forEach(b=>b.onclick=()=>openHelp(b.dataset.helpTopic));$('#dismissGuide').onclick=()=>$('#guideStrip').classList.add('hidden');
function phaseId(){return String(els.phase.value).slice(0,2)}
function applyPhase(){currentPhase=phaseId();$('#gateQuestion').textContent=phaseQuestions[currentPhase]||'Can the team defend the current engineering gate?';const context=$('#gateQuestionContext'),repoReady=!!studentContext?.onboarding?.repository_connected,phaseReleased=currentPhaseIsReleased();if(context)context.textContent=!repoReady?`This is the standing ${currentPhase} phase-gate review question. Once your repository is connected, the board will evaluate it using your team’s actual evidence.`:!phaseReleased?`This is the standing ${currentPhase} phase-gate review question. Your team repository is connected; the board can evaluate it once ${currentPhase} is released.`:`This is the standing ${currentPhase} phase-gate review question. The board will evaluate it using your team’s actual repository evidence.`;$('#dimensionChips').innerHTML=(phaseDimensions[currentPhase]||[]).map(x=>`<span>${x}</span>`).join('');renderStudentReadiness();updateStartReviewButton()}
els.phase.onchange=()=>{applyPhase();resetReview(`Phase changed to ${currentPhase}. Begin a new review to freeze the repository evidence for this gate.`)};
function resetReview(message){document.body.classList.remove('review-session-active');els.phase.disabled=false;$('#reviewCompletionSummary').classList.add('hidden');sessionId=null;currentEvidence=null;reviewSnapshotId=null;currentChallenge=null;committed=false;setPending(false);els.send.disabled=true;$('#reviewStatus').classList.add('hidden');$('#conversationControls').classList.add('hidden');$('#conversationReadyNote')?.classList.add('hidden');$('#challengeBrief').classList.add('hidden');hideActiveReviewer();$('#commitBar').classList.add('hidden');$('#challengeTitle').textContent='Start a review to convene the board';els.transcript.innerHTML=`<div class="empty"><div class="glyph">⌬</div><h3>Ready for a new review.</h3><p>${escapeHtml(message)}</p></div>`;els.evidenceList.innerHTML='<p class="quiet">Begin a review to freeze the current evidence snapshot.</p>';$('#relatedGuidance').innerHTML='<p class="quiet">Relevant ETIS and reference guidance will appear here when useful.</p>';$('#findingList').innerHTML='<p class="quiet">Findings appear after the evidence snapshot is analyzed.</p>';$('#coverage').textContent='—';$('#evCoverage').textContent='No review open';$('#meter').style.width='0';$('#defense').textContent='Not started';$('#depth').textContent='—';renderEvidenceSummary(null);els.decision.value='';$('#postureMeaning').textContent=postureMeanings[''];setMode('ask');refreshHistorySelection();updateStartReviewButton()}
function showActiveReviewer(reviewer){if(!reviewer){hideActiveReviewer();return}currentReviewer=reviewer;const box=$('#activeReviewer');$('#activeReviewerPortrait').src=reviewer.portrait;$('#activeReviewerPortrait').alt=`Portrait of ${reviewer.name}, ${reviewer.role}`;$('#activeReviewerName').textContent=`${reviewer.name} · ${reviewer.role}`;$('#activeReviewerFocus').textContent=reviewer.focus;box.classList.remove('hidden');const askLabel=$('#askMode b');if(askLabel)askLabel.textContent=`Talk with ${reviewer.name.split(' ')[0]}`;updateReplyInvitation()}
function updateReplyInvitation(active=!!sessionId&&document.body.classList.contains('review-session-active')){
  const label=$('#replyLabel'),cue=$('#replyCue');
  if(!label||!cue)return;
  label.classList.toggle('hidden',!active);
  cue.classList.toggle('hidden',!active);
  if(active){
    const name=currentReviewer?.name?String(currentReviewer.name).split(' ')[0]:'your reviewer';
    label.textContent=`Your turn — reply to ${name}`;
    cue.textContent='Ask a question, share what your team knows, or say what needs checking. You can disagree.';
  }
}
function hideActiveReviewer(){$('#activeReviewer').classList.add('hidden');currentReviewer=null;updateReplyInvitation()}
let thinkingTimer=null,pendingStartedAt=0,pendingElapsedTimer=null;
function setPending(on,status='Reviewing your answer and the frozen evidence…',kind='reviewer'){
  pending=on;
  const box=$('#reviewerThinking');
  const controls=[els.send,$('#coachButton'),$('#askMode'),$('#decisionMode'),$('#commitPosition'),els.newReview];
  controls.filter(Boolean).forEach(x=>x.disabled=on);
  els.response.disabled=on;
  els.decision.disabled=on;
  clearTimeout(thinkingTimer);
  clearInterval(pendingElapsedTimer);

  if(on){
    pendingStartedAt=Date.now();
    const preparing=kind==='review_start';
    const r=currentReviewer||{name:'Senior reviewer',portrait:'/assets/reviewers/maya-chen.svg'};

    $('#thinkingPortrait').src=r.portrait;
    $('#thinkingPortrait').alt=preparing
      ?'ETIS review preparation'
      :`Portrait of ${r.name}`;

    $('#thinkingName').textContent=preparing
      ?`Preparing ${reviewModeLabel(reviewMode)}…`
      :`${r.name} is thinking…`;

    $('#thinkingStatus').textContent=status;
    box.classList.remove('hidden');

    if(preparing){
      thinkingTimer=setTimeout(()=>{
        $('#thinkingStatus').textContent=`Analyzing ${currentPhase} evidence…`;
      },6000);

      pendingElapsedTimer=setInterval(()=>{
        const sec=Math.floor((Date.now()-pendingStartedAt)/1000);
        if(sec>=15){
          $('#thinkingStatus').textContent=`Preparing reviewer… (${sec}s elapsed)`;
        }
      },1000);
    }else{
      thinkingTimer=setTimeout(()=>{
        $('#thinkingStatus').textContent=
          'Still working — connecting your answer to the conversation and the frozen evidence…';
      },3200);

      pendingElapsedTimer=setInterval(()=>{
        const sec=Math.floor((Date.now()-pendingStartedAt)/1000);
        if(sec>=7){
          $('#thinkingStatus').textContent=
            `Still working (${sec}s) — you do not need to send the message again.`;
        }
      },1000);
    }
  }else{
    box.classList.add('hidden');
    els.decision.disabled=false;
    els.response.disabled=false;
    els.send.disabled=!sessionId;
  }
}
function addGuidance(refs=[]){if(!refs.length)return;const box=$('#relatedGuidance');if(box.querySelector('.quiet'))box.innerHTML='';refs.forEach(r=>{if(box.querySelector(`[data-guidance="${CSS.escape(r.id||r.title)}"]`))return;const a=document.createElement('a');a.className='guidance-link';a.dataset.guidance=r.id||r.title;a.href=r.website_url||'#';a.target='_blank';a.rel='noopener noreferrer';a.innerHTML=`<span>${escapeHtml(r.stage||'ETIS guidance')}</span><b>${escapeHtml(r.title)}</b><p>${escapeHtml(r.student_hint||r.why||'Open the related Engineering Platform guidance.')}</p>`;box.appendChild(a)})}
function readableGuidanceText(value,refs=[]){let result=String(value||'');for(const ref of refs){const stage=String(ref.stage||'');if(!/^ES-\d{3}$/.test(stage)||!/^https:\/\//.test(ref.website_url||''))continue;result=result.replace(new RegExp(`\\bSee \\[${stage}\\]\\([^\\n)]*\\) for (?:the )?(?:relevant )?guidance\\.`, 'gi'),'')}return result.replace(/\[(ES-\d{3})\]\([^\n)]*\)/g,'$1').replace(/\n{3,}/g,'\n\n').trim()}
function reviewerCard(lens,text,meta={}){const d=document.createElement('div');d.className='reviewer-card coaching-message';const reviewer=meta.reviewer||{name:lensLabels[lens]||'Reviewer',role:lensLabels[lens]||'Reviewer'};const mode=meta.provider==='openai'?'<span class="semantic-badge">semantic coaching</span>':'';d.innerHTML=`<div class="reviewer-meta"><span class="lens-badge">${escapeHtml(reviewer.name)} · ${escapeHtml(reviewer.role)}</span>${meta.kind?`<span>${escapeHtml(String(meta.kind).replaceAll('_',' '))}</span>`:''}${mode}</div><div class="reviewer-copy"></div>`;const refs=meta.guidance_refs||[];d.querySelector('.reviewer-copy').textContent=readableGuidanceText(text,refs);if(meta.kind!=='teaching')addGuidance(refs);if(meta.kind==='teaching'&&refs.length){const guidance=document.createElement('div');guidance.className='teaching-guidance';const label=document.createElement('b');label.textContent='Learn more about this';guidance.appendChild(label);refs.slice(0,2).forEach(r=>{if(!/^https:\/\//.test(r.website_url||''))return;const a=document.createElement('a');a.href=r.website_url;a.target='_blank';a.rel='noopener noreferrer';a.textContent=`${r.title} — ${r.student_hint||'Open the related guidance'}`;guidance.appendChild(a)});d.appendChild(guidance)}if(meta.kind==='teaching'&&(!meta.coaching_phase||meta.coaching_phase===currentPhase)){const path=findingPrimaryPath(currentChallenge?.finding);const art=(currentEvidence?.artifacts||[]).find(a=>a.path===path);if(art){const button=document.createElement('button');button.type='button';button.className='secondary compact';button.textContent=`Inspect ${path}`;button.onclick=()=>showArtifact(path,path);d.appendChild(button)}}return d}
function addTurn(actor,lens,text,meta={}){
  let turnElement=null;
  if(actor==='student'){
    const d=document.createElement('div');
    d.className='turn student';
    d.innerHTML='<div class="who">You</div><div class="bubble"></div>';
    d.querySelector('.bubble').textContent=meta.kind==='student_coach_request'?'Explain this and show me how.':text;
    els.transcript.appendChild(d);
    turnElement=d;
  }else{
    turnElement=reviewerCard(lens,text,meta);
    els.transcript.appendChild(turnElement);
    if(meta.reviewer)showActiveReviewer(meta.reviewer);
  }
  if(actor==='student'){
    els.transcript.scrollTop=els.transcript.scrollHeight;
  }else if(turnElement){
    // Start at the beginning of a new reviewer reply. Short replies stay fully
    // visible; long replies can be read downward without hunting for their start.
    const top=turnElement.getBoundingClientRect().top-els.transcript.getBoundingClientRect().top+els.transcript.scrollTop-18;
    els.transcript.scrollTop=Math.max(0,top);
  }
  requestAnimationFrame(updateReadingCue);
  return turnElement;
}
function showSubmittedExchange(studentTurn){
  switchView('studio',{scroll:false});
  requestAnimationFrame(()=>{
    if(!studentTurn?.isConnected)return;
    const top=studentTurn.getBoundingClientRect().top-els.transcript.getBoundingClientRect().top+els.transcript.scrollTop-18;
    els.transcript.scrollTop=Math.max(0,top);
    els.transcript.scrollIntoView({block:'center',behavior:'auto'});
    updateReadingCue();
  });
}
function updateReadingCue(){const cue=$('#continueReading');if(!cue)return;cue.classList.toggle('hidden',!sessionId||!document.body.classList.contains('review-session-active')||els.transcript.scrollHeight-els.transcript.scrollTop-els.transcript.clientHeight<12)}
els.transcript.addEventListener('scroll',updateReadingCue);
$('#continueReading').onclick=()=>els.transcript.scrollBy({top:Math.max(160,els.transcript.clientHeight*.8),behavior:'smooth'});
function renderStrengths(ev){const panel=$('#boardReadout .board-readout-details');if(!panel)return;panel.querySelector('.strengths-strip')?.remove();const strengths=(ev?.items||[]).filter(x=>['strong','okay'].includes(evidenceCondition(x).key)).slice(0,4).map(x=>{const c=evidenceCondition(x),s=c.support||{};return `${c.label} for ${x.title}: ${s.claim||''} (${s.support_kind==='demonstrated'?'decision or use visible':'approach defined; use not established'} in excerpt from ${s.support_path||'frozen source'}${(s.corroborating_evidence||[]).length?' with '+s.corroborating_evidence.map(r=>r.path).join(', '):''}). Boundary: ${s.limitation||'Review the cited excerpt.'}`});if(!strengths.length&&!ev?.longitudinal?.has_prior_snapshot)return;const d=document.createElement('div');d.className='strengths-strip';let html='<b>Bounded phase support</b>';html+=strengths.length?'<ul>'+strengths.map(x=>`<li>${escapeHtml(x)}</li>`).join('')+'</ul>':'<p class="quiet">No specific strength identified from this snapshot.</p>';const l=ev?.longitudinal;if(l?.has_prior_snapshot){const improved=(l.improved_evidence||[]).length,regressed=(l.regressed_evidence||[]).length;html+=`<div class="longitudinal-note"><b>Since ${escapeHtml(l.previous_phase||'the prior review')}</b> · ${improved} improved · ${regressed} regressed</div>`}d.innerHTML=html;panel.appendChild(d)}
function preparationHTML(p){
 if(!p)return '';
 const f=p.focus;
 const focus=f?`<div><b>A course concern to examine · ${escapeHtml(f.title)}</b><span>${escapeHtml(f.why||'')}</span><small>Next: ${escapeHtml(f.next_step||'Ask the reviewer what evidence is needed.')}</small></div>`:'<div><b>No course concern selected for this snapshot</b><span>That does not establish readiness. Ask the reviewer to test a consequential decision against the frozen evidence.</span></div>';
 const support=(p.supported||[]).map(x=>`<li><b>${escapeHtml(x.label)} · ${escapeHtml(x.path)}</b> · ${escapeHtml(x.claim)} <small>${x.support_kind==='demonstrated'?'Demonstrated in':'Defined in'} the cited excerpt at ${escapeHtml((x.source_paths||[x.source_path]).join(', '))}. Boundary: ${escapeHtml(x.limitation)}</small></li>`).join('');
 const unknown=(p.unknowns||[]).map(x=>`<li>${escapeHtml(x.path)} · ${escapeHtml(x.why)}</li>`).join('');
 return `<div class="preparation-focus">${focus}</div>${support?`<div><b>Supported here, with limits</b><ul>${support}</ul></div>`:'<p>No bounded positive phase claim is established in this snapshot.</p>'}${unknown?`<div><b>Still to verify</b><ul>${unknown}</ul></div>`:''}<small>${escapeHtml(p.boundary||'This is preparation, not an instructor decision.')}</small>`;
}
function renderChallengeBrief(c){
  currentChallenge=c;
  const ro=c.board_readout||null;
  const panel=$('#boardReadout');
  if(panel)panel.open=false;
  if(ro&&panel){
    $('#boardReadoutTitle').textContent=`${ro.phase_id} · ${ro.phase_title}`;
    $('#boardPreparation').innerHTML=preparationHTML(ro.preparation);
    panel.querySelector('summary span').textContent=`Other ${ro.phase_id} concerns in this review`;
    const agenda=ro.agenda||[];
    const ch=ro.since_last_review||null;
    const changes=$('#boardChanges');
    if(ch&&ch.has_prior_snapshot){
      const bits=[];
      if((ch.no_longer_detected||[]).length)bits.push(`${ch.no_longer_detected.length} no longer detected`);
      if((ch.continuing_findings||[]).length)bits.push(`${ch.continuing_findings.length} continuing`);
      if((ch.new_findings||[]).length)bits.push(`${ch.new_findings.length} new`);
      changes.textContent=`Since the last evidence snapshot: ${bits.join(' · ')||'no material finding change detected'}.`;
      changes.classList.remove('hidden');
    }else if(changes){changes.classList.add('hidden')}
    const other=agenda.filter(x=>String(x.id)!==String(c.finding?.id||''));
    $('#boardAgenda').innerHTML=other.slice(0,5).map((x,i)=>`<div class="agenda-row"><b>${i+1}. ${escapeHtml(x.title||'Review concern')}</b></div>`).join('')||'<div class="agenda-row"><b>No other concern in this review agenda.</b></div>';
    $('#readinessMap').innerHTML=(ro.readiness_map||[]).map(x=>`<div class="readiness-row"><span>${escapeHtml(x.name)}</span></div>`).join('');
    $('#submissionBaseline').textContent=ro.submission_baseline?.message||'';
    panel.classList.remove('hidden');
  }else if(panel){panel.classList.add('hidden')}
  $('#noticedText').textContent=c.noticed||'The board identified a condition that deserves engineering review.';
  $('#significanceText').textContent=c.significance||c.why_now;
  $('#decisionQuestionText').textContent=c.decision_question||c.prompt;
  $('#challengeBrief').classList.remove('hidden');
  updateReviewJourney();
  if(c.reviewer)showActiveReviewer(c.reviewer)
}
function renderEvidenceSummary(ev){const box=$('#evidenceSummary');if(!ev){box.innerHTML='<div><b>—</b><small>Team evidence</small></div><div><b>—</b><small>Needs review</small></div><div><b>—</b><small>Snapshot</small></div>';return}const team=ev.items.filter(i=>i.status==='present').length,needs=ev.items.filter(i=>i.status!=='present').length;box.innerHTML=`<div><b>${team}</b><small>Team evidence</small></div><div><b>${needs}</b><small>Needs review</small></div><div><b>${ev.snapshot_kind==='demo'?'Demo':'Frozen'}</b><small>Snapshot</small></div>`}
function findingStatus(f){return f?.lifecycle?.status||'open'}
function renderFindingPicker(fs){const box=$('#findingPicker');if(!box)return;box.innerHTML='';const open=fs.filter(f=>!['corrected','resolved'].includes(findingStatus(f)));const selected=open.filter(f=>selectedFindingIds.has(f.id));const visible=[...selected,...open.filter(f=>!selectedFindingIds.has(f.id))].slice(0,Math.max(8,selected.length));const scope=$('#findingPickerScope');scope.classList.toggle('hidden',open.length<=visible.length);scope.textContent=open.length>visible.length?`Showing ${visible.length} of ${open.length} open findings. For another concern, use its action in Engineering Evidence.`:'';if(!visible.length){box.innerHTML='<p class="quiet">No open findings are available for this snapshot. Start a Board or Focused Review instead.</p>';return}visible.forEach(f=>{const l=document.createElement('label');l.className='finding-pick'+(selectedFindingIds.has(f.id)?' selected':'');l.innerHTML=`<input type="checkbox" value="${escapeHtml(f.id)}" ${selectedFindingIds.has(f.id)?'checked':''}><div><b>${escapeHtml(f.title)}</b><span>${escapeHtml(f.statement)}</span></div>`;l.querySelector('input').onchange=e=>{if(e.target.checked&&selectedFindingIds.size>=3){e.target.checked=false;toast('Choose up to three related findings so the conversation stays coherent.');return}e.target.checked?selectedFindingIds.add(f.id):selectedFindingIds.delete(f.id);renderFindingPicker(fs);renderFindings(fs===currentEvidence?.findings?currentEvidence:{findings:fs});updateReviewModeSummary()};box.appendChild(l)})}
function findingPrimaryPath(f){const ref=(f?.evidence_refs||[]).find(x=>String(x).startsWith('PATH:'));return ref?String(ref).slice(5):''}
function concernArtifact(challenge,evidence){
 const refs=[...(challenge?.finding?.evidence_refs||[]),...(challenge?.evidence_refs||[])];
 for(const ref of refs){
  if(!String(ref).startsWith('PATH:'))continue;
  const path=String(ref).slice(5);
  const equivalent=(evidence?.items||[]).find(i=>i.title===path&&i.equivalent_path)?.equivalent_path;
  const art=(evidence?.artifacts||[]).find(a=>a.path===path||a.path===equivalent);
  if(art)return art;
 }
 return null;
}
function currentConcernArtifact(){return concernArtifact(currentChallenge,currentEvidence)}
function updateReviewJourney(){
 const inspect=$('#inspectCurrentConcern');
 if(!inspect)return;
 const available=!!currentConcernArtifact();
 inspect.classList.toggle('hidden',!available);
 $('#browseReviewEvidence').textContent=available?'Browse Engineering Evidence':'Browse Engineering Evidence and concerns';
}
function findingContext(f,intent='discuss'){return {kind:'finding',id:f.id,label:f.title,detail:f.statement,evidence_refs:f.evidence_refs||[],intent}}
function findingStudentPrompt(f,intent){if(intent==='resolve')return `I agree the finding “${f.title}” has merit. Help me act on this exact finding: what should we improve first, why, and what evidence would show it is addressed?`;if(intent==='challenge')return `I think the board may have missed or misinterpreted evidence for the finding “${f.title}”. I want to challenge this exact finding.`;return `I want to discuss the finding “${f.title}”. Please stay on this finding and help me understand what the evidence supports, why it matters, and what I should consider next.`}
async function actOnFinding(f,intent='discuss',source='studio'){
  if(!f){toast('That finding is no longer available in this snapshot. Refresh the evidence view.');return}
  if(pending||finishingReview){toast('Wait for the current reviewer response to finish.');return}
  if(intent==='challenge'){
    const path=findingPrimaryPath(f);
    if(sessionId){openEvidenceDispute(path,f.id);return}
    await configureFindingFromEvidence(f.id,'challenge',source);
    return;
  }
  if(!sessionId){await configureFindingFromEvidence(f.id,intent,source);return}
  switchView('studio');
  // A student's unfinished thought is theirs to keep; do not replace or send it.
  if(els.response.value.trim()){
    els.response.focus();
    requestAnimationFrame(()=>els.response.scrollIntoView({block:'center',behavior:'smooth'}));
    toast('Your draft is still here. Send or clear it before discussing another concern.');
    return;
  }
  setMode('ask');
  setComposerContext(findingContext(f,intent));
  els.response.value=findingStudentPrompt(f,intent);
  updateDraftHint();
  const sending=send();
  requestAnimationFrame(()=>els.transcript.scrollIntoView({block:'center',behavior:'smooth'}));
  await sending;
}
function renderFindings(ev){const box=$('#findingList');const fs=(ev.findings||ev.challenge_candidates||[]).slice(0,8);const openCount=fs.filter(f=>!['corrected','resolved'].includes(findingStatus(f))).length;const summary=$('#findingSummaryLabel');if(summary)summary.textContent=`Review findings${openCount?` · ${openCount} open`:''}`;if(!fs.length){box.innerHTML='<p class="quiet">No high-priority repository finding is blocking this snapshot; the board can still challenge engineering judgment.</p>';renderFindingPicker([]);return}box.innerHTML='';fs.forEach(f=>{const status=findingStatus(f),d=document.createElement('div');d.className='finding-item'+(selectedFindingIds.has(f.id)?' in-review':'');const path=findingPrimaryPath(f),art=path?actualArtifact(path):null;d.innerHTML=`<div class="finding-head"><b>${escapeHtml(f.title)}</b><span><span class="provenance-badge review">REVIEW</span><span class="finding-state ${status}">${escapeHtml(status.replaceAll('_',' '))}</span></span></div><p>${escapeHtml(f.statement)}</p><div class="finding-actions"><button type="button" class="discuss-finding">Discuss</button><button type="button" class="challenge-finding">Challenge</button><button type="button" class="resolve-finding">Help me resolve this</button>${art?'<button type="button" class="open-finding-evidence">Open evidence ↗</button>':''}</div>`;d.querySelector('.discuss-finding').onclick=()=>actOnFinding(f,'discuss','studio_finding_rail');d.querySelector('.challenge-finding').onclick=()=>actOnFinding(f,'challenge','studio_finding_rail');d.querySelector('.resolve-finding').onclick=()=>actOnFinding(f,'resolve','studio_finding_rail');const op=d.querySelector('.open-finding-evidence');if(op)op.onclick=()=>showArtifact(path,`Evidence for ${f.title}`);box.appendChild(d)});renderFindingPicker(fs)}
function renderEvidence(ev){currentEvidence=ev;els.evidenceList.innerHTML='';(ev.items||[]).forEach(i=>{const d=document.createElement('div');d.className='eitem';d.title='Evidence currently in scope for this review';const actualPath=evidenceActualPath(i),art=artifactForEvidence(i),scope=(i.phase_scope||'CURRENT_PHASE').toLowerCase();d.innerHTML=`<div class="eitem-main"><span class="pill ${evidenceStatusClass(i)}">${escapeHtml(evidenceStatusLabel(i))}</span><span class="eref">${escapeHtml(i.ref)}</span><b>${escapeHtml(i.title)}</b><small>${escapeHtml(evidenceCondition(i).why)}</small><span class="e-meta"><em class="provenance-badge fact">FACT</em>${i.source_provenance&&i.source_provenance!=='UNKNOWN'?`<em class="source-badge ${String(i.source_provenance).toLowerCase()}">${escapeHtml(String(i.source_provenance).replaceAll('_',' '))}</em>`:''}<em class="scope-badge ${scope}">${escapeHtml((i.phase_scope||'CURRENT_PHASE').replaceAll('_',' '))}</em></span><span class="scope-reason">${escapeHtml(i.scope_reason||`${currentPhase} evidence`)}</span>${i.equivalent_path?`<span class="equivalent-evidence">Equivalent evidence detected: ${escapeHtml(i.equivalent_path)}</span>`:''}</div><div class="eitem-actions">${sessionId?'<button type="button" class="ask-evidence">Ask about this</button>':''}<button type="button" class="reference-evidence">Reference</button><button type="button" class="open-evidence" ${art?'':'disabled title="No exact frozen artifact is available to open"'}>Open ↗</button></div>`;const ctx={kind:'evidence',path:actualPath,label:`${i.ref} · ${actualPath}`,detail:i.detail};const ask=d.querySelector('.ask-evidence');if(ask)ask.onclick=()=>{setMode('ask');setComposerContext(ctx);els.response.focus();toast(`Ask the reviewer anything about ${actualPath}.`)};d.querySelector('.reference-evidence').onclick=()=>{setComposerContext(ctx);insertText(`${i.ref} `);els.response.focus();toast(`${i.ref} is attached to your next message.`)};const open=d.querySelector('.open-evidence');if(art)open.onclick=()=>showArtifact(art.path,`${i.ref} · ${art.path}`);else open.onclick=()=>toast('This expected evidence was not found as an exact artifact in the frozen snapshot.');els.evidenceList.appendChild(d)});const canonical=new Set((ev.items||[]).map(i=>String(i.equivalent_path||i.title||'')));const refs=(currentChallenge?.evidence_refs||[]).filter(r=>String(r).startsWith('PATH:')).map(r=>String(r).slice(5));refs.forEach((path,idx)=>{if(canonical.has(path))return;const a=(ev.artifacts||[]).find(x=>x.path===path);if(!a)return;const d=document.createElement('div');d.className='eitem';d.innerHTML=`<div class="eitem-main"><span class="pill present">in scope</span><span class="eref">X-${idx+1}</span><b>${escapeHtml(path)}</b><small>${escapeHtml(a.summary||'Repository-discovered evidence relevant to this review.')}</small><span class="e-meta"><em class="provenance-badge fact">FACT</em><em class="source-badge ${String(a.provenance||'UNKNOWN').toLowerCase()}">${escapeHtml(String(a.provenance||'UNKNOWN').replaceAll('_',' '))}</em><em class="scope-badge project_specific">PROJECT SPECIFIC</em></span><span class="scope-reason">${escapeHtml(a.scope_reason||'Selected because it supports or challenges the current engineering question.')}</span></div><div class="eitem-actions">${sessionId?'<button type="button" class="ask-evidence">Ask about this</button>':''}<button type="button" class="reference-evidence">Reference</button><button type="button" class="open-evidence">Open ↗</button></div>`;const ctx={kind:'evidence',path,label:path,detail:a.summary||''};const ask=d.querySelector('.ask-evidence');if(ask)ask.onclick=()=>{setMode('ask');setComposerContext(ctx);els.response.focus()};d.querySelector('.reference-evidence').onclick=()=>{setComposerContext(ctx);insertText(`X-${idx+1} `);els.response.focus()};d.querySelector('.open-evidence').onclick=()=>showArtifact(path,path);els.evidenceList.appendChild(d)});$('#coverage').textContent=ev.coverage+'%';$('#evCoverage').textContent=ev.coverage+'% team evidence';$('#meter').style.width=ev.coverage+'%';renderEvidenceSummary(ev);renderFindings(ev);updateReviewJourney()}
async function ensureDemo(){if(demoContext)return demoContext;demoContext=await fetch('/api/v1/dev/seed',{method:'POST'}).then(r=>r.json());return demoContext}
async function loadStudentContext(userId=null){const seed=userId?{user_id:userId}:await ensureDemo();studentContext=await fetch(`/api/v1/onboarding/users/${seed.user_id}`).then(r=>r.json());const sc=studentContext.sections?.[0];if(sc){selectedSectionId=sc.section.id;const team=sc.team;if(team){$('#contextTeam').textContent=team.name;$('#contextProject').textContent=team.project_name;els.repo.value=team.repo_full_name||'';}configurePhaseSelector(sc.phase_access)}updateRepoMode();renderMyTeam();renderStudentReadiness();updateStartReviewButton();setIdentity(currentView);return studentContext}
function configurePhaseSelector(access){if(!access)return;const names={A1:'Project Launch',A2:'Planning & Estimation',A3:'Architecture & Review',A4:'Construction & Integration',A5:'Cycle 1 Release',A6:'Final Release & Maturity'};els.phase.innerHTML='';(access.phases||[]).forEach(p=>{const o=document.createElement('option');o.value=`${p.phase_id} · ${names[p.phase_id]}`;o.textContent=`${p.phase_id} · ${names[p.phase_id]}${p.status==='locked'?' · Locked':''}`;o.disabled=p.status==='locked';els.phase.appendChild(o)});currentPhase=access.current_phase||'A1';const opt=[...els.phase.options].find(o=>o.value.startsWith(currentPhase));if(opt)els.phase.value=opt.value;$('#phaseLockHint').textContent='Future phases unlock from the instructor-controlled section calendar. Earlier released phases remain available.';applyPhase()}
function validGitHubRepositoryUrl(value){try{const u=new URL(String(value||'').trim());if(u.protocol!=='https:'||u.hostname.toLowerCase()!=='github.com'||u.username||u.password||u.port||u.search||u.hash)return false;const parts=u.pathname.split('/').filter(Boolean);if(parts.length!==2)return false;const owner=parts[0],repo=parts[1].replace(/\.git$/i,'');return /^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$/.test(owner)&&/^[A-Za-z0-9._-]{1,100}$/.test(repo)&&repo!=='.'&&repo!=='..'}catch(_e){return false}}
function repositoryOwnerTeamMember(team,repo){const members=team?.members||[],byId=members.find(m=>m.repository_owner);if(byId)return byId;const owner=String(repo?.owner_login||'').toLowerCase();if(!owner)return null;return members.find(m=>String(m.github_login||'').toLowerCase()===owner)||null}
function repositoryErrorBlock(teamId){const show=repositoryActionError&&repositoryActionErrorTeamId===teamId;return `<div id="repositoryActionError" class="repository-inline-error ${show?'':'hidden'}" role="alert"><b>Repository setup needs attention</b><span>${show?escapeHtml(repositoryActionError):''}</span></div>`}
function setRepositoryActionError(teamId,message){repositoryActionErrorTeamId=teamId;repositoryActionError=String(message||'Repository setup could not be completed.').trim();const box=$('#repositoryActionError');if(box){box.classList.remove('hidden');box.querySelector('span').textContent=repositoryActionError}}
function clearRepositoryActionError(teamId=null){if(teamId===null||repositoryActionErrorTeamId===teamId){repositoryActionError='';repositoryActionErrorTeamId=null}const box=$('#repositoryActionError');if(box){box.classList.add('hidden');const span=box.querySelector('span');if(span)span.textContent=''}}
function repositoryFriendlyError(detail,repo){const msg=String(detail||'').trim();const name=repo?.repo_full_name||'the nominated repository';if(/Only select repositories|All repositories/i.test(msg))return `GitHub granted ETIS broader access than allowed. In GitHub, configure ETIS for Only select repositories and select only ${name}, then try verification again.`;if(/not installed for this repository/i.test(msg))return `GitHub has not granted ETIS access to ${name} yet. Complete the GitHub authorization/request step, or wait for organization approval, then try verification again.`;if(/exact team repository|token scope did not match/i.test(msg))return `GitHub did not return access scoped to exactly ${name}. Review the repository selection on GitHub, make sure only the intended repository is selected, and try again.`;if(/shared COMP 330 starter kit/i.test(msg))return msg;if(/Use the HTTPS Git clone URL|HTTPS GitHub/i.test(msg))return 'Use an HTTPS GitHub repository URL such as https://github.com/organization/team-repository. The .git suffix is optional.';if(/Waiting for repository owner/i.test(msg))return msg;if(/Repository access is not ready/i.test(msg))return `ETIS still cannot read ${name}. Complete the GitHub step shown above, confirm the correct repository was selected, and try verification again.`;return msg||'Repository setup could not be completed. Check the repository and try again.'}
function repositoryCandidateEditor(repo,{force=false}={}){if(repo&&!repositoryEditorOpen&&!force)return '<button id="changeTeamRepo" class="text-button repository-change-link">Repository wrong? Use a different repository</button>';const value=repo?.clone_url||'',valid=validGitHubRepositoryUrl(value);return `<div class="repository-change-controls"><label for="teamRepoCloneUrl">HTTPS GitHub repository URL</label><span class="quiet">Use your team’s actual working repository. The <code>.git</code> suffix is optional. Example: https://github.com/organization/team-repository</span><input id="teamRepoCloneUrl" value="${escapeHtml(value)}" placeholder="https://github.com/organization/team-repository" autocomplete="off" spellcheck="false" aria-describedby="teamRepoUrlHelp repositoryConnectProgress"><span id="teamRepoUrlHelp" class="repository-input-help ${valid?'valid':''}">${valid?'Repository URL format looks valid.':'Paste a complete https://github.com/owner/repository URL to continue.'}</span><div id="repositoryConnectProgress" class="repository-connect-progress hidden" role="status" aria-live="polite"><span class="button-spinner" aria-hidden="true"></span><span>Verifying repository setup with GitHub. This may take a few moments.</span></div><div class="repository-editor-actions"><button id="connectTeamRepo" class="primary compact repository-primary-action setup-required-action" ${valid?'':'disabled'}>${repo?'Save new candidate':'Nominate team repository'} →</button>${repo?'<button id="cancelTeamRepoChange" class="text-button">Cancel</button>':''}</div></div>`}
async function submitRepositoryCandidate(team,user,cloneUrl,control){if(!validGitHubRepositoryUrl(cloneUrl)){setRepositoryActionError(team.id,'Use a complete HTTPS GitHub repository URL before continuing.');return false}clearRepositoryActionError(team.id);const original=control?.innerHTML,progress=$('#repositoryConnectProgress');if(control){control.disabled=true;control.setAttribute('aria-busy','true');control.innerHTML='<span class="button-spinner" aria-hidden="true"></span> Connecting repository…'}if(progress)progress.classList.remove('hidden');try{const r=await fetch(`/api/v1/onboarding/teams/${team.id}/repository`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({clone_url:cloneUrl,user_id:user.id})});let d={};try{d=await r.json()}catch(_e){}if(!r.ok){setRepositoryActionError(team.id,repositoryFriendlyError(d.detail,null));return false}repositoryEditorOpen=false;clearRepositoryActionError(team.id);await loadStudentContext(user.id);return true}catch(e){setRepositoryActionError(team.id,safeErrorMessage(e,'The Studio could not save this repository candidate. Try again.'));return false}finally{if(progress&&document.body.contains(progress))progress.classList.add('hidden');if(control&&document.body.contains(control)){control.disabled=false;control.removeAttribute('aria-busy');control.innerHTML=original}}}
async function verifyTeamRepository(team,repo,user,control){clearRepositoryActionError(team.id);const original=control?.textContent;if(control){control.disabled=true;control.textContent='Checking exact repository access…'}try{const r=await fetch(`/api/v1/onboarding/teams/${team.id}/repository/verify`,{method:'POST'});let d={};try{d=await r.json()}catch(_e){}if(!r.ok){setRepositoryActionError(team.id,repositoryFriendlyError(d.detail,repo));return false}repositoryEditorOpen=false;clearRepositoryActionError(team.id);toast('Verified team repository is now shared by the whole team.');await loadStudentContext(user.id);return true}catch(e){setRepositoryActionError(team.id,safeErrorMessage(e,'The Studio could not verify repository access. Try again.'));return false}finally{if(control&&document.body.contains(control)){control.disabled=false;control.textContent=original}}}
async function beginRepositoryAuthorization(team,repo,user,control){clearRepositoryActionError(team.id);const original=control?.textContent;if(control){control.disabled=true;control.textContent='Opening GitHub…'}let popup=null;try{popup=window.open('about:blank','_blank');if(popup)popup.opener=null;const r=await fetch(`/api/v1/onboarding/teams/${team.id}/repository/authorize`,{method:'POST'});let d={};try{d=await r.json()}catch(_e){}if(!r.ok){if(popup)popup.close();setRepositoryActionError(team.id,repositoryFriendlyError(d.detail,repo));return false}repo.authorization_started=true;if(popup){popup.location.href=d.authorization_url}else{window.location.assign(d.authorization_url)}await loadStudentContext(user.id);return true}catch(e){if(popup)popup.close();setRepositoryActionError(team.id,safeErrorMessage(e,'The Studio could not start GitHub authorization. Try again.'));return false}finally{if(control&&document.body.contains(control)){control.disabled=false;control.textContent=original}}}
function renderMyTeam(){
  if(!studentContext)return;
  const u=studentContext.user,sc=studentContext.sections?.[0],team=sc?.team,ob=studentContext.onboarding||{},repo=sc?.repository;
  $('#myTeamHeading').textContent=team?`${team.name} · ${team.project_name}`:'Team assignment pending';
  $('#onboardingChecklist').innerHTML=[['Loyola identity verified',ob.institutional_identity],['COMP 330 team assigned',ob.team_assigned],['GitHub identity linked',ob.github_identity],['Verified team repository',ob.repository_connected]].map(([t,ok])=>`<div class="check-step ${ok?'done':''}"><span>${ok?'✓':'○'}</span><b>${t}</b></div>`).join('');
  if(!team){$('#myTeamContent').innerHTML='<p class="quiet">Your instructor has not assigned you to a team yet.</p>';return}

  if(repositoryActionErrorTeamId!==null&&repositoryActionErrorTeamId!==team.id)clearRepositoryActionError();
  const errorBlock=repositoryErrorBlock(team.id);
  let repoBlock='';

  if(ob.repository_connected&&repo?.production_test_repository){
    repoBlock=`<div class="team-context-card verified-repository-card"><small>PRODUCTION ACCEPTANCE TEST REPOSITORY</small><b>${escapeHtml(team.repo_full_name||repo.repo_full_name)}</b><span>This controlled public starter-kit fixture is enabled only through the configured production-test identity. Normal student teams must use their own working repository.</span></div>`;
  }else if(ob.repository_connected){
    repoBlock=`<div class="team-context-card verified-repository-card"><small>✓ VERIFIED TEAM REPOSITORY</small><b>${escapeHtml(team.repo_full_name||repo?.repo_full_name||'Connected')}</b><span>Verified once and shared by the whole team. Repository replacement after verification is instructor-controlled.</span></div>`;
  }else if(!u.github_login){
    const relink=!!ob.github_identity_relink_required;
    repoBlock=`<div class="team-context-card connect-card setup-required-card"><small class="setup-required-label">ACTION REQUIRED · GITHUB IDENTITY</small><b>${relink?'Reconnect your GitHub account':'Connect the GitHub account you use for COMP 330'}</b><span>${relink?'Your older GitHub link is missing GitHub’s immutable account ID, so Studio cannot safely use it for repository ownership. Reconnect the account to repair the link.':'GitHub may reuse the account already signed in to this browser. Confirm it is the account you use for COMP 330 before authorizing. Studio does not retain the OAuth access token used for identity linking.'}</span><a href="/auth/github/link" class="primary compact link-button setup-required-action">${relink?'Reconnect GitHub account →':'Connect GitHub account →'}</a>${errorBlock}</div>`;
  }else if(!repo){
    repoBlock=`<div class="team-context-card connect-card setup-required-card" data-state-label="ACTION REQUIRED · TEAM REPOSITORY"><small class="setup-required-label">SETUP REQUIRED · TEAM REPOSITORY</small><b>Next step: nominate the team’s actual working repository</b><span>Any teammate may nominate it. Studio will not use the repository as review evidence until ownership and ETIS access are verified.</span>${repositoryCandidateEditor(null,{force:true})}${errorBlock}</div>`;
  }else if(repo.owner_type==='User'&&repo.owner_is_current_user){
    const started=!!repo.authorization_started;
    repoBlock=`<div class="team-context-card connect-card setup-required-card"><small class="setup-required-label">ACTION REQUIRED · REPOSITORY OWNER</small><b>Complete your team’s repository connection</b><span>GitHub identifies your linked account <strong>@${escapeHtml(u.github_login)}</strong> as the owner of <strong>${escapeHtml(repo.repo_full_name)}</strong>.</span><div class="repository-steps"><div class="repository-step ${started?'complete':'active'}"><small>${started?'STEP 1 OF 2 · OPENED ✓':'STEP 1 OF 2 · ACTION REQUIRED'}</small><b>${started?'GitHub authorization opened':'Authorize ETIS on GitHub'}</b><span>GitHub is being opened for repository owner <strong>@${escapeHtml(repo.owner_login||u.github_login)}</strong>. Before installing or updating access, choose <strong>Only select repositories</strong> and select only <strong>${escapeHtml(repo.repo_full_name)}</strong>. GitHub may initially show a broader selection.</span>${repo.authorization_url?`<button id="repositoryAuthorizationAction" class="${started?'secondary':'primary compact setup-required-action'} repository-github-link">${started?'Open GitHub authorization again ↗':'Authorize ETIS on GitHub ↗'}</button>`:''}</div><div class="repository-step ${started?'active':'locked'}"><small>${started?'STEP 2 OF 2 · ACTION REQUIRED':'STEP 2 OF 2 · LOCKED'}</small><b>Verify the exact repository</b><span>Return here after GitHub is complete. Studio will verify only the nominated repository before making it team evidence.</span><button id="verifyTeamRepo" class="primary compact repository-primary-action setup-required-action" ${started?'':'disabled'}>${started?'Verify repository access →':'Complete Step 1 first'}</button></div></div>${errorBlock}${repositoryCandidateEditor(repo)}</div>`;
  }else if(repo.owner_type==='User'){
    const ownerMember=repositoryOwnerTeamMember(team,repo),linked=`@${u.github_login}`;
    repoBlock=ownerMember?`<div class="team-context-card connect-card setup-required-card"><small class="setup-required-label">TEAM SETUP IN PROGRESS</small><b>Waiting for ${escapeHtml(ownerMember.name)} (@${escapeHtml(repo.owner_login)})</b><span><strong>No action is required from you right now.</strong> ${escapeHtml(ownerMember.name)} owns the nominated repository and must authorize and verify it. Once complete, every teammate inherits the verified state.</span>${errorBlock}${repositoryCandidateEditor(repo)}</div>`:`<div class="team-context-card connect-card setup-required-card"><small class="setup-required-label">REPOSITORY OWNER NEEDS TO ACT</small><b>Waiting for @${escapeHtml(repo.owner_login||'repository owner')}</b><span>Studio does not currently see @${escapeHtml(repo.owner_login||'the owner')} linked to a current team member. You are linked as <strong>${escapeHtml(linked)}</strong>.</span><div class="repository-next-step"><small>NEXT STEP</small><b>The teammate who owns @${escapeHtml(repo.owner_login||'this repository')} should sign in and link that GitHub account.</b><span>If @${escapeHtml(repo.owner_login||'the owner')} is actually your account, change your linked GitHub account. If this is the wrong repository, choose a different one.</span></div><div class="repository-secondary-actions"><a href="/auth/github/link" class="secondary link-button">Change linked GitHub account ↗</a></div>${errorBlock}${repositoryCandidateEditor(repo)}</div>`;
  }else if(repo.organization_approval_required||repo.owner_type==='Organization'){
    const started=!!repo.authorization_started;
    repoBlock=`<div class="team-context-card connect-card setup-required-card"><small class="setup-required-label">TEAM SETUP · ORGANIZATION REPOSITORY</small><b>${escapeHtml(repo.repo_full_name)} needs GitHub organization authorization</b><span>GitHub — not ETIS — decides whether your account can install the App directly or must send an approval request to the organization owner.</span><div class="repository-steps"><div class="repository-step ${started?'complete':'active'}"><small>${started?'STEP 1 OF 2 · OPENED ✓':'STEP 1 OF 2 · ACTION REQUIRED'}</small><b>${started?'GitHub organization access requested/opened':'Request organization access on GitHub'}</b><span>GitHub is being opened for the owning organization <strong>@${escapeHtml(repo.owner_login||'organization')}</strong>. Keep ETIS on <strong>Only select repositories</strong> with only the nominated team repository selected. GitHub may initially show a broader selection.</span>${repo.organization_request_url?`<button id="repositoryAuthorizationAction" class="${started?'secondary':'primary compact setup-required-action'} repository-github-link">${started?'Open GitHub request again ↗':'Request organization access on GitHub ↗'}</button>`:''}</div><div class="repository-step ${started?'active':'locked'}"><small>${started?'STEP 2 OF 2 · ACTION REQUIRED':'STEP 2 OF 2 · LOCKED'}</small><b>Check and verify repository access</b><span>If ETIS is already approved for this repository, simply return here and verify. If GitHub sent an approval request, wait for an organization owner/admin to approve repository access first.</span><button id="verifyTeamRepo" class="primary compact repository-primary-action setup-required-action" ${started?'':'disabled'}>${started?'Check & verify repository access →':'Complete Step 1 first'}</button></div></div>${errorBlock}${repositoryCandidateEditor(repo)}</div>`;
  }else{
    repoBlock=`<div class="team-context-card connect-card setup-required-card"><small class="setup-required-label">CANDIDATE REPOSITORY · OWNER NOT CONFIRMED</small><b>${escapeHtml(repo.repo_full_name||repo.clone_url||'Repository candidate saved')}</b><span>Studio saved the candidate but could not confirm its GitHub owner. It remains unverified and is not review evidence.</span><div class="repository-next-step"><small>NEXT STEP</small><b>Retry owner detection.</b><span>If GitHub still cannot confirm the owner, verify the URL or use a different repository.</span></div><button id="retryOwnerLookup" class="primary compact repository-primary-action setup-required-action">Retry owner check →</button>${errorBlock}${repositoryCandidateEditor(repo)}</div>`;
  }

  $('#myTeamContent').innerHTML=`<div class="team-context-card"><small>SECTION</small><b>${escapeHtml(sc.section.display_name)}</b></div><div class="team-context-card"><small>TEAM</small><b>${escapeHtml(team.name)}</b><span>${escapeHtml(team.team_key)}</span></div><div class="team-context-card"><small>PROJECT</small><b>${escapeHtml(team.project_name)}</b><button id="editProjectName" class="text-button">Edit project details</button></div>${repoBlock}<div class="team-context-card ${u.github_login?'':'setup-required-card'}"><small class="${u.github_login?'':'setup-required-label'}">${u.github_login?'GITHUB IDENTITY':'ACTION REQUIRED · GITHUB IDENTITY'}</small><b>${u.github_login?'@'+escapeHtml(u.github_login):(ob.github_identity_relink_required?'Reconnect required':'Not linked yet')}</b>${u.github_login?'<span>This is the GitHub account Studio uses to determine personal-repository ownership.</span><a href="/auth/github/link" class="text-button link-button">Change linked GitHub account</a>':`<a href="/auth/github/link" class="secondary link-button setup-required-action">${ob.github_identity_relink_required?'Reconnect GitHub account →':'Connect GitHub account →'}</a>`}</div><div class="team-context-card team-members-card"><small>TEAM MEMBERS</small>${(team.members||[]).map(m=>`<span><b>${escapeHtml(m.name)}</b> · ${escapeHtml(m.responsibility_role||'Engineering Contributor')}${m.github_login?` · @${escapeHtml(m.github_login)}`:' · GitHub not linked'}</span>`).join('')||'<span>Team membership has not been populated yet.</span>'}</div>`;

  const authAction=$('#repositoryAuthorizationAction');
  if(authAction)authAction.onclick=()=>beginRepositoryAuthorization(team,repo,u,authAction);

  const change=$('#changeTeamRepo');
  if(change)change.onclick=()=>{repositoryEditorOpen=true;clearRepositoryActionError(team.id);renderMyTeam();requestAnimationFrame(()=>$('#teamRepoCloneUrl')?.focus())};
  const cancel=$('#cancelTeamRepoChange');
  if(cancel)cancel.onclick=()=>{repositoryEditorOpen=false;clearRepositoryActionError(team.id);renderMyTeam()};

  const input=$('#teamRepoCloneUrl'),connect=$('#connectTeamRepo');
  if(input&&connect){const update=()=>{const valid=validGitHubRepositoryUrl(input.value),help=$('#teamRepoUrlHelp');connect.disabled=!valid;if(help){help.textContent=valid?'Repository URL format looks valid.':'Paste a complete https://github.com/owner/repository URL to continue.';help.classList.toggle('valid',valid)}if(repositoryActionErrorTeamId===team.id)clearRepositoryActionError(team.id)};input.addEventListener('input',update);update();connect.onclick=()=>submitRepositoryCandidate(team,u,input.value.trim(),connect)};

  const retry=$('#retryOwnerLookup');
  if(retry)retry.onclick=()=>submitRepositoryCandidate(team,u,repo.clone_url,retry);

  const verify=$('#verifyTeamRepo');
  if(verify)verify.onclick=()=>verifyTeamRepository(team,repo,u,verify);

  const edit=$('#editProjectName');
  if(edit)edit.onclick=async()=>{const value=prompt('Confirm the project name used by Engineering Studio:',team.project_name);if(!value||value.trim()===team.project_name)return;const r=await fetch(`/api/v1/onboarding/teams/${team.id}/project`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({project_name:value.trim()})});if(r.ok){toast('Project name updated for the team.');await loadStudentContext(u.id)}};
}
async function loadHistoryPage(){await loadHistory();$('#reviewHistoryPage').innerHTML=$('#reviewHistory').innerHTML;$$('#reviewHistoryPage .history-item').forEach(b=>b.onclick=()=>resumeSession(Number(b.dataset.session)))}

function updateRepoMode(){const b=$('#repoMode'),repo=els.repo.value.trim();els.repo.title=repo||'Repository not connected';if(appRole==='student'&&studentContext){const sc=studentContext.sections?.[0],ob=studentContext.onboarding||{},candidate=sc?.repository;if(ob.repository_connected&&candidate?.production_test_repository){b.innerHTML='<span class="status green"></span> Production acceptance test repository';return}if(ob.repository_connected){b.innerHTML='<span class="status green"></span> Repository connected · Verified team repository';return}if(candidate?.owner_type==='User'&&candidate.owner_is_current_user){b.innerHTML='<span class="status amber"></span> Repository owner action required';return}if(candidate?.owner_type==='User'){b.innerHTML='<span class="status amber"></span> Waiting for repository owner';return}if(candidate?.organization_approval_required){b.innerHTML='<span class="status amber"></span> Repository pending organization approval';return}if(candidate){b.innerHTML='<span class="status amber"></span> Candidate repository · owner not confirmed';return}b.innerHTML='<span class="status amber"></span> Repository not connected';return}b.innerHTML=repo==='etis-framework/comp330-f26-starter-kit'?'<span class="status green"></span> Public starter-kit acceptance test':'<span class="status amber"></span> Repository selected'}
els.repo.addEventListener('input',updateRepoMode);
async function beginReview(mode='board',opts={}){
  if(!semanticReady){openHelp('semantic-required');return}
  if(pending)return;
  if(sessionId){
    toast('Complete or pause the current review before starting another.');
    return;
  }

  reviewMode=mode;
  requestedFindingId=opts.finding_id||null;

  const reviewLabel=reviewModeLabel(mode);
  const retry=$('#retryStartReview');

  els.newReview.disabled=true;
  els.newReview.setAttribute('aria-busy','true');
  els.newReview.innerHTML=
    `<span class="button-spinner" aria-hidden="true"></span> Preparing ${reviewLabel}…`;

  $('#reviewStatus').classList.remove('review-status-error');
  $('#reviewStatusLabel').textContent=`Preparing ${reviewLabel}`;
  $('#reviewStatus').classList.remove('hidden');
  $('#reviewStatusText').textContent=
    'Freezing repository evidence and preparing the phase review.';

  retry?.classList.add('hidden');

  setPending(
    true,
    'Freezing repository evidence…',
    'review_start'
  );

  try{
    const seed=await ensureDemo();

    const sc=studentContext?.sections?.[0],
      teamId=sc?.team?.id||seed.team_id,
      userId=studentContext?.user?.id||seed.user_id,
      repo=sc?.team?.repo_full_name||els.repo.value.trim();

    const body={
      team_id:teamId,
      phase_id:currentPhase,
      user_id:userId,
      repo_full_name:repo||null,
      mode:mode==='board'
        ?'board_review'
        :mode==='focused'
          ?'focused_review'
          :'finding_review',
      focus:opts.focus||null,
      finding_id:opts.finding_id||null,
      finding_ids:opts.finding_ids||[],
      entry_intent:
        opts.entry_intent
        ||pendingEntryContext?.entry_intent
        ||'review',
      source_view:
        opts.source_view
        ||pendingEntryContext?.source_view
        ||'studio'
    };

    body.client_request_id=reviewStartRequestId(body);

    const r=await fetch(
      '/api/v1/reviews/start',
      {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify(body)
      }
    );

    const payload=await r.json();

    if(!r.ok){
      throw new Error(payload.detail||r.statusText);
    }

    const d=payload;

    sessionId=d.session_id;
    els.phase.disabled=true;$('#reviewCompletionSummary').classList.add('hidden');
    reviewSnapshotId=d.snapshot_id||null;
    clearReviewStartRequest();
    committed=false;

    document.body.classList.add('review-session-active');

    renderSessionPurpose(
      mode,
      {
        ...opts,
        entry_intent:body.entry_intent,
        source_view:body.source_view
      },
      d
    );

    clearEntryContext();
    renderChallengeBrief(d.challenge);
    renderEvidence(d.evidence);

    els.transcript.innerHTML='';
    renderStrengths(d.evidence);

    $('#challengeTitle').textContent=d.challenge.title;

    addTurn(
      'reviewer',
      d.challenge.lens,
      d.challenge.opening_text||d.challenge.prompt,
      {
        level:d.challenge.level,
        reviewer:d.challenge.reviewer,
        kind:'opening challenge'
      }
    );

    $('#defense').textContent='In discussion';
    $('#depth').textContent='1 move at a time';

    $('#reviewStatus').classList.remove('review-status-error');

    $('#reviewStatusLabel').textContent=
      mode==='focused'
        ?'Focused review in progress'
        :mode==='finding'
          ?'Finding review in progress'
          :'Board review in progress';

    retry?.classList.add('hidden');

    $('#conversationControls').classList.remove('hidden');
    $('#conversationReadyNote')?.classList.remove('hidden');

    $('#reviewStatusText').textContent=
      `${currentPhase} · Reviewing a frozen repository snapshot. After changing your work, start a new review.`;
    $('#reviewStatusText').title=`${d.evidence.repo_full_name}@${String(d.evidence.commit_sha).slice(0,8)} · Session #${sessionId}`;

    $('#coachPanel').classList.add('hidden');
    $('#commitBar').classList.add('hidden');

    setMode('ask');
    restoreDraft();

    await loadHistory();
    requestAnimationFrame(()=>requestAnimationFrame(()=>{
      els.transcript.scrollTop=0;
      updateReadingCue();
      document.querySelector('.review-room')?.scrollIntoView({behavior:'auto',block:'start'});
    }));

  }catch(e){
    console.error('Review preparation failed',e);

    document.body.classList.remove('review-session-active');
    sessionId=null;

    $('#conversationControls').classList.add('hidden');
    $('#conversationReadyNote')?.classList.add('hidden');

    $('#reviewStatus').classList.add('review-status-error');
    $('#reviewStatus').classList.remove('hidden');
    $('#reviewStatusLabel').textContent='Review could not be prepared';

    $('#reviewStatusText').textContent=
      `${safeErrorMessage(e,'Review preparation failed.')} No review was started.`;

    if(retry){
      retry.classList.remove('hidden');
      retry.onclick=()=>beginReview(mode,{...opts});
    }

  }finally{
    els.newReview.removeAttribute('aria-busy');
    setPending(false);
    updateStartReviewButton();
    if(!sessionId)els.response.focus();
  }
}
function insertText(text){
  if(!els.response)return;
  const start=els.response.selectionStart??els.response.value.length;
  const end=els.response.selectionEnd??start;
  const before=els.response.value.slice(0,start),after=els.response.value.slice(end);
  els.response.value=before+text+after;
  const pos=start+text.length;
  els.response.setSelectionRange(pos,pos);
  updateDraftHint();
}
$$('[data-insert]').forEach(b=>b.onclick=()=>insertText(b.dataset.insert));
function updateDraftHint(){
  const t=els.response.value.trim();
  if(!t){$('#draftHint').textContent=sessionId?'You can answer, ask a question, disagree, or say you are stuck.':'';return}
  $('#draftHint').textContent=t.length<30?'A rough thought is enough to start':'The reviewer will interpret meaning, not exact wording or grammar.';
}
els.response.addEventListener('input',updateDraftHint);
function setMode(mode){
  interactionMode=mode;
  $('#askMode').classList.toggle('active',mode==='ask');
  $('#decisionMode').classList.toggle('active',mode==='decision');
  $('#askBanner').classList.toggle('hidden',mode!=='ask');
  $('#decisionComposerHead').classList.toggle('hidden',mode==='ask');
  $('#movePrompts').classList.toggle('hidden',mode==='ask');
  els.response.placeholder=mode==='ask'?'Talk naturally—ask, answer, disagree, think out loud, or say where you are stuck.':'Start shaping your recommendation. It can be rough; the reviewer will coach the next step.';
  els.send.textContent=mode==='ask'?'Send to Reviewer →':'Discuss Recommendation →';
  updateDraftHint();
}
$('#askMode').onclick=()=>{if(!sessionId){toast('Start a review first.');return}setMode('ask');els.response.focus()};
$('#decisionMode').onclick=()=>{if(!sessionId){toast('Start a review first.');return}setMode('decision');els.response.focus()};
els.decision.onchange=()=>{$('#postureMeaning').textContent=postureMeanings[els.decision.value]||postureMeanings['']};
function turnId(){return (crypto.randomUUID?crypto.randomUUID():`turn-${Date.now()}-${Math.random().toString(16).slice(2)}`)}
$('#coachButton').onclick=async()=>{
  if(!semanticReady){openHelp('semantic-required');return}
  if(!sessionId){toast('Start a review first.');return}
  if(pending)return;

  const body={
    decision:els.decision.value||null,
  };

  const mutation=reviewMutationRequest(
    'coach',
    sessionId,
    body
  );

  body.client_turn_id=mutation.id;

  setPending(
    true,
    `${currentReviewer?.name||'Your reviewer'} is deciding how much help will be useful…`
  );

  try{
    const r=await fetch(
      `/api/v1/reviews/${sessionId}/coach`,
      {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify(body),
      }
    );

    const responseBody=await r.json();

    if(!r.ok){
      throw new Error(responseBody.detail||r.statusText);
    }

    const reply=responseBody.reply;

    // A duplicate Coach result after an uncertain delivery is recovery of
    // the original logical coaching request. The browser did not receive
    // that reply previously, so render it now.
    addTurn('student','conversation','Explain this and show me how.',{kind:'student_coach_request'});
    addTurn(
      'reviewer',
      reply.lens,
      reply.text,
      {
        reviewer:reply.reviewer,
        kind:reply.kind,
        guidance_refs:reply.guidance_refs,
        coaching_phase:reply.coaching_phase,
        provider:reply.provider,
      }
    );

    if(responseBody.duplicate){
      toast(
        'Your earlier coaching request had already been processed. '
        +'The reviewer response was recovered.'
      );
    }

    $('#depth').textContent=
      `Coaching level ${responseBody.coaching_level}`;

    clearReviewMutation(mutation);

    await loadHistory();

  }catch(e){
    toast('Coaching could not load: '+e.message);

  }finally{
    setPending(false);
    els.response.focus();
  }
};

async function send(challengeTurn=null){
  if(!semanticReady){openHelp('semantic-required');return}
  if(!sessionId){toast('Start a review first.');return}
  if(pending)return;

  const text=(challengeTurn?.text??els.response.value).trim();
  if(!text){
    toast('Type a thought or question first.');
    return;
  }

  const body={
    response:text,
    evidence_refs:contextRefs(),
    decision:challengeTurn?null:els.decision.value||null,
    intent:challengeTurn||interactionMode==='ask'?'discuss':'decision',
  };
  if(challengeTurn)body.evidence_refs=challengeTurn.evidenceRefs;

  const mutation=reviewMutationRequest(
    'respond',
    sessionId,
    body
  );

  body.client_turn_id=mutation.id;

  let studentTurn=null;
  if(!mutation.rendered){
    studentTurn=addTurn(
      'student',
      'conversation',
      text,
      {kind:challengeTurn?'ask':interactionMode}
    );
    markReviewMutationRendered(mutation);
  }

  if(!challengeTurn){
    saveDraft();
    els.response.value='';
    updateDraftHint();
  }

  setPending(
    true,
    `${currentReviewer?.name||'Your reviewer'} is considering what you meant and what the evidence supports…`
  );

  let serverAccepted=false;

  try{
    const r=await fetch(
      `/api/v1/reviews/${sessionId}/respond`,
      {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify(body),
      }
    );

    const responseBody=await r.json();

    if(!r.ok){
      throw new Error(responseBody.detail||r.statusText);
    }

    // HTTP success is the transaction boundary. From this point forward the
    // student's logical turn has been accepted by the server. A later browser
    // rendering/refresh problem must never restore the draft or tell the
    // student that the review turn itself failed.
    serverAccepted=true;
    if(!challengeTurn)clearDraft();
    clearReviewMutation(mutation);

    const reply=responseBody.follow_up;

    addTurn(
      'reviewer',
      reply.lens,
      reply.text,
      {
        reviewer:reply.reviewer,
        kind:reply.kind,
        guidance_refs:reply.guidance_refs,
        coaching_phase:reply.coaching_phase,
        provider:reply.provider,
      }
    );

    if(responseBody.duplicate){
      toast(
        'Your previous message had already been processed. '
        +'The reviewer response was recovered.'
      );
    }

    const ev=responseBody.evaluation||{};

    $('#defense').textContent=ev.disposition
      ?humanizeDisposition(ev.disposition)
      :'In discussion';

    $('#depth').textContent=ev.learning_score!=null
      ?`${ev.learning_score}/${ev.learning_score_max} moves`
      :'In discussion';

    // The reviewer already supplies the next conversational step. A separate
    // reasoning-rubric prompt can contradict direct teaching and confuse the student.
    $('#coachPanel').classList.add('hidden');

    updateRecommendationBar(
      ev,
      responseBody.reasoning_state||{}
    );

    if(!$('#commitBar').classList.contains('hidden')){
      $('#defense').textContent='Recommendation ready';
    }

    if(!challengeTurn)setComposerContext(null);
    await loadHistory();

  }catch(e){
    console.error('Review response handling failed',e);

    if(serverAccepted){
      toast(
        'Your response was saved, but Studio could not refresh part of the review. '
        +'Reload this review if anything looks incomplete.'
      );
    }else{
      toast(safeErrorMessage(e,'Studio could not confirm that response.'));

      if(!challengeTurn&&!els.response.value){
        els.response.value=text;
        updateDraftHint();
        saveDraft();
      }

      addTurn(
        'reviewer',
        'system',
        'Studio could not confirm that turn. Your draft is preserved. '
        +'Wait a moment, then retry once. If the server already received it, '
        +'Studio will recover the same logical turn rather than create a duplicate.',
        {
          reviewer:{
            name:'Studio',
            role:'System',
            focus:'Review continuity',
            portrait:'/assets/reviewers/maya-chen.svg'
          },
          kind:'system'
        }
      );
    }

  }finally{
    setPending(false);
    if(!challengeTurn)els.response.focus();
  }
  return serverAccepted?studentTurn||true:false;
}

function reviewModeLabel(mode){
  return mode==='focused'
    ?'Focused Review'
    :mode==='finding'
      ?'Finding Review'
      :'Board Review';
}

function formatEstimatedCost(value){
  const amount=Number(value||0);
  if(!Number.isFinite(amount)||amount<=0)return '$0.00';
  if(amount<0.0001)return '<$0.0001';
  if(amount<0.01)return `$${amount.toFixed(4)}`;
  return `$${amount.toFixed(2)}`;
}

function pluralizeCount(value,singular,plural=`${singular}s`){
  const count=Number(value||0);
  return `${count} ${count===1?singular:plural}`;
}

function reviewerTurnLabel(turn){
  const reviewer=turn?.signals?.reviewer;
  if(reviewer?.name){
    return reviewer.role
      ?`${reviewer.name} · ${reviewer.role}`
      :reviewer.name;
  }
  return lensLabels[turn?.lens]
    ||String(turn?.lens||'Senior reviewer').replaceAll('_',' ');
}

function updateStartReviewButton(){
  const btn=els.newReview;
  if(!btn)return;
  if(sessionId&&document.body.classList.contains('review-session-active')){btn.textContent='Review in progress';btn.disabled=true;return}
  if(sessionId){btn.textContent='Start another review';btn.disabled=false;btn.onclick=()=>newReviewHome();return}
  btn.onclick=startReviewAction;
  if(!semanticReady){btn.textContent='Configure Coaching';btn.disabled=false;btn.removeAttribute('title');return}
  const readiness=studentReviewReadiness();
  if(appRole==='student'&&!readiness.ready){btn.textContent=readiness.code==='phase'?`${currentPhase} not released`:'Setup required before review';btn.disabled=true;btn.title=readiness.detail;return}
  btn.removeAttribute('title');
  if(reviewMode==='focused'){
    const ready=!!$('#reviewFocus')?.value.trim();
    btn.textContent='Start Focused Review →';btn.disabled=!ready||pending;
  }else if(reviewMode==='finding'){
    btn.textContent='Start Finding Review →';btn.disabled=!selectedFindingIds.size||pending;
  }else{btn.textContent='Start Board Review →';btn.disabled=!!pending}
}

function reviewModeIntroduction(mode){
 const lead=mode==='focused'
  ?'Name the decision, artifact, or question you want examined. Then select Start Focused Review.'
  :mode==='finding'
   ?'Select one to three saved concerns, then select Start Finding Review. You can challenge the board’s interpretation.'
   :'Let the board choose a phase question from your repository evidence. Select Start Board Review to begin.';
 return `${lead} Engineering Evidence holds saved sources and concerns. You can move between rooms without ending a review.`;
}
function updateReviewModeSummary(){const box=$('#reviewModeSummary');$('#reviewModeIntro').textContent=reviewModeIntroduction(reviewMode);if(reviewMode==='board')box.textContent='Board Review · the board chooses the agenda. Use Start Board Review in the team bar above.';else if(reviewMode==='focused')box.textContent=$('#reviewFocus')?.value.trim()?'Focused Review · use Start Focused Review in the team bar above.':'Focused Review · enter a subject above to enable Start Focused Review.';else box.textContent=selectedFindingIds.size?`Review Findings · ${selectedFindingIds.size} selected. Use Start Finding Review in the team bar above.`:'Review Findings · select one to three concerns to enable Start Finding Review.';updateStartReviewButton()}
let findingPickerRequestId=0;
async function prepareLauncherEvidence(){if(currentEvidence?.phase_id===currentPhase)return currentEvidence;const seed=await ensureDemo();const sc=studentContext?.sections?.[0],teamId=sc?.team?.id||seed.team_id,repo=sc?.team?.repo_full_name||els.repo.value.trim();const r=await fetch('/api/v1/repositories/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({team_id:teamId,phase_id:currentPhase,repo_full_name:repo||null})}),d=await r.json();if(!r.ok)throw new Error(d.detail||r.statusText);return d}
async function selectReviewMode(mode,options={}){if(sessionId){toast('This review keeps its purpose. Finish or pause it before starting a different review type.');return}const requestId=++findingPickerRequestId;reviewMode=mode;$$('.review-choice').forEach(b=>{const selected=b.dataset.reviewMode===mode;b.classList.toggle('selected',selected);b.setAttribute('aria-pressed',String(selected))});$('#focusedReviewPanel').classList.toggle('hidden',mode!=='focused');$('#findingReviewPanel').classList.toggle('hidden',mode!=='finding');updateReviewModeSummary();if(mode==='finding'){const picker=$('#findingPicker'),readiness=studentReviewReadiness();if(appRole==='student'&&!readiness.ready){picker.innerHTML=`<p class="quiet">${escapeHtml(readiness.detail)} Finish setup in My Team before Studio prepares repository findings.</p>`;return}if(options.findings){renderFindingPicker(options.findings);updateReviewModeSummary();return}picker.innerHTML='<div class="picker-loading"><span class="mini-spinner"></span><span>Preparing current-phase findings from the repository snapshot…</span></div>';try{const ev=await prepareLauncherEvidence();if(requestId!==findingPickerRequestId||reviewMode!=='finding'||sessionId)return;currentEvidence=ev;renderFindings(ev);renderFindingPicker(ev.findings||[])}catch(e){if(requestId!==findingPickerRequestId)return;picker.innerHTML='<p class="quiet">Findings could not be prepared. You can still start a Board or Focused Review.</p>';toast('Could not prepare findings: '+e.message)}finally{if(requestId===findingPickerRequestId)updateReviewModeSummary()}}}
function renderSessionPurpose(mode,opts,d){
  const label=reviewModeLabel(mode);

  let detail=
    'The senior board selected the agenda from current phase evidence.';

  if(mode==='focused'){
    detail=
      `You asked the board to challenge: ${opts.focus||'a specific engineering concern'}.`;
  }

  if(mode==='finding'){
    const f=(d.evidence?.findings||[])
      .find(x=>(opts.finding_ids||[]).includes(x.id));

    const action=
      opts.entry_intent==='resolve'
        ?'Help resolve'
        :opts.entry_intent==='challenge'
          ?'Challenge'
          :opts.entry_intent==='understand'
            ?'Understand'
            :'Discuss';

    detail=
      `${action}: ${f?.title||`${(opts.finding_ids||[]).length} selected finding(s)`}.`;
  }

  const box=$('#reviewSessionPurpose');

  box.innerHTML=
    `<div><b>${label} · ${currentPhase}</b><span>${escapeHtml(detail)} Snapshot ${escapeHtml(String(d.evidence?.commit_sha||'').slice(0,8))}.</span></div>`;

  box.classList.remove('hidden');
  $('#reviewHomeButton').classList.add('hidden');
}
$$('.review-choice').forEach(b=>{b.setAttribute('aria-pressed',String(b.dataset.reviewMode===reviewMode));b.onclick=()=>selectReviewMode(b.dataset.reviewMode)});
$('#reviewFocus').addEventListener('input',updateReviewModeSummary);
function startReviewAction(){if(pending)return;const readiness=studentReviewReadiness();if(appRole==='student'&&!readiness.ready){renderStudentReadiness();toast(readiness.detail);if(readiness.code!=='phase')switchView('myteam');return}if(sessionId&&!document.body.classList.contains('review-session-active')){newReviewHome();return}if(sessionId)return;if(reviewMode==='focused'){const focus=$('#reviewFocus').value.trim();if(!focus){toast('Tell the board what engineering concern you want challenged.');return}beginReview('focused',{focus,source_view:pendingEntryContext?.source_view||'studio'});return}if(reviewMode==='finding'){if(!selectedFindingIds.size){toast('Choose one to three findings first.');return}beginReview('finding',{finding_ids:[...selectedFindingIds],entry_intent:pendingEntryContext?.entry_intent||'review',source_view:pendingEntryContext?.source_view||'studio'});return}beginReview('board',{source_view:pendingEntryContext?.source_view||'studio'})}
els.newReview.onclick=startReviewAction;
function humanizeDisposition(value){
  const key=String(value||'').trim();
  const labels={
    defensible_move:'Defensible move',
    needs_challenge:'Needs challenge',
    insufficient_defense:'Insufficient defense',
    developing_position:'Developing position',
    developing:'Developing position',
  };
  if(labels[key])return labels[key];
  const text=key.replaceAll('_',' ').replaceAll('-',' ').trim();
  return text?text.charAt(0).toUpperCase()+text.slice(1):'In discussion';
}
function humanizeMove(m){return ({decision_explicit:'Make the actual decision explicit.',boundary_visible:'Clarify what may continue and what should pause or escalate.',tradeoff_visible:'Name the benefit you preserve and the risk or cost you accept.',evidence_boundary_visible:'Separate what the evidence supports from what it cannot support.',uncertainty_visible:'Identify the assumption or unknown that matters most.',ownership_visible:'Name who owns the action and who verifies closure.',change_trigger_visible:'Say what evidence or event changes the condition.',consequence_visible:'Explain who or what is affected if the judgment is wrong.'}[m]||String(m).replaceAll('_',' '))}
els.send.onclick=send;els.response.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}});els.response.addEventListener('input',()=>{updateDraftHint();saveDraft()});
function updateRecommendationBar(evaluation,reasoning={}){const eligible=!!evaluation?.ready_to_commit&&!committed&&sessionId&&reviewMode!=='finding'&&(reviewMode==='board'||reasoning.decision_explicit||!!els.decision.value);$('#commitBar').classList.toggle('hidden',!eligible)}
$('#commitPosition').onclick=async()=>{if(!sessionId||pending)return;setPending(true,'Recording the recommendation you are prepared to defend…');try{const r=await fetch(`/api/v1/reviews/${sessionId}/commit`,{method:'POST'});const d=await r.json();if(!r.ok)throw new Error(d.detail||r.statusText);committed=true;addTurn('reviewer',d.reply.lens,d.reply.text,{reviewer:d.reply.reviewer,kind:'recommendation stated'});$('#commitBar').classList.add('hidden');$('#defense').textContent='Recommendation stated';toast('Recommendation recorded. You may revise it if the evidence or your reasoning changes.')}catch(e){toast(e.message)}finally{setPending(false)}};
function renderReviewCompletionSummary(){
  const box=$('#reviewCompletionSummary');
  const finding=currentChallenge?.finding;
  const title=finding?.title||currentChallenge?.title||'';
  const path=findingPrimaryPath(finding);
  const art=(currentEvidence?.artifacts||[]).find(a=>a.path===path);
  box.innerHTML=`<b>Review complete. Your conversation and frozen evidence are saved.</b><span>${title?`Before the next review, revisit: ${escapeHtml(title)}. `:''}Improve your team's repository work, then start another review to check its current commit. This is preparation, not instructor approval.</span>${art?'<button type="button" class="secondary compact" id="completionInspect">Inspect cited evidence</button>':''}`;
  if(art)box.querySelector('#completionInspect').onclick=()=>showArtifact(path,path);
  box.classList.remove('hidden');
}
function closeReviewExit(){reviewExitIntent=null;$('#reviewExitOverlay').classList.add('hidden')}
function openReviewExit(intent='finish'){
  if(!sessionId||!document.body.classList.contains('review-session-active')||pending||finishingReview)return;
  reviewExitIntent=intent;
  $('#reviewExitTitle').textContent=intent==='new'?'Start another review?':'Finish this review?';
  $('#reviewExitExplanation').textContent=intent==='new'
    ?'This review uses a frozen snapshot. Finish it to make this conversation read-only, or leave it open to resume later. The next review checks the current repository commit.'
    :'Finishing makes this conversation read-only and preserves its frozen evidence. You can start another review of updated work afterward.';
  if(els.response.value.trim())$('#reviewExitExplanation').textContent+=' Your unsent message is not part of the saved conversation; send it first if you want it included.';
  $('#leaveReviewOpen').classList.toggle('hidden',intent!=='new');
  $('#leaveReviewOpen').textContent='Leave open; start another';
  $('#confirmFinishReview').textContent=intent==='new'?'Finish; start another':'Finish this review';
  $('#reviewExitOverlay').classList.remove('hidden');
  $('#keepReviewing').focus();
}
function applyReviewCompleted(){
  document.body.classList.remove('review-session-active');
  els.phase.disabled=false;
  $('#conversationControls').classList.add('hidden');
  $('#conversationReadyNote')?.classList.add('hidden');
  els.send.disabled=true;
  $('#commitBar').classList.add('hidden');
  $('#defense').textContent='Review complete';
  hideActiveReviewer();
  $('#reviewStatus').classList.remove('hidden');
  $('#reviewStatusLabel').textContent='Review complete · read-only';
  $('#reviewStatusText').textContent=`Session #${sessionId} · conversation and frozen evidence preserved`;
  $('#reviewHomeButton').classList.add('hidden');
  renderReviewCompletionSummary();
  committed=false;
  updateStartReviewButton();
}
async function finishReview(){
  if(!sessionId||pending||finishingReview)return false;
  const completingSession=sessionId;
  finishingReview=true;
  $('#confirmFinishReview').disabled=true;
  $('#leaveReviewOpen').disabled=true;
  try{
    const response=await fetch(`/api/v1/reviews/${completingSession}/complete`,{method:'POST'});
    if(!response.ok){const body=await response.json();throw new Error(body.detail||response.statusText)}
    if(sessionId!==completingSession)return false;
    applyReviewCompleted();
    closeReviewExit();
    toast('Review complete. Start another review when your team is ready.');
    loadHistory().catch(()=>toast('The review completed, but history could not refresh. Reload to see it.'));
    requestAnimationFrame(()=>window.scrollTo({top:0,behavior:'auto'}));
    return true;
  }catch(e){
    // A lost completion response may follow a successful database commit.
    // Reconcile before telling the student the review is still active.
    try{
      const detail=await jsonRequest(`/api/v1/reviews/${completingSession}`);
      if(detail.session?.status==='completed'&&sessionId===completingSession){applyReviewCompleted();closeReviewExit();toast('Review completion confirmed after reconnecting.');return true}
    }catch(_ignored){}
    toast('Could not confirm review completion: '+safeErrorMessage(e)+' Try again; the review remains available in history.');
    return false;
  }finally{finishingReview=false;$('#confirmFinishReview').disabled=false;$('#leaveReviewOpen').disabled=false}
}
$('#completeReview').onclick=()=>openReviewExit('finish');
$('#startAnotherReview').onclick=()=>openReviewExit('new');
$('#closeReviewExit').onclick=closeReviewExit;
$('#keepReviewing').onclick=closeReviewExit;
$('#reviewExitOverlay').onclick=e=>{if(e.target.id==='reviewExitOverlay')closeReviewExit()};
$('#leaveReviewOpen').onclick=()=>{if(finishingReview)return;closeReviewExit();newReviewHome('Choose a new review. Your earlier review remains open in history.',true)};
$('#confirmFinishReview').onclick=async()=>{const startAnother=reviewExitIntent==='new';if(await finishReview()&&startAnother)newReviewHome()};
let disputePath='',disputeFindingId=null,challengeInFlight=false,challengeSpinnerTimer=null,challengeSlowTimer=null;
function beginChallengeProgress(){
  challengeInFlight=true;
  const submit=$('#submitEvidenceDispute'),status=$('#challengeProgress');
  submit.disabled=true;$('#cancelEvidenceDispute').textContent='Close while waiting';
  $('#closeEvidenceDispute').setAttribute('aria-label','Close dialog; challenge continues');
  $('#evidenceDisputePath').disabled=true;$('#evidenceDisputeExplanation').disabled=true;
  document.querySelectorAll('input[name="evidenceDisputeKind"]').forEach(input=>input.disabled=true);
  status.textContent='';status.classList.add('hidden');
  challengeSpinnerTimer=setTimeout(()=>{submit.classList.add('challenge-working');status.textContent='Studio is sending your challenge and waiting for a response.';status.classList.remove('hidden')},450);
  challengeSlowTimer=setTimeout(()=>{status.textContent='Still waiting for a response. Please do not submit the challenge again.';status.classList.remove('hidden')},5000);
}
function endChallengeProgress(){
  clearTimeout(challengeSpinnerTimer);clearTimeout(challengeSlowTimer);
  challengeSpinnerTimer=null;challengeSlowTimer=null;challengeInFlight=false;
  $('#submitEvidenceDispute').classList.remove('challenge-working');$('#submitEvidenceDispute').disabled=false;
  $('#cancelEvidenceDispute').textContent='Cancel';$('#closeEvidenceDispute').setAttribute('aria-label','Close challenge');
  $('#evidenceDisputePath').disabled=false;$('#evidenceDisputeExplanation').disabled=false;
  document.querySelectorAll('input[name="evidenceDisputeKind"]').forEach(input=>input.disabled=false);
  $('#challengeProgress').textContent='';$('#challengeProgress').classList.add('hidden');
}
function disputeKind(){return document.querySelector('input[name="evidenceDisputeKind"]:checked')?.value||'interpretation'}
function clearDisputeError(){const error=$('#evidenceDisputeError');error.textContent='';error.classList.add('hidden');$('#evidenceDisputePath').removeAttribute('aria-invalid');$('#evidenceDisputeExplanation').removeAttribute('aria-invalid')}
function showDisputeError(message,field){const error=$('#evidenceDisputeError');error.textContent=message;error.classList.remove('hidden');field.setAttribute('aria-invalid','true');field.focus()}
function updateDisputeKind(){const evidence=disputeKind()==='evidence';$('#evidenceDisputePathGroup').classList.toggle('hidden',!evidence);$('#submitEvidenceDispute').textContent=evidence?'Ask Maya to re-check →':'Ask reviewer to reconsider →';clearDisputeError()}
document.querySelectorAll('input[name="evidenceDisputeKind"]').forEach(input=>input.onchange=updateDisputeKind);
function openEvidenceDispute(path='',findingId=null){if(!sessionId){toast('Begin or resume a review first.');return}if(challengeInFlight){toast('Your earlier challenge is still being reviewed. Please wait for its response.');return}disputePath=path||'';disputeFindingId=findingId||null;$('#evidenceDisputePath').value=disputePath;$('#evidenceDisputeExplanation').value='';document.querySelector(`input[name="evidenceDisputeKind"][value="${path?'evidence':'interpretation'}"]`).checked=true;updateDisputeKind();$('#evidenceDisputeOverlay').classList.remove('hidden');setTimeout(()=>$('#evidenceDisputeExplanation').focus(),30)}
function closeEvidenceDispute(){$('#evidenceDisputeOverlay').classList.add('hidden');if(challengeInFlight){toast('The challenge is still running. The Review Room will open when the response arrives.');return}disputePath='';disputeFindingId=null}
$('#closeEvidenceDispute').onclick=closeEvidenceDispute;$('#cancelEvidenceDispute').onclick=closeEvidenceDispute;$('#evidenceDisputeOverlay').onclick=e=>{if(e.target.id==='evidenceDisputeOverlay')closeEvidenceDispute()};
$('#submitEvidenceDispute').onclick=async()=>{
  if(pending||challengeInFlight)return;
  const path=$('#evidenceDisputePath').value.trim();
  const explanation=$('#evidenceDisputeExplanation').value.trim();
  clearDisputeError();
  if(!explanation){showDisputeError('Explain what you want the reviewer to reconsider.',$('#evidenceDisputeExplanation'));return}
  if(disputeKind()==='evidence'&&!path){showDisputeError('Enter the real repository path Maya should check, or choose “I disagree with the interpretation.”',$('#evidenceDisputePath'));return}
  const fid=disputeFindingId;
  if(disputeKind()==='evidence'){
    await disputeEvidence(path,explanation,fid);
    return;
  }
  const finding=(currentEvidence?.findings||[]).find(item=>String(item.id)===String(fid));
  if(!finding){showDisputeError('This finding is no longer in the current snapshot. Close this dialog and reload Engineering Evidence.',$('#evidenceDisputeExplanation'));return}
  const submit=$('#submitEvidenceDispute');
  beginChallengeProgress();
  submit.textContent='The reviewer is considering your challenge…';
  try{
    const result=await send({text:`I challenge the finding “${finding.title}”: ${explanation}`,evidenceRefs:[`FINDING:${fid}`,...(finding.evidence_refs||[])]});
    endChallengeProgress();
    if(result){closeEvidenceDispute();switchView('studio');if(result!==true)showSubmittedExchange(result)}
    else{$('#evidenceDisputeOverlay').classList.remove('hidden');showDisputeError('Studio could not confirm this challenge. Your explanation is still here; wait a moment and try again.',$('#evidenceDisputeExplanation'))}
  }catch(e){
    $('#evidenceDisputeOverlay').classList.remove('hidden');
    showDisputeError('Studio could not complete the challenge. Your explanation is still here; try again.',$('#evidenceDisputeExplanation'));
  }finally{if(challengeInFlight)endChallengeProgress();submit.textContent='Ask reviewer to reconsider →'}
};

async function disputeEvidence(path,explanation,findingId=null){
  if(!sessionId||pending||challengeInFlight)return;
  const submit=$('#submitEvidenceDispute');

  const body={
    path,
    explanation,
    finding_id:findingId,
  };

  const mutation=reviewMutationRequest(
    'evidence_dispute',
    sessionId,
    body
  );

  body.client_turn_id=mutation.id;
  beginChallengeProgress();
  submit.textContent='Maya is checking the frozen snapshot…';

  setPending(
    true,
    'Maya is re-checking that evidence against the frozen snapshot…'
  );

  try{
    const r=await fetch(
      `/api/v1/reviews/${sessionId}/evidence-dispute`,
      {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify(body),
      }
    );

    const responseBody=await r.json();

    if(!r.ok){
      throw new Error(responseBody.detail||r.statusText);
    }

    const studentTurn=addTurn(
      'student',
      'evidence_dispute',
      `I think the board should reconsider ${path}: ${explanation}`
    );

    const reply=responseBody.reply;

    addTurn(
      'reviewer',
      reply.lens,
      reply.text,
      {
        reviewer:reply.reviewer,
        kind:reply.kind
      }
    );

    if(responseBody.duplicate){
      toast(
        'Your earlier evidence dispute had already been recorded. '
        +'The review response was recovered.'
      );
    }else{
      toast(
        'Evidence dispute recorded. The review record keeps both '
        +'the original finding and the correction.'
      );
    }

    clearReviewMutation(mutation);
    endChallengeProgress();
    closeEvidenceDispute();
    showSubmittedExchange(studentTurn);

  }catch(e){
    endChallengeProgress();
    // Keep the overlay and its exact path/explanation open. If the server
    // committed before delivery failed, retrying this unchanged form will
    // reuse the same client_turn_id and recover the original result.
    toast(e.message);

    $('#evidenceDisputeOverlay').classList.remove('hidden');

    if($('#evidenceDisputePath').value!==path){
      $('#evidenceDisputePath').value=path;
    }

    if($('#evidenceDisputeExplanation').value!==explanation){
      $('#evidenceDisputeExplanation').value=explanation;
    }

    disputePath=path;
    disputeFindingId=findingId;

  }finally{
    if(challengeInFlight)endChallengeProgress();
    setPending(false);
    submit.disabled=false;
    submit.textContent='Ask Maya to re-check →';
  }
}

async function loadHistory(){
  try{
    const seed=await ensureDemo(),
      sc=studentContext?.sections?.[0],
      teamId=sc?.team?.id||seed.team_id,
      userId=studentContext?.user?.id||seed.user_id,
      d=await fetch(`/api/v1/reviews?team_id=${teamId}&user_id=${userId}&limit=6`).then(r=>r.json()),
      box=$('#reviewHistory');

    if(!d.sessions.length){
      box.innerHTML='<span class="quiet">No review sessions yet.</span>';
      return;
    }

    box.innerHTML=d.sessions.map(s=>{
      const selected=Number(s.id)===Number(sessionId);
      const state=s.status==='active'?(selected?'Current review':'Saved for later'):
        s.status==='completed'?'Completed':String(s.status||'historical').replaceAll('_',' ');
      const progress=
        s.committed
          ?'Recommendation stated'
          :s.evaluation?.disposition
            ?humanizeDisposition(s.evaluation.disposition)
            :s.status==='active'
              ?'Awaiting your first response'
              :'Opening challenge presented';

      return `<button class="history-item${selected?' current-review':''}" data-session="${s.id}" ${selected?'aria-current="true"':''}><span><b>${escapeHtml(s.phase_id)} · Session #${s.id}</b><small>${new Date(s.started_at).toLocaleString()}</small></span><span class="history-state ${escapeHtml(s.status)}">${escapeHtml(state)}</span><span>${escapeHtml(progress)}</span></button>`;
    }).join('');

    $$('.history-item').forEach(
      b=>b.onclick=()=>resumeSession(Number(b.dataset.session))
    );

  }catch(e){
    console.error('Review history could not be refreshed',e);
  }
}
$('#viewAllHistory').onclick=()=>switchView('history');
function refreshHistorySelection(){
  for(const box of [$('#reviewHistory'),$('#reviewHistoryPage')]){
    if(!box)continue;
    box.querySelectorAll('.history-item').forEach(row=>{
      const selected=!!sessionId&&Number(row.dataset.session)===Number(sessionId);
      row.classList.toggle('current-review',selected);
      if(selected)row.setAttribute('aria-current','true');else row.removeAttribute('aria-current');
      const badge=row.querySelector('.history-state.active');
      if(badge)badge.textContent=selected?'Current review':'Saved for later';
    });
  }
}
function reviewHistoricalPresentation(status,id){
 if(status==='archived_incomplete')return {purpose:'Archived semester · incomplete review · read-only',label:'Archived semester · incomplete review · read-only',detail:`Session #${id} · archive ended the active review; frozen evidence and conversation preserved`,toast:'Archived incomplete review opened read-only. The semester ended this session before normal completion; its original frozen evidence and conversation are preserved.'};
 if(status==='completed')return {purpose:'Completed session · read-only',label:'Review complete · read-only',detail:`Session #${id} · preserved history`,toast:'Review complete and read-only. Start another review when your team is ready.'};
 const human=String(status||'historical').replaceAll('_',' ');
 return {purpose:`${human} · read-only`,label:`${human} · read-only`,detail:`Session #${id} · preserved history`,toast:'Historical review opened read-only against its original frozen evidence snapshot.'}
}
async function resumeSession(id,opts={}){try{const r=await fetch(`/api/v1/reviews/${id}`),d=await r.json();if(!r.ok)throw new Error(d.detail||r.statusText);switchView('studio',{history:false});sessionId=id;reviewSnapshotId=d.snapshot?.id||null;if(opts.history!==false)recordNavigationState();clearEntryContext();setComposerContext(null);const active=d.session.status==='active',historical=active?null:reviewHistoricalPresentation(d.session.status,id);document.body.classList.toggle('review-session-active',active);els.phase.disabled=active;$('#reviewCompletionSummary').classList.add('hidden');const modeName=String(d.session.mode||'board_review');const label=modeName.includes('focused')?'Focused Review':modeName.includes('finding')?'Finding Review':'Board Review';$('#reviewSessionPurpose').innerHTML=`<div><b>${label} · ${d.session.phase_id}</b><span>${active?'Resumed':historical.purpose} against its original frozen evidence snapshot.</span></div>`;$('#reviewSessionPurpose').classList.remove('hidden');$('#reviewHomeButton').classList.remove('hidden');$('#reviewHomeButton').textContent='Start another review';currentPhase=d.session.phase_id;const opt=[...els.phase.options].find(o=>o.value.startsWith(currentPhase));if(opt)els.phase.value=opt.value;applyPhase();els.transcript.innerHTML='';currentChallenge=d.state.challenge||null;if(currentChallenge)renderChallengeBrief(currentChallenge);if(d.evidence){renderEvidence(d.evidence);renderStrengths(d.evidence)}d.turns.forEach(t=>addTurn(t.actor,t.lens,t.content,{...t.signals,reviewer:t.signals?.reviewer,guidance_refs:t.signals?.guidance_refs}));$('#challengeTitle').textContent=d.state.challenge?.title||'Review session';committed=!!d.state.committed_position;reviewMode=modeName.includes('focused')?'focused':modeName.includes('finding')?'finding':'board';els.decision.value='';$('#postureMeaning').textContent=postureMeanings[''];setMode('ask');$('#reviewStatus').classList.toggle('hidden',!active);$('#conversationControls').classList.toggle('hidden',!active);$('#conversationReadyNote')?.classList.toggle('hidden',!active);$('#reviewStatusText').textContent=active?`${currentPhase} · Reviewing a frozen repository snapshot. After changing your work, start a new review.`:historical.detail;updateRecommendationBar(d.state.evaluation,d.state.reasoning_state||{});if(!active){hideActiveReviewer();$('#challengeBrief').classList.remove('hidden');$('#reviewStatus').classList.remove('hidden');$('#reviewStatusLabel').textContent=historical.label;$('#reviewStatusText').textContent=historical.detail;}else{$('#reviewCompletionSummary').classList.add('hidden')}$('#reviewHomeButton').classList.toggle('hidden',active||d.session.status==='completed');if(d.session.status==='completed')renderReviewCompletionSummary();els.send.disabled=!active;refreshHistorySelection();updateStartReviewButton();if(active)restoreDraft();requestAnimationFrame(()=>window.scrollTo({top:0,behavior:'auto'}));toast(active?'Review resumed with its original frozen evidence snapshot.':historical.toast)}catch(e){toast(safeErrorMessage(e,'Could not open that review session.'))}}

const evidenceLensIds={
 A1:['business_value','governability','ai_governance','traceability','accountability','uncertainty','compliance','maintainability'],
 A2:['business_value','cost_time','traceability','accountability','uncertainty','technical_debt','sustainability'],
 A3:['reliability','availability','performance','scalability','security','privacy','maintainability','governability','reversibility','blast_radius'],
 A4:['reliability','security','maintainability','traceability','ai_governance','technical_debt','accountability'],
 A5:['reliability','operability','traceability','accountability','uncertainty','blast_radius','governability'],
 A6:['availability','serviceability','recoverability','security','privacy','operability','observability','governability','sustainability','accountability']
};
const lensTerms={
 business_value:['value','stakeholder','user','purpose','scope'],cost_time:['estimate','schedule','cost','time','milestone','planning'],reliability:['reliab','correct','failure','test'],availability:['availab','downtime','service'],serviceability:['diagnos','support','repair','runbook'],recoverability:['recover','rollback','restore','incident'],performance:['perform','latency','throughput'],scalability:['scale','growth','capacity'],security:['security','permission','auth','threat','secret'],privacy:['privacy','data handling','sensitive','retention'],compliance:['policy','governance','approval','course constraint'],maintainability:['maintain','review','dependency','architecture'],operability:['operation','runbook','runtime','support'],observability:['observ','metric','log','runtime'],governability:['govern','decision','escalat','approval','working agreement'],ai_governance:['ai','model','verification','human review'],traceability:['trace','requirement','issue','pull request','commit'],accountability:['role','owner','accountab','responsib'],uncertainty:['uncertain','assumption','open question','risk'],reversibility:['rollback','revers','change course'],blast_radius:['impact','affected','failure','risk'],technical_debt:['debt','defer','shortcut','future cost'],sustainability:['supportable','steward','sustain','long-term']
};
function currentTeamId(){return studentContext?.sections?.[0]?.team?.id||demoContext?.team_id||null}
function evidenceHay(item){return [item.title,item.detail,item.scope_reason,item.equivalent_path,item.status,item.quality,item.source_provenance].filter(Boolean).join(' ').toLowerCase()}
function findingHay(f){return [f.title,f.statement,f.significance,f.category,...(f.evidence_refs||[])].filter(Boolean).join(' ').toLowerCase()}
function relatedToLens(obj,dimension){const terms=[dimension.label,dimension.question,...(lensTerms[dimension.id]||[])].join(' ').toLowerCase().match(/[a-z0-9_-]{4,}/g)||[];const hay=obj.evidence_refs?findingHay(obj):evidenceHay(obj);return terms.some(t=>hay.includes(t.replace(/[^a-z0-9]/g,''))||hay.includes(t))}
function evidenceCondition(item){return item.condition||{key:'unknown',label:'Check evidence',why:'The condition of this evidence has not been assessed here.',next_step:'Inspect the frozen source and ask the reviewer what it supports.'}}
function evidenceStatusLabel(item){return evidenceCondition(item).label}
function evidenceStatusClass(item){return ({gap:'bad',concern:'warn',unknown:'warn',explore:'neutral',verify:'neutral',strong:'good',okay:'neutral'})[evidenceCondition(item).key]||'warn'}
async function configureFocusedFromEvidence(focus,path=''){
  if(pending||finishingReview){toast('Wait for the current reviewer response to finish.');return}
  if(sessionId&&document.body.classList.contains('review-session-active')){
    switchView('studio');
    if(els.response.value.trim()){
      els.response.focus();
      requestAnimationFrame(()=>els.response.scrollIntoView({block:'center',behavior:'smooth'}));
      toast('Your draft is still here. Send or clear it before asking about another artifact.');
      return;
    }
    setMode('ask');
    if(path)setComposerContext({kind:'evidence',path,label:path,detail:'Selected from Engineering Evidence'});
    els.response.value=`I want your honest senior-engineer opinion about ${path||focus}. What is strong, weak, unclear, or worth improving before we move on?`;
    updateDraftHint();
    const sending=send();
    requestAnimationFrame(()=>els.transcript.scrollIntoView({block:'center',behavior:'smooth'}));
    await sending;
    return;
  }
  if(sessionId)newReviewHome();
  prepareEntryContext({source_view:'engineering_evidence',entry_intent:'review',focus,path});
  switchView('studio');
  await selectReviewMode('focused');
  $('#reviewFocus').value=focus;
  updateReviewModeSummary();
  $('#reviewSessionPurpose').innerHTML=`<div><b>Starting artifact review</b><span>${escapeHtml(path||focus)}</span></div>`;
  $('#reviewSessionPurpose').classList.remove('hidden');
  startReviewAction();
}
async function configureFindingFromEvidence(fid,intent='discuss',source='engineering_evidence'){
  if(pending||finishingReview){toast('The current review action is still completing. Try again in a moment.');return}
  const f=currentFindingById(fid);
  if(!f){toast('That finding is not available in the current frozen snapshot. Refresh Engineering Evidence and try again.');return}
  if(sessionId&&document.body.classList.contains('review-session-active')){await actOnFinding(f,intent,source);return}
  if(sessionId)newReviewHome();
  const findings=engineeringEvidenceData?.findings||currentEvidence?.findings||[];
  const available=findings.some(x=>String(x.id)===String(fid))?findings:[f,...findings];
  selectedFindingIds.clear();selectedFindingIds.add(fid);
  prepareEntryContext({source_view:source,entry_intent:intent,finding_ids:[fid],finding_id:fid,title:f.title});
  switchView('studio');
  await selectReviewMode('finding',{findings:available});
  const cb=$(`#findingPicker input[value="${CSS.escape(fid)}"]`);
  if(!cb){
    selectedFindingIds.clear();updateReviewModeSummary();
    toast('The selected finding could not be placed in the review picker. Refresh Engineering Evidence and try again.');
    return;
  }
  cb.checked=true;
  cb.closest('.finding-pick')?.classList.add('selected');
  updateReviewModeSummary();
  const action=intent==='resolve'?'Help resolve':intent==='challenge'?'Challenge':'Discuss';
  $('#reviewSessionPurpose').innerHTML=`<div><b>Starting ${escapeHtml(action)} Finding Review</b><span>${escapeHtml(f.title)}</span></div>`;
  $('#reviewSessionPurpose').classList.remove('hidden');
  requestAnimationFrame(()=>window.scrollTo({top:0,behavior:'auto'}));
  startReviewAction();
}
function renderEvidenceLensDetail(dimension,evidence){activeEvidenceLens=dimension.id;$$('.mcard').forEach(c=>c.classList.toggle('selected',c.dataset.lens===dimension.id));const items=(evidence.items||[]).filter(x=>relatedToLens(x,dimension));const findings=(evidence.findings||[]).filter(x=>relatedToLens(x,dimension));const box=$('#evidenceLensDetail');box.classList.remove('hidden');box.innerHTML=`<div class="lens-detail-head"><div><span class="eyebrow">${escapeHtml(dimension.label.toUpperCase())}</span><h3>${escapeHtml(dimension.question)}</h3><p>${items.length} related evidence item(s) · showing ${Math.min(findings.length,6)} of ${findings.length} related finding(s) in the frozen ${escapeHtml(evidence.phase_id)} snapshot. The complete finding list is below.</p></div><button class="primary compact" id="focusLensReview">Ask the Board about ${escapeHtml(dimension.label)}</button></div><div class="lens-detail-grid"><div><b>Related evidence</b>${items.slice(0,8).map(x=>`<span class="lens-evidence ${evidenceStatusClass(x)}">${escapeHtml(evidenceStatusLabel(x))} · ${escapeHtml(x.equivalent_path||x.title)}</span>`).join('')||'<span class="quiet">No direct evidence relationship was identified in this snapshot. That may itself be worth asking about.</span>'}</div><div><b>Related findings</b>${findings.slice(0,6).map(f=>`<button class="lens-finding" data-finding="${escapeHtml(f.id)}">${escapeHtml((f.lifecycle?.status||'open').replaceAll('_',' '))} · ${escapeHtml(f.title)}</button>`).join('')||'<span class="quiet">No current board finding is tied to this lens.</span>'}</div></div>`;$('#focusLensReview').onclick=()=>configureFocusedFromEvidence(`${dimension.label}: ${dimension.question}`);$$('.lens-finding').forEach(b=>b.onclick=()=>configureFindingFromEvidence(b.dataset.finding,'discuss','engineering_evidence_lens'));box.scrollIntoView({behavior:'smooth',block:'nearest'})}
function snapshotCaptureLabel(value){if(!value)return 'capture time unavailable';const stamped=/Z$|[+-]\d{2}:\d{2}$/.test(value)?value:`${value}Z`;const date=new Date(stamped);return Number.isNaN(date.getTime())?'capture time unavailable':date.toLocaleString()}
function renderEngineeringEvidence(evidence,payload){engineeringEvidenceData=evidence;const title=$('#evidenceWorkspaceTitle'),meta=$('#evidenceWorkspaceMeta');title.textContent=`${evidence.phase_id} · ${phaseQuestions[evidence.phase_id]||'Current phase'}`;meta.textContent=`${payload.team?.project_name||payload.team?.name||'Team project'} · saved snapshot #${payload.snapshot_id??'—'} · ${snapshotCaptureLabel(payload.created_at)} · commit ${String(evidence.commit_sha||'').slice(0,8)||'local'} · ${evidence.coverage??'—'}% expected-evidence coverage (not a quality score)`;const sameActive=!!sessionId&&document.body.classList.contains('review-session-active');const snapshotNote=sameActive&&Number(reviewSnapshotId)===Number(payload.snapshot_id)?'This saved snapshot is used by your active review.':sameActive?'This is the latest saved team snapshot. Your active review keeps its original frozen snapshot; open the Review Room to inspect that conversation.':'Saved evidence from an earlier analysis, not a live scan. Start a new review to check current repository work.';const omitted=evidence.semantic_review?.inspection?.omitted_artifact_count||0;$('#evidenceSnapshotNote').textContent=`Saved ${snapshotCaptureLabel(payload.created_at)} · commit ${String(evidence.commit_sha||'').slice(0,8)||'local'}. ${snapshotNote}`+(omitted?` The semantic reviewer sampled excerpts from ${evidence.semantic_review.inspection.inspected_artifact_count} artifacts; ${omitted} artifacts were outside its context. Point the reviewer to a specific file if something was missed.`:'');
 updateEvidenceReviewActions();
 const items=evidence.items||[],findings=evidence.findings||[];
 const count=key=>items.filter(x=>evidenceCondition(x).key===key).length;
 $('#engineeringEvidenceSummary').innerHTML=`<div><b>${count('gap')}</b><span>Areas needing work or missing</span></div><div><b>${count('concern')}</b><span>Evidence areas with concerns</span></div><div><b>${count('unknown')+count('verify')+count('explore')}</b><span>Areas to check or cannot judge</span></div><div><b>${count('strong')+count('okay')}</b><span>Areas with supported claims</span></div>`;
 $('#evidenceFindingCount').textContent=`(${findings.length} ${findings.length===1?'finding':'findings'})`;
 const priority={gap:0,concern:1,unknown:2,verify:3,explore:4,okay:5,strong:6};
 const ordered=[...items].sort((a,b)=>(priority[evidenceCondition(a).key]??5)-(priority[evidenceCondition(b).key]??5));
 const ranked=(evidence.challenge_candidates||[]).map(f=>f.id);
 const first=ordered.find(x=>evidenceCondition(x).key==='concern'&&ranked.includes(evidenceCondition(x).finding_id))||ordered[0],state=first&&evidenceCondition(first);
 $('#evidenceNextAction').innerHTML=payload.preparation?preparationHTML(payload.preparation):(first?`<b>Start here: ${escapeHtml(evidenceActualPath(first))}</b><span>${escapeHtml(state.why)} ${escapeHtml(state.next_step)}</span><small>Review the evidence area below. A concern can be challenged with stronger frozen evidence.</small>`:'<b>No phase evidence areas are available in this snapshot.</b><span>Ask the reviewer what evidence would make the current engineering claim reviewable.</span>');
 const supported=items.filter(x=>['strong','okay'].includes(evidenceCondition(x).key));
 $('#evidenceSupportedSection').classList.toggle('hidden',!supported.length);
 $('#engineeringEvidenceStrengths').innerHTML=supported.map(x=>{const condition=evidenceCondition(x),support=condition.support||{};return `<div class="strength-card"><span>•</span><p><b>${escapeHtml(condition.label)} · ${escapeHtml(x.title)}</b><br>${escapeHtml(support.claim||'')}<br><small>${support.support_kind==='demonstrated'?'Decision or use visible':'Approach defined; use not established'} in the bounded excerpt at ${escapeHtml(support.support_path||'the frozen source')} · Boundary: ${escapeHtml(support.limitation||'Review the cited excerpt.')}</small></p></div>`}).join('')||'<p class="quiet">No phase claim has bounded support in this snapshot. Starter files and adapted locations are useful places to work, but do not establish what the team decided or demonstrated. Start with the concern above or ask the reviewer for help.</p>';
 const dims=(courseModel?.course?.judgment_dimensions||[]).filter(x=>(evidenceLensIds[evidence.phase_id]||[]).includes(x.id));const matrix=$('#evidenceMatrix');matrix.innerHTML='';dims.forEach(x=>{const related=items.filter(i=>relatedToLens(i,x)),attention=findings.filter(f=>relatedToLens(f,x)&&!['corrected','resolved'].includes(f.lifecycle?.status));const c=document.createElement('button');c.className='mcard';c.dataset.lens=x.id;c.innerHTML=`<div class="lens-card-head"><b>${escapeHtml(x.label)}</b><span class="lens-count ${attention.length?'warn':'good'}">${attention.length?attention.length+' to discuss':related.length+' evidence'}</span></div><p>${escapeHtml(x.question)}</p><span>View Evidence →</span>`;c.onclick=()=>renderEvidenceLensDetail(x,evidence);matrix.appendChild(c)});
 const renderInventory=()=>{const show=$('#showOutOfScopeEvidence').checked;const visible=ordered.filter(x=>show||x.phase_scope!=='OUT_OF_SCOPE');$('#engineeringEvidenceInventory').innerHTML=visible.map(x=>{const path=evidenceActualPath(x),art=(evidence.artifacts||[]).find(a=>a.path===path),condition=evidenceCondition(x),finding=condition.finding_id&&findings.find(f=>f.id===condition.finding_id);return `<article class="inventory-card ${evidenceStatusClass(x)}"><div><strong class="evidence-condition ${escapeHtml(condition.key)}">${escapeHtml(condition.label)}</strong></div><h4>${escapeHtml(path)}</h4><p>${escapeHtml(condition.why)}</p><p class="evidence-next-step"><b>Next:</b> ${escapeHtml(condition.next_step)}</p>${finding?`<small class="evidence-linked-finding">Related concern: ${escapeHtml(finding.title)}</small>`:''}<details class="evidence-card-details"><summary>Evidence context</summary>${condition.support?`<p><b>Phase claim:</b> ${escapeHtml(condition.support.claim)}</p><p><b>Frozen excerpt from ${escapeHtml(condition.support.support_path)}:</b></p><blockquote>${escapeHtml(condition.support.support_quote)}</blockquote>${(condition.support.corroborating_evidence||[]).map(r=>`<p><b>Corroborating frozen excerpt from ${escapeHtml(r.path)}:</b></p><blockquote>${escapeHtml(r.quote)}</blockquote>`).join('')}${condition.support.operating_evidence_quote?`<p><b>Operating record at ${escapeHtml(condition.support.operating_evidence_path)}:</b></p><blockquote>${escapeHtml(condition.support.operating_evidence_quote)}</blockquote>`:''}<p><b>Boundary:</b> ${escapeHtml(condition.support.limitation)} This is a bounded excerpt, not a verdict on the whole file or submission.</p>`:''}<p>${escapeHtml(x.detail||x.scope_reason||'')}</p><small>${escapeHtml((x.phase_scope||'CURRENT_PHASE').replaceAll('_',' '))} · ${escapeHtml((x.source_provenance||'UNKNOWN').replaceAll('_',' '))}</small></details><footer><button data-inspect-path="${escapeHtml(path)}" ${art?'':'disabled title="No exact frozen artifact is available"'}>Inspect frozen source</button>${finding?`<button data-condition-finding="${escapeHtml(finding.id)}">Discuss concern</button>`:`<button data-focus-path="${escapeHtml(path)}">Ask reviewer</button>`}</footer></article>`}).join('')||'<p class="quiet">No evidence items match this view.</p>';$$('[data-focus-path]').forEach(b=>b.onclick=()=>configureFocusedFromEvidence(`Review the evidence at ${b.dataset.focusPath}. Tell me honestly what it supports, where it is weak, and how to improve it.`,b.dataset.focusPath));$$('[data-condition-finding]').forEach(b=>b.onclick=()=>configureFindingFromEvidence(b.dataset.conditionFinding,'discuss','engineering_evidence'));$$('[data-inspect-path]').forEach(b=>b.onclick=()=>showArtifact(b.dataset.inspectPath,b.dataset.inspectPath))};$('#showOutOfScopeEvidence').onchange=renderInventory;renderInventory();
 $('#engineeringEvidenceFindings').innerHTML=findings.map(f=>{const st=f.lifecycle?.status||'open',path=findingPrimaryPath(f),art=(evidence.artifacts||[]).find(a=>a.path===path);return `<article class="evidence-finding-card ${escapeHtml(st)}" data-finding-card="${escapeHtml(f.id)}"><div><span class="provenance ${escapeHtml((f.provenance||'REVIEW').toLowerCase())}">${escapeHtml(f.provenance||'REVIEW')}</span><span class="finding-state">${escapeHtml(st.replaceAll('_',' '))}</span></div><h4>${escapeHtml(f.title||'Finding')}</h4><p>${escapeHtml(f.statement||f.significance||'')}</p><footer class="finding-card-actions"><button class="secondary compact" data-finding-discuss="${escapeHtml(f.id)}">Discuss</button><button class="secondary compact" data-finding-challenge="${escapeHtml(f.id)}">Challenge</button><button class="secondary compact" data-finding-resolve="${escapeHtml(f.id)}">Help me resolve this</button>${art?`<button class="text-button" data-finding-open="${escapeHtml(f.id)}">Open evidence ↗</button>`:''}</footer></article>`}).join('')||'<p class="quiet">No current findings. A strong team can still use Focused Review to challenge a decision or artifact.</p>';$$('[data-finding-discuss]').forEach(b=>b.onclick=()=>configureFindingFromEvidence(b.dataset.findingDiscuss,'discuss','engineering_evidence'));$$('[data-finding-challenge]').forEach(b=>b.onclick=()=>configureFindingFromEvidence(b.dataset.findingChallenge,'challenge','engineering_evidence'));$$('[data-finding-resolve]').forEach(b=>b.onclick=()=>configureFindingFromEvidence(b.dataset.findingResolve,'resolve','engineering_evidence'));$$('[data-finding-open]').forEach(b=>b.onclick=()=>{const f=currentFindingById(b.dataset.findingOpen),p=findingPrimaryPath(f);showArtifact(p,`Evidence for ${f?.title||'finding'}`)})
 const m=evidence.repository_metrics||{};const requirementsVisible=items.some(x=>String(x.title).toLowerCase().includes('requirements')&&!['gap'].includes(evidenceCondition(x).key));const chain=[['Intent / requirements',requirementsVisible?'artifact visible; inspect support':m.issue_count>0?'issues visible; inspect intent':'unclear'],['Work / Issues',m.issue_count>0?`${m.issue_count} issue(s)`:'no issues visible'],['Review / PRs',m.pr_count>0?`${m.pr_count} PR(s)`:'not expected or not visible'],['Validation / Actions',m.actions_runs>0?`${m.actions_runs} run(s)`:'not expected or not visible'],['Release baseline',m.tag_count>0?`${m.tag_count} tag(s)`:'later-phase / not visible']];$('#engineeringTraceability').innerHTML=chain.map((x,i)=>`<div class="trace-step"><span>${i+1}</span><b>${escapeHtml(x[0])}</b><small>${escapeHtml(String(x[1]))}</small></div>`).join('<i>→</i>')}
function updateEvidenceReviewActions(){const active=!!sessionId&&document.body.classList.contains('review-session-active');const start=$('#startBoardFromEvidence'),open=$('#backToStudio'),hint=$('#evidenceActionHint');start.textContent=active?'Return to active review':sessionId?'Start another review':'Choose Board Review →';open.classList.toggle('hidden',active);if(hint)hint.textContent=active?'Return to the Review Room to continue talking. Concern actions discuss, challenge, or resolve a specific finding in this active review.':sessionId?'Start another review opens a fresh setup using the current repository state.':'Board Review opens setup. Discuss, Challenge, or Help me resolve this starts a review of that saved concern.';start.onclick=()=>{if(active){switchView('studio');return}if(sessionId){newReviewHome();return}switchView('studio');selectReviewMode('board');requestAnimationFrame(()=>window.scrollTo({top:0,behavior:'auto'}));toast('Board Review selected. Use Start Board Review in the Review Room to begin.')}}
async function loadEngineeringEvidence(){const status=$('#evidenceWorkspaceStatus'),workspace=$('#evidenceWorkspace');status.classList.remove('hidden');workspace.classList.add('hidden');const readiness=studentReviewReadiness();if(appRole==='student'&&!readiness.ready){if(readiness.code==='phase'){status.innerHTML=`<div><b>${escapeHtml(currentPhase)} Engineering Evidence is not available yet.</b><span>${escapeHtml(readiness.detail)}</span></div>`;return}status.innerHTML=`<div><b>Finish setup before Engineering Evidence can be prepared.</b><span>${escapeHtml(readiness.detail)}</span></div><button class="primary compact" id="evidenceOpenSetup">Open My Team</button>`;$('#evidenceOpenSetup').onclick=()=>switchView('myteam');return}try{const teamId=currentTeamId();if(!teamId){status.innerHTML='<span>No team context is available yet.</span>';return}let phase=currentPhase;const r=await fetch(`/api/v1/reviews/evidence/current?team_id=${teamId}&phase_id=${encodeURIComponent(phase)}`),d=await r.json();if(!r.ok)throw new Error(d.detail||r.statusText);if(!d.available){status.innerHTML=`<div><b>No frozen ${escapeHtml(phase)} evidence snapshot yet.</b><span>Choose Board Review in the Review Room, then start it to prepare repository evidence.</span></div><button class="primary compact" id="evidenceStartFirstReview">Choose Board Review →</button>`;$('#evidenceStartFirstReview').onclick=()=>{switchView('studio');selectReviewMode('board');requestAnimationFrame(()=>window.scrollTo({top:0,behavior:'auto'}));};return}engineeringEvidenceData=d.evidence;engineeringSnapshotId=d.snapshot_id;status.classList.add('hidden');workspace.classList.remove('hidden');renderEngineeringEvidence(d.evidence,d)}catch(e){status.innerHTML=`<div><b>Engineering Evidence could not be loaded.</b><span>${escapeHtml(e.message)}</span></div>`}}

updateEvidenceReviewActions();
$('#inspectCurrentConcern').onclick=()=>{const art=currentConcernArtifact();if(art)showArtifact(art.path,art.path);else switchView('evidence')};
$('#browseReviewEvidence').onclick=()=>switchView('evidence');
$('#backToStudio').onclick=()=>switchView('studio');
async function loadInstructor(){try{const setup=await adminSetupData();fillSectionSelectors(setup);const d=await jsonRequest(`/api/v1/instructor/overview${instructorSectionQuery()}`,{},'Instructor intelligence could not be loaded.');const sig=d.class_signals||{},u=d.ai_usage||{};$('#classSignals').innerHTML=`<div><b>${sig.students??0}</b><span>Students</span></div><div><b>${sig.teams??0}</b><span>Teams</span></div><div><b>${sig.repositories_connected??0}</b><span>Repositories</span></div><div><b>${sig.teams_needing_attention??0}</b><span>Need attention</span></div><div><b>${sig.active_reviews??0}</b><span>Active reviews</span></div><div><b>${sig.review_sessions??0}</b><span>Review sessions</span></div>`;$('#aiUsageMetrics').innerHTML=`<div><b>${formatEstimatedCost(u.estimated_cost_usd)}</b><span>Estimated cost</span></div><div><b>${Number(u.input_tokens||0).toLocaleString()}</b><span>Input tokens</span></div><div><b>${Number(u.cached_input_tokens||0).toLocaleString()}</b><span>Cached input</span></div><div><b>${Number(u.output_tokens||0).toLocaleString()}</b><span>Output tokens</span></div><div><b>${Math.round(Number(u.cache_hit_ratio||0)*100)}%</b><span>Cache hit</span></div><div><b>${u.calls?`${(Number(u.avg_latency_ms||0)/1000).toFixed(1)}s`:'—'}</b><span>Avg response</span></div><div><b>${Number(u.calls||0).toLocaleString()}</b><span>Model calls</span></div>`;const box=$('#teamCards');box.innerHTML='';d.teams.forEach(t=>{const c=document.createElement('button');c.className=`teamcard ${t.attention}`;c.dataset.team=t.id;const context=[t.section?.display_name,teamIdentifierLabel(t.team_key)].filter(Boolean).join(' · ');c.innerHTML=`<div class="team-name"><span class="attention-dot"></span><div><b>${escapeHtml(t.name)}</b><small>${escapeHtml(t.project)}</small><small class="team-card-context">${escapeHtml(context)}</small></div></div><div><small>Phase</small><b>${t.phase}</b></div><div><small>Evidence</small><b>${t.evidence_coverage==null?'Not scanned':t.evidence_coverage+'%'}</b></div><div><small>AI cost</small><b>${formatEstimatedCost(t.ai_usage?.estimated_cost_usd)}</b></div><span class="inspect">Inspect →</span>`;c.onclick=()=>loadTeamDetail(t.id,{focus:true,history:true});box.appendChild(c)});if(d.teams.length){const selected=currentInstructorTeamId&&d.teams.some(t=>Number(t.id)===Number(currentInstructorTeamId))?currentInstructorTeamId:d.teams[0].id;loadTeamDetail(Number(selected))}else{$('#teamDetail').classList.add('hidden');currentInstructorTeamId=null}}catch(e){console.error(e);$('#teamCards').innerHTML='<div class="error-card">Could not load instructor overview.</div>'}}
$('#refreshInstructor').onclick=loadInstructor;
async function loadTeamDetail(teamId,opts={}){
  const box=$('#teamDetail');

  try{
    $$('.teamcard').forEach(
      c=>c.classList.toggle(
        'selected',
        Number(c.dataset.team)===teamId
      )
    );

    const d=await jsonRequest(
      `/api/v1/instructor/teams/${teamId}`,
      {},
      'Team detail could not be loaded.'
    );

    box.classList.remove('hidden');
    currentInstructorTeamId=teamId;
    if(opts.history)recordNavigationState();

    const ev=d.evidence,
      gaps=ev?.items?.filter(x=>x.status!=='present')||[],
      activeReviews=d.active_sessions||[],
      sectionContext=[d.team.section?.display_name,teamIdentifierLabel(d.team.team_key)].filter(Boolean).join(' · '),
      activeReviewControls=activeReviews.length?`<div class="team-active-reviews"><span>ACTIVE REVIEWS</span>${activeReviews.map(r=>`<button type="button" class="secondary compact" data-team-active-review="${r.id}">${escapeHtml(r.student?.name||'Student')} · ${escapeHtml(r.phase)} ${escapeHtml(String(r.mode||'review').replaceAll('_',' '))} →</button>`).join('')}</div>`:'';

    box.innerHTML=
      `<div class="detail-head"><div><span class="eyebrow">TEAM DETAIL</span><div class="team-detail-context">${escapeHtml(sectionContext)}</div><h2>${escapeHtml(d.team.name)} · ${escapeHtml(d.team.project)}</h2><p>${escapeHtml(d.team.repo||'Repository not connected')}</p></div><div class="detail-head-actions">${activeReviewControls}${d.team.repo&&canManageSectionUi()?'<button id="resetTeamRepository" class="secondary compact">Reset repository onboarding</button>':''}</div></div><div class="detail-grid"><div class="detail-section"><h3>People & accountability</h3><div class="member-list">${d.members.map(m=>`<div><span class="avatar small-avatar">${initials(m.name)}</span><span><b>${escapeHtml(m.name)}</b><small>${escapeHtml(m.role)} · ${m.github_login?'@'+escapeHtml(m.github_login):'GitHub not linked'}</small></span></div>`).join('')||'<p class="quiet">No roster mapping yet.</p>'}</div></div><div class="detail-section"><h3>Current evidence</h3>${ev?`<div class="coverage-big"><b>${ev.coverage}%</b><span>team evidence against ${ev.phase_id}</span></div><p>${gaps.length} evidence area(s) need review, including scaffold/weak/missing states.</p><p><b>AI usage:</b> ${formatEstimatedCost(d.team.ai_usage?.estimated_cost_usd)} · ${Number(d.team.ai_usage?.input_tokens||0).toLocaleString()} input · ${Number(d.team.ai_usage?.cached_input_tokens||0).toLocaleString()} cached · ${d.team.ai_usage?.calls?`${(Number(d.team.ai_usage.avg_latency_ms||0)/1000).toFixed(1)}s avg response`:'no model calls yet'}.</p>`:'<p class="quiet">No evidence snapshot yet.</p>'}</div></div>`;

    $$('[data-team-active-review]').forEach(button=>{
      button.onclick=()=>{
        switchView('instructorReviews',{history:false});
        loadInstructorReviewDetail(Number(button.dataset.teamActiveReview),{history:true});
      };
    });

    const resetRepository=$('#resetTeamRepository');
    if(resetRepository){
      resetRepository.onclick=async()=>{
        if(!confirm('Reset this team’s repository onboarding? The verified current repository will be cleared. Frozen evidence and prior reviews will be preserved.'))return;
        await withBusy(resetRepository,'Resetting…',async()=>{
          await jsonRequest(`/api/v1/onboarding/teams/${teamId}/repository/reset`,{method:'POST'},'Repository onboarding could not be reset.');
          toast('Repository onboarding reset. Historical evidence and reviews were preserved.');
          await loadInstructor();
        });
      };
    }

    if(opts.focus){
      box.setAttribute('tabindex','-1');
      box.scrollIntoView({
        behavior:'smooth',
        block:'start'
      });
      box.focus({preventScroll:true});
    }

  }catch(e){
    box.classList.remove('hidden');
    opsError(
      '#teamDetail',
      safeErrorMessage(e),
      ()=>loadTeamDetail(teamId,opts)
    );
  }
}
async function adminSetupData(){return jsonRequest('/api/v1/admin/setup',{},'Course setup could not be loaded.')}
function fillSectionSelectors(data){const sections=(data.terms||[]).flatMap(t=>(t.sections||[]).map(s=>({...s,term:t})));syncInstructorSectionControls(sections);const termSel=$('#newSectionTerm');if(termSel){const prev=termSel.value;termSel.innerHTML=(data.terms||[]).map(t=>`<option value="${t.id}" ${t.status==='archived'?'disabled':''}>${escapeHtml(t.course_code)} · ${escapeHtml(t.term_label)} (${escapeHtml(t.namespace)})${t.status==='archived'?' · Archived':''}</option>`).join('');if(prev&&[...termSel.options].some(o=>o.value===prev&&!o.disabled))termSel.value=prev;else if(termSel.selectedOptions[0]?.disabled){const first=[...termSel.options].find(o=>!o.disabled);if(first)termSel.value=first.value}}return sections}
async function loadInstructorTeams(){const box=$('#instructorTeamGrid');try{const setup=await adminSetupData();fillSectionSelectors(setup);const d=await jsonRequest(`/api/v1/instructor/overview${instructorSectionQuery()}`,{},'Team operations could not be loaded.');box.innerHTML=d.teams.map(t=>{const context=[t.section?.display_name,teamIdentifierLabel(t.team_key)].filter(Boolean).join(' · ');return `<button class="teamcard ${t.attention}" data-team="${t.id}" data-team-open="${t.id}"><div class="team-name"><span class="attention-dot"></span><div><b>${escapeHtml(t.name)}</b><small>${escapeHtml(t.project)}</small><small class="team-card-context">${escapeHtml(context)}</small></div></div><div><small>Repository</small><b>${t.repo?'Connected':'Not connected'}</b></div><div><small>Reviews</small><b>${t.review_sessions}</b></div><div><small>AI cost</small><b>${formatEstimatedCost(t.ai_usage?.estimated_cost_usd)}</b></div><span class="inspect">Inspect →</span></button>`}).join('')||'<div class="empty-card">No teams in this section context yet.</div>';$$('[data-team-open]').forEach(b=>b.onclick=()=>{switchView('instructor',{history:false});loadTeamDetail(Number(b.dataset.teamOpen),{focus:true,history:true})})}catch(e){opsError('#instructorTeamGrid',safeErrorMessage(e),loadInstructorTeams)}}
async function loadInstructorStudents(){try{const setup=await adminSetupData();fillSectionSelectors(setup);selectedSectionId=currentInstructorSectionId();if(!selectedSectionId){$('#studentRosterTable').innerHTML='<div class="section-required"><b>Choose a section to manage its roster.</b><span>The shared SECTION context is currently All sections. Select one section before adding, deactivating, or moving students.</span></div>';return;}const [students,teams]=await Promise.all([fetch(`/api/v1/admin/sections/${selectedSectionId}/students`).then(r=>r.json()),fetch(`/api/v1/admin/sections/${selectedSectionId}/teams`).then(r=>r.json())]);const opts=['<option value="">Unassigned</option>',...teams.teams.map(t=>`<option value="${t.id}">${escapeHtml(t.name)}</option>`)].join(''),manage=canManageSectionUi();const toolbar=manage?`<div class="student-admin-toolbar"><div><b>Add student</b><span>Use the Loyola Student ID. Their login is ${'<studentid>@luc.edu'}.</span></div><input id="manualStudentId" placeholder="Student ID"><input id="manualStudentName" placeholder="Last, First or display name"><select id="manualStudentTeam">${opts}</select><button id="manualAddStudent" class="secondary">Add / reactivate</button></div>`:`<div class="read-only-notice"><b>Read-only roster view</b><span>Your teaching-staff role can inspect the roster and team context. Course Owners and Instructors manage enrollment and team changes.</span></div>`;$('#studentRosterTable').innerHTML=`${toolbar}<div class="roster-table"><div class="roster-row header"><span>Student</span><span>Loyola ID</span><span>GitHub</span><span>Status</span><span>Team${manage?' / action':''}</span></div>${students.students.map(st=>`<div class="roster-row"><span><b>${escapeHtml(st.name)}</b><small>${escapeHtml(st.email)}</small></span><span>${escapeHtml(st.student_id)}</span><span>${st.github_login?'@'+escapeHtml(st.github_login):'<em>not linked</em>'}</span><span class="status-text ${st.status}">${st.status}</span><span class="row-actions">${manage?`<select class="student-team-select" data-user="${st.user_id}" ${st.status!=='active'?'disabled':''}>${opts}</select><button class="student-status-button text-button" data-user="${st.user_id}" data-status="${st.status}">${st.status==='active'?'Deactivate':'Reactivate'}</button>`:escapeHtml(st.team_name||'Unassigned')}</span></div>`).join('')}</div>`;if(!manage)return;$$('.student-team-select').forEach(x=>{const st=students.students.find(s=>s.user_id===Number(x.dataset.user));x.value=st?.team_id||'';x.onchange=async()=>{const r=await fetch(`/api/v1/admin/sections/${selectedSectionId}/students/${x.dataset.user}/team`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({team_id:x.value?Number(x.value):null})});if(!r.ok){const d=await r.json();toast(d.detail||'Could not update team assignment');return}toast('Team assignment updated; history preserved.')}});$$('.student-status-button').forEach(b=>b.onclick=async()=>{const next=b.dataset.status==='active'?'dropped':'active';const r=await fetch(`/api/v1/admin/sections/${selectedSectionId}/students/${b.dataset.user}/status?status=${next}`,{method:'PUT'});if(!r.ok){const d=await r.json();toast(d.detail||'Could not update student status');return}toast(next==='active'?'Student reactivated.':'Student deactivated; history preserved.');loadInstructorStudents()});$('#manualAddStudent').onclick=async()=>{const student_id=$('#manualStudentId').value.trim(),name=$('#manualStudentName').value.trim(),team_id=$('#manualStudentTeam').value;if(!student_id||!name){toast('Student ID and name are required.');return}const r=await fetch(`/api/v1/admin/sections/${selectedSectionId}/students`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({student_id,name,team_id:team_id?Number(team_id):null})}),d=await r.json();if(!r.ok){toast(d.detail||'Could not add student');return}toast('Student added or reactivated.');loadInstructorStudents()}}catch(e){opsError('#studentRosterTable',safeErrorMessage(e),loadInstructorStudents)}}
async function loadInstructorReviewDetail(sessionId){const opts=arguments[1]||{};
  const box=$('#reviewOpsDetail');

  box.classList.remove('hidden');
  box.innerHTML=
    '<div class="loading-card">Loading persisted review conversation…</div>';

  try{
    const d=await jsonRequest(
      `/api/v1/reviews/${sessionId}`,
      {},
      'Review conversation could not be loaded.'
    );

    currentInstructorReviewSessionId=Number(sessionId);
    if(opts.history)recordNavigationState();

    const s=d.session||{},
      team=d.team||{},
      snapshot=d.snapshot||{},
      turns=d.turns||[];

    const mode=String(s.mode||'review').replaceAll('_',' ');

    const repo=
      team.repo_full_name
      ||d.evidence?.repo_full_name
      ||'Repository not recorded';

    const frozen=snapshot.commit_sha
      ?`${repo} @ ${String(snapshot.commit_sha).slice(0,8)}`
      :repo;

    const lastUpdated=
      turns.length
        ?turns[turns.length-1].created_at
        :s.started_at;

    box.innerHTML=
      `<div class="instructor-review-detail-head"><div><span class="eyebrow">READ-ONLY REVIEW CONVERSATION</span><h3>${escapeHtml(s.student?.name||'Student')} · ${escapeHtml(s.phase_id||'')} ${escapeHtml(mode)}</h3><p>${escapeHtml(team.name||'Team')} · ${escapeHtml(team.project_name||'Project not confirmed')}</p></div><div class="instructor-review-detail-actions"><button id="refreshInstructorReview" class="secondary compact">Refresh conversation</button><button id="closeInstructorReview" class="text-button">Close</button></div></div><div class="review-readonly-note"><b>Teaching-staff view only.</b><span>Only persisted review turns are shown. Drafts and unsent text are not visible here.</span></div><div class="instructor-review-meta"><div><small>STATUS</small><b>${escapeHtml(s.status||'unknown')}</b></div><div><small>STARTED</small><b>${s.started_at?escapeHtml(new Date(s.started_at).toLocaleString()):'—'}</b></div><div><small>TURN COUNT</small><b>${pluralizeCount(turns.length,'turn')}</b></div><div><small>LAST UPDATED</small><b>${lastUpdated?escapeHtml(new Date(lastUpdated).toLocaleString()):'—'}</b></div><div><small>FROZEN EVIDENCE</small><b>${escapeHtml(frozen)}</b></div><div><small>SNAPSHOT</small><b>${snapshot.id?`#${snapshot.id}`:'—'}</b></div></div><div class="instructor-review-transcript">${turns.map(t=>`<article class="instructor-review-turn ${t.actor==='student'?'student':'reviewer'}"><header><b>${t.actor==='student'?escapeHtml(s.student?.name||'Student'):escapeHtml(reviewerTurnLabel(t))}</b><span>${t.created_at?escapeHtml(new Date(t.created_at).toLocaleString()):`Turn ${t.sequence}`}</span></header><p>${escapeHtml(t.content)}</p>${(t.evidence_refs||[]).length?`<small>Evidence: ${(t.evidence_refs||[]).map(escapeHtml).join(', ')}</small>`:''}</article>`).join('')||'<p class="quiet">No persisted conversation turns yet.</p>'}</div>`;

    $('#refreshInstructorReview').onclick=
      ()=>loadInstructorReviewDetail(sessionId);

    $('#closeInstructorReview').onclick=()=>{
      currentInstructorReviewSessionId=null;
      box.classList.add('hidden');
      box.innerHTML='';
      recordNavigationState();
    };

    box.scrollIntoView({
      behavior:'smooth',
      block:'start'
    });

  }catch(e){
    opsError(
      '#reviewOpsDetail',
      safeErrorMessage(e),
      ()=>loadInstructorReviewDetail(sessionId)
    );
  }
}
async function loadInstructorReviews(){
  try{
    const setup=await adminSetupData();
    fillSectionSelectors(setup);
    const d=await jsonRequest(
      `/api/v1/instructor/overview${instructorSectionQuery()}`,
      {},
      'Review operations could not be loaded.'
    );

    const details=await Promise.all(
      (d.teams||[]).map(
        t=>jsonRequest(
          `/api/v1/instructor/teams/${t.id}`,
          {},
          `Could not load ${t.name}.`
        )
      )
    );

    $('#reviewOps').innerHTML=details.map(x=>{
      const recent=pluralizeCount(
        x.sessions.length,
        'recent session'
      );

      return `<article class="ops-card"><div><span class="eyebrow">${escapeHtml(x.team.name)}</span><h3>${escapeHtml(x.team.project)}</h3><p>${recent} · ${x.team.active_sessions} active</p></div><div class="ops-list">${x.sessions.slice(0,6).map(s=>`<div class="review-ops-row"><span><b>${escapeHtml(s.phase)} · ${escapeHtml(String(s.mode||'review').replaceAll('_',' '))}</b><small>${escapeHtml(s.student?.name||'Student')} · ${escapeHtml(s.status)} · ${pluralizeCount(s.turns,'turn')} · ${s.started_at?new Date(s.started_at).toLocaleString():''}</small></span><button type="button" class="secondary compact" data-review-session="${s.id}">View review →</button></div>`).join('')||'<span class="quiet">No reviews yet.</span>'}</div></article>`;
    }).join('')
      ||'<p class="quiet">No review activity is available for your assigned sections yet.</p>';

    $$('[data-review-session]').forEach(
      b=>b.onclick=
        ()=>loadInstructorReviewDetail(
          Number(b.dataset.reviewSession),
          {history:true}
        )
    );

  }catch(e){
    opsError(
      '#reviewOps',
      safeErrorMessage(e),
      loadInstructorReviews
    );
  }
}
async function loadInstructorEvidence(){try{const setup=await adminSetupData();fillSectionSelectors(setup);const d=await jsonRequest(`/api/v1/instructor/overview${instructorSectionQuery()}`,{},'Engineering evidence could not be loaded.'),details=await Promise.all((d.teams||[]).map(t=>jsonRequest(`/api/v1/instructor/teams/${t.id}`,{},`Could not load ${t.name}.`)));$('#evidenceOps').innerHTML=details.map(x=>{const ev=x.evidence,findings=ev?.findings||[],strengths=ev?.strengths||[];return `<article class="ops-card"><div><span class="eyebrow">${escapeHtml(x.team.name)} · ${escapeHtml(x.team.phase||'')}</span><h3>${escapeHtml(x.team.project)}</h3><p>${ev?`${ev.coverage??'—'}% evidence coverage · snapshot ${escapeHtml(String(ev.commit_sha||'').slice(0,8)||'available')}`:'No frozen evidence snapshot yet.'}</p></div>${ev?`<div class="ops-columns"><div><b>Strengths</b>${strengths.slice(0,4).map(v=>`<span>✓ ${escapeHtml(v)}</span>`).join('')||'<span class="quiet">No manufactured praise; strengths appear only when supported.</span>'}</div><div><b>Current findings</b>${findings.slice(0,5).map(f=>`<span>${escapeHtml(f.provenance||'REVIEW')} · ${escapeHtml(f.title||f.message||f.finding_type||'Finding')}</span>`).join('')||'<span class="quiet">No current findings.</span>'}</div></div>`:''}</article>`}).join('')||'<p class="quiet">No engineering evidence is available for your assigned sections yet.</p>'}catch(e){opsError('#evidenceOps',safeErrorMessage(e),loadInstructorEvidence)}}
function loadAccessSettings(){if(!healthState)return;$('#entraStatus').textContent=healthState.entra_sso_ready?'Configured for Microsoft Entra sign-in':'Not configured yet';const box=$('#accessSettings .settings-cards');if(box&&!box.querySelector('[data-runtime-access]')){const d=document.createElement('div');d.dataset.runtimeAccess='1';d.innerHTML=`<b>Your current privilege</b><span>${escapeHtml(roleLabel(authenticatedUser?.role||'developer'))}. Authorization is section-scoped for Instructors, TAs, and Reviewers.</span>`;box.appendChild(d)}}

async function loadInstructorUsage(){
  try{
    const setup=await adminSetupData();
    fillSectionSelectors(setup);
    const d=await jsonRequest(
      `/api/v1/instructor/overview${instructorSectionQuery()}`,
      {},
      'AI usage telemetry could not be loaded.'
    );

    const u=d.ai_usage||{};

    $('#usageOps').innerHTML=
      `<div class="usage-summary-grid"><div><b>${formatEstimatedCost(u.estimated_cost_usd)}</b><span>Estimated term cost</span></div><div><b>${Number(u.input_tokens||0).toLocaleString()}</b><span>Input tokens</span></div><div><b>${Number(u.cached_input_tokens||0).toLocaleString()}</b><span>Cached input</span></div><div><b>${Math.round(Number(u.cache_hit_ratio||0)*100)}%</b><span>Cache hit</span></div><div><b>${u.calls?`${(Number(u.avg_latency_ms||0)/1000).toFixed(1)}s`:'—'}</b><span>Average model latency</span></div></div><p class="quiet">Costs use the versioned advisory rate card${u.rate_card_version?` (${escapeHtml(u.rate_card_version)})`:''}. Sub-cent totals are shown with additional precision. Team and purpose drill-down remains available in the Command Center.</p>`;

  }catch(e){
    opsError(
      '#usageOps',
      safeErrorMessage(e),
      loadInstructorUsage
    );
  }
}
function applySemesterLifecycleUi(term){
 const status=String(term?.status||'').toLowerCase(),archived=status==='archived',notice=$('#semesterLifecycleNotice');
 if(notice){
  if(archived){notice.innerHTML='<div><b>Archived semester · read-only</b><span>Student access ended when this term was archived. Historical reviews, frozen evidence, roster history, and usage records remain preserved. Any review that was active at archive is retained as an incomplete historical review, not a completed review.</span></div>';notice.classList.remove('hidden')}
  else if(status==='setup'){notice.innerHTML='<div><b>Semester setup</b><span>This term is not yet active for normal student use. Course Owners and Instructors may finish configuration before activation.</span></div>';notice.classList.remove('hidden')}
  else notice.classList.add('hidden')
 }
 const selectedTermControls=['importRoster','deactivateMissing','newTeamKey','newTeamName','createTeam','staffEmail','staffRole','addStaff'];
 selectedTermControls.forEach(id=>{const el=$('#'+id);if(el)el.disabled=archived});
 $$('#scheduleEditor input,#scheduleEditor select,#scheduleEditor button').forEach(el=>{el.disabled=archived});
 const archive=$('#archiveTerm');if(archive){archive.disabled=archived;archive.textContent=archived?'Term archived':'Archive term'}
 const createSection=$('#createSection'),sectionTerm=$('#newSectionTerm');
 if(createSection&&sectionTerm){const target=(term?.id!=null&&String(sectionTerm.value)===String(term.id));createSection.disabled=!!sectionTerm.selectedOptions[0]?.disabled||(archived&&target)}
 return archived
}
async function loadSemesterSetup(){try{const data=await adminSetupData();const sections=fillSectionSelectors(data);selectedSectionId=currentInstructorSectionId();const owner=!authenticatedUser||['course_owner','developer'].includes(authenticatedUser.role);['createTerm','createSection','archiveTerm'].forEach(id=>{const el=$('#'+id);if(el)el.classList.toggle('hidden',!owner)});const roleSelect=$('#staffRole');if(roleSelect){[...roleSelect.options].forEach(o=>o.disabled=!owner&&['course_owner','instructor'].includes(o.value));if(!owner&&['course_owner','instructor'].includes(roleSelect.value))roleSelect.value='ta'}if(!selectedSectionId){applySemesterLifecycleUi(null);['importRoster','deactivateMissing','newTeamKey','newTeamName','createTeam','staffEmail','staffRole','addStaff','archiveTerm'].forEach(id=>{const el=$('#'+id);if(el)el.disabled=true});$('#semesterLifecycleNotice').innerHTML='<div><b>Choose a section to manage it.</b><span>The shared SECTION context is currently All sections. Select one section before changing roster, teams, review dates, staff, or lifecycle state. Term creation remains separate.</span></div>';$('#semesterLifecycleNotice').classList.remove('hidden');$('#teamAssignmentList').innerHTML='<div class="section-required"><b>No section selected.</b><span>Select a section above to see its teams.</span></div>';$('#scheduleEditor').innerHTML='<div class="section-required"><b>No section selected.</b><span>Select a section above to edit its review calendar.</span></div>';$('#staffList').innerHTML='<p class="quiet">Select a section to see teaching-staff assignments.</p>';return}const selected=sections.find(s=>Number(s.id)===selectedSectionId),term=selected?.term||null;await Promise.all([renderSetupTeams(),renderScheduleEditor(),renderStaff()]);applySemesterLifecycleUi(term);}catch(e){opsError('#scheduleEditor',safeErrorMessage(e),loadSemesterSetup)}}
async function renderSetupTeams(){const [students,teams]=await Promise.all([jsonRequest(`/api/v1/admin/sections/${selectedSectionId}/students`,{},'Student roster could not be loaded.'),jsonRequest(`/api/v1/admin/sections/${selectedSectionId}/teams`,{},'Team list could not be loaded.')]);$('#teamAssignmentList').innerHTML=`<div class="setup-team-list">${teams.teams.map(t=>`<div><b>${escapeHtml(t.name)}</b><span>${t.members} student(s) · ${escapeHtml(t.repo_full_name||'repository not connected')}</span></div>`).join('')||'<p class="quiet">No teams created yet.</p>'}</div><p class="quiet">Use the Students page to assign or move individual students between teams.</p>`}
async function renderScheduleEditor(){
 try{
  const d=await jsonRequest(`/api/v1/admin/sections/${selectedSectionId}/schedule`,{},'The section schedule could not be loaded.');
  $('#scheduleEditor').innerHTML=`<div class="schedule-table"><div class="schedule-row header"><span>Phase</span><span>Available</span><span>Due</span><span>Accept until</span><span>Release</span></div>${d.phases.map(p=>`<div class="schedule-row" data-phase="${p.phase_id}"><b>${p.phase_id}</b><input data-field="available_at" type="datetime-local" value="${localDateValue(p.available_at)}"><input data-field="due_at" type="datetime-local" value="${localDateValue(p.due_at)}"><input data-field="accept_until" type="datetime-local" value="${localDateValue(p.accept_until)}"><select data-field="release_override"><option value="auto">Automatic</option><option value="released">Release now</option><option value="locked">Lock</option></select><button class="save-phase secondary compact">Save</button></div>`).join('')}</div>`;
  $$('.schedule-row[data-phase]').forEach(row=>{row.querySelector('[data-field="release_override"]').value=d.phases.find(x=>x.phase_id===row.dataset.phase).override;const btn=row.querySelector('.save-phase');btn.onclick=()=>withBusy(btn,'Saving…',async()=>{const body={};['available_at','due_at','accept_until'].forEach(f=>{const v=row.querySelector(`[data-field="${f}"]`).value;body[f]=v?new Date(v).toISOString():null});body.release_override=row.querySelector('[data-field="release_override"]').value;await jsonRequest(`/api/v1/admin/sections/${selectedSectionId}/schedule/${row.dataset.phase}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)},`${row.dataset.phase} schedule could not be saved.`);toast(`${row.dataset.phase} schedule saved`)})})
 }catch(e){opsError('#scheduleEditor',safeErrorMessage(e),renderScheduleEditor)}
}

function localDateValue(v){if(!v)return'';const d=new Date(v),z=new Date(d.getTime()-d.getTimezoneOffset()*60000);return z.toISOString().slice(0,16)}
async function renderStaff(){const d=await jsonRequest(`/api/v1/admin/sections/${selectedSectionId}/staff`,{},'Teaching-staff access could not be loaded.');$('#staffList').innerHTML=d.staff.map(x=>`<div class="staff-row"><b>${escapeHtml(x.name)}</b><span>${escapeHtml(x.email||'')} · ${escapeHtml(x.role)}</span></div>`).join('')||'<p class="quiet">No staff assignments yet.</p>'}


$('#closeArtifactOverlay').onclick=closeArtifact;$('#artifactOverlay').onclick=e=>{if(e.target.id==='artifactOverlay')closeArtifact()};$('#artifactReferenceButton').onclick=()=>{if(!artifactContext)return;if(!sessionId){closeArtifact();configureFocusedFromEvidence(`Review the evidence at ${artifactContext.path}. Tell me what it supports, what it does not support, and what is worth improving.`,artifactContext.path);return}setComposerContext(artifactContext);closeArtifact();switchView('studio');setMode('ask');els.response.focus();toast('Evidence attached to your next message.')};$('#reviewHomeButton').onclick=()=>newReviewHome();
$('#createTerm').onclick=async()=>{const btn=$('#createTerm');await withBusy(btn,'Creating…',async()=>{const namespace=$('#termNamespace').value.trim(),term_label=$('#termLabel').value.trim(),starts_on=$('#termStart').value,ends_on=$('#termEnd').value;if(!namespace||!term_label||!starts_on){toast('Term namespace, label, and start date are required.');return}await jsonRequest('/api/v1/admin/terms',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({namespace,term_label,starts_on,ends_on,course_code:'COMP 330'})},'The course term could not be created.');toast('Course term created. Add its section next.');$('#termNamespace').value='';$('#termLabel').value='';$('#termStart').value='';$('#termEnd').value='';await loadSemesterSetup()})}
$('#createSection').onclick=async()=>{const btn=$('#createSection');await withBusy(btn,'Adding…',async()=>{const termId=Number($('#newSectionTerm').value),section_key=$('#newSectionKey').value.trim(),display_name=$('#newSectionName').value.trim(),meeting_pattern=$('#newSectionMeeting').value.trim();if(!termId||!section_key){toast('Choose the term and enter a section key.');return}await jsonRequest(`/api/v1/admin/terms/${termId}/sections`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({section_key,display_name:display_name||null,meeting_pattern})},'The section could not be created.');toast('Section created with a proposed A1–A6 review calendar.');$('#newSectionKey').value='';$('#newSectionName').value='';$('#newSectionMeeting').value='';await loadSemesterSetup()})}
$('#importRoster').onclick=async()=>{const btn=$('#importRoster'),f=$('#rosterFile').files[0];if(!f){toast('Choose the Sakai gradebook CSV first.');return}await withBusy(btn,'Importing…',async()=>{const fd=new FormData();fd.append('file',f);const d=await jsonRequest(`/api/v1/admin/sections/${selectedSectionId}/roster?deactivate_missing=${$('#deactivateMissing').checked}`,{method:'POST',body:fd},'Roster import failed. The existing roster was not silently removed.');$('#rosterImportResult').textContent=`${d.rows} roster rows · ${d.added} added · ${d.reactivated} reactivated · ${d.deactivated} deactivated`;await renderSetupTeams();toast('Roster import complete.')})}
$('#createTeam').onclick=async()=>{const btn=$('#createTeam');await withBusy(btn,'Creating…',async()=>{const team_key=$('#newTeamKey').value.trim(),name=$('#newTeamName').value.trim();if(!team_key){toast('Enter a team key such as team-02.');return}await jsonRequest(`/api/v1/admin/sections/${selectedSectionId}/teams`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({team_key,name:name||null})},'The team could not be created.');$('#newTeamKey').value='';$('#newTeamName').value='';await renderSetupTeams();toast('Team created')})}
$('#addStaff').onclick=async()=>{const btn=$('#addStaff');await withBusy(btn,'Adding…',async()=>{const email=$('#staffEmail').value.trim(),role=$('#staffRole').value;if(!email){toast('Enter the staff Loyola email.');return}await jsonRequest(`/api/v1/admin/sections/${selectedSectionId}/staff`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,role})},'Staff access could not be added.');$('#staffEmail').value='';await renderStaff();toast('Staff access added')})}
$('#archiveTerm').onclick=async()=>{if(!confirm('Archive this term? Student access will end immediately. Historical reviews and evidence will be preserved, and any active review will be retained as an incomplete historical review rather than marked completed.'))return;const btn=$('#archiveTerm');await withBusy(btn,'Archiving…',async()=>{const data=await adminSetupData(),section=(data.terms||[]).flatMap(t=>(t.sections||[]).map(s=>({s,t}))).find(x=>x.s.id===selectedSectionId);if(!section)throw new Error('The active section is no longer available. Refresh Semester Setup.');await jsonRequest(`/api/v1/admin/terms/${section.t.id}/status?status=archived`,{method:'PUT'},'The term could not be archived. Nothing was deleted.');toast('Term archived; student access ended and historical records were preserved.')});await loadSemesterSetup()}

async function logoutStudio(){
  const btn=$('#logoutButton');
  if(!btn||btn.disabled)return;
  const original=btn.textContent;
  btn.disabled=true;
  btn.textContent='Signing out…';
  try{
    const r=await fetch('/auth/logout',{method:'POST'});
    if(!r.ok)throw new Error('Sign out failed');
    csrfToken=null;
    authenticatedUser=null;
    $('#appShell').classList.add('hidden');
    $('#loginGate').classList.remove('hidden');
    $('#logoutButton').classList.add('hidden');

    const signedOutUrl=new URL('/',window.location.origin);
    signedOutUrl.searchParams.set('signed_out',String(Date.now()));
    window.location.replace(signedOutUrl.toString());
  }catch(e){
    btn.disabled=false;
    btn.textContent=original;
    toast(safeErrorMessage(e,'Could not sign out. Try again.'));
  }
}
$('#logoutButton').onclick=logoutStudio;


(async function init(){try{const h=await fetch('/health').then(r=>r.json());healthState=h;semanticReady=!!h.semantic_coaching_ready;const m=$('#conversationMode');if(semanticReady){m.textContent='Coaching ready';m.title=`Coaching model: ${h.model||'configured'}`;m.className='conversation-mode semantic';$('#semanticSetupWarning')?.classList.add('hidden')}else{m.textContent='Natural coaching not configured';m.className='conversation-mode fallback';$('#semanticSetupWarning')?.classList.remove('hidden');els.newReview.textContent='Configure Coaching'}
if(h.environment==='development'){courseModel=await fetch('/api/v1/course').then(r=>r.json());const seed=await ensureDemo();authenticatedUser={display_name:'William O\'Connell',role:'course_owner'};$('#devPersona').classList.remove('hidden');$('#devPersona').onchange=()=>{appRole=$('#devPersona').value;if(appRole==='instructor')authenticatedUser={display_name:'William O\'Connell',role:'course_owner'};applyRoleShell()};await loadStudentContext(seed.user_id);await loadHistory();appRole='student';applyRoleShell();$('#appShell').removeAttribute('hidden');$('#appShell').classList.remove('hidden')}else{const me=await fetch('/auth/me').then(r=>r.json());if(!me.authenticated){$('#appShell').classList.add('hidden');$('#loginGate').classList.remove('hidden');return}csrfToken=me.csrf_token||null;authenticatedUser=me.user;courseModel=await fetch('/api/v1/course').then(r=>r.json());$('#loginGate').classList.add('hidden');$('#appShell').removeAttribute('hidden');$('#appShell').classList.remove('hidden');$('#logoutButton').classList.remove('hidden');demoContext={user_id:me.user.id};appRole=['course_owner','instructor','ta','reviewer'].includes(me.user.role)?'instructor':'student';if(appRole==='student'){await loadStudentContext(me.user.id);await loadHistory()}applyRoleShell()}await initializeBrowserNavigation()
}catch(e){console.error(e);toast('Studio initialization encountered a problem.')}applyPhase();updateRepoMode();setIdentity('studio');els.decision.onchange();updateReviewModeSummary();updateStartReviewButton()})();
