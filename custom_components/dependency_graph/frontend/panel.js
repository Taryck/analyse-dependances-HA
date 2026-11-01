/** Explorateur Home Assistant. Aucun CDN, aucune bibliothèque externe. */
class DependencyGraphPanel extends HTMLElement {
  set hass(value) {
    this._hass=value;
    if (this.isConnected && !this._started) this.start();
  }
  connectedCallback() {
    this.attachShadow({mode:'open'});
    this.shadowRoot.innerHTML=`<style>
      :host{display:block;background:var(--primary-background-color);color:var(--primary-text-color);min-height:100%;font:14px system-ui,sans-serif}
      .wrap{max-width:1400px;margin:auto;padding:22px}.toolbar{display:flex;gap:9px;flex-wrap:wrap;margin-bottom:16px}
      input,select,button{background:var(--card-background-color);color:var(--primary-text-color);border:1px solid var(--divider-color);border-radius:7px;padding:10px;font:inherit}
      input{min-width:230px;flex:1}button{cursor:pointer}button:hover,a:hover{color:var(--primary-color)}
      table{width:100%;border-collapse:collapse;background:var(--card-background-color)}td,th{padding:9px;border-bottom:1px solid var(--divider-color);text-align:left}tr:hover{background:var(--secondary-background-color)}
      a{color:var(--primary-color);cursor:pointer;text-decoration:none}pre{overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;background:var(--secondary-background-color);padding:14px;border-radius:8px}
      .layout{display:grid;grid-template-columns:minmax(330px,1fr) minmax(380px,1.2fr);gap:20px}
      .panel{background:var(--card-background-color);border-radius:10px;padding:14px;min-width:0}
      .missing{color:var(--error-color);font-weight:bold}.muted{color:var(--secondary-text-color)}.line{margin:8px 0;padding:8px;border-bottom:1px solid var(--divider-color)}
      @media(max-width:950px){.layout{grid-template-columns:1fr}}
    </style><div class="wrap"><h1>Graphe des dépendances</h1><div class="toolbar">
      <input id="query" placeholder="ID ou nom (ex. *sdb*rdc*)" aria-label="Recherche" />
      <select id="domain"><option value="">Tous les domaines</option></select>
      <select id="scope"><option value="">Toutes les catégories</option><option value="helpers">Assistants</option><option value="automation">Automatisations</option></select>
      <select id="category"><option value="">Toutes les catégories</option></select>
      <button id="analyze">Analyser</button></div>
      <p id="status" role="status" class="muted"></p><div class="layout"><div class="panel"><h2>Objets <span id="total"></span></h2><div style="overflow:auto"><table><thead><tr><th>Identifiant</th><th>Nom</th><th>Pièce</th></tr></thead><tbody id="rows"></tbody></table></div><div class="toolbar"><button id="prev">Précédent</button><button id="next">Suivant</button></div></div>
      <div class="panel" id="details"><h2>Détails</h2><p>Sélectionnez un objet.</p></div></div></div>`;
    const $=id=>this.shadowRoot.getElementById(id);this.$=$;
    this.offset=0;this.limit=100;
    $('query').addEventListener('input',()=>{clearTimeout(this._debounce);this._debounce=setTimeout(()=>{this.offset=0;this.list()},250)});
    for(const id of ['domain','scope','category'])$(id).addEventListener('change',()=>{this.offset=0;if(id==='scope')this.categories();this.list()});
    $('prev').onclick=()=>{this.offset=Math.max(0,this.offset-this.limit);this.list()};
    $('next').onclick=()=>{this.offset+=this.limit;this.list()};
    $('analyze').onclick=()=>this.analyze();
    if(this._hass)this.start();
  }
  async api(type,extra={}){return this._hass.callWS({type:'dependency_graph/'+type,...extra})}
  async start(){this._started=true;try{this.values=await this.api('values');this.fill('domain',this.values.domain||[]);this.categories();await this.list();}catch(e){this.status(e.message)}}
  status(s){this.$('status').textContent=s}
  fill(id,values){const el=this.$(id),selected=el.value;while(el.options.length>1)el.remove(1);for(const value of values){const opt=document.createElement('option');opt.value=value;opt.textContent=value;el.add(opt)}el.value=selected}
  categories(){const scope=this.$('scope').value;const all=scope?[...(this.values['category_'+scope]||[])]:[...(this.values.category_helpers||[]),...(this.values.category_automation||[])];this.fill('category',[...new Set(all)].sort())}
  async list(){try{const result=await this.api('list',{query:this.$('query').value,domain:this.$('domain').value,scope:this.$('scope').value,category:this.$('category').value,offset:this.offset,limit:this.limit});this.$('total').textContent=`(${result.total})`;const body=this.$('rows');body.replaceChildren();for(const obj of result.items){const tr=document.createElement('tr');for(const value of [obj.object_id,obj.name,obj.area_name]){const td=document.createElement('td');if(value===obj.object_id){const a=this.link(obj.object_id);td.append(a)}else td.textContent=value||'—';tr.append(td)}body.append(tr)}this.$('prev').disabled=this.offset===0;this.$('next').disabled=this.offset+this.limit>=result.total;this.status(result.analyzed?'Analyse disponible':'Cliquez sur Analyser pour créer l’inventaire.')}catch(e){this.status(e.message)}}
  link(id){const a=document.createElement('a');a.href='#'+encodeURIComponent(id);a.textContent=id;a.onclick=e=>{e.preventDefault();this.detail(id)};return a}
  async detail(id){try{const data=await this.api('detail',{identifier:id});const box=this.$('details');box.replaceChildren();const title=document.createElement('h2');title.textContent=data.object.name||id;box.append(title);const meta=document.createElement('p');meta.textContent=id+' · '+(data.object.source_file||'');box.append(meta);for(const [key,label] of [['depend_on','Dépend de'],['required_by','Utilisé par']]){const h=document.createElement('h3');h.textContent=label+' ('+(data[key]||[]).length+')';box.append(h);for(const item of data[key]||[]){const line=document.createElement('div');line.className='line';line.append(this.link(item.id));if(item.missing){const badge=document.createElement('span');badge.className='missing';badge.textContent='  ⚠ Introuvable';line.append(badge)}const file=document.createElement('div');file.className='muted';file.textContent=item.file||'';line.append(file);for(const loc of item.locations||[]){const p=document.createElement('div');p.className='muted';p.textContent='↳ '+loc.path;line.append(p)}box.append(line)}}for(const [key,label] of [['object','Propriétés'],['configuration','Configuration source']]){const h=document.createElement('h3');h.textContent=label;const pre=document.createElement('pre');pre.textContent=JSON.stringify(data[key],null,2);box.append(h,pre)}this.status('Fiche : '+id)}catch(e){this.status(e.message)}}
  async analyze(){const b=this.$('analyze');b.disabled=true;this.status('Analyse en cours…');try{const result=await this.api('analyze');this.status(`Analyse terminée : ${result.objects} objets, ${result.dependencies} références, ${result.errors} erreurs`);this.values=await this.api('values');this.fill('domain',this.values.domain||[]);this.categories();this.offset=0;await this.list()}catch(e){this.status('Échec : '+e.message)}finally{b.disabled=false}}
}
customElements.define('dependency-graph-panel',DependencyGraphPanel);
