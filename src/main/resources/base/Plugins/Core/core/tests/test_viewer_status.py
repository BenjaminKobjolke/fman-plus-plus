from core.tests.viewer_stubs import StubPane
from core.viewer_status import viewer_status
from unittest import TestCase

class ViewerStatusTest(TestCase):
	def test_sends_the_message_to_the_pane_with_three_second_timeout(self):
		pane = StubPane([])
		viewer_status(pane, 'x')
		self.assertEqual([('x', 3)], pane.status_messages)
