"""Inventorie les configurations HA associables aux entités du registre.

Une entrée de configuration peut être de domaine ``filter``, ``template``,
``integration``, etc. Le domaine ne doit pas déterminer si elle est indexée :
la liaison est faite exclusivement par ``config_entry_id`` / ``entry_id``.
"""
from ...parsers.base_parser import BaseParser


class ConfigEntriesParser(BaseParser):
    """Enregistre les options de chaque entrée sans inventer d'entité."""

    def parse(self, payload, filename):
        """Indexe les entrées identifiées, quel que soit leur domaine.

        Les options et données sont utiles pour les dépendances ; les autres
        champs de gestion de HA (dates, versions, découverte) sont ignorés.
        La suppression des secrets est réalisée au moment de la lecture API.
        """
        for entry in payload.get('data', {}).get('entries', []):
            if not isinstance(entry, dict):
                continue
            entry_id = entry.get('entry_id')
            if not isinstance(entry_id, str) or not entry_id:
                continue
            domain = entry.get('domain') or 'unknown'
            # Éviter de créer un objet technique pour chaque intégration HA :
            # seules les entrées réellement liées à une entité (ou Template,
            # historiquement indexées) servent à notre graphe.
            linked = self.db.db.execute(
                "SELECT 1 FROM objects WHERE entity_id IS NOT NULL "
                "AND json_extract(attributes, '$.config_entry_id')=? LIMIT 1",
                (entry_id,),
            ).fetchone()
            if not linked and domain != 'template':
                continue
            attrs = {
                'entry_id': entry_id,
                'domain': domain,
                'title': entry.get('title'),
                'options': entry.get('options') or {},
                'data': entry.get('data') or {},
            }
            # Conserver le préfixe historique pour les configurations Template.
            # Les autres entrées utilisent un identifiant distinct et stable.
            object_id = ('template_config.' if domain == 'template' else 'config_entry.') + entry_id
            self.add(object_id, domain, 'config_entry', 'json', filename,
                     entry.get('title'), config_id=entry_id, attributes=attrs)
