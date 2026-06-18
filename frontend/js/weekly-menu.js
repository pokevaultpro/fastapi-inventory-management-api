import CONFIG from "./config.js";

const DAYS=[{index:0,label:"Lunedì",short:"Lun"},{index:1,label:"Martedì",short:"Mar"},{index:2,label:"Mercoledì",short:"Mer"},{index:3,label:"Giovedì",short:"Gio"},{index:4,label:"Venerdì",short:"Ven"},{index:5,label:"Sabato",short:"Sab"},{index:6,label:"Domenica",short:"Dom"}];
const MEALS=[{id:"breakfast",label:"Colazione",emoji:"☕"},{id:"lunch",label:"Pranzo",emoji:"🍝"},{id:"snack",label:"Spuntino",emoji:"🍎"},{id:"dinner",label:"Cena",emoji:"🍽️"}];

let currentWeekStart=getMonday(new Date()),currentMenu=null,recipes=[],activeSlot=null;
const $=id=>document.getElementById(id);

document.addEventListener("DOMContentLoaded",async()=>{
  $("weekStart").value=toISO(currentWeekStart);
  $("prevWeek").addEventListener("click",()=>shiftWeek(-7));
  $("nextWeek").addEventListener("click",()=>shiftWeek(7));
  $("weekStart").addEventListener("change",()=>{currentWeekStart=getMonday(new Date(`${$("weekStart").value}T12:00:00`));$("weekStart").value=toISO(currentWeekStart);loadAll();});
  $("downloadPdf").addEventListener("click",downloadPdf);
  $("addToCart").addEventListener("click",addWeekToCart);
  $("duplicateWeek").addEventListener("click",duplicateNextWeek);
  $("recipeSearch").addEventListener("input",renderRecipePicker);
  document.querySelectorAll("[data-close-modal]").forEach(el=>el.addEventListener("click",closeRecipeModal));
  await loadAll();
});

