import importlib.util
import unittest


CONNECTOR_AVAILABLE = (
	importlib.util.find_spec('automated_screenshot_connector') is not None
)


class DemoThumbnailsTest(unittest.TestCase):
	@unittest.skipUnless(
		CONNECTOR_AVAILABLE,
		'automated-screenshot-connector is not installed in this environment',
	)
	def test_thumbnail_view_demo_takes_stills_and_ends_in_list_view(self):
		from fman.impl.demo_scripts import DEMOS

		demo = DEMOS[31]
		still_names = [
			step.name for step in demo.steps
			if step.__class__.__name__ == 'Screenshot'
		]
		return_steps = [
			step for step in demo.steps
			if step.__class__.__name__ == 'PressKey'
			and step.chord == 'Return'
		]
		toggle_steps = [
			step for step in demo.steps
			if step.__class__.__name__ == 'Command'
			and step.line.startswith('toggle thumbnail')
		]

		self.assertEqual(demo.name, 'thumbnail-view')
		self.assertEqual(
			still_names,
			['thumbnail-grid', 'thumbnail-larger', 'thumbnail-off'],
		)
		self.assertFalse(return_steps)
		self.assertEqual(len(toggle_steps) % 2, 0)


if __name__ == '__main__':
	unittest.main()
