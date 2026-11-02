/**
 * GUIDE DE LECTURE DU FRONTEND
 * ===========================
 *
 * CONTRAT DES DONNÉES
 * -------------------
 * Le navigateur ne lit jamais directement le répertoire .storage.
 * La commande values renvoie les valeurs disponibles pour les listes.
 * La commande list renvoie un tableau paginé et un total filtré.
 * La commande detail renvoie la fiche de l'objet sélectionné.
 * La commande analyze reconstruit l'inventaire à la demande.
 * Les réponses sont envoyées au composant par hass.callWS.
 * Les droits d'administration sont contrôlés côté Python.
 * Le HTML ne doit jamais être construit avec des données YAML non échappées.
 * Pour cette raison, les champs issus de l'analyse utilisent textContent.
 * Les chemins de source restent des informations, pas des URL exécutables.
 * L'interface ne doit pas modifier les registres de Home Assistant.
 * Une erreur WebSocket doit rester visible dans la zone de statut.
 *
 * FILTRES ET DÉPENDANCES
 * ----------------------
 * La famille est une classification de présentation.
 * Le domaine est le préfixe de l'identifiant d'objet.
 * Une famille ne crée ni ne supprime d'objet dans la base.
 * Le choix de famille limite les domaines proposés.
 * Le type de catégorie distingue assistants et automatisations.
 * Deux catégories homonymes de portées différentes restent distinctes.
 * Le filtre étage précède le filtre pièce dans l'interface.
 * Le changement d'étage reconstruit la liste des pièces.
 * Les pièces sont associées aux étages via le registre HA.
 * Le nom de la pièce n'est pas utilisé pour deviner son étage.
 * Une pièce devenue incompatible est automatiquement désélectionnée.
 * Le filtre de dépendance manquante examine les cibles introuvables.
 * Le filtre sans dépendance ne compte que les liens fonctionnels.
 * Les rattachements organisationnels restent visibles dans les détails.
 * Un rattachement ne contribue pas à la colonne Dépend de.
 * Les objets d'organisation comptent leurs membres dans Utilisé par.
 * Le total affiché est recalculé côté serveur après filtrage.
 *
 * PRÉSENTATION ET ACCESSIBILITÉ
 * -----------------------------
 * Les trois cadres de filtres correspondent aux choix validés.
 * Chaque cadre contient exactement deux sélecteurs côte à côte.
 * Les cadres passent verticalement sur les écrans plus étroits.
 * Les deux sélecteurs internes restent côte à côte.
 * Le logo est cadré dans un carré sans étirement de l'image source.
 * Le titre reste distinct des actions de maintenance.
 * Le bouton Analyser est situé dans l'en-tête.
 * Son icône est le symbole de recyclage demandé par l’utilisateur.
 * La date affichée provient d'une ligne SQLite persistante.
 * Une date absente déclenche le style de mise en évidence.
 * Une date de plus de vingt-quatre heures déclenche aussi ce style.
 * La date est formatée avec les préférences locales du navigateur.
 * L'heure est conservée en UTC dans la base.
 * Le bouton est désactivé pendant l'analyse.
 * Le tableau comporte une barre de défilement indépendante.
 * Les colonnes de localisation restent visibles.
 * Les titres de colonnes activent le tri croissant ou décroissant.
 * Le tri est réalisé en SQL avant la pagination.
 * Les compteurs sont affichés comme des nombres, pas des chaînes.
 * L'indicateur de référence manquante est visuellement distinct.
 * Les liens vers les objets ouvrent la fiche dans le panneau de droite.
 * Le panneau de détail n'exécute aucun contenu provenant des sources.
 * Les chemins actions[0] sont affichés actions[1] aux humains.
 * Cette conversion ne modifie jamais les valeurs enregistrées.
 * Les écrans de petite largeur empilent la liste et le détail.
 *
 * MAINTENANCE ET DÉBOGAGE
 * -----------------------
 * Les méthodes sont documentées à proximité de leur déclaration.
 * Le traitement métier reste du côté Python et SQLite.
 * Le composant conserve uniquement les sélections nécessaires à l'UI.
 * Les éléments du DOM sont recherchés par leur identifiant stable.
 * La recherche textuelle utilise un délai pour éviter les requêtes répétées.
 * Le changement de filtre revient à la première page.
 * Le changement de tri revient également à la première page.
 * Le bouton Précédent ne permet pas un décalage négatif.
 * Le bouton Suivant est désactivé sur la dernière page.
 * Le serveur impose une limite maximale de lignes par requête.
 * La version du nom de fichier JavaScript évite les anciens caches.
 * Le logo est servi depuis le fichier unique brand/icon.png.
 * Aucune copie supplémentaire du PNG n’est nécessaire.
 * Le démarrage du panneau ne déclenche pas de reconstruction SQLite.
 * Une reconstruction explicite recharge ensuite les valeurs de filtres.
 * Le code privilégie des nœuds DOM sûrs pour les données utilisateur.
 * La zone de statut sert aux confirmations et aux erreurs.
 * Les erreurs détaillées côté serveur restent dans les journaux HA.
 * La méthode d'analyse ne doit pas bloquer la boucle événementielle HA.
 * Le serveur exécute les traitements dans un exécuteur séparé.
 * L'interface ne déduit pas de lien à partir d'un simple nom similaire.
 * Les compteurs doivent correspondre aux objets distincts.
 * Les chemins d'occurrence détaillés restent consultables séparément.
 */
