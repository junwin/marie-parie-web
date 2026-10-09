const categories=[
  {id:"clothing",title:"Couture Cuteness",description:"A few of Heidi’s current couture cuteness favorites…",images:[
    {src:"assets/couture-look-1.jpg",alt:"Autumn outfit with a rust cardigan, lace camisole, floral skirt and tall brown boots"},
    {src:"assets/couture-look-2.jpg",alt:"Blue striped French-inspired sweater with relaxed blue trousers"},
    {src:"assets/couture-look-3.jpg",alt:"Bohemian floral kimono with a burgundy top and ruffled cream trousers"},
    {src:"assets/couture-look-4.jpg",alt:"Orange and pink statement cardigan styled with jeans"},
    {src:"assets/couture-look-5.jpg",alt:"Three-view collage of a red floral fringed kimono outfit"},
    {src:"assets/couture-look-6.jpg",alt:"Flowing dark printed maxi dress styled with a textured scarf"}
  ]},
  {id:"jewelry",title:"Ooh La La Bijoux",description:"Jewelry"},
  {id:"accessories",title:"Très Chic Accessories",description:"Accessories"},
  {id:"vintage",title:"Va Va Voom",description:"Vintage"},
  {id:"france",title:"Parisian Pleasures",description:"Handmade + Made in France"},
  {id:"treasures",title:"Little Frenchy Finds",description:"Décor & Little Treasures"}
];

const dialog=document.querySelector('#category-dialog');
const dialogTitle=document.querySelector('#dialog-title');
const dialogImage=document.querySelector('#dialog-image');
const dialogDescription=document.querySelector('#dialog-description');
const dialogNote=dialogDescription?.nextElementSibling;

const gallery=document.createElement('div');
gallery.id='category-gallery';
gallery.className='category-gallery';
gallery.hidden=true;
dialogDescription?.after(gallery);

const galleryStyle=document.createElement('style');
galleryStyle.textContent=`
#category-dialog{max-width:900px}
#category-dialog #dialog-title{text-align:center;font-size:42px;line-height:1.1;margin:8px 0 6px}
#category-dialog #dialog-description{text-align:center;color:#685350;margin:0 0 22px}
#dialog-image[hidden],#category-gallery[hidden]{display:none!important}
.category-gallery{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin:20px 0 24px}
.gallery-thumb{appearance:none;border:2px solid var(--gold);border-radius:14px;background:var(--cream);padding:6px;cursor:zoom-in;transition:transform .16s ease,box-shadow .16s ease;overflow:hidden}
.gallery-thumb:hover{transform:translateY(-3px);box-shadow:0 8px 18px #4d292022}
.category-gallery .gallery-thumb img{display:block;width:100%;height:250px;max-width:none;max-height:none;margin:0;object-fit:contain;border-radius:9px;background:#fff}
#category-dialog .gallery-note{text-align:center;font-style:italic;color:#685350}
#category-dialog>.pill{display:table;margin:18px auto 0}
.gallery-lightbox{position:relative;width:min(92vw,900px);max-width:900px;border:3px solid var(--gold);border-radius:20px;padding:18px 58px 16px;background:var(--cream);color:var(--ink)}
.gallery-lightbox::backdrop{background:#21191bcc}
.gallery-lightbox figure{margin:0;display:grid;justify-items:center}
.gallery-lightbox img{display:block;max-width:100%;max-height:78vh;width:auto;height:auto;border-radius:12px}
.gallery-lightbox figcaption{margin-top:10px;color:#685350;font-size:14px;text-align:center}
.lightbox-close,.lightbox-nav{border:0;background:#fffaf4dd;color:var(--ink);cursor:pointer;line-height:1;box-shadow:0 2px 10px #21191b22}
.lightbox-close{position:absolute;right:12px;top:10px;width:38px;height:38px;border-radius:50%;font-size:28px;z-index:2}
.lightbox-nav{position:absolute;top:50%;transform:translateY(-50%);width:42px;height:54px;border-radius:22px;font-size:36px;z-index:2}
.lightbox-prev{left:8px}.lightbox-next{right:8px}
@media(max-width:700px){
  #category-dialog{padding:24px 18px}
  #category-dialog #dialog-title{font-size:36px}
  .category-gallery{grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
  .category-gallery .gallery-thumb img{height:220px}
  .gallery-lightbox{padding:52px 42px 14px}
  .lightbox-nav{width:36px;height:48px;font-size:30px}
}
@media(prefers-reduced-motion:reduce){.gallery-thumb{transition:none}}
`;
document.head.appendChild(galleryStyle);

