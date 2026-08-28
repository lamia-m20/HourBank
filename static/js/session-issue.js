(() => {
  const dialog=document.getElementById('issue-dialog'),open=document.getElementById('open-issue-dialog');if(!dialog||!open)return;
  const details=document.getElementById('issue-details'),radios=[...dialog.querySelectorAll('input[name="reason"]')];
  function toggle(show){dialog.hidden=!show;document.body.classList.toggle('issue-dialog-open',show);if(show)radios[0]?.focus();else open.focus();}
  function syncDetails(){const other=radios.find(item=>item.checked)?.value==='other';details.required=other;details.closest('.issue-details').classList.toggle('is-required',other);}
  open.addEventListener('click',()=>toggle(true));dialog.querySelectorAll('[data-close-issue]').forEach(button=>button.addEventListener('click',()=>toggle(false)));radios.forEach(radio=>radio.addEventListener('change',syncDetails));document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!dialog.hidden)toggle(false)});
})();