/** Dependency Graph — interface autonome, aucune bibliothèque distante. */
/**
 * Panneau Home Assistant sans framework externe.
 * Le navigateur ne lit jamais directement les fichiers de configuration :
 * toutes les données passent par les commandes WebSocket réservées aux admins.
 * Le composant conserve son état (filtres, tri, page) dans ses propriétés.
 */
class DependencyGraphPanel extends HTMLElement {
  // Home Assistant fournit automatiquement sa connexion WebSocket au panneau.
  set hass(v){this._hass=v;if(this.isConnected&&!this._started)this.start()}
  // Construit l’interface une seule fois lors de son insertion dans la page.
  /**
   * connectedCallback : Initialise le DOM isolé du panneau. Le shadow DOM empêche les styles du tableau de modifier ceux de Home Assistant. Les gestionnaires de clics ne sont créés qu’une seule fois.
   * Les étapes sont volontairement séparées de la présentation pour faciliter
   * la maintenance et le diagnostic depuis la console du navigateur.
   */
  connectedCallback(){
    this.attachShadow({mode:'open'});
    this.shadowRoot.innerHTML=`<style>
      /* Deux tiers pour le tableau, un tiers pour la fiche. */
      :host{display:block;background:var(--primary-background-color);color:var(--primary-text-color);font:16px system-ui,sans-serif;min-height:100%}
      .wrap{width:calc(100% - 44px);max-width:none;margin:auto;padding:18px 0}
      /* Les filtres sont regroupés exclusivement dans les trois fieldsets. */
      .field{display:flex;flex-direction:column;gap:5px;min-width:0}.search{grid-column:span 4}.field label{font-size:14px;color:var(--secondary-text-color)}
      input,select,button{background:var(--card-background-color);color:var(--primary-text-color);border:1px solid var(--divider-color);border-radius:7px;padding:9px;font:inherit;min-width:0}
      button,th.sort{cursor:pointer}button:hover,a:hover,th.sort:hover{color:var(--primary-color)}
      .layout{display:grid;grid-template-columns:minmax(0,2fr) minmax(0,1fr);gap:16px}
      .panel{background:var(--card-background-color);border-radius:12px;padding:16px;min-width:0;box-shadow:0 1px 5px #00000012}
      .table-scroll{overflow:auto;max-height:calc(100vh - 300px)}table{width:100%;border-collapse:collapse}td,th{padding:8px 6px;border-bottom:1px solid var(--divider-color);text-align:left;vertical-align:top}th{position:sticky;top:0;background:var(--card-background-color);white-space:nowrap;font-size:14px}tr:hover{background:var(--secondary-background-color)}
      /* La sélection reste visible après disparition du survol de souris. */
      tbody tr.selected{background:color-mix(in srgb,var(--primary-color) 17%,var(--card-background-color))!important;box-shadow:inset 4px 0 var(--primary-color)}
      tbody tr.selected:hover{background:color-mix(in srgb,var(--primary-color) 24%,var(--card-background-color))!important}
      /* Les sections natives details/summary fonctionnent au clavier et à la souris. */
      details.section{border-top:1px solid var(--divider-color);margin-top:12px;padding-top:6px}
      details.section>summary{font-weight:700;font-size:1.08em;cursor:pointer;padding:7px 0}
      details.section>summary::marker{color:var(--primary-color)}
      .source{font-family:ui-monospace,Consolas,monospace;white-space:pre-wrap;overflow-wrap:anywhere;font-size:.91em;line-height:1.5}
      .source strong{font-weight:800;color:var(--primary-color)}
      a{color:var(--primary-color);cursor:pointer;text-decoration:none}pre{overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;background:var(--secondary-background-color);padding:12px;border-radius:8px}
      .missing{color:var(--error-color);font-weight:700}.muted{color:var(--secondary-text-color)}.line{margin:7px 0;padding:7px;border-bottom:1px solid var(--divider-color)}.small{font-size:11px}.num{text-align:center}.pagination{display:flex;gap:8px;margin-top:12px;align-items:center}
      @media(max-width:1000px){.filters{grid-template-columns:repeat(2,minmax(130px,1fr))}.search{grid-column:span 2}.layout{grid-template-columns:1fr}.table-scroll{max-height:600px}}
      @media(max-width:600px){.filters{grid-template-columns:repeat(2,minmax(100px,1fr))}.search{grid-column:span 2}.wrap{width:calc(100% - 20px)}}
      /* Les trois groupes restent chacun sur deux colonnes, même sur mobile. */
      .filter-groups{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:14px 0}
      .filter-group{border:1px solid var(--divider-color);border-radius:12px;padding:12px;min-width:0}
      .filter-group legend{font-weight:700;padding:0 8px;color:var(--primary-text-color)}
      .filter-pair{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
      .topbar{display:flex;justify-content:space-between;align-items:center;gap:16px}
      .analysis-controls{display:flex;flex-direction:column;align-items:flex-end;gap:5px}
      .analysis-controls button{font-weight:700;white-space:nowrap}
      .analysis-controls button.stale{background:var(--warning-color,#f3ad25);color:#111;border-color:var(--warning-color,#f3ad25)}
      .analysis-controls small{font-size:11px;color:var(--secondary-text-color)}
      .checkboxes{display:flex;gap:20px;flex-wrap:wrap;margin:8px 0 14px}
      .checkboxes label{display:flex;align-items:center;gap:7px}
      .checkboxes input{min-width:auto}
      @media(max-width:1100px){.filter-groups{grid-template-columns:1fr}}
      .heading{display:flex;align-items:center;gap:15px;margin-bottom:14px}.heading img{width:64px;height:64px;object-fit:contain;aspect-ratio:1/1;border-radius:8px;background:white;padding:3px;box-sizing:border-box;flex-shrink:0}.heading h1{margin:0;font-size:25px}.toolbar{display:flex;align-items:end;justify-content:flex-end}.toolbar button{width:100%}.sort:hover{text-decoration:underline}.sort{user-select:none}.meta-name{font-size:11px;color:var(--secondary-text-color);margin-top:3px}.object-cell{min-width:165px}.counter{font-variant-numeric:tabular-nums}.details-head{overflow-wrap:anywhere}
      /* On empile les panneaux plus tôt, pour éviter le tableau écrasé. */
      @media(max-width:1150px){.layout{grid-template-columns:minmax(0,1fr)!important}}
    </style><div class="wrap">
    <!-- Le logo est servi par HA depuis le répertoire local de l'intégration. -->
    <header class="topbar"><div class="heading"><img src="/dependency_graph_brand/icon.png" alt="Logo Dependency Graph"><h1>Graphe des dépendances</h1></div>
      <div class="analysis-controls"><button id="analyze">♻ Analyser</button><small id="analyzed-at">Dernière analyse : inconnue</small></div></header>
    <div class="field"><label for="query">Rechercher un objet</label><input id="query" placeholder="Mots-clés (ex. chauffage temps)"></div>
    <!-- Trois groupes distincts : chaque groupe garde ses deux filtres côte à côte. -->
    <div class="filter-groups">
      <fieldset class="filter-group"><legend>Objets</legend><div class="filter-pair">
        <div class="field"><label for="family">Famille</label><select id="family" multiple size="4" title="Ctrl/Cmd ou Maj pour sélectionner plusieurs valeurs"><option value="">Toutes les familles</option><option value="entites">Entités</option><option value="assistants">Assistants</option><option value="automatisations">Automatisations et scripts</option><option value="organisation">Organisation HA</option></select></div>
        <div class="field"><label for="domain">Domaine</label><select id="domain" multiple size="4" title="Ctrl/Cmd ou Maj pour sélectionner plusieurs valeurs"><option value="">Tous les domaines</option></select></div>
      </div></fieldset>
      <fieldset class="filter-group"><legend>Catégorie</legend><div class="filter-pair">
        <div class="field"><label for="scope">Type</label><select id="scope" multiple size="4" title="Ctrl/Cmd ou Maj pour sélectionner plusieurs valeurs"><option value="">Tous les types</option><option value="helpers">Assistants</option><option value="automation">Automatisations</option></select></div>
        <div class="field"><label for="category">Nom</label><select id="category" multiple size="4" title="Ctrl/Cmd ou Maj pour sélectionner plusieurs valeurs"><option value="">Toutes les catégories</option></select></div>
      </div></fieldset>
      <fieldset class="filter-group"><legend>Localisation</legend><div class="filter-pair">
        <div class="field"><label for="floor">Étage</label><select id="floor" multiple size="4" title="Ctrl/Cmd ou Maj pour sélectionner plusieurs valeurs"><option value="">Tous les étages</option></select></div>
        <div class="field"><label for="area">Pièce</label><select id="area" multiple size="4" title="Ctrl/Cmd ou Maj pour sélectionner plusieurs valeurs"><option value="">Toutes les pièces</option></select></div>
      </div></fieldset>
      <fieldset class="filter-group"><legend>Mesure</legend><div class="filter-pair">
        <div class="field"><label for="measurement">Classe (ex. énergie)</label><select id="measurement" multiple size="4" title="Sélection multiple avec Ctrl/Cmd ou Maj"><option value="">Toutes les mesures</option></select></div>
        <div class="field"><label for="unit">Unité (kWh, A, V, W…)</label><select id="unit" multiple size="4" title="Sélection multiple avec Ctrl/Cmd ou Maj"><option value="">Toutes les unités</option></select></div>
      </div></fieldset>
    </div>
    <div class="checkboxes"><label><input type="checkbox" id="missing-only"> Dépendance manquante</label><label><input type="checkbox" id="no-dependencies"> Objets sans dépendance</label></div>
    <p id="status" class="muted" role="status"></p>
    <div class="layout"><section class="panel"><h2>Objets <span id="total"></span></h2><div class="table-scroll"><table><thead><tr>
      <th class="sort" data-sort="object_id">Objet</th><th class="sort" data-sort="name">Nom</th><th class="sort" data-sort="floor_name">Étage</th><th class="sort" data-sort="area_name">Pièce</th>
      <th class="sort num" data-sort="depend_on_count" title="Nombre d'objets dont dépend celui-ci">Dépend de</th><th class="sort num" data-sort="required_by_count" title="Nombre d'objets qui dépendent de celui-ci">Utilisé par</th><th class="sort num" data-sort="missing_count" title="Références vers des objets introuvables">État</th>
    </tr></thead><tbody id="rows"></tbody></table></div><div class="pagination"><button id="prev">Précédent</button><span id="page" class="muted"></span><button id="next">Suivant</button></div></section>
    <section class="panel" id="details"><h2>Détails</h2><p>Sélectionnez un objet.</p></section></div></div>`;
    this.$=id=>this.shadowRoot.getElementById(id);this.offset=0;this.limit=100;this.sort='object_id';this.descending=false;
    this.$('query').addEventListener('input',()=>{clearTimeout(this._debounce);this._debounce=setTimeout(()=>{this.offset=0;this.list()},250)});
    for(const id of ['family','domain','scope','category','floor','area','measurement','unit'])this.$(id).addEventListener('change',()=>{this.offset=0;if(id==='family')this.domains();if(id==='scope')this.categories();if(id==='floor')this.areas();if(id==='measurement'||id==='unit')this.measurementUnits(id);this.list()});
    this.shadowRoot.querySelectorAll('th[data-sort]').forEach(th=>th.onclick=()=>{const next=th.dataset.sort;this.descending=this.sort===next?!this.descending:false;this.sort=next;this.offset=0;this.updateSort();this.list()});
    this.$('missing-only').onchange=()=>{this.offset=0;this.list()};this.$('no-dependencies').onchange=()=>{this.offset=0;this.list()};
    this.$('prev').onclick=()=>{this.offset=Math.max(0,this.offset-this.limit);this.list()};this.$('next').onclick=()=>{this.offset+=this.limit;this.list()};// Le bouton est branché une seule fois, au montage du panneau.
    this.$('analyze').onclick=()=>this.analyze();
    if(this._hass)this.start();
  }
  // Point d’entrée unique pour appeler le serveur Home Assistant.
  /**
   * api : Encapsule les appels WebSocket. Le serveur contrôle les droits administrateur et exécute les lectures SQLite dans un thread dédié.
   * Les étapes sont volontairement séparées de la présentation pour faciliter
   * la maintenance et le diagnostic depuis la console du navigateur.
   */
  async api(type,extra={}){return this._hass.callWS({type:'dependency_graph/'+type,...extra})}
  /**
   * status : Écrit un message lisible dans la zone de statut, sans injecter de HTML venant des fichiers Home Assistant.
   * Les étapes sont volontairement séparées de la présentation pour faciliter
   * la maintenance et le diagnostic depuis la console du navigateur.
   */
  status(s){this.$('status').textContent=s}
  /**
   * fill : Reconstruit une liste déroulante. Préserve la sélection précédente si elle existe toujours, sinon sélectionne « Toutes ». Cela évite une sélection invisible après changement de filtre.
   * Les étapes sont volontairement séparées de la présentation pour faciliter
   * la maintenance et le diagnostic depuis la console du navigateur.
   */
  // La sélection vide signifie « Tous ». Plusieurs valeurs sont combinées en OU.
  selected(id){return [...this.$(id).selectedOptions].map(o=>o.value).filter(Boolean)}
  fill(id,values){const el=this.$(id),old=this.selected(id);while(el.options.length>1)el.remove(1);for(const value of values){const opt=document.createElement('option');opt.value=value;opt.textContent=value;opt.selected=old.includes(value);el.add(opt)}if(!this.selected(id).length)el.options[0].selected=true}
  // Chaque méthode ci-dessous est indépendante de l'analyse lourde.
  // Les sélecteurs n'envoient que des critères de lecture au serveur.
  // Les objets HA et leurs identifiants ne sont jamais modifiés.
  // La recherche ne reconstruit pas la base et reste rapide.
  // Les compteurs viennent de SQLite et non du nombre de lignes affichées.
  // Les regroupements sont une convention de l'interface uniquement.
  // Le filtre de localisation est hiérarchique : étage puis pièce.
  // La valeur d'une pièce est son nom affiché dans le registre HA.
  // Si une pièce est déplacée d'étage, le prochain scan met à jour la liste.
  // L'utilisateur peut conserver ses autres filtres en changeant d'étage.
  // Le serveur garde la responsabilité de valider toutes les requêtes.
  // Les domaines proposés changent avec la famille choisie.
  /**
   * domains : Déduit les domaines autorisés de la famille. Les tableaux décrivent la classification métier de l’interface, pas des objets nouveaux.
   * Les étapes sont volontairement séparées de la présentation pour faciliter
   * la maintenance et le diagnostic depuis la console du navigateur.
   */
  domains(){const families=this.selected('family'),all=this.values.domain||[];const org=['area','floor','category','label'];const helpers=['input_boolean','input_datetime','input_number','input_select','input_text','input_button','counter','timer','schedule'];const autom=['automation','script','scene'];const allowed=d=>!families.length||families.some(f=>f==='organisation'?org.includes(d):f==='assistants'?helpers.includes(d):f==='automatisations'?autom.includes(d):!org.includes(d)&&!helpers.includes(d)&&!autom.includes(d));this.fill('domain',all.filter(allowed))}
  // Deux listes HA distinctes : catégories d’assistants et d’automatisations.
  /**
   * categories : Les catégories HA ont deux portées indépendantes. La liste de noms dépend du type choisi et élimine les doublons.
   * Les étapes sont volontairement séparées de la présentation pour faciliter
   * la maintenance et le diagnostic depuis la console du navigateur.
   */
  categories(){const scopes=this.selected('scope');const values=(scopes.length?scopes:['helpers','automation']).flatMap(s=>this.values['category_'+s]||[]);this.fill('category',[...new Set(values)].sort())}
  /**
   * Réduit les pièces proposées à celles de l'étage sélectionné.
   * La correspondance étage/pièce vient de la base et non du nom de la pièce :
   * deux pièces de noms similaires sur des étages différents restent distinctes.
   * Lorsqu'on change d'étage, une ancienne pièce incompatible est désélectionnée.
   */
  areas(){
    const floors=this.selected('floor');
    /* floor_areas est renvoyé par le serveur : chaque ligne associe un étage et une pièce. */
    /* On ne déduit jamais un étage du nom d’une pièce. */
    const pairs=this.values.floor_areas||[];
    /* Sans étage choisi, toutes les pièces sont proposées. */
    /* Avec un étage, seules ses pièces restent disponibles. */
    const names=floors.length?pairs.filter(p=>floors.includes(p.floor)).map(p=>p.area):this.values.area_name||[];
    /* fill conserve la sélection si elle existe encore, sinon la remet à « Toutes ». */
    this.fill('area',[...new Set(names)].sort((a,b)=>a.localeCompare(b,'fr')));
  }

