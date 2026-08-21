const STORAGE_KEY='etis:github-setup-complete';
const CHANNEL_NAME='etis-github-setup';
const STUDIO_URL='/?view=myteam';

function notifyStudio(){
  const payload=JSON.stringify({type:'github-setup-complete',completed_at:Date.now()});
  try{
    localStorage.setItem(STORAGE_KEY,payload);
    localStorage.removeItem(STORAGE_KEY);
  }catch(_e){}

  if('BroadcastChannel' in window){
    try{
      const channel=new BroadcastChannel(CHANNEL_NAME);
      channel.postMessage({type:'github-setup-complete'});
      channel.close();
    }catch(_e){}
  }
}

function closeSetupTab(){
  window.close();
}

function navigateThisTabToStudio(){
  window.location.assign(STUDIO_URL);
}

function requestOriginalStudioTab(){
  if(!('BroadcastChannel' in window)){
    navigateThisTabToStudio();
    return;
  }

  const requestId=(globalThis.crypto?.randomUUID?.()||`${Date.now()}-${Math.random()}`);
  const channel=new BroadcastChannel(CHANNEL_NAME);
  let finished=false;

  const finish=focused=>{
    if(finished)return;
    finished=true;
    channel.close();
    if(focused){
      window.setTimeout(()=>{
        window.close();
        window.setTimeout(()=>{
          if(!window.closed)navigateThisTabToStudio();
        },150);
      },75);
      return;
    }
    navigateThisTabToStudio();
  };

  channel.addEventListener('message',event=>{
    const message=event.data||{};
    if(message.type!=='github-setup-return-ack'||message.request_id!==requestId)return;
    finish(message.focused===true);
  });

  channel.postMessage({type:'github-setup-return-request',request_id:requestId});
  window.setTimeout(()=>finish(false),600);
}

document.addEventListener('DOMContentLoaded',()=>{
  notifyStudio();
  document.querySelector('#returnToStudio')?.addEventListener('click',event=>{
    event.preventDefault();
    requestOriginalStudioTab();
  });
  document.querySelector('#closeGithubSetupTab')?.addEventListener('click',closeSetupTab);
});
