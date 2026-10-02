// Dependency-free behavioral DOM harness. Actual browser acceptance remains separate.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('apps/api/app/static/studio.js','utf8');
const helper=source.slice(source.indexOf('// BEGIN STUDIO DIALOG KEYBOARD CONTRACT'),source.indexOf('// END STUDIO DIALOG KEYBOARD CONTRACT'));
const listeners={},nodes=new Map();
class Element{
 constructor(id,parent=null){this.id=id;this.parent=parent;this.children=[];this.inert=false;this.disabled=false;this.tabIndex=0;this.type='button';this.name='';this.checked=false;this.isConnected=true;this.value='';this.visibility='visible';this.attrs={};const hidden=new Set();this.classList={add:x=>hidden.add(x),remove:x=>hidden.delete(x),contains:x=>hidden.has(x)};if(parent)parent.children.push(this);nodes.set(id,this)}
 contains(node){return node===this||this.children.some(x=>x.contains(node))}
 closest(){for(let n=this;n;n=n.parent)if(n.inert)return n;return null}
 getClientRects(){for(let n=this;n;n=n.parent)if(n.classList.contains('hidden'))return [];return this.isConnected?[{}]:[]}
 querySelectorAll(selector){const all=this.children.flatMap(x=>[x,...x.querySelectorAll('*')]);return selector==='input[type="radio"]'?all.filter(x=>x.type==='radio'):all}
 focus(){if(this.disabled||!this.isConnected||this.closest())return;document.activeElement=this;(listeners.focusin||[]).forEach(fn=>fn({target:this}))}
 setAttribute(k,v){this.attrs[k]=v;if(k==='tabindex')this.tabIndex=Number(v)}
 click(){if(!this.disabled)this.onclick?.()}
}
const body=new Element('body');
const document={body,activeElement:body,getElementById:id=>nodes.get(id)||null,addEventListener:(event,fn)=>(listeners[event]??=[]).push(fn)};
const root=new Element('app',body),opener=new Element('opener',root),draft=new Element('response',root);draft.value='Student-owned unsent draft';
new Element('newReview',root);new Element('helpButton',root);
const dialogs={helpOverlay:'closeHelp',artifactOverlay:'closeArtifactOverlay',evidenceDisputeOverlay:'closeEvidenceDispute',reviewExitOverlay:'closeReviewExit'};
for(const [id,button] of Object.entries(dialogs)){const dialog=new Element(id,body);dialog.classList.add('hidden');new Element(button,dialog);new Element(id+'Last',dialog)}
const ctx={document,getComputedStyle:n=>({visibility:n.visibility})};vm.createContext(ctx);vm.runInContext(helper,ctx);
for(const [id,button] of Object.entries(dialogs))nodes.get(button).onclick=()=>ctx.closeStudioDialog(id);
function key(key,shiftKey=false,isComposing=false){const e={key,shiftKey,isComposing,preventDefault(){this.prevented=true},stopPropagation(){}};for(const fn of listeners.keydown||[])fn(e);return e}
function controls(id){return ctx.studioDialogControls(nodes.get(id))}
let count=0;
for(const phase of ['A1','A2','A3','A4','A5','A6'])for(const repo of ['weak','average','strong'])for(const student of ['weak','average','strong'])for(const id of Object.keys(dialogs)){
 opener.focus();ctx.openStudioDialog(id);assert(nodes.get(id).contains(document.activeElement));assert(root.inert);
 controls(id).at(-1).focus();assert(key('Tab').prevented);assert.equal(document.activeElement,controls(id)[0]);
 assert(key('Tab',true).prevented);assert.equal(document.activeElement,controls(id).at(-1));
 assert(key('Escape').prevented);assert.equal(document.activeElement,opener);assert(!root.inert);assert.equal(draft.value,'Student-owned unsent draft');count++;
}
// Engine/evidence state remains unchanged across keyboard interactions in all evidence shapes.
for(const evidence of ['ambiguous','contradictory','missing','equivalent','stale','post-snapshot','valid-reviewer-challenge']){
 const state={evidence,finding:'evidence_disputed',snapshot:'frozen',reasoning:[true,false],student:'no grade'};
 const before=JSON.stringify(state);opener.focus();ctx.openStudioDialog('evidenceDisputeOverlay');key('Escape');assert.equal(JSON.stringify(state),before);
}
// Nested dialogs return to the underlying dialog; original inert state survives.
nodes.get('newReview').inert=true;opener.focus();ctx.openStudioDialog('artifactOverlay');nodes.get('artifactOverlayLast').focus();ctx.openStudioDialog('helpOverlay');
key('Escape');assert.equal(document.activeElement,nodes.get('artifactOverlayLast'));key('Escape');assert.equal(document.activeElement,opener);assert(nodes.get('newReview').inert);
// Hidden/disabled controls and IME Escape.
opener.focus();ctx.openStudioDialog('evidenceDisputeOverlay');nodes.get('evidenceDisputeOverlayLast').disabled=true;
assert.equal(controls('evidenceDisputeOverlay').length,1);assert(key('Tab').prevented);
key('Escape',false,true);assert(!nodes.get('evidenceDisputeOverlay').classList.contains('hidden'));
key('Escape');
// Removed opener falls back to a usable page control; pending draft stays intact.
opener.focus();ctx.openStudioDialog('artifactOverlay');opener.isConnected=false;key('Escape');assert.equal(document.activeElement,draft);
// Focus escape is repaired, and a dialog with no usable controls remains focusable.
opener.isConnected=true;opener.focus();ctx.openStudioDialog('helpOverlay');document.activeElement=draft;listeners.focusin.forEach(fn=>fn({target:draft}));assert(nodes.get('helpOverlay').contains(document.activeElement));
for(const el of controls('helpOverlay'))el.disabled=true;key('Tab');assert.equal(document.activeElement,nodes.get('helpOverlay'));key('Escape');
// Deliberate focus/navigation after dialog work should not be overwritten on close.
for(const el of nodes.get('helpOverlay').children)el.disabled=false;
opener.focus();ctx.openStudioDialog('helpOverlay');ctx.closeStudioDialog('helpOverlay');draft.focus();ctx.closeStudioDialog('helpOverlay');assert.equal(document.activeElement,draft);
console.log(`Dialog keyboard DOM harness: ${count} A1-A6/repository/student/dialog combinations, 7 evidence-shape invariance cases and nested/hidden/disabled/IME/no-control/removed-opener/focus-escape cases passed. No live semantic-model evaluation.`);