  /**
   * Croise les classes de mesure et les unités réellement observées dans HA.
   * Une classe sélectionnée restreint les unités ; une unité sélectionnée
   * restreint les classes. Les choix incompatibles sont désélectionnés.
   */
  measurementUnits(changed){
    const pairs=this.values.measurement_units||[];
    const classes=this.selected('measurement'),units=this.selected('unit');
    if(changed==='measurement'){
      this.fill('unit',[...new Set(pairs.filter(p=>!classes.length||classes.includes(p.measurement)).map(p=>p.unit))].sort());
    }else if(changed==='unit'){
      this.fill('measurement',[...new Set(pairs.filter(p=>!units.length||units.includes(p.unit)).map(p=>p.measurement))].sort());
    }else{
      this.fill('measurement',this.values.measurement||[]);
      this.fill('unit',this.values.unit||[]);
    }
  }

  /**
   * Affiche la date réelle du dernier scan mémorisée par SQLite.
   * Un scan datant de plus de 24 heures colore le bouton Analyser.
   * Les dates sont transmises en ISO UTC, puis affichées dans le fuseau du navigateur.
   */
  analysisTime(iso){
    const button=this.$('analyze');
    const label=this.$('analyzed-at');
    const date=iso?new Date(iso):null;
    const valid=date&&!Number.isNaN(date.getTime());
    label.textContent=valid?'Dernière analyse : '+date.toLocaleString('fr-FR'):'Dernière analyse : jamais';
    button.classList.toggle('stale',!valid||(Date.now()-date.getTime()>24*60*60*1000));
  }

