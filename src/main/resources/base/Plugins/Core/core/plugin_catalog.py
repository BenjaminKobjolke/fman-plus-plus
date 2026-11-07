"""Adapt approved fman catalog entries to the plugin installer interface."""

class CatalogPlugin:
	source = 'catalog'
	num_stars = 0

	def __init__(self, client, name: str, description: str = '') -> None:
		self._client = client
		self.name = name
		self.description = description
		self.location = name
		self.url = self._client.catalog_plugin_url(name)

	def fetch_description(self) -> str:
		return self.description

	def get_latest_release(self) -> str:
		releases = self._client.get_catalog_releases(self.name)
		if not releases:
			raise LookupError('The catalog plugin has no released versions')
		return releases[0].version

	def download_zipball(self, version: str) -> bytes:
		return self._client.download_release(self.name, version)


def search(client, query: str, limit: int = 20) -> tuple[CatalogPlugin, ...]:
	return tuple(
		CatalogPlugin(client, plugin.name, plugin.description)
		for plugin in client.search_catalog(query, limit=limit)
	)
