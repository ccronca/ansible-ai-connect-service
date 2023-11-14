"""
Django settings for main project.

Generated by 'django-admin startproject' using Django 4.1.3.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.1/ref/settings/
"""

import os
import sys
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

ANSIBLE_AI_MODEL_NAME = os.getenv("ANSIBLE_AI_MODEL_NAME", "wisdom")

# WCA
ANSIBLE_WCA_INFERENCE_URL = os.getenv("ANSIBLE_WCA_INFERENCE_URL")
ANSIBLE_WCA_FREE_API_KEY = os.getenv("ANSIBLE_WCA_FREE_API_KEY")
ANSIBLE_WCA_FREE_MODEL_ID = os.getenv("ANSIBLE_WCA_FREE_MODEL_ID")
ANSIBLE_WCA_RETRY_COUNT = int(os.getenv("ANSIBLE_WCA_RETRY_COUNT", "4"))


SECRET_KEY = os.environ["SECRET_KEY"]

ALLOWED_HOSTS = ["localhost"]

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "social_django",
    "users",
    "ai",
    "django_prometheus",
    "drf_spectacular",
    "django_extensions",
    "health_check",
    "health_check.db",
    "healthcheck",
    "oauth2_provider",
    'import_export',
]

MIDDLEWARE = [
    "allow_cidr.middleware.AllowCIDRMiddleware",
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "oauth2_provider.middleware.OAuth2TokenMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "social_django.middleware.SocialAuthExceptionMiddleware",
    "main.middleware.SegmentMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
    "csp.middleware.CSPMiddleware",
]

# Allow Prometheus to scrape metrics
ALLOWED_CIDR_NETS = [os.environ.get('ALLOWED_CIDR_NETS', '10.0.0.0/8')]

AUTH_USER_MODEL = "users.User"

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'
LOGIN_ERROR_URL = 'login'

SIGNUP_URL = os.environ.get('SIGNUP_URL', 'https://www.redhat.com/en/engage/project-wisdom')
DOCUMENTATION_URL = os.getenv('DOCUMENTATION_URL', 'https://docs.ai.ansible.redhat.com')
COMMERCIAL_DOCUMENTATION_URL = os.getenv(
    'COMMERCIAL_DOCUMENTATION_URL', 'https://www.redhat.com/en/engage/ansible-lightspeed'
)

SOCIAL_AUTH_JSONFIELD_ENABLED = True
if 'SOCIAL_AUTH_GITHUB_TEAM_KEY' in os.environ:
    USE_GITHUB_TEAM = True
    SOCIAL_AUTH_GITHUB_TEAM_KEY = os.environ.get('SOCIAL_AUTH_GITHUB_TEAM_KEY')
    SOCIAL_AUTH_GITHUB_TEAM_SECRET = os.environ.get('SOCIAL_AUTH_GITHUB_TEAM_SECRET')
    SOCIAL_AUTH_GITHUB_TEAM_ID = os.environ.get('SOCIAL_AUTH_GITHUB_TEAM_ID', 7188893)
    SOCIAL_AUTH_GITHUB_TEAM_SCOPE = ["read:org"]
    SOCIAL_AUTH_GITHUB_TEAM_EXTRA_DATA = ['login']
else:
    USE_GITHUB_TEAM = False
    SOCIAL_AUTH_GITHUB_KEY = os.environ.get('SOCIAL_AUTH_GITHUB_KEY')
    SOCIAL_AUTH_GITHUB_SECRET = os.environ.get('SOCIAL_AUTH_GITHUB_SECRET')
    SOCIAL_AUTH_GITHUB_SCOPE = [""]
    SOCIAL_AUTH_GITHUB_EXTRA_DATA = ['login']

SOCIAL_AUTH_LOGIN_ERROR_URL = '/unauthorized/'

