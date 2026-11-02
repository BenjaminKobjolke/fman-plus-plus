import json
import unittest
from pathlib import Path


class BuildConfigurationTest(unittest.TestCase):
	def test_windows_hidden_imports_include_network_constants(self):
		project_root = Path(__file__).resolve().parents[5]
		settings_path = (
			project_root / 'src' / 'build' / 'settings' / 'windows.json'
		)
		with settings_path.open(encoding='utf-8') as settings_file:
			settings = json.load(settings_file)

		self.assertIn('win32netcon', settings['hidden_imports'])


if __name__ == '__main__':
	unittest.main()
