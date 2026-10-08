/* Only injected by the 127.0.0.1:8766 local simulator, never by production. */
(()=>{function ready(){
 const bar=document.createElement('section');bar.id='studentSimulationBanner';bar.setAttribute('role','status');
 bar.style.cssText='position:sticky;top:0;z-index:10000;background:#ffe69c;color:#172018;padding:10px 16px;font:600 14px system-ui;display:flex;gap:10px;align-items:center;flex-wrap:wrap;border-bottom:3px solid #765300';
 bar.innerHTML='<strong>SIMULATION — synthetic evidence, no GitHub or AI</strong><span id="simStatus">Loading…</span><button type="button" data-sim="older-newer">Test old review vs newer evidence</button><details id="simMoreControls"><summary style="cursor:pointer;padding:7px 9px;border:1px solid #765300;border-radius:5px">Other simulation tests ▾</summary><div style="display:flex;flex-wrap:wrap;gap:7px;padding:9px 0"><button type="button" data-sim="long-conversation">Load long conversation</button><button type="button" data-sim="advance">Simulate new commit</button><button type="button" data-sim="mixed-history">Create 16 mixed reviews</button><button type="button" data-sim="fail-start">Fail next review start</button><button type="button" data-sim="fail-response">Fail next reply</button><button type="button" data-sim="reset">Reset all simulation data</button></div></details>';
 const instructions=document.createElement('div');instructions.id='simScenarioInstructions';instructions.setAttribute('role','status');instructions.setAttribute('aria-live','polite');instructions.style.cssText='display:none;width:100%;font:600 13px/1.5 system-ui;padding:9px 11px;background:#fff2c5;border:1px solid #795b00;border-radius:6px';bar.appendChild(instructions);
 document.body.prepend(bar);
 // Keep a local simulation in its synthetic origin, even if Studio exposes an outbound evidence link.
 document.addEventListener('click',event=>{const link=event.target.closest?.('a[href]');if(!link)return;try{if(new URL(link.href,location.href).origin!==location.origin){event.preventDefault();document.getElementById('simStatus').textContent='External navigation blocked in simulation.';}}catch(_){event.preventDefault();}},true);
 function show(s){document.getElementById('simStatus').textContent=`Commit ${s.commit} · ${s.sessions} review(s) · ${s.snapshots} snapshot(s)${s.failure_queued?' · next start will fail':''}${s.response_failure_queued?' · next reply will fail':''}`;
   instructions.textContent=s.scenario_hint||'';instructions.style.display=s.scenario_hint?'block':'none';}
 bar.querySelectorAll('[data-sim]').forEach(button=>{button.style.cssText='color:#172018;background:#fff5d6;border:1px solid #765300;border-radius:5px;padding:7px 10px;font:600 12px system-ui;cursor:pointer';button.onclick=async()=>{button.disabled=true;try{const r=await fetch('/__simulation/'+button.dataset.sim,{method:'POST'});if(!r.ok)throw Error('Simulation control failed');show(await r.json());if(['reset','older-newer','long-conversation'].includes(button.dataset.sim))location.replace('/');}catch(_){document.getElementById('simStatus').textContent='Simulation control failed';}finally{button.disabled=false;}}});
 // Keep the synthetic counter accurate after Studio review lifecycle mutations.
 // This wrapper exists only in the loopback simulator's injected script.
 const nativeFetch=window.fetch.bind(window);
 window.fetch=async (input,options={})=>{
   const response=await nativeFetch(input,options);
   const path=typeof input==='string'?input:input?.url||'';
   const method=String(options.method||input?.method||'GET').toUpperCase();
   if(response.ok&&method==='POST'&&/^\/api\/v1\/reviews\/(start|[0-9]+\/(respond|complete))/.test(path)){
     nativeFetch('/__simulation/state').then(r=>r.json()).then(show).catch(()=>{});
   }
   return response;
 };
 nativeFetch('/__simulation/state').then(r=>r.json()).then(show);
}if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',ready,{once:true});else ready();})();
