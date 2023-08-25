from io import StringIO
from unittest.mock import patch

# from ai.management.commands.post_wca_key import Command
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

# from ai.api.aws.wca_secret_manager import WcaSecretManager


class GetWcaKeyCommandTestCase(TestCase):
    def test_missing_required_args(self):
        with self.assertRaisesMessage(
            CommandError, 'Error: the following arguments are required: org_id'
        ):
            call_command('get_wca_key')

    @patch("ai.management.commands.get_wca_key.WcaSecretManager")
    def test_key_found(self, mock_secret_manager):
        instance = mock_secret_manager.return_value
        instance.get_key.return_value = {"CreatedDate": "xxx"}

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            call_command('get_wca_key', 'mock_org_id')
            instance.get_key.assert_called_once_with("mock_org_id")
            captured_output = mock_stdout.getvalue()
            self.assertIn(
                "API Key for orgId 'mock_org_id' found. Last updated: xxx", captured_output
            )

    @patch("ai.management.commands.get_wca_key.WcaSecretManager")
    def test_key_not_found(self, mock_secret_manager):
        instance = mock_secret_manager.return_value
        instance.get_key.return_value = None

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            call_command('get_wca_key', 'mock_org_id')
            instance.get_key.assert_called_once_with("mock_org_id")
            captured_output = mock_stdout.getvalue()
            self.assertIn("No API Key for orgId 'mock_org_id' found", captured_output)