"""Intégration Home Assistant : exploration des dépendances statiques."""
import asyncio
from pathlib import Path
from homeassistant.components import frontend, panel_custom
from homeassistant.components.frontend import async_panel_exists
from homeassistant.components.http import StaticPathConfig
from .const import DOMAIN,PANEL_PATH
from .service import GraphService
from .websocket import register

async def async_setup_entry(hass,entry):
    """Monte une API locale et un panneau accessible aux administrateurs."""
    if DOMAIN not in hass.data:
        hass.data[DOMAIN]={'service':GraphService(hass.config.config_dir),'lock':asyncio.Lock()}
        register(hass)
    if not async_panel_exists(hass,PANEL_PATH):
        await hass.http.async_register_static_paths([
            StaticPathConfig('/dependency_graph_static',str(Path(__file__).parent/'frontend'),False)
        ])
        await panel_custom.async_register_panel(
            hass,frontend_url_path=PANEL_PATH,webcomponent_name='dependency-graph-panel',
            module_url='/dependency_graph_static/panel-v140.js',sidebar_title='Dépendances',
            sidebar_icon='mdi:graph-outline',require_admin=True,embed_iframe=False)
    return True

async def async_unload_entry(hass,entry):
    """Supprime le panneau ; les données SQLite sont conservées."""
    frontend.async_remove_panel(hass,PANEL_PATH)
    hass.data.pop(DOMAIN,None)
    return True
