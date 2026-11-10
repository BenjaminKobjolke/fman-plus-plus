from fman.impl.model.shading import (
	SHADE_BOLD, SHADE_STYLES, SHADE_TINT, SHADE_TRANSPARENCY,
	Shade, ShadeRole, safe_shade
)
from unittest import TestCase
from unittest.mock import patch


class SafeShadeTest(TestCase):
	def test_style_constants(self):
		self.assertEqual(
			{'transparency', 'tint', 'bold'},
			set(SHADE_STYLES)
		)
		self.assertEqual(
			(SHADE_TRANSPARENCY, SHADE_TINT, SHADE_BOLD),
			('transparency', 'tint', 'bold')
		)
	def test_clamps_numeric_amount(self):
		self.assertEqual(Shade('tint', 1), safe_shade(lambda _url: 2, 'tint', 'a'))
		self.assertEqual(Shade('tint', 0), safe_shade(lambda _url: -1, 'tint', 'a'))
		self.assertEqual(Shade('tint', .5), safe_shade(lambda _url: .5, 'tint', 'a'))
	def test_passes_through_none(self):
		self.assertIsNone(safe_shade(lambda _url: None, 'tint', 'a'))
	def test_catches_and_reports_each_shader_only_once(self):
		def shader(_url):
			raise ValueError('broken shader')
		with patch('fman.impl.model.shading.traceback.print_exc') as print_exc:
			self.assertIsNone(safe_shade(shader, 'tint', 'a'))
			self.assertIsNone(safe_shade(shader, 'tint', 'b'))
		self.assertEqual(1, print_exc.call_count)
	def test_shade_role_is_a_distinct_user_role(self):
		self.assertEqual(0x0100 + 2, ShadeRole)