function token(){return localStorage.getItem("token");}
async function api(path,options={}){
  const headers={...(options.body instanceof FormData?{}:{"Content-Type":"application/json"}),...(options.headers||{}),Authorization:`Bearer ${token()}`};
  const res=await fetch(`${CONFIG.API_BASE_URL}${path}`,{...options,headers});
  if(res.status===401){localStorage.removeItem("token");window.location.href="index.html";return null;}
  if(!res.ok){let detail=res.statusText;try{const data=await res.json();detail=typeof data.detail==="string"?data.detail:JSON.stringify(data);}catch{}throw new Error(detail);}
  if(res.status===204)return null;return res.json();
}
async function loadAll(){try{const week=toISO(currentWeekStart);const [m,r]=await Promise.all([api(`/weekly-menus?week_start=${week}`),api("/weekly-menus/recipes")]);currentMenu=m;recipes=r||[];renderStats();renderPlanner();renderRecipePicker();}catch(err){showToast(err.message||"Errore caricamento menu");}}
function shiftWeek(days){currentWeekStart=addDays(currentWeekStart,days);$("weekStart").value=toISO(currentWeekStart);loadAll();}
function getMonday(date){const d=new Date(date);const day=d.getDay();const diff=(day===0?-6:1)-day;d.setDate(d.getDate()+diff);d.setHours(12,0,0,0);return d;}
function addDays(date,days){const d=new Date(date);d.setDate(d.getDate()+days);return d;}
function toISO(date){return date.toISOString().slice(0,10);}
function formatDate(date){return new Intl.DateTimeFormat("it-IT",{day:"2-digit",month:"short"}).format(date);}
function money(value){return new Intl.NumberFormat("it-IT",{style:"currency",currency:"EUR"}).format(Number(value||0));}
function absoluteImageUrl(path){if(!path)return"/static/images/placeholder.jpg";if(/^https?:\/\//i.test(path))return path;if(path.startsWith("/"))return`${window.location.origin}${path}`;return`${window.location.origin}/${path}`;}
function imageOrPlaceholder(path){return path||"/static/images/placeholder.jpg";}
function getItem(dayIndex,mealType){return(currentMenu?.items||[]).find(i=>Number(i.day_index)===Number(dayIndex)&&i.meal_type===mealType)||null;}
function renderStats(){const end=addDays(currentWeekStart,6);$("weekRange").textContent=`${formatDate(currentWeekStart)} → ${formatDate(end)}`;$("plannedCount").textContent=currentMenu?.summary?.planned_meals||0;$("estimatedTotal").textContent=money(currentMenu?.summary?.estimated_total||0);$("recipesCount").textContent=recipes.length;}

function renderPlanner(){
  const grid=$("plannerGrid"),todayISO=toISO(new Date());
  grid.innerHTML=DAYS.map(day=>{const dayDate=addDays(currentWeekStart,day.index),isToday=toISO(dayDate)===todayISO;return`<article class="day-column ${isToday?"today":""}"><header class="day-head"><div><h3>${day.label}</h3><span>${formatDate(dayDate)}</span></div></header>${MEALS.map(meal=>renderMealSlot(day,meal)).join("")}</article>`;}).join("");
  grid.querySelectorAll("[data-add-slot],[data-change-slot]").forEach(btn=>btn.addEventListener("click",()=>openRecipeModal(Number(btn.dataset.day),btn.dataset.meal)));
  grid.querySelectorAll("[data-remove-item]").forEach(btn=>btn.addEventListener("click",()=>removeItem(Number(btn.dataset.removeItem))));
  grid.querySelectorAll("img").forEach(img=>img.addEventListener("error",()=>{img.src="/static/images/placeholder.jpg";}));
}
function renderMealSlot(day,meal){
  const item=getItem(day.index,meal.id),recipe=item?.recipe;
  if(!recipe)return`<section class="meal-slot"><div class="slot-top"><span class="slot-label">${meal.emoji} ${meal.label}</span><button class="add-slot-btn" type="button" data-add-slot data-day="${day.index}" data-meal="${meal.id}">+</button></div><div class="empty-slot">Aggiungi ricetta</div></section>`;
  return`<section class="meal-slot filled"><div class="slot-top"><span class="slot-label">${meal.emoji} ${meal.label}</span></div><div class="recipe-slot-card"><img src="${escapeAttr(imageOrPlaceholder(recipe.image))}" alt="${escapeAttr(recipe.name)}" /><div><h4>${escapeHTML(recipe.name)}</h4><div class="recipe-meta"><span>${recipe.prep_time_minutes?`${recipe.prep_time_minutes} min`:"tempo n/d"}</span><span>${recipe.servings||1} porz.</span><span>${money(recipe.estimated_total)}</span></div></div></div><div class="slot-actions"><button class="secondary-btn" type="button" data-change-slot data-day="${day.index}" data-meal="${meal.id}">Cambia</button><button class="danger-btn" type="button" data-remove-item="${item.id}">Rimuovi</button></div></section>`;
}
function openRecipeModal(dayIndex,mealType){activeSlot={dayIndex,mealType};const day=DAYS.find(d=>d.index===dayIndex),meal=MEALS.find(m=>m.id===mealType);$("modalSlotLabel").textContent=`${day?.label||""} · ${meal?.label||""}`;$("recipeSearch").value="";renderRecipePicker();$("recipeModal").classList.remove("hidden");}
function closeRecipeModal(){$("recipeModal").classList.add("hidden");activeSlot=null;}
function renderRecipePicker(){
  const container=$("recipePickerList");if(!container)return;const q=($("recipeSearch")?.value||"").trim().toLowerCase();
  const filtered=recipes.filter(r=>!q||`${r.name||""} ${r.description||""}`.toLowerCase().includes(q));
  if(!filtered.length){container.innerHTML=`<div class="empty-slot" style="grid-column:1/-1;min-height:150px;">Nessuna ricetta trovata. Crea prima una ricetta nella sezione Ricette.</div>`;return;}
  container.innerHTML=filtered.map(recipe=>`<article class="recipe-picker-card"><img src="${escapeAttr(imageOrPlaceholder(recipe.image))}" alt="${escapeAttr(recipe.name)}" /><div><h3>${escapeHTML(recipe.name)}</h3><p>${recipe.items_count||0} ingredienti · ${recipe.prep_time_minutes?`${recipe.prep_time_minutes} min · `:""}${money(recipe.estimated_total)}</p></div><button type="button" data-select-recipe="${recipe.id}">Scegli</button></article>`).join("");
  container.querySelectorAll("img").forEach(img=>img.addEventListener("error",()=>{img.src="/static/images/placeholder.jpg";}));
  container.querySelectorAll("[data-select-recipe]").forEach(btn=>btn.addEventListener("click",()=>selectRecipe(Number(btn.dataset.selectRecipe))));
}
async function selectRecipe(recipeId){if(!activeSlot)return;try{currentMenu=await api("/weekly-menus/item",{method:"POST",body:JSON.stringify({week_start:toISO(currentWeekStart),day_index:activeSlot.dayIndex,meal_type:activeSlot.mealType,recipe_id:recipeId})});renderStats();renderPlanner();closeRecipeModal();showToast("Ricetta aggiunta al menu");}catch(err){showToast(err.message||"Errore inserimento ricetta");}}
async function removeItem(itemId){try{currentMenu=await api(`/weekly-menus/item/${itemId}`,{method:"DELETE"});renderStats();renderPlanner();showToast("Ricetta rimossa");}catch(err){showToast(err.message||"Errore rimozione");}}
async function addWeekToCart(){if(!currentMenu?.menu?.id)return;if(!confirm("Aggiungo tutti gli ingredienti del menu settimanale alla lista della spesa?"))return;try{const data=await api(`/weekly-menus/${currentMenu.menu.id}/add-to-cart`,{method:"POST",body:JSON.stringify({replace_cart:false})});showToast(`${data.added_count} prodotti aggiunti alla lista`);}catch(err){showToast(err.message||"Errore lista spesa");}}
async function duplicateNextWeek(){if(!currentMenu?.menu?.id)return;try{const data=await api(`/weekly-menus/${currentMenu.menu.id}/duplicate-next-week`,{method:"POST"});currentWeekStart=new Date(`${data.menu.week_start}T12:00:00`);$("weekStart").value=toISO(currentWeekStart);currentMenu=data;renderStats();renderPlanner();showToast("Menu duplicato sulla prossima settimana");}catch(err){showToast(err.message||"Errore duplicazione");}}
function showToast(message){const toast=$("toast");toast.textContent=message;toast.classList.add("show");clearTimeout(showToast._timer);showToast._timer=setTimeout(()=>toast.classList.remove("show"),2800);}

async function downloadPdf(){
  if(!currentMenu)return;if(!window.jspdf?.jsPDF){showToast("PDF non disponibile: CDN jsPDF non caricata");return;}
  try{
    showToast("Creo PDF...");
    const {jsPDF}=window.jspdf;const doc=new jsPDF({orientation:"landscape",unit:"mm",format:"a4"});
    const pageW=297,pageH=210,margin=10,startY=34,colW=(pageW-margin*2)/7,slotH=34;
    drawHeader(doc,pageW,"Menu settimanale",`${formatDate(currentWeekStart)} - ${formatDate(addDays(currentWeekStart,6))}`);
    for(const day of DAYS){const x=margin+day.index*colW,dayDate=addDays(currentWeekStart,day.index);doc.setFillColor(240,253,244);doc.setDrawColor(187,247,208);doc.roundedRect(x+1,startY,colW-2,10,2,2,"FD");doc.setFont("helvetica","bold");doc.setFontSize(9.5);doc.setTextColor(15,23,42);doc.text(day.short,x+3,startY+6.5);doc.setFont("helvetica","normal");doc.setFontSize(7);doc.setTextColor(100,116,139);doc.text(formatDate(dayDate),x+colW-4,startY+6.5,{align:"right"});for(let mi=0;mi<MEALS.length;mi++){const meal=MEALS[mi],y=startY+13+mi*slotH,item=getItem(day.index,meal.id);await drawPdfSlot(doc,x+1,y,colW-2,slotH-2,meal,item);}}
    drawFooter(doc,pageW,pageH);
    const used=currentMenu.items.filter(i=>i.recipe);if(used.length){doc.addPage("a4","portrait");await drawRecipeDetails(doc,used);}
    doc.save(`menu-settimanale-${toISO(currentWeekStart)}.pdf`);showToast("PDF scaricato");
  }catch(err){console.error(err);showToast("Errore PDF: "+(err.message||"impossibile generare"));}
}
function drawHeader(doc,pageW,title,subtitle){doc.setFillColor(22,163,74);doc.roundedRect(10,8,pageW-20,18,4,4,"F");doc.setTextColor(255,255,255);doc.setFont("helvetica","bold");doc.setFontSize(17);doc.text(title,16,19);doc.setFont("helvetica","normal");doc.setFontSize(9);doc.text(subtitle,pageW-16,19,{align:"right"});}
function drawFooter(doc,pageW,pageH){doc.setTextColor(100,116,139);doc.setFont("helvetica","normal");doc.setFontSize(7);doc.text(`Creato con SmartGrocery · ${currentMenu.summary.planned_meals} pasti · ${money(currentMenu.summary.estimated_total)}`,pageW/2,pageH-6,{align:"center"});}
async function drawPdfSlot(doc,x,y,w,h,meal,item){doc.setDrawColor(226,232,240);doc.setFillColor(248,250,252);doc.roundedRect(x,y,w,h,2,2,"FD");doc.setTextColor(22,101,52);doc.setFont("helvetica","bold");doc.setFontSize(6.8);doc.text(`${meal.label}`,x+2.2,y+5);if(!item?.recipe){doc.setTextColor(148,163,184);doc.setFont("helvetica","normal");doc.setFontSize(7);doc.text("vuoto",x+w/2,y+h/2+2,{align:"center"});return;}const recipe=item.recipe,img=await loadImageData(recipe.image);if(img){try{doc.addImage(img,"JPEG",x+2.2,y+7,10,10);}catch{}}else{doc.setFillColor(220,252,231);doc.roundedRect(x+2.2,y+7,10,10,1.5,1.5,"F");}doc.setTextColor(15,23,42);doc.setFont("helvetica","bold");doc.setFontSize(6.7);doc.text(doc.splitTextToSize(recipe.name||"",w-16).slice(0,3),x+14,y+9);doc.setTextColor(100,116,139);doc.setFont("helvetica","normal");doc.setFontSize(6);doc.text(`${recipe.servings||1} porz. · ${money(recipe.estimated_total)}`,x+2.2,y+h-3);}
async function drawRecipeDetails(doc,items){let y=18;doc.setFont("helvetica","bold");doc.setTextColor(15,23,42);doc.setFontSize(18);doc.text("Dettaglio ricette",14,y);y+=10;const unique=[],seen=new Set();for(const item of items){if(!item.recipe||seen.has(item.recipe.id))continue;seen.add(item.recipe.id);unique.push(item.recipe);}for(const recipe of unique){if(y>238){doc.addPage("a4","portrait");y=18;}doc.setDrawColor(226,232,240);doc.setFillColor(248,250,252);doc.roundedRect(12,y,186,48,4,4,"FD");const img=await loadImageData(recipe.image);if(img){try{doc.addImage(img,"JPEG",16,y+6,34,34);}catch{}}doc.setTextColor(15,23,42);doc.setFont("helvetica","bold");doc.setFontSize(12);doc.text(doc.splitTextToSize(recipe.name||"",130).slice(0,2),56,y+12);doc.setFont("helvetica","normal");doc.setTextColor(100,116,139);doc.setFontSize(8);doc.text(`${recipe.items_count||0} ingredienti · ${recipe.servings||1} porzioni · ${money(recipe.estimated_total)}`,56,y+24);const ingredients=(recipe.items||[]).slice(0,5).map(i=>`• ${i.product?.name||"Ingrediente"} x${i.cart_quantity||i.quantity||1}`);doc.text(doc.splitTextToSize(ingredients.join("\n"),130),56,y+32);y+=56;}}
const imageCache=new Map();async function loadImageData(path){if(!path)return null;const url=absoluteImageUrl(path);if(imageCache.has(url))return imageCache.get(url);try{const res=await fetch(url,{mode:"cors",cache:"force-cache"});if(!res.ok)throw new Error("image not found");const blob=await res.blob(),data=await blobToDataURL(blob);imageCache.set(url,data);return data;}catch{imageCache.set(url,null);return null;}}
function blobToDataURL(blob){return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result));reader.onerror=reject;reader.readAsDataURL(blob);});}
function escapeHTML(value){return String(value??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;");}
function escapeAttr(value){return escapeHTML(value).replaceAll('"',"&quot;");}
