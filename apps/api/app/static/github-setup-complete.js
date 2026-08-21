const STORAGE_KEY='etis:github-setup-complete';
const CHANNEL_NAME='etis-github-setup';

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

document.addEventListener('DOMContentLoaded',()=>{
  notifyStudio();
  document.querySelector('#closeGithubSetupTab')?.addEventListener('click',closeSetupTab);
  window.setTimeout(closeSetupTab,1500);
});
