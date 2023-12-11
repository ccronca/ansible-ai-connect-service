#!/usr/bin/env python3

from datetime import datetime
from functools import wraps
from http import HTTPStatus
from unittest.mock import Mock, PropertyMock, patch

import requests
from django.test import override_settings
from prometheus_client import Counter, Histogram
from requests.exceptions import HTTPError
from test_utils import WisdomServiceLogAwareTestCase
from users.authz_checker import (
    AMSCheck,
    CIAMCheck,
    DummyCheck,
    Token,
    authz_token_service_retry_counter,
)


def assert_call_count_metrics(metric):
    def count_metrics_decorator(func):
        @wraps(func)
        def wrapped_function(*args, **kwargs):
            def get_count():
                for m in metric.collect():
                    for sample in m.samples:
                        if isinstance(metric, Histogram) and sample.name.endswith("_count"):
                            return sample.value
                        if isinstance(metric, Counter) and sample.name.endswith("_total"):
                            return sample.value
                return 0.0

            count_before = get_count()
            func(*args, **kwargs)
            count_after = get_count()
            assert count_after > count_before

        return wrapped_function

    return count_metrics_decorator


class TestToken(WisdomServiceLogAwareTestCase):
    @patch("requests.post")
    def test_token_refresh(self, m_post):
        m_r = Mock()
        m_r.json.return_value = {"access_token": "foo_bar", "expires_in": 900}
        m_r.status_code = 200
        m_post.return_value = m_r

        my_token = Token("foo", "bar")
        my_token.refresh()
        self.assertGreater(my_token.expiration_date, datetime.utcnow())
        self.assertEqual(my_token.access_token, "foo_bar")

        # Ensure we server the cached result the second time
        m_r.json.reset_mock()
        self.assertEqual(my_token.get(), "foo_bar")
        self.assertEqual(m_r.json.call_count, 0)

    @patch("requests.post")
    @assert_call_count_metrics(metric=authz_token_service_retry_counter)
    @override_settings(AUTHZ_SSO_TOKEN_SERVICE_RETRY_COUNT=1)
    def test_token_refresh_with_500_status_code(self, m_post):
        m_post.side_effect = HTTPError(
            "Internal Server Error", response=Mock(status_code=500, text="Internal Server Error")
        )

        with self.assertLogs(logger='root', level='ERROR') as log:
            my_token = Token("foo", "bar")
            self.assertIsNone(my_token.refresh())
            self.assertInLog("SSO token service failed", log)

    @patch("requests.post")
    @assert_call_count_metrics(metric=authz_token_service_retry_counter)
    @override_settings(AUTHZ_SSO_TOKEN_SERVICE_RETRY_COUNT=1)
    def test_token_refresh_success_on_retry(self, m_post):
        fail_side_effect = HTTPError(
            "Internal Server Error", response=Mock(status_code=500, text="Internal Server Error")
        )
        success_mock = Mock()
        success_mock.json.return_value = {"access_token": "foo_bar", "expires_in": 900}
        success_mock.status_code = 200

        m_post.side_effect = [fail_side_effect, success_mock]

        my_token = Token("foo", "bar")
        my_token.refresh()
        self.assertGreater(my_token.expiration_date, datetime.utcnow())
        self.assertEqual(my_token.access_token, "foo_bar")

    def test_fatal_exception(self):
        """Test the logic to determine if an exception is fatal or not"""
        exc = Exception()
        b = Token.fatal_exception(exc)
        self.assertFalse(b)

        exc = requests.RequestException()
        response = requests.Response()
        response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        exc.response = response
        b = Token.fatal_exception(exc)
        self.assertFalse(b)

        exc = requests.RequestException()
        response = requests.Response()
        response.status_code = HTTPStatus.TOO_MANY_REQUESTS
        exc.response = response
        b = Token.fatal_exception(exc)
        self.assertFalse(b)

        exc = requests.RequestException()
        response = requests.Response()
        response.status_code = HTTPStatus.BAD_REQUEST
        exc.response = response
        b = Token.fatal_exception(exc)
        self.assertTrue(b)


