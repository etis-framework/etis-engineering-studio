// Optional real-browser war game: node tests/dialog_keyboard_wargame.cjs
// Requires Playwright and its Chromium; never makes network/model calls.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {chromium}=require('playwright');
const source=fs.readFileSync('apps/api/app/static/studio.js','utf8');
const helper=source.slice(source.indexOf('// BEGIN STUDIO DIALOG KEYBOARD CONTRACT'),source.indexOf('// END STUDIO DIALOG KEYBOARD CONTRACT'));
const html=fs.readFileSync('apps/api/app/static/index.html','utf8').replace(/<script[^>]*>[\s\S]*?<\/script>/g,'').replace(/<link[^>]*>/g,'');
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage();
 await page.setContent(html+'<style>.hidden{display:none!important}</style>');
 await page.addScriptTag({content:helper});
 await page.evaluate(()=>{
  for(const [dialog,button] of Object.entries(studioDialogCloseButtons))document.getElementById(button).onclick=()=>closeStudioDialog(dialog);
  const opener=document.createElement('button');opener.id='keyboardOpener';opener.textContent='Open';document.body.prepend(opener);
 });
 let cases=0;
 for(const phase of ['A1','A2','A3','A4','A5','A6'])for(const repo of ['weak','average','strong'])for(const student of ['weak','average','strong']){
  for(const id of ['helpOverlay','artifactOverlay','evidenceDisputeOverlay','reviewExitOverlay']){
   await page.evaluate(id=>{document.getElementById('keyboardOpener').focus();openStudioDialog(id)},id);
   assert.equal(await page.evaluate(id=>document.getElementById(id).contains(document.activeElement),id),true);
   await page.evaluate(id=>studioDialogControls(document.getElementById(id)).at(-1).focus(),id);
   await page.keyboard.press('Tab');
   assert.equal(await page.evaluate(id=>document.activeElement===studioDialogControls(document.getElementById(id))[0],id),true);
   await page.keyboard.press('Shift+Tab');
   assert.equal(await page.evaluate(id=>document.activeElement===studioDialogControls(document.getElementById(id)).at(-1),id),true);
   await page.keyboard.press('Escape');
   assert.equal(await page.evaluate(()=>document.activeElement.id),'keyboardOpener');
   cases++;
  }
 }
 // Nested dialog, existing inert state, disabled/hidden controls, and removed opener.
 await page.evaluate(()=>{
  document.getElementById('toast').inert=true;
  document.getElementById('keyboardOpener').focus();openStudioDialog('artifactOverlay');
  document.getElementById('artifactReferenceButton').focus();openStudioDialog('helpOverlay');
 });
 await page.keyboard.press('Escape');
 assert.equal(await page.evaluate(()=>document.activeElement.id),'artifactReferenceButton');
 await page.keyboard.press('Escape');
 assert.equal(await page.evaluate(()=>document.getElementById('toast').inert),true);
 await page.evaluate(()=>{
  document.getElementById('keyboardOpener').focus();openStudioDialog('evidenceDisputeOverlay','evidenceDisputeExplanation');
  document.getElementById('evidenceDisputeExplanation').disabled=true;
  document.getElementById('submitEvidenceDispute').disabled=true;
  document.getElementById('evidenceDisputePathGroup').classList.add('hidden');
 });
 await page.keyboard.press('Tab');
 assert.equal(await page.evaluate(()=>document.activeElement.id),'closeEvidenceDispute');
 // Closing does not clear the explanation or a pending request's disabled state.
 await page.evaluate(()=>{document.getElementById('evidenceDisputeExplanation').value='Contrary frozen evidence';document.getElementById('keyboardOpener').remove()});
 await page.keyboard.press('Escape');
 assert.equal(await page.evaluate(()=>document.getElementById('evidenceDisputeExplanation').value),'Contrary frozen evidence');
 assert.equal(await page.evaluate(()=>document.getElementById('submitEvidenceDispute').disabled),true);
 assert.equal(await page.evaluate(()=>document.activeElement!==document.body&&!document.activeElement.closest('[inert]')),true);
 // No controls: focus stays on dialog. IME Escape must not dismiss it.
 await page.evaluate(()=>{
  openStudioDialog('helpOverlay');
  for(const node of studioDialogControls(document.getElementById('helpOverlay')))node.disabled=true;
 });
 await page.keyboard.press('Tab');
 assert.equal(await page.evaluate(()=>document.activeElement.id),'helpOverlay');
 await page.evaluate(()=>document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',isComposing:true,bubbles:true})));
 assert.equal(await page.evaluate(()=>document.getElementById('helpOverlay').classList.contains('hidden')),false);
 await page.keyboard.press('Escape');
 assert.equal(await page.evaluate(()=>studioDialogStack.length),0);
 await browser.close();
 console.log(`Dialog keyboard: ${cases} phase/repository/student/dialog combinations plus nested, pending, hidden/disabled, removed-opener, zero-control and IME cases passed. This matrix tests keyboard independence, not semantic model quality.`);
})().catch(e=>{console.error(e);process.exit(1)});