  // Charge les valeurs de filtres avant la première liste.
  /**
   * start : Au premier chargement, lit les valeurs de filtres puis l’inventaire. Aucune analyse lourde ne démarre automatiquement.
   * Les étapes sont volontairement séparées de la présentation pour faciliter
   * la maintenance et le diagnostic depuis la console du navigateur.
   */
  async start(){this._started=true;try{this.values=await this.api('values');this.domains();this.categories();this.fill('floor',this.values.floor_name||[]);this.areas();this.measurementUnits();this.updateSort();await this.list()}catch(e){this.status(e.message)}}
  // ▲ / ▼ reflète le tri choisi en cliquant sur un titre de colonne.
  /**
   * updateSort : Conserve une seule colonne de tri active et ajoute une flèche à son libellé. Le tri réel se fait en SQLite.
   * Les étapes sont volontairement séparées de la présentation pour faciliter
   * la maintenance et le diagnostic depuis la console du navigateur.
   */
  updateSort(){this.shadowRoot.querySelectorAll('th[data-sort]').forEach(th=>{const original=th.textContent.replace(/ [▲▼]$/,'');th.textContent=original+(th.dataset.sort===this.sort?(this.descending?' ▼':' ▲'):'')})}
  // La pagination et le tri sont effectués côté serveur (SQLite).
  /**
   * list : Envoie les filtres, la pagination et le tri au serveur. Recrée uniquement les lignes visibles, jamais les 1000+ objets à la fois.
   * Les étapes sont volontairement séparées de la présentation pour faciliter
   * la maintenance et le diagnostic depuis la console du navigateur.
   */
  async list() {
    // 1. Préparer les critères de recherche choisis dans le panneau.
    // Le texte et les listes sont lus au moment précis de la requête.
    // On ne conserve pas de copie des filtres dans une seconde variable globale.
    // Ainsi, l'état affiché correspond toujours aux critères envoyés à SQLite.
    const args = {
      query: this.$('query').value,
      family: this.selected('family'),
      domain: this.selected('domain'),
      scope: this.selected('scope'),
      category: this.selected('category'),
      floor: this.selected('floor'),
      area: this.selected('area'),
      measurement: this.selected('measurement'),
      unit: this.selected('unit'),
      offset: this.offset,
      limit: this.limit,
      sort: this.sort,
      descending: this.descending,
      missing_only: this.$('missing-only').checked,
      no_dependencies: this.$('no-dependencies').checked
    };

    try {
      // 2. Demander au serveur une seule page d'objets.
      // Le serveur est responsable du filtrage et du tri.
      // Le navigateur n'a donc pas besoin de charger tous les objets en mémoire.
      const result = await this.api('list', args);
      this.$('total').textContent = `(${result.total})`;
      this.analysisTime(result.analyzed_at);

      // 3. Effacer uniquement les anciennes lignes du tableau.
      // replaceChildren évite de concaténer du HTML potentiellement dangereux.
      // Chaque valeur est insérée comme texte, jamais interprétée comme du code.
      const body = this.$('rows');
      body.replaceChildren();

      for (const obj of result.items) {
        // 4. Créer une ligne par objet retourné par SQLite.
        // Le lien de la première colonne ouvre la fiche dans le panneau de droite.
        // Les colonnes suivantes conservent explicitement étage et pièce.
        const row = document.createElement('tr');
        // La couleur de sélection est indépendante du survol et survit à la pagination.
        row.dataset.objectId = obj.object_id;
        if (obj.object_id === this.selectedId) row.classList.add('selected');
        const identity = document.createElement('td');
        identity.className = 'object-cell';
        identity.append(this.link(obj.object_id));
        row.append(identity);

        // 5. Ajouter les propriétés et compteurs calculés côté Python.
        // « Dépend de » exclut les rattachements organisationnels.
        // « Utilisé par » inclut les membres des pièces/étages/catégories.
        // Une valeur nulle s'affiche comme un tiret et non comme « null ».
        const columns = [
          obj.name, obj.floor_name, obj.area_name,
          obj.depend_on_count, obj.required_by_count
        ];
        for (const value of columns) {
          const cell = document.createElement('td');
          cell.textContent = value ?? '—';
          if (typeof value === 'number') cell.className = 'num';
          row.append(cell);
        }

        // 6. Signaler une référence absente dans la dernière colonne.
        // L'icône d'alerte est visible même sans ouvrir la fiche.
        // Le survol donne le nombre exact de références manquantes.
        const state = document.createElement('td');
        state.className = 'num';
        state.textContent = obj.missing_count ? '⚠ ' + obj.missing_count : '✓';
        state.title = obj.missing_count
          ? obj.missing_count + ' référence(s) manquante(s)'
          : 'Aucune référence manquante';
        if (obj.missing_count) state.classList.add('missing');
        row.append(state);
        body.append(row);
      }

      // 7. Mettre à jour les commandes de pagination.
      // « Précédent » est interdit au début de la liste.
      // « Suivant » est interdit quand il n'y a plus de page.
      this.$('prev').disabled = this.offset === 0;
      this.$('next').disabled = this.offset + this.limit >= result.total;
      this.$('page').textContent = result.total
        ? `${this.offset + 1}–${Math.min(this.offset + this.limit, result.total)} / ${result.total}`
        : '0';

      // 8. Confirmer la lecture de l'inventaire.
      // La présence de la base n'entraîne pas une nouvelle analyse automatique.
      this.status(result.analyzed
        ? 'Analyse disponible'
        : 'Cliquez sur Analyser pour créer l’inventaire.');
    } catch (error) {
      // Une erreur WebSocket reste visible plutôt que de vider silencieusement l'écran.
      this.status('Erreur de liste : ' + error.message);
    }
  }
  // Tous les identifiants sont cliquables et ouvrent leur fiche.
  /**
   * link : Construit un lien interne vers la fiche de l’objet sans recharger la page Home Assistant.
   * Les étapes sont volontairement séparées de la présentation pour faciliter
   * la maintenance et le diagnostic depuis la console du navigateur.
   */
  link(id){const a=document.createElement('a');a.href='#'+encodeURIComponent(id);a.textContent=id;a.onclick=e=>{e.preventDefault();this.detail(id)};return a}
  // Présente séparément dépendances fonctionnelles et organisationnelles.
  /**
   * detail : Construit le détail d’un objet en créant des nœuds texte, afin que les configurations YAML ne puissent pas injecter de HTML.
   * Les étapes sont volontairement séparées de la présentation pour faciliter
   * la maintenance et le diagnostic depuis la console du navigateur.
   */
  /**
   * Ouvre une fiche, puis marque sa ligne dans le tableau.
   * Chaque bloc de détail est un élément HTML <details> : le navigateur gère
   * automatiquement le déploiement, la fermeture et le clavier.
   * Les sources sont présentées sans interpréter les données comme du HTML.
   */
  async detail(id) {
    try {
      const data = await this.api('detail', {identifier:id});
      this.selectedId = id;
      // Le navigateur conserve la sélection même quand la souris quitte la ligne.
      this.shadowRoot.querySelectorAll('tbody tr').forEach(row => {
        row.classList.toggle('selected', row.dataset.objectId === id);
      });
      const box = this.$('details');
      box.replaceChildren();
      const title = document.createElement('h2');
      title.textContent = data.object.name || id;
      const meta = document.createElement('p');
      meta.textContent = id + ' · ' + (data.object.source_file || '');
      box.append(title, meta);

      // Les quatre groupes restent séparés : fonctionnel != organisation.
      for (const [key,label] of [
        ['depend_on','Dépend de (fonctionnel)'],
        ['required_by','Utilisé par (fonctionnel)'],
        ['organisation_depend_on','Rattaché à (organisation)'],
        ['organisation_required_by','Contient / classe (organisation)']
      ]) {
        const section = this.section(box, label, (data[key] || []).length);
        for (const item of data[key] || []) {
          const line = document.createElement('div');
          line.className = 'line';
          line.append(this.link(item.id));
          if (item.missing) {
            const warning = document.createElement('strong');
            warning.className = 'missing';
            warning.textContent = ' ⚠ Introuvable';
            line.append(warning);
          }
          const file = document.createElement('div');
          file.className = 'muted';
          file.textContent = item.file || '';
          line.append(file);
          for (const location of item.locations || []) {
            const path = document.createElement('div');
            path.className = 'muted';
            path.textContent = '↳ ' + this.humanPath(location.path);
            line.append(path);
          }
          section.append(line);
        }
      }
      // Le serveur fournit déjà le format YAML pour les automatismes.
      // On ne convertit pas ici un objet YAML en JSON, sinon le style d'origine se perd.
      const props = this.section(box, 'Propriétés');
      this.sourceBlock(props, JSON.stringify(data.object, null, 2), data);
      const source = this.section(box, 'Configuration source');
      if (data.configuration_yaml) {
        this.sourceBlock(source, data.configuration_yaml, data);
      } else {
        this.sourceBlock(source, JSON.stringify(data.configuration, null, 2), data);
      }
    } catch (error) {
      this.status('Erreur de fiche : ' + error.message);
    }
  }