const lightbox=document.createElement('dialog');
lightbox.id='gallery-lightbox';
lightbox.className='gallery-lightbox';
lightbox.setAttribute('aria-label','Couture Cuteness photo viewer');
lightbox.innerHTML=`<button class="lightbox-close" type="button" aria-label="Close photo">×</button><button class="lightbox-nav lightbox-prev" type="button" aria-label="Previous photo">‹</button><figure><img id="lightbox-image" alt=""><figcaption id="lightbox-caption"></figcaption></figure><button class="lightbox-nav lightbox-next" type="button" aria-label="Next photo">›</button>`;
document.body.appendChild(lightbox);

const lightboxImage=lightbox.querySelector('#lightbox-image');
const lightboxCaption=lightbox.querySelector('#lightbox-caption');
let lightboxImages=[];
let lightboxIndex=0;
function renderLightbox(){
  if(!lightboxImages.length)return;
  const item=lightboxImages[lightboxIndex];
  lightboxImage.src=item.src;
  lightboxImage.alt=item.alt;
  lightboxCaption.textContent=`Look ${lightboxIndex+1} of ${lightboxImages.length}`;
}
function openLightbox(index,images){
  lightboxImages=images;
  lightboxIndex=index;
  renderLightbox();
  lightbox.showModal();
}
function stepLightbox(delta){
  if(!lightboxImages.length)return;
  lightboxIndex=(lightboxIndex+delta+lightboxImages.length)%lightboxImages.length;
  renderLightbox();
}
lightbox.querySelector('.lightbox-close').addEventListener('click',()=>lightbox.close());
lightbox.querySelector('.lightbox-prev').addEventListener('click',()=>stepLightbox(-1));
lightbox.querySelector('.lightbox-next').addEventListener('click',()=>stepLightbox(1));
lightbox.addEventListener('keydown',e=>{
  if(e.key==='ArrowLeft'){e.preventDefault();stepLightbox(-1)}
  if(e.key==='ArrowRight'){e.preventDefault();stepLightbox(1)}
});

function showCategoryGallery(item){
  gallery.innerHTML='';
  item.images.forEach((image,index)=>{
    const button=document.createElement('button');
    button.type='button';
    button.className='gallery-thumb';
    button.setAttribute('aria-label',`Open look ${index+1} of ${item.images.length}`);
    const img=document.createElement('img');
    img.src=image.src;
    img.alt=image.alt;
    img.loading='lazy';
    img.decoding='async';
    button.appendChild(img);
    button.addEventListener('click',()=>openLightbox(index,item.images));
    gallery.appendChild(button);
  });
  gallery.hidden=false;
  dialogImage.hidden=true;
  if(dialogNote){dialogNote.textContent='See something you adore?';dialogNote.classList.add('gallery-note')}
}
function showCategoryImage(anchor){
  gallery.hidden=true;
  gallery.innerHTML='';
  dialogImage.hidden=false;
  const source=anchor.querySelector('img');
  dialogImage.src=source.src;
  dialogImage.alt=source.alt;
  if(dialogNote){dialogNote.textContent='Visit the boutique to discover the latest finds, or get in touch to ask about this collection.';dialogNote.classList.remove('gallery-note')}
}

document.querySelectorAll('[data-category]').forEach(anchor=>anchor.addEventListener('click',e=>{
  e.preventDefault();
  const item=categories.find(category=>category.id===anchor.dataset.category);
  if(!item)return;
  dialogTitle.textContent=item.title;
  dialogDescription.textContent=item.description;
  if(item.images)showCategoryGallery(item);else showCategoryImage(anchor);
  dialog.showModal();
}));

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
  const payload={kind:form.dataset.kind,firstName:data.get('firstName'),lastName:data.get('lastName'),email:data.get('email'),turnstileToken:token};
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
