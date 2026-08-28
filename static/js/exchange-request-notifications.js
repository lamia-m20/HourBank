(function(){
  const config=document.getElementById('exchange-request-notifications');
  if(!config)return;
  if(document.documentElement.lang==='ar'){
    document.querySelectorAll('.new-request-badge').forEach(item=>item.textContent='جديد');
  }
  const badge=document.getElementById('exchange-requests-badge');
  const key='hourbank-shown-exchange-requests';
  let shown=[];
  try{shown=JSON.parse(localStorage.getItem(key)||'[]')}catch(error){}
  function showToast(item){
    if(!item||shown.includes(item.id))return;
    shown.push(item.id);localStorage.setItem(key,JSON.stringify(shown.slice(-100)));
    const toast=document.createElement('aside'),title=document.createElement('strong');
    const detail=document.createElement('span'),link=document.createElement('a');
    toast.className='exchange-request-toast';title.textContent=config.dataset.label;
    detail.textContent=`${item.requester} ${config.dataset.requested} ${item.skill}`;
    link.href=item.url;link.textContent=config.dataset.view;
    toast.append(title,detail,link);document.body.appendChild(toast);
    setTimeout(()=>toast.remove(),10000);
  }
  async function poll(){
    if(document.hidden)return;
    try{
      const response=await fetch(config.dataset.url,{headers:{Accept:'application/json'}});
      if(!response.ok)return;
      const data=await response.json();
      if(badge){badge.textContent=data.exchange_requests||'';badge.hidden=!data.exchange_requests}
      showToast(data.latest_request);
    }catch(error){}
  }
  setInterval(poll,15000);
})();