SOCIAL_AUTH_OIDC_OIDC_ENDPOINT = os.environ.get('SOCIAL_AUTH_OIDC_OIDC_ENDPOINT')
SOCIAL_AUTH_OIDC_KEY = os.environ.get('SOCIAL_AUTH_OIDC_KEY')
SOCIAL_AUTH_OIDC_SECRET = os.environ.get('SOCIAL_AUTH_OIDC_SECRET')
SOCIAL_AUTH_OIDC_SCOPE = ['id.idp', 'id.organization', 'roles']
SOCIAL_AUTH_OIDC_EXTRA_DATA = [('preferred_username', 'login')]

AUTHZ_BACKEND_TYPE = os.environ.get("AUTHZ_BACKEND_TYPE")
AUTHZ_SSO_CLIENT_ID = os.environ.get("AUTHZ_SSO_CLIENT_ID")
AUTHZ_SSO_CLIENT_SECRET = os.environ.get("AUTHZ_SSO_CLIENT_SECRET")
AUTHZ_SSO_SERVER = os.environ.get("AUTHZ_SSO_SERVER")
AUTHZ_API_SERVER = os.environ.get("AUTHZ_API_SERVER")

AUTHENTICATION_BACKENDS = [
    "social_core.backends.github.GithubTeamOAuth2"
    if USE_GITHUB_TEAM
    else "social_core.backends.github.GithubOAuth2",
    "social_core.backends.open_id_connect.OpenIdConnectAuth",
    "django.contrib.auth.backends.ModelBackend",
    "oauth2_provider.backends.OAuth2Backend",
]

SOCIAL_AUTH_FIELDS_STORED_IN_SESSION = [
    'terms_accepted',
]
SOCIAL_AUTH_PIPELINE = (
    'users.pipeline.block_auth_users',
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.social_user',
    'main.pipeline.remove_pii',
    'social_core.pipeline.social_auth.auth_allowed',
    'users.pipeline.github_get_username',
    # 'social_core.pipeline.user.get_username',
    'social_core.pipeline.user.create_user',
    'users.pipeline.redhat_organization',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.user.user_details',
    'users.pipeline.load_extra_data',
    'users.pipeline.terms_of_service',
)

# Wisdom Eng Team:
# gh api -H "Accept: application/vnd.github+json" /orgs/ansible/teams/wisdom-contrib

# Write key for sending analytics data to Segment. Note that each of Prod/Dev have a different key.
SEGMENT_WRITE_KEY = os.environ.get("SEGMENT_WRITE_KEY")

OAUTH2_PROVIDER = {
    'SCOPES': {
        'read': "Read basic user information",
        'write': "Request Ansible content suggestions",
    },
    'ALLOWED_REDIRECT_URI_SCHEMES': [
        'http',
        'https',
        'vscode',
        'vscodium',
        'vscode-insiders',
        'code-oss',
        'checode',
    ],
    # ACCESS_TOKEN_EXPIRE_SECONDS = 36_000  # = 10 hours, default value
    'REFRESH_TOKEN_EXPIRE_SECONDS': 864_000,  # = 10 days
}

#
# We need to run 'manage.py migrate' before adding our own OAuth2 application model.
# See https://django-oauth-toolkit.readthedocs.io/en/latest/advanced_topics.html
# #extending-the-application-model
#
# Also, if these lines are executed in testing, test fails with:
#   django.db.utils.ProgrammingError: relation "users_user" does not exist
#
if sys.argv[1:2] not in [['migrate'], ['test']]:
    INSTALLED_APPS.append('wildcard_oauth2')
    OAUTH2_PROVIDER_APPLICATION_MODEL = 'wildcard_oauth2.Application'

# OAUTH: todo
# - remove ansible_wisdom/users/auth.py module
# - remove ansible_wisdom/users/views.py module
# - remove "Authentication Token" line from ansible_wisdom/users/templates/users/home.html

COMPLETION_USER_RATE_THROTTLE = os.environ.get('COMPLETION_USER_RATE_THROTTLE') or '10/minute'
SPECIAL_THROTTLING_GROUPS = ['test']

