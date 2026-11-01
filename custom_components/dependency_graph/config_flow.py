"""Ajout depuis Paramètres > Appareils et services > Ajouter une intégration."""
from homeassistant import config_entries
from .const import DOMAIN

class DependencyGraphConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Une seule installation par Home Assistant."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """La configuration HA active est détectée automatiquement."""
        await self.async_set_unique_id("local")
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="Dependency Graph", data={})
