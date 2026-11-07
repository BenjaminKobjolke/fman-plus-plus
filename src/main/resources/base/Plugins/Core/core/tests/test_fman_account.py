from core.fman_account import (
	clear_token, load_token, save_token, sign_in, signed_in_client
)
from core.fman_api import (
	AuthCallbackResponse, AuthInitResponse, FmanApiAuthError
)
from unittest import TestCase
from unittest.mock import Mock, patch


class AccountTokenTest(TestCase):
	@patch('core.fman_account.keyring')
	def test_loads_token_from_system_credential_store(self, keyring):
		keyring.get_password.return_value = 'secret-token'
		self.assertEqual('secret-token', load_token())
		keyring.get_password.assert_called_once_with('fman++ API', 'access_token')

	@patch('core.fman_account.keyring')
	def test_saves_token_to_system_credential_store(self, keyring):
		save_token('secret-token')
		keyring.set_password.assert_called_once_with(
			'fman++ API', 'access_token', 'secret-token'
		)

	@patch('core.fman_account.keyring')
	def test_clears_token_from_system_credential_store(self, keyring):
		clear_token()
		keyring.delete_password.assert_called_once_with(
			'fman++ API', 'access_token'
		)


class AccountSignInTest(TestCase):
	@patch('core.fman_account.time.sleep')
	@patch('core.fman_account.QDesktopServices.openUrl')
	@patch('core.fman_account.save_token')
	def test_omits_redirect_and_polls_callback_until_sign_in_finishes(
			self, save_token, open_url, sleep):
		client = Mock()
		client.start_sign_in.return_value = AuthInitResponse(
			'register-code', 'https://login.example/sign-in'
		)
		client.finish_sign_in.side_effect = [
			FmanApiAuthError('not signed in yet'),
			AuthCallbackResponse('access-token', 'user@example.com')
		]

		result = sign_in(client)

		client.start_sign_in.assert_called_once_with()
		client.finish_sign_in.assert_called_with('register-code')
		self.assertEqual(2, client.finish_sign_in.call_count)
		self.assertEqual(
			'https://login.example/sign-in', open_url.call_args.args[0].toString()
		)
		save_token.assert_called_once_with('access-token')
		self.assertEqual('user@example.com', result.email)
		sleep.assert_called_once()


class SignedInClientTest(TestCase):
	@patch('core.fman_account.FmanApiClient')
	@patch('core.fman_account.save_token')
	@patch('core.fman_account.load_token', return_value='old-token')
	def test_refreshes_and_saves_access_token(
			self, load_token, save_token, api_client):
		old_client, new_client = Mock(), Mock()
		old_client.refresh.return_value = AuthCallbackResponse('new-token')
		api_client.side_effect = [old_client, new_client]

		self.assertIs(new_client, signed_in_client())

		api_client.assert_any_call('old-token')
		api_client.assert_any_call('new-token')
		save_token.assert_called_once_with('new-token')

	@patch('core.fman_account.FmanApiClient')
	@patch('core.fman_account.clear_token')
	@patch('core.fman_account.load_token', return_value='expired-token')
	def test_clears_expired_token_and_returns_none(
			self, load_token, clear_token, api_client):
		api_client.return_value.refresh.side_effect = FmanApiAuthError()

		self.assertIsNone(signed_in_client())

		clear_token.assert_called_once_with()

	@patch('core.fman_account.FmanApiClient')
	@patch('core.fman_account.load_token', return_value=None)
	def test_returns_none_without_a_saved_token(self, load_token, api_client):
		self.assertIsNone(signed_in_client())
		api_client.assert_not_called()