MULTI_TASK_MAX_REQUESTS = os.environ.get('MULTI_TASK_MAX_REQUESTS', 10)

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'DEFAULT_THROTTLE_CLASSES': ['users.throttling.GroupSpecificThrottle'],
    'DEFAULT_THROTTLE_RATES': {
        'user': COMPLETION_USER_RATE_THROTTLE,
        'test': "100000/minute",
    },
    'PAGE_SIZE': 10,
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'oauth2_provider.contrib.rest_framework.OAuth2Authentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'main.exception_handler.exception_handler_with_error_type',
    'DEFAULT_RENDERER_CLASSES': ('rest_framework.renderers.JSONRenderer',),
}

ROOT_URLCONF = "main.urls"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "{levelname} {asctime} {filename}:{funcName} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple", "level": "INFO"},
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "propagate": True,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "users.signals": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.getenv("DJANGO_LOG_LEVEL", "WARNING"),
    },
}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "social_django.context_processors.backends",
            ],
        },
    },
]

WSGI_APPLICATION = "main.wsgi.application"

# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["ANSIBLE_AI_DATABASE_NAME"],
        "USER": os.environ["ANSIBLE_AI_DATABASE_USER"],
        "PASSWORD": os.environ["ANSIBLE_AI_DATABASE_PASSWORD"],
        "HOST": os.environ["ANSIBLE_AI_DATABASE_HOST"],
        "PORT": os.getenv("ANSIBLE_AI_DATABASE_PORT", 5432),
    }
}

# Model API Timeout (in seconds). Default is None.
ANSIBLE_AI_MODEL_MESH_API_TIMEOUT = os.getenv("ANSIBLE_AI_MODEL_MESH_API_TIMEOUT")

# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

STATIC_URL = "static/"

# Absolute filesystem path to the directory where static file are collected via
# the collectstatic command.
STATIC_ROOT = '/var/www/wisdom/public/static'

# Paths to where static files that are not explicitly part of a
# particular Django app should be collected from.
STATICFILES_DIRS = [BASE_DIR / 'static']

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

APPEND_SLASH = True

MOCK_MODEL_RESPONSE_BODY = os.environ.get(
    'MOCK_MODEL_RESPONSE_BODY',
    (
        '{"predictions":["ansible.builtin.apt:\\n  name: nginx\\n'
        '  update_cache: true\\n  state: present\\n"]}'
    ),
)

MOCK_MODEL_RESPONSE_MAX_LATENCY_MSEC = int(
    os.environ.get('MOCK_MODEL_RESPONSE_MAX_LATENCY_MSEC', 3000)
)
MOCK_MODEL_RESPONSE_LATENCY_USE_JITTER = bool(
    os.environ.get('MOCK_MODEL_RESPONSE_LATENCY_USE_JITTER', False)
)

ENABLE_ARI_POSTPROCESS = os.getenv('ENABLE_ARI_POSTPROCESS', 'False').lower() == 'true'
ARI_BASE_DIR = os.getenv('ARI_KB_PATH', '/etc/ari/kb/')
ARI_RULES_DIR = os.path.join(ARI_BASE_DIR, 'rules')
ARI_DATA_DIR = os.path.join(ARI_BASE_DIR, 'data')
ARI_RULES = [
    "P001",
    "P002",
    "P003",
    "P004",
    "W001",
    "W003",
    "W004",
    "W005",
    "W006",
    "W007",
    "W008",
    "W009",
    "W010",
    "W011",  # replace with_* loop with the modern loop:
    "W012",
    "W013",
    # "W014",  # anonymizer: already done by the ansible_wisdom app
    "W015",
    "W016",
    "W017",
    "W018",
    "W019",
    "W021",
    "W022",
    "W023",
    "W024",
    "W025",
    "W026",
    "W027",
]
if 'ARI_RULES' in os.environ:
    ARI_RULES = os.environ['ARI_RULES'].split(',')
ARI_RULE_FOR_OUTPUT_RESULT = os.getenv('ARI_RULE_FOR_OUTPUT_RESULT', "W007")

ENABLE_ANSIBLE_LINT_POSTPROCESS = (
    os.getenv('ENABLE_ANSIBLE_LINT_POSTPROCESS', 'False').lower() == 'true'
)