  /** Crée une section escamotable ouverte par défaut, avec un chevron natif. */
  section(parent, label, count=null) {
    const section = document.createElement('details');
    section.className = 'section';
    section.open = true;
    const heading = document.createElement('summary');
    heading.textContent = label + (count === null ? '' : ' (' + count + ')');
    section.append(heading);
    parent.append(section);
    return section;
  }

  /**
   * Affiche du texte de source, et met en gras les identifiants des références.
   * On découpe la chaîne en fragments texte : aucun innerHTML provenant d'un
   * fichier YAML/JSON n'est exécuté, même si ce fichier contient des balises.
   */
  sourceBlock(parent, source, data) {
    const block = document.createElement('pre');
    block.className = 'source';
    const ids = [...new Set((data.depend_on || []).map(item => item.id))]
      .filter(Boolean).sort((a,b) => b.length - a.length);
    if (!ids.length) {
      block.textContent = source || '';
    } else {
      // L'expression ne sert qu'à trouver du texte ; on n'injecte pas de HTML.
      const escape = value => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const pattern = new RegExp('(' + ids.map(escape).join('|') + ')', 'g');
      for (const fragment of String(source || '').split(pattern)) {
        if (!fragment) continue;
        if (ids.includes(fragment)) {
          const bold = document.createElement('strong');
          bold.textContent = fragment;
          block.append(bold);
        } else {
          block.append(document.createTextNode(fragment));
        }
      }
    }
    parent.append(block);
  }
  /**
   * Les chemins YAML sont indexés à zéro en interne (ex. actions[0]).
   * On affiche 1 à l'utilisateur, sans modifier les chemins enregistrés dans la BD.
   * Le remplacement est limité aux segments trigger/action et à leurs pluriels.
   */
  humanPath(path){
    return String(path||'').replace(/\b(triggers?|actions?)\[(\d+)\]/gi,(_match,word,index)=>word+'['+(Number(index)+1)+']');
  }

  // Analyse manuelle uniquement : aucun lancement automatique au démarrage.
  /**
   * analyze : Désactive temporairement le bouton, demande un scan manuel, recharge les filtres et réaffiche les résultats.
   * Les étapes sont volontairement séparées de la présentation pour faciliter
   * la maintenance et le diagnostic depuis la console du navigateur.
   */
  async analyze(){const b=this.$('analyze');b.disabled=true;this.status('Analyse en cours…');try{const result=await this.api('analyze');this.values=await this.api('values');this.domains();this.categories();this.fill('floor',this.values.floor_name||[]);this.areas();this.measurementUnits();this.offset=0;await this.list();this.status(`Analyse terminée : ${result.objects} objets, ${result.dependencies} références, ${result.errors} erreurs`)}catch(e){this.status('Échec : '+e.message)}finally{b.disabled=false}}
}
customElements.define('dependency-graph-panel',DependencyGraphPanel);