class TestCIAM(WisdomServiceLogAwareTestCase):
    def test_ciam_check(self):
        m_r = Mock()
        m_r.json.return_value = {"result": True}
        m_r.status_code = 200

        checker = CIAMCheck("foo", "bar", "https://sso.redhat.com", "https://some-api.server.host")
        checker._token = Mock()
        checker._session = Mock()
        checker._session.post.return_value = m_r
        self.assertTrue(checker.check("my_id", "my_name", "123"))
        checker._session.post.assert_called_with(
            'https://some-api.server.host/v1alpha/check',
            json={
                'subject': 'my_id',
                'operation': 'access',
                'resourcetype': 'license',
                'resourceid': '123/smarts',
            },
            timeout=0.8,
        )

    def test_ciam_check_with_500_status_code(self):
        m_r = Mock()
        m_r.status_code = 500

        checker = CIAMCheck("foo", "bar", "https://sso.redhat.com", "https://some-api.server.host")
        checker._token = Mock()
        checker._session = Mock()
        checker._session.post.return_value = m_r

        with self.assertLogs(logger='root', level='ERROR') as log:
            self.assertFalse(checker.check("my_id", "my_name", "123"))
            self.assertInLog("Unexpected error code (500) returned by CIAM backend", log)

    def test_ciam_self_test_success(self):
        m_r = Mock()
        m_r.status_code = 200

        checker = CIAMCheck("foo", "bar", "https://sso.redhat.com", "https://some-api.server.host")
        checker._token = Mock()
        checker._session = Mock()
        checker._session.post.return_value = m_r
        try:
            checker.self_test()
        except HTTPError:
            self.fail("self_test() should not have raised an exception.")

    def test_ciam_self_test_failure(self):
        r = requests.models.Response()
        r.status_code = 500

        checker = CIAMCheck("foo", "bar", "https://sso.redhat.com", "https://some-api.server.host")
        checker._token = Mock()
        checker._session = Mock()
        checker._session.post.return_value = r

        with self.assertRaises(HTTPError):
            checker.self_test()


