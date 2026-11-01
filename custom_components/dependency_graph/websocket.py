# ARCHITECTURE ET CONVENTIONS
# ---------------------------
# Ce module ne doit jamais écrire dans les registres sources Home Assistant.
# Les écritures concernent exclusivement les fichiers propres à l'intégration.
# Les données sont lues dans un thread via hass.async_add_executor_job.
# Les identifiants HA restent inchangés : aucune renumérotation dans la base.
# Les relations fonctionnelles viennent du code YAML/Jinja analysé.
# Les relations d'organisation proviennent des registres HA (étage/pièce).
# Une référence manquante est une cible absente de la table des objets.
# La présentation française appartient au frontend, pas aux tables SQLite.
# Les requêtes SQL utilisent des paramètres pour les valeurs fournies par l'UI.
# Seuls les noms de colonnes de tri présents dans la liste blanche sont admis.
# Les appels WebSocket sont réservés aux administrateurs de Home Assistant.
# Les exceptions internes sont consignées dans les journaux du serveur.
# Le navigateur ne reçoit pas les champs de secrets identifiés par _redact.
# La date de dernière analyse est enregistrée après une reconstruction réussie.
# Le bouton d'analyse reste manuel : aucun scan n'est programmé au démarrage.
# La base peut être supprimée puis reconstruite sans modifier les sources HA.
# Ce commentaire décrit les invariants de sécurité et les choix de conception.

"""API WebSocket réservée aux administrateurs Home Assistant."""
import logging
import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant
from .const import DOMAIN

_LOGGER=logging.getLogger(__name__)

def register(hass):
    """Enregistre les commandes une seule fois."""
    for handler in (ws_list,ws_detail,ws_values,ws_analyze):
        websocket_api.async_register_command(hass,handler)

async def _execute(hass, connection, msg, method, *args, **kwargs):
    """Toutes les opérations disque s'exécutent dans le pool de threads HA."""
    service=hass.data[DOMAIN]['service']
    try:
        result=await hass.async_add_executor_job(lambda: getattr(service,method)(*args,**kwargs))
    except (ValueError, OSError) as exc:
        connection.send_error(msg['id'],'dependency_graph_error',str(exc))
    except Exception:
        _LOGGER.exception('Erreur dans Dependency Graph')
        connection.send_error(msg['id'],'dependency_graph_error','Erreur interne : consulter les journaux HA')
    else:
        connection.send_result(msg['id'],result)

@websocket_api.websocket_command({vol.Required('type'):'dependency_graph/list',vol.Optional('query',default=''):str,vol.Optional('domain',default=''):str,vol.Optional('area',default=''):str,vol.Optional('floor',default=''):str,vol.Optional('category',default=''):str,vol.Optional('scope',default=''):str,vol.Optional('family',default=''):str,vol.Optional('sort',default='object_id'):str,vol.Optional('descending',default=False):bool,vol.Optional('limit',default=200):vol.All(int,vol.Range(min=1,max=500)),vol.Optional('offset',default=0):vol.All(int,vol.Range(min=0)),vol.Optional('missing_only',default=False):bool,vol.Optional('no_dependencies',default=False):bool})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_list(hass,connection,msg):
    await _execute(hass,connection,msg,'list_objects',**{k:msg[k] for k in ('query','domain','area','floor','category','scope','family','sort','descending','limit','offset','missing_only','no_dependencies')})

@websocket_api.websocket_command({vol.Required('type'):'dependency_graph/detail',vol.Required('identifier'):str})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_detail(hass,connection,msg):
    await _execute(hass,connection,msg,'detail',msg['identifier'])

@websocket_api.websocket_command({vol.Required('type'):'dependency_graph/values'})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_values(hass,connection,msg):
    await _execute(hass,connection,msg,'values')

@websocket_api.websocket_command({vol.Required('type'):'dependency_graph/analyze'})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_analyze(hass,connection,msg):
    lock=hass.data[DOMAIN]['lock']
    if lock.locked():
        connection.send_error(msg['id'],'busy','Analyse déjà en cours')
        return
    async with lock:
        await _execute(hass,connection,msg,'analyze')
