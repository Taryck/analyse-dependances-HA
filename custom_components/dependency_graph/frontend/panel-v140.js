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
 * Le logo est inclus dans le JavaScript pour éviter toute erreur de chemin statique.
 * Le PNG carré est également livré dans brand/ pour Home Assistant.
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
      :host{display:block;background:var(--primary-background-color);color:var(--primary-text-color);font:14px system-ui,sans-serif;min-height:100%}
      .wrap{width:calc(100% - 44px);max-width:none;margin:auto;padding:18px 0}
      /* Les filtres sont regroupés exclusivement dans les trois fieldsets. */
      .field{display:flex;flex-direction:column;gap:5px;min-width:0}.search{grid-column:span 4}.field label{font-size:12px;color:var(--secondary-text-color)}
      input,select,button{background:var(--card-background-color);color:var(--primary-text-color);border:1px solid var(--divider-color);border-radius:7px;padding:9px;font:inherit;min-width:0}
      button,th.sort{cursor:pointer}button:hover,a:hover,th.sort:hover{color:var(--primary-color)}
      .layout{display:grid;grid-template-columns:minmax(0,42fr) minmax(0,58fr);gap:16px}
      .panel{background:var(--card-background-color);border-radius:12px;padding:16px;min-width:0;box-shadow:0 1px 5px #00000012}
      .table-scroll{overflow:auto;max-height:calc(100vh - 300px)}table{width:100%;border-collapse:collapse}td,th{padding:8px 6px;border-bottom:1px solid var(--divider-color);text-align:left;vertical-align:top}th{position:sticky;top:0;background:var(--card-background-color);white-space:nowrap;font-size:12px}tr:hover{background:var(--secondary-background-color)}
      a{color:var(--primary-color);cursor:pointer;text-decoration:none}pre{overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;background:var(--secondary-background-color);padding:12px;border-radius:8px}
      .missing{color:var(--error-color);font-weight:700}.muted{color:var(--secondary-text-color)}.line{margin:7px 0;padding:7px;border-bottom:1px solid var(--divider-color)}.small{font-size:11px}.num{text-align:center}.pagination{display:flex;gap:8px;margin-top:12px;align-items:center}
      @media(max-width:1000px){.filters{grid-template-columns:repeat(2,minmax(130px,1fr))}.search{grid-column:span 2}.layout{grid-template-columns:1fr}.table-scroll{max-height:600px}}
      @media(max-width:600px){.filters{grid-template-columns:repeat(2,minmax(100px,1fr))}.search{grid-column:span 2}.wrap{width:calc(100% - 20px)}}
      /* Les trois groupes restent chacun sur deux colonnes, même sur mobile. */
      .filter-groups{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:14px 0}
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
    </style><div class="wrap">
    <!-- Le logo est servi par HA depuis le répertoire local de l'intégration. -->
    <header class="topbar"><div class="heading"><img src="data:image/png;base64,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" alt="Logo Dependency Graph"><h1>Graphe des dépendances</h1></div>
      <div class="analysis-controls"><button id="analyze">♻ Analyser</button><small id="analyzed-at">Dernière analyse : inconnue</small></div></header>
    <div class="field"><label for="query">Rechercher un objet</label><input id="query" placeholder="Identifiant ou nom (*ballon*)"></div>
    <!-- Trois groupes distincts : chaque groupe garde ses deux filtres côte à côte. -->
    <div class="filter-groups">
      <fieldset class="filter-group"><legend>Objets</legend><div class="filter-pair">
        <div class="field"><label for="family">Famille</label><select id="family"><option value="">Toutes les familles</option><option value="entites">Entités</option><option value="assistants">Assistants</option><option value="automatisations">Automatisations et scripts</option><option value="organisation">Organisation HA</option></select></div>
        <div class="field"><label for="domain">Domaine</label><select id="domain"><option value="">Tous les domaines</option></select></div>
      </div></fieldset>
      <fieldset class="filter-group"><legend>Catégorie</legend><div class="filter-pair">
        <div class="field"><label for="scope">Type</label><select id="scope"><option value="">Tous les types</option><option value="helpers">Assistants</option><option value="automation">Automatisations</option></select></div>
        <div class="field"><label for="category">Nom</label><select id="category"><option value="">Toutes les catégories</option></select></div>
      </div></fieldset>
      <fieldset class="filter-group"><legend>Localisation</legend><div class="filter-pair">
        <div class="field"><label for="floor">Étage</label><select id="floor"><option value="">Tous les étages</option></select></div>
        <div class="field"><label for="area">Pièce</label><select id="area"><option value="">Toutes les pièces</option></select></div>
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
    for(const id of ['family','domain','scope','category','floor','area'])this.$(id).addEventListener('change',()=>{this.offset=0;if(id==='family')this.domains();if(id==='scope')this.categories();if(id==='floor')this.areas();this.list()});
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
  fill(id,values){const el=this.$(id),selected=el.value;while(el.options.length>1)el.remove(1);for(const value of values){const opt=document.createElement('option');opt.value=value;opt.textContent=value;el.add(opt)}el.value=values.includes(selected)?selected:''}
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
  domains(){const f=this.$('family').value;const all=this.values.domain||[];const org=['area','floor','category','label'];const helpers=['input_boolean','input_datetime','input_number','input_select','input_text','input_button','counter','timer','schedule'];const autom=['automation','script','scene'];this.fill('domain',all.filter(d=>!f||(f==='organisation'?org.includes(d):f==='assistants'?helpers.includes(d):f==='automatisations'?autom.includes(d):!org.includes(d)&&!helpers.includes(d)&&!autom.includes(d))))}
  // Deux listes HA distinctes : catégories d’assistants et d’automatisations.
  /**
   * categories : Les catégories HA ont deux portées indépendantes. La liste de noms dépend du type choisi et élimine les doublons.
   * Les étapes sont volontairement séparées de la présentation pour faciliter
   * la maintenance et le diagnostic depuis la console du navigateur.
   */
  categories(){const scope=this.$('scope').value;const values=scope?(this.values['category_'+scope]||[]):[...(this.values.category_helpers||[]),...(this.values.category_automation||[])];this.fill('category',[...new Set(values)].sort())}
  /**
   * Réduit les pièces proposées à celles de l'étage sélectionné.
   * La correspondance étage/pièce vient de la base et non du nom de la pièce :
   * deux pièces de noms similaires sur des étages différents restent distinctes.
   * Lorsqu'on change d'étage, une ancienne pièce incompatible est désélectionnée.
   */
  areas(){
    const floor=this.$('floor').value;
    /* floor_areas est renvoyé par le serveur : chaque ligne associe un étage et une pièce. */
    /* On ne déduit jamais un étage du nom d’une pièce. */
    const pairs=this.values.floor_areas||[];
    /* Sans étage choisi, toutes les pièces sont proposées. */
    /* Avec un étage, seules ses pièces restent disponibles. */
    const names=floor?pairs.filter(p=>p.floor===floor).map(p=>p.area):this.values.area_name||[];
    /* fill conserve la sélection si elle existe encore, sinon la remet à « Toutes ». */
    this.fill('area',[...new Set(names)].sort((a,b)=>a.localeCompare(b,'fr')));
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
  async start(){this._started=true;try{this.values=await this.api('values');this.domains();this.categories();this.fill('floor',this.values.floor_name||[]);this.areas();this.updateSort();await this.list()}catch(e){this.status(e.message)}}
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
      family: this.$('family').value,
      domain: this.$('domain').value,
      scope: this.$('scope').value,
      category: this.$('category').value,
      floor: this.$('floor').value,
      area: this.$('area').value,
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
  async detail(id){try{const data=await this.api('detail',{identifier:id});const box=this.$('details');box.replaceChildren();const title=document.createElement('h2');title.className='details-head';title.textContent=data.object.name||id;box.append(title);const meta=document.createElement('p');meta.textContent=id+' · '+(data.object.source_file||'');box.append(meta);for(const [key,label] of [['depend_on','Dépend de (fonctionnel)'],['required_by','Utilisé par (fonctionnel)'],['organisation_depend_on','Rattaché à (organisation)'],['organisation_required_by','Contient / classe (organisation)']]){const h=document.createElement('h3');h.textContent=label+' ('+(data[key]||[]).length+')';box.append(h);for(const item of data[key]||[]){const line=document.createElement('div');line.className='line';line.append(this.link(item.id));if(item.missing){const badge=document.createElement('span');badge.className='missing';badge.textContent=' ⚠ Introuvable';line.append(badge)}const file=document.createElement('div');file.className='muted';file.textContent=item.file||'';line.append(file);for(const loc of item.locations||[]){const p=document.createElement('div');p.className='muted';p.textContent='↳ '+this.humanPath(loc.path);line.append(p)}box.append(line)}}for(const [key,label] of [['object','Propriétés'],['configuration','Configuration source']]){const h=document.createElement('h3');h.textContent=label;const pre=document.createElement('pre');pre.textContent=JSON.stringify(data[key],null,2);box.append(h,pre)}this.status('Fiche : '+id)}catch(e){this.status('Erreur de fiche : '+e.message)}}
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
  async analyze(){const b=this.$('analyze');b.disabled=true;this.status('Analyse en cours…');try{const result=await this.api('analyze');this.values=await this.api('values');this.domains();this.categories();this.fill('floor',this.values.floor_name||[]);this.areas();this.offset=0;await this.list();this.status(`Analyse terminée : ${result.objects} objets, ${result.dependencies} références, ${result.errors} erreurs`)}catch(e){this.status('Échec : '+e.message)}finally{b.disabled=false}}
}
customElements.define('dependency-graph-panel',DependencyGraphPanel);