class TestAMS(WisdomServiceLogAwareTestCase):
    def get_default_ams_checker(self):
        return AMSCheck("foo", "bar", "https://sso.redhat.com", "https://some-api.server.host")

    def test_ams_get_ams_org(self):
        m_r = Mock()
        m_r.json.return_value = {"items": [{"id": "qwe"}]}
        m_r.status_code = 200

        checker = self.get_default_ams_checker()
        checker._token = Mock()
        checker._session = Mock()
        checker._session.get.return_value = m_r
        self.assertEqual(checker.get_ams_org("123"), "qwe")
        checker._session.get.assert_called_with(
            'https://some-api.server.host/api/accounts_mgmt/v1/organizations',
            params={'search': "external_id='123'"},
            timeout=0.8,
        )

        # Ensure the second call is cached
        m_r.json.reset_mock()
        self.assertEqual(checker.get_ams_org("123"), "qwe")
        self.assertEqual(m_r.json.call_count, 0)

    def test_ams_get_ams_org_with_500_status_code(self):
        m_r = Mock()
        # use a PropertyMock to verify that the property was accessed
        # https://docs.python.org/3/library/unittest.mock.html#unittest.mock.PropertyMock
        p = PropertyMock(return_value=500)
        type(m_r).status_code = p

        checker = self.get_default_ams_checker()
        checker._token = Mock()
        checker._session = Mock()
        checker._session.get.return_value = m_r

        with self.assertLogs(logger='root', level='ERROR') as log:
            self.assertEqual(checker.get_ams_org("123"), "")
            self.assertInLog("Unexpected error code (500) returned by AMS backend (org)", log)
            p.assert_called()
            # Ensure the second call is NOT cached
            p.reset_mock()
            self.assertEqual(checker.get_ams_org("123"), "")
            p.assert_called()

    def test_ams_get_ams_org_with_empty_data(self):
        m_r = Mock()
        m_r.json.return_value = {"items": []}
        m_r.status_code = 200

        checker = self.get_default_ams_checker()
        checker._token = Mock()
        checker._session = Mock()
        checker._session.get.return_value = m_r
        checker.user_is_active = Mock(return_value=True)

        with self.assertLogs(logger='root', level='ERROR') as log:
            self.assertEqual(checker.get_ams_org("123"), "")
            self.assertInLog("Unexpected organization answer from AMS: data={'items': []}", log)
            self.assertInLog("IndexError: list index out of range", log)

    def test_ams_check(self):
        m_r = Mock()
        m_r.json.side_effect = [{"items": [{"id": "qwe"}]}, {"items": [{"id": "asd"}]}]
        m_r.status_code = 200

        checker = self.get_default_ams_checker()
        checker._token = Mock()
        checker._session = Mock()
        checker._session.get.return_value = m_r
        checker.user_is_active = Mock(return_value=True)
        self.assertTrue(checker.check("my_id", "my_name", 123))
        checker._session.get.assert_called_with(
            'https://some-api.server.host/api/accounts_mgmt/v1/subscriptions',
            params={
                'search': "plan.id = 'AnsibleWisdom' AND status = 'Active' "
                "AND creator.username = 'my_name' AND organization_id='qwe'"
            },
            timeout=0.8,
        )

    def test_ams_check_multiple_seats(self):
        m_r = Mock()
        m_r.json.side_effect = [
            {"items": [{"id": "qwe"}, {"id": "rty"}]},
            {"items": [{"id": "asd"}, {"id": "fgh"}]},
        ]
        m_r.status_code = 200

        checker = self.get_default_ams_checker()
        checker._token = Mock()
        checker._session = Mock()
        checker._session.get.return_value = m_r
        checker.user_is_active = Mock(return_value=True)
        self.assertTrue(checker.check("my_id", "my_name", 123))
        checker._session.get.assert_called_with(
            'https://some-api.server.host/api/accounts_mgmt/v1/subscriptions',
            params={
                'search': "plan.id = 'AnsibleWisdom' AND status = 'Active' "
                "AND creator.username = 'my_name' AND organization_id='qwe'"
            },
            timeout=0.8,
        )

    def test_ams_check_with_500_status_code(self):
        m_r = Mock()
        m_r.status_code = 500

        checker = self.get_default_ams_checker()
        checker._token = Mock()
        checker._session = Mock()
        checker._session.get.return_value = m_r
        checker.user_is_active = Mock(return_value=True)

        with self.assertLogs(logger='root', level='ERROR') as log:
            self.assertFalse(checker.check("my_id", "my_name", 123))
            self.assertInLog("Unexpected error code (500) returned by AMS backend (sub)", log)

    def test_ams_self_test_success(self):
        m_r = Mock()
        m_r.status_code = 200

        checker = self.get_default_ams_checker()
        checker._token = Mock()
        checker._session = Mock()
        checker._session.get.return_value = m_r
        try:
            checker.self_test()
        except HTTPError:
            self.fail("self_test() should not have raised an exception.")

    def test_ams_self_test_failure(self):
        r = requests.models.Response()
        r.status_code = 500

        checker = self.get_default_ams_checker()
        checker._token = Mock()
        checker._session = Mock()
        checker._session.get.return_value = r

        with self.assertRaises(HTTPError):
            checker.self_test()

    def test_rh_user_is_org_admin(self):
        m_r = Mock()
        m_r.json.side_effect = [
            {"items": [{"id": "123"}]},
            {"items": [{"role": {"id": "OrganizationAdmin"}}]},
        ]
        m_r.status_code = 200

        checker = self.get_default_ams_checker()
        checker._token = Mock()
        checker._session = Mock()
        checker._session.get.return_value = m_r

        self.assertTrue(checker.rh_user_is_org_admin("user", "123"))
        checker._session.get.assert_called_with(
            'https://some-api.server.host/api/accounts_mgmt/v1/role_bindings',
            params={"search": "account.username = 'user' AND organization.id='123'"},
            timeout=0.8,
        )

    def test_is_not_org_admin(self):
        m_r = Mock()
        m_r.json.side_effect = [
            {"items": [{"id": "123"}]},
            {"items": [{"role": {"id": "NotAnAdmin"}}]},
        ]
        m_r.status_code = 200

        checker = self.get_default_ams_checker()
        checker._token = Mock()
        checker._session = Mock()
        checker._session.get.return_value = m_r

        self.assertFalse(checker.rh_user_is_org_admin("user", "123"))
        checker._session.get.assert_called_with(
            'https://some-api.server.host/api/accounts_mgmt/v1/role_bindings',
            params={"search": "account.username = 'user' AND organization.id='123'"},
            timeout=0.8,
        )

    def test_user_has_no_role(self):
        m_r = Mock()
        m_r.json.side_effect = [
            {"items": [{"id": "123"}]},
            {"items": [{"role": {}}]},
        ]
        m_r.status_code = 200
        checker = self.get_default_ams_checker()
        checker._token = Mock()
        checker._session = Mock()
        checker._session.get.return_value = m_r

        self.assertFalse(checker.rh_user_is_org_admin("user", "123"))

    def test_role_has_no_id(self):
        m_r = Mock()
        m_r.json.side_effect = [
            {"items": [{"id": "123"}]},
            {"items": []},
        ]
        m_r.status_code = 200
        checker = self.get_default_ams_checker()
        checker._token = Mock()
        checker._session = Mock()
        checker._session.get.return_value = m_r

        self.assertFalse(checker.rh_user_is_org_admin("user", "123"))

    def test_rh_user_is_org_admin_timeout(self):
        checker = self.get_default_ams_checker()
        checker._token = Mock()
        checker._session = Mock()
        checker._session.get.side_effect = requests.exceptions.Timeout
        with self.assertLogs(logger='root', level='ERROR') as log:
            self.assertFalse(checker.rh_user_is_org_admin("user", "123"))
            self.assertInLog(AMSCheck.ERROR_AMS_CONNECTION_TIMEOUT, log)

    def test_rh_user_is_org_admin_network_error(self):
        m_r = Mock()
        m_r.status_code = 500

        checker = self.get_default_ams_checker()
        checker._token = Mock()
        checker._session = Mock()
        checker._session.get.return_value = m_r

        with self.assertLogs(logger='root', level='ERROR') as log:
            self.assertFalse(checker.rh_user_is_org_admin("user", "123"))
            self.assertInLog(
                "Unexpected error code (500) returned by AMS backend when listing role bindings",
                log,
            )

    def test_rh_org_has_subscription(self):
        m_r = Mock()
        m_r.json.side_effect = [
            {"items": [{"id": "rdgdfhbrdb"}]},
            {"items": [{"allowed": 10}], "total": 1},
        ]
        m_r.status_code = 200

        checker = self.get_default_ams_checker()
        checker._token = Mock()
        checker._session = Mock()
        checker._session.get.return_value = m_r

        self.assertTrue(checker.rh_org_has_subscription("123"))
        checker._session.get.assert_called_with(
            (
                'https://some-api.server.host'
                '/api/accounts_mgmt/v1/organizations/rdgdfhbrdb/quota_cost'
            ),
            params={"search": "quota_id LIKE 'seat|ansible.wisdom%'"},
            timeout=0.8,
        )

    def test_is_org_not_lightspeed_subscriber(self):
        m_r = Mock()
        m_r.json.side_effect = [
            {"items": [{"id": "rdgdfhbrdb"}]},
            {"items": [], "total": 0},
        ]
        m_r.status_code = 200

        checker = self.get_default_ams_checker()
        checker._token = Mock()
        checker._session = Mock()
        checker._session.get.return_value = m_r

        self.assertFalse(checker.rh_org_has_subscription("123"))
        checker._session.get.assert_called_with(
            (
                'https://some-api.server.host'
                '/api/accounts_mgmt/v1/organizations/rdgdfhbrdb/quota_cost'
            ),
            params={"search": "quota_id LIKE 'seat|ansible.wisdom%'"},
            timeout=0.8,
        )

    def test_rh_org_has_subscription_timeout(self):
        checker = self.get_default_ams_checker()
        checker._token = Mock()
        checker._session = Mock()
        checker._session.get.side_effect = requests.exceptions.Timeout
        with self.assertLogs(logger='root', level='ERROR') as log:
            self.assertFalse(checker.rh_org_has_subscription("123"))
            self.assertInLog(AMSCheck.ERROR_AMS_CONNECTION_TIMEOUT, log)

    def test_rh_org_has_subscription_network_error(self):
        m_r = Mock()
        m_r.status_code = 500

        checker = self.get_default_ams_checker()
        checker._token = Mock()
        checker._session = Mock()
        checker._session.get.return_value = m_r

        with self.assertLogs(logger='root', level='ERROR') as log:
            self.assertFalse(checker.rh_org_has_subscription("123"))
            self.assertInLog(
                "Unexpected error code (500) returned by AMS backend when listing resource_quota",
                log,
            )

    def test_rh_org_has_subscription_wrong_output(self):
        m_r = Mock()
        m_r.json.side_effect = [
            {"items": [{"id": "rdgdfhbrdb"}]},
            {"msg": "something unexpected"},
        ]
        m_r.status_code = 200

        checker = self.get_default_ams_checker()
        checker._token = Mock()
        checker._session = Mock()
        checker._session.get.return_value = m_r

        with self.assertLogs(logger='root', level='ERROR') as log:
            self.assertFalse(checker.rh_org_has_subscription("123"))
            self.assertInLog("Unexpected resource_quota answer from AMS", log)

    def test_user_is_active(self):
        m_r = Mock()
        m_r.json.side_effect = [
            {"items": [{"id": "fooo"}]},
        ]
        m_r.status_code = 200

        checker = self.get_default_ams_checker()
        checker._token = Mock()
        checker._session = Mock()
        checker._session.get.return_value = m_r

        self.assertTrue(checker.user_is_active("jean-pierre", 123))

    def test_user_is_not_active(self):
        m_r = Mock()
        m_r.json.side_effect = [
            {"items": []},
        ]
        m_r.status_code = 200

        checker = self.get_default_ams_checker()
        checker._token = Mock()
        checker._session = Mock()
        checker._session.get.return_value = m_r

        self.assertFalse(checker.user_is_active("jean-pierre", 123))

    def test_user_is_active_with_api_timeout(self):
        checker = self.get_default_ams_checker()
        checker._session = Mock()
        checker._session.get.side_effect = requests.exceptions.Timeout

        with self.assertLogs(logger='root', level='ERROR') as log:
            self.assertFalse(checker.user_is_active("jean-pierre", 123))
            self.assertInLog("Cannot reach the AMS backend in time", log)

    def test_user_is_active_with_err_500(self):
        checker = self.get_default_ams_checker()
        checker._session = Mock()
        r = requests.Response()
        r.status_code = 500
        checker._session.get.return_value = r

        with self.assertLogs(logger='root', level='ERROR') as log:
            self.assertFalse(checker.user_is_active("jean-pierre", 123))
            self.assertInLog("Unexpected error code (500) returned", log)

    def test_ams_check_with_inactive_user(self):
        checker = self.get_default_ams_checker()
        checker._session = Mock()
        r = requests.Response()
        r.status_code = 500
        checker._session.get.return_value = r

        with self.assertLogs(logger='root', level='DEBUG') as log:
            self.assertFalse(checker.check(321, "jean-pierre", 123))
            self.assertInLog("Unexpected error code (500) returned", log)
            self.assertInLog("username=jean-pierre from org=123 is not active anymore", log)