ANSIBLE_LINT_TRANSFORM_RULES = ["all"]

ENABLE_ADDITIONAL_CONTEXT = os.getenv('ENABLE_ADDITIONAL_CONTEXT', 'False').lower() == 'true'

LAUNCHDARKLY_SDK_KEY = os.getenv('LAUNCHDARKLY_SDK_KEY', '')

ANSIBLE_AI_SEARCH = {
    'HOST': os.getenv('ANSIBLE_AI_SEARCH_HOST', ''),
    'PORT': int(os.getenv('ANSIBLE_AI_SEARCH_PORT') or '443'),
    'KEY': os.getenv('ANSIBLE_AI_SEARCH_KEY'),
    'SECRET': os.getenv('ANSIBLE_AI_SEARCH_SECRET'),
    'REGION': os.getenv('ANSIBLE_AI_SEARCH_REGION'),
    'USE_SSL': True,
    'VERIFY_CERTS': True,
    'INDEX': os.getenv('ANSIBLE_AI_SEARCH_INDEX', 'attribution'),
    # MODEL, DIMENSION, and METHOD all need to match for the underlying model chosen
    'MODEL': os.getenv('ANSIBLE_AI_SEARCH_MODEL', 'all-MiniLM-L6-v2'),
    'DIMENSION': int(os.getenv('ANSIBLE_AI_SEARCH_DIMENSION') or '384'),
    'METHOD': dict(
        x.split(':')
        for x in os.getenv(
            'ANSIBLE_AI_SEARCH_METHOD', 'name:hnsw,space_type:innerproduct,engine:nmslib'
        ).split(',')
    ),
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "cache",
    }
}

WCA_SECRET_MANAGER_ACCESS_KEY = os.getenv('WCA_SECRET_MANAGER_ACCESS_KEY', '')
WCA_SECRET_MANAGER_SECRET_ACCESS_KEY = os.getenv('WCA_SECRET_MANAGER_SECRET_ACCESS_KEY', '')
WCA_SECRET_MANAGER_KMS_KEY_ID = os.getenv('WCA_SECRET_MANAGER_KMS_KEY_ID', '')
WCA_SECRET_MANAGER_PRIMARY_REGION = os.getenv('WCA_SECRET_MANAGER_PRIMARY_REGION', '')
WCA_SECRET_MANAGER_REPLICA_REGIONS = [
    c.strip() for c in os.getenv('WCA_SECRET_MANAGER_REPLICA_REGIONS', '').split(',') if c
]
MOCK_WCA_SECRETS_MANAGER = os.environ.get("MOCK_WCA_SECRETS_MANAGER", "False") == "True"

CSP_DEFAULT_SRC = ("'self'", "data:")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_INCLUDE_NONCE_IN = ['script-src-elem']

# Region for where the service is deployed. Used by the Health Check endpoint.
DEPLOYED_REGION = os.getenv('DEPLOYED_REGION', 'unknown')

# Support to disable health checks. The default is that they are enabled.
# The naming convention in the existing settings is to ENABLE_XXX and not DISABLE_XXX.
ENABLE_HEALTHCHECK_MODEL_MESH = os.getenv('ENABLE_HEALTHCHECK_MODEL_MESH', 'True').lower() == 'true'
ENABLE_HEALTHCHECK_SECRET_MANAGER = (
    os.getenv('ENABLE_HEALTHCHECK_SECRET_MANAGER', 'True').lower() == 'true'
)
ENABLE_HEALTHCHECK_WCA = os.getenv('ENABLE_HEALTHCHECK_WCA', 'True').lower() == 'true'
ENABLE_HEALTHCHECK_AUTHORIZATION = (
    os.getenv('ENABLE_HEALTHCHECK_AUTHORIZATION', 'True').lower() == 'true'
)
ENABLE_HEALTHCHECK_ATTRIBUTION = (
    os.getenv('ENABLE_HEALTHCHECK_ATTRIBUTION', 'True').lower() == 'true'
)
