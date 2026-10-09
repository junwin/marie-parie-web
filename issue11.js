const categories=[["clothing","Couture Cuteness","Clothing"],["jewelry","Ooh La La Bijoux","Jewelry"],["accessories","Très Chic Accessories","Accessories"],["vintage","Va Va Voom","Vintage"],["france","Parisian Pleasures","Handmade + Made in France"],["treasures","Little Frenchy Finds","Décor & Little Treasures"]];
const dialog=document.querySelector('#category-dialog');
document.querySelectorAll('[data-category]').forEach(a=>a.addEventListener('click',e=>{e.preventDefault();const item=categories.find(x=>x[0]===a.dataset.category);document.querySelector('#dialog-title').textContent=item[1];document.querySelector('#dialog-description').textContent=item[2];document.querySelector('#dialog-image').src=a.querySelector('img').src;dialog.showModal()}));
document.querySelectorAll('.form-open').forEach(b=>b.addEventListener('click',()=>document.getElementById(b.dataset.dialog).showModal()));
document.querySelectorAll('.dialog .close').forEach(b=>b.addEventListener('click',()=>b.closest('dialog').close()));
document.querySelectorAll('dialog').forEach(d=>d.addEventListener('click',e=>{if(e.target===d){const r=d.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)d.close()}}));
const CONTACT_API="https://marie-parie-contact-api-dhfkcxhbapbyh9b3.centralus-01.azurewebsites.net/api/contact";
document.querySelectorAll('.email-form').forEach(form=>form.addEventListener('submit',async e=>{
  e.preventDefault();
  if(!form.reportValidity())return;
  const status=form.querySelector('.form-status');
  const submit=form.querySelector('button[type="submit"]');
  const token=form.querySelector('input[name="cf-turnstile-response"]')?.value;
  if(!token){status.textContent="Please complete the security verification.";return;}
  const data=new FormData(form);
  const payload={kind:form.dataset.kind,firstName:data.get('firstName'),lastName:data.get('lastName'),
    email:data.get('email'),turnstileToken:token};
  if(payload.kind==='contact')payload.message=data.get('message');
  else {payload.phone=data.get('phone')||'';payload.consent=data.get('consent')==='on';}
  submit.disabled=true;status.textContent="Sending your message…";
  try{
    const response=await fetch(CONTACT_API,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const result=await response.json().catch(()=>({}));
    if(!response.ok)throw new Error((result.message||"Unable to send. Please try again.")+(result.requestId?` (Reference: ${result.requestId})`:""));
    status.textContent=result.message||"Thank you! Your message has been sent.";
    form.reset();
  }catch(error){
    status.textContent=error.message||"We could not send your message. Please try again.";
  }finally{
    submit.disabled=false;
    if(window.turnstile){const widget=form.querySelector('.cf-turnstile');if(widget)window.turnstile.reset(widget);}
  }
}));