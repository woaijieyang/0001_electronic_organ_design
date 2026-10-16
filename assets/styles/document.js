(()=>{
 const bar=document.querySelector('.progress');
 function progress(){const d=document.documentElement;bar.style.width=(100*d.scrollTop/Math.max(1,d.scrollHeight-d.clientHeight))+'%'}
 addEventListener('scroll',progress,{passive:true});progress();
 const links=[...document.querySelectorAll('.sidebar a[href^="#"]')];
 const hs=[...document.querySelectorAll('article h2[id]')];
 function activate(){let cur=hs[0];for(const h of hs){if(h.getBoundingClientRect().top<=130)cur=h}links.forEach(a=>a.classList.toggle('active',a.hash==='#'+cur?.id))}
 addEventListener('scroll',activate,{passive:true});activate();
 document.querySelector('.to-top')?.addEventListener('click',()=>scrollTo({top:0,behavior:'smooth'}));
 document.querySelector('[data-expand]')?.addEventListener('click',e=>{const all=[...document.querySelectorAll('.appendix-block')];const open=all.some(d=>!d.open);all.forEach(d=>d.open=open);e.target.textContent=open?'收起附录':'展开全部附录'});
 let printState=[];addEventListener('beforeprint',()=>{printState=[...document.querySelectorAll('details')].map(d=>[d,d.open]);printState.forEach(([d])=>d.open=true)});addEventListener('afterprint',()=>printState.forEach(([d,v])=>d.open=v));
 function reveal(){let id;try{id=decodeURIComponent(location.hash.slice(1))}catch{return}const el=document.getElementById(id);if(!el)return;let p=el.parentElement;while(p){if(p.tagName==='DETAILS')p.open=true;p=p.parentElement}}
 addEventListener('hashchange',reveal);reveal();
 document.querySelectorAll('.mobile-nav a').forEach(a=>a.addEventListener('click',()=>{document.querySelector('.mobile-nav').open=false}));
})();
