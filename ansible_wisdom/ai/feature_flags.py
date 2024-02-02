import logging
import os.path
from enum import Enum

from django.conf import settings
from ldclient import Context
from ldclient.client import LDClient
from ldclient.config import Config
from ldclient.integrations import Files
from users.models import User

logger = logging.getLogger(__name__)


class WisdomFlags(str, Enum):
    # model name selection
    MODEL_NAME = "model_name"
    # Schema 2 Telemetry is enabled for an Organization
    SCHEMA_2_TELEMETRY_ORG_ENABLED = "schema_2_telemetry_org_enabled"


class FeatureFlags:
    instance = None

    # Ensure FeatureFlags is a Singleton
    def __new__(cls):
        if cls.instance is not None:
            return cls.instance
        else:
            inst = cls.instance = super().__new__(cls)
            return inst

    def __init__(self):
        self.client = None
        if settings.LAUNCHDARKLY_SDK_KEY:
            if os.path.exists(settings.LAUNCHDARKLY_SDK_KEY):
                data_source_callback = Files.new_data_source(
                    paths=[settings.LAUNCHDARKLY_SDK_KEY], auto_update=True
                )
                # SDK is needed but since there is no real connection it can be any string
                # update_processor reload the file data if it detects that you have modified a file.
                # send_event needed to prevent analytics event to raise
                self.client = LDClient(
                    Config(
                        'sdk-key-123abc',
                        update_processor_class=data_source_callback,
                        send_events=False,
                    )
                )
                logger.info("development version of feature flag client initialized")
            else:
                self.client = LDClient(
                    Config(settings.LAUNCHDARKLY_SDK_KEY),
                    start_wait=settings.LAUNCHDARKLY_SDK_TIMEOUT,
                )
                logger.info("feature flag client initialized")

    def get(self, name: str, user: User, default: str):
        if self.client:
            if user.is_anonymous:
                user_context = Context.builder("AnonymousUser").anonymous(True).build()
            else:
                groups = list(user.groups.values_list("name", flat=True))
                userId = str(user.uuid)

                logger.debug(f"constructing user context for {userId}")
                user_context = (
                    Context.builder(userId)
                    .set("username", user.username)
                    .set("groups", groups)
                    .build()
                )
            logger.debug(f"retrieving feature flag {name}")
            return self.client.variation(name, user_context, default)
        else:
            raise Exception("feature flag client is not initialized")

    def is_schema_2_telemetry_enabled(self, org_id: int) -> bool:
        if self.client:
            logger.debug(f"constructing User context for Organization '{org_id}'")
            logger.debug(f"retrieving feature flag '{WisdomFlags.SCHEMA_2_TELEMETRY_ORG_ENABLED}'")
            context = Context.builder(str(org_id)).set("org_id", org_id).build()
            return self.client.variation(WisdomFlags.SCHEMA_2_TELEMETRY_ORG_ENABLED, context, False)
        else:
            raise Exception("feature flag client is not initialized")
