import json
from pathlib import Path
import unittest


class WindowsTerminalSettingsTest(unittest.TestCase):
	def test_unc_directories_are_entered_with_pushd(self):
		settings_path = Path(__file__).resolve().parents[2] / 'Core Settings (Windows).json'
		with settings_path.open(encoding='utf-8') as file:
			settings = json.load(file)

		terminal = settings['terminal']
		self.assertIn('pushd', terminal['args'])
		self.assertNotEqual('{curr_dir}', terminal.get('cwd'))


if __name__ == '__main__':
	unittest.main()