class TestDummy(WisdomServiceLogAwareTestCase):
    def setUp(self):
        self.checker = DummyCheck()

    def test_self_test(self):
        self.assertIsNone(self.checker.self_test())

    @override_settings(AUTHZ_DUMMY_USERS_WITH_SEAT="yves")
    @override_settings(AUTHZ_DUMMY_ORGS_WITH_SUBSCRIPTION="123")
    def test_check_with_seat(self):
        self.assertTrue(self.checker.check(None, "yves", 123))

    @override_settings(AUTHZ_DUMMY_ORGS_WITH_SUBSCRIPTION="123")
    def test_check_with_no_seat(self):
        self.assertFalse(self.checker.check(None, "noseat", 123))

    @override_settings(AUTHZ_DUMMY_USERS_WITH_SEAT="*")
    @override_settings(AUTHZ_DUMMY_ORGS_WITH_SUBSCRIPTION="123")
    def test_check_with_wildcard(self):
        self.assertTrue(self.checker.check(None, "rose", 123))

    @override_settings(AUTHZ_DUMMY_USERS_WITH_SEAT="yves")
    def test_check_with_no_sub(self):
        self.assertFalse(self.checker.check(None, "noseat", 123))

    @override_settings(AUTHZ_DUMMY_ORGS_WITH_SUBSCRIPTION="123")
    def test_rh_org_has_subscription_with_sub(self):
        self.assertTrue(self.checker.rh_org_has_subscription(123))

    @override_settings(AUTHZ_DUMMY_ORGS_WITH_SUBSCRIPTION="123")
    def test_rh_org_has_subscription_with_param_as_string(self):
        self.assertFalse(self.checker.rh_org_has_subscription("123"))

    def test_rh_org_has_subscription_no_sub(self):
        self.assertFalse(self.checker.rh_org_has_subscription(13))

    @override_settings(AUTHZ_DUMMY_ORGS_WITH_SUBSCRIPTION="*")
    def test_rh_org_has_subscription_all(self):
        self.assertTrue(self.checker.rh_org_has_subscription(56))
