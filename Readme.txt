================================================================================
  UNIVERSAL API INGESTOR FRAMEWORK — README
================================================================================

OVERVIEW
--------
A config-driven API ingestion framework for Snowflake that fetches data from
external REST APIs. It handles authentication, pagination, retry with backoff,
payload deduplication (SHA-256 hash), and response logging — all orchestrated
via stored procedures.

Database: API_DATA_PIPELINE
Schemas:  METADATA (configs, logs, procedures)
          RAW_LANDING (raw JSON payloads)


================================================================================
ARCHITECTURE
================================================================================

  +---------------------+       +----------------------------+
  | INGESTION_CONFIGS   |       | INGESTION_RESPONSE_LOG     |
  | (config per API)    |       | (audit log per HTTP call)  |
  +---------------------+       +----------------------------+
           |                                 ^
           v                                 |
  +----------------------------------------------+
  |       USP_UNIVERSAL_INGESTOR(api_name)       |
  |  - Reads config                              |
  |  - Authenticates (4 modes)                   |
  |  - Applies extra headers                     |
  |  - Paginates (PAGE/OFFSET/NONE)              |
  |  - Retries with backoff                      |
  |  - Deduplicates via payload hash             |
  |  - Logs every response                       |
  +----------------------------------------------+
           |                                 ^
           v                                 |
  +----------------------------+    +---------------------+
  | RAW_LANDING.API_RAW_DATA   |    | USP_REBUILD_INGESTOR|
  | (raw JSON landing table)   |    | (recreates proc     |
  +----------------------------+    |  with SECRETS clause)|
                                    +---------------------+


================================================================================
AUTHENTICATION TYPES — FLOW FOR EACH
================================================================================

The framework supports 4 authentication types, set via the AUTH_TYPE column in
INGESTION_CONFIGS. Below is the setup flow for each.


------------------------------------------------------------------------
1. AUTH_TYPE = 'NONE' (No Authentication)
------------------------------------------------------------------------
Use for public APIs that require no credentials.

SETUP STEPS:
  1. Create a Network Rule for the API host
  2. Add the network rule to EAI_UNIVERSAL_INGESTOR
  3. Insert config row

EXAMPLE:
  -- Network Rule
  CREATE OR REPLACE NETWORK RULE API_DATA_PIPELINE.METADATA.NR_PUBLIC_API
    MODE = EGRESS
    TYPE = HOST_PORT
    VALUE_LIST = ('api.example.com');

  -- Update EAI
  ALTER EXTERNAL ACCESS INTEGRATION EAI_UNIVERSAL_INGESTOR
    SET ALLOWED_NETWORK_RULES = (...existing..., API_DATA_PIPELINE.METADATA.NR_PUBLIC_API);

  -- Config
  INSERT INTO API_DATA_PIPELINE.METADATA.INGESTION_CONFIGS
    (API_NAME, ENDPOINT_URL, HTTP_METHOD, AUTH_TYPE, PAGINATION_TYPE)
  VALUES
    ('PUBLIC_API', 'https://api.example.com/data', 'GET', 'NONE', 'NONE');

  -- Rebuild & Run
  CALL API_DATA_PIPELINE.METADATA.USP_REBUILD_INGESTOR();
  CALL API_DATA_PIPELINE.METADATA.USP_UNIVERSAL_INGESTOR('PUBLIC_API');

CONFIG COLUMNS USED:
  - ENDPOINT_URL, HTTP_METHOD, PAGINATION_TYPE, PAGE_PARAM, START_INDEX
  - MAX_RETRIES, RETRY_DELAY_SEC, TIMEOUT_SEC
  - EXTRA_HEADERS_JSON (optional)


------------------------------------------------------------------------
2. AUTH_TYPE = 'API_KEY' (Static API Key)
------------------------------------------------------------------------
Use for APIs that require a static key sent as a header.
The key is stored securely in a Snowflake GENERIC_STRING secret.

SETUP STEPS:
  1. Create a GENERIC_STRING secret with the API key
  2. Create a Network Rule for the API host
  3. Add the secret and network rule to EAI_UNIVERSAL_INGESTOR
  4. Insert config row with SECRET_NAME and API_KEY_HEADER
  5. Rebuild the ingestor

EXAMPLE:
  -- Secret
  CREATE OR REPLACE SECRET API_DATA_PIPELINE.METADATA.SK_MY_API_KEY
    TYPE = GENERIC_STRING
    SECRET_STRING = 'your-api-key-here';

  -- Network Rule
  CREATE OR REPLACE NETWORK RULE API_DATA_PIPELINE.METADATA.NR_MY_API
    MODE = EGRESS
    TYPE = HOST_PORT
    VALUE_LIST = ('api.example.com');

  -- Update EAI
  ALTER EXTERNAL ACCESS INTEGRATION EAI_UNIVERSAL_INGESTOR
    SET ALLOWED_NETWORK_RULES = (...existing..., API_DATA_PIPELINE.METADATA.NR_MY_API)
        ALLOWED_AUTHENTICATION_SECRETS = (...existing..., API_DATA_PIPELINE.METADATA.SK_MY_API_KEY);

  -- Config
  INSERT INTO API_DATA_PIPELINE.METADATA.INGESTION_CONFIGS
    (API_NAME, ENDPOINT_URL, HTTP_METHOD, AUTH_TYPE, SECRET_NAME, API_KEY_HEADER, PAGINATION_TYPE)
  VALUES
    ('MY_API', 'https://api.example.com/data', 'GET', 'API_KEY', 'SK_MY_API_KEY', 'X-Api-Key', 'NONE');

  -- Rebuild & Run
  CALL API_DATA_PIPELINE.METADATA.USP_REBUILD_INGESTOR();
  CALL API_DATA_PIPELINE.METADATA.USP_UNIVERSAL_INGESTOR('MY_API');

HOW IT WORKS:
  1. Procedure reads SECRET_NAME from config -> 'SK_MY_API_KEY'
  2. Calls _snowflake.get_generic_secret_string('sk_my_api_key')
  3. Sets headers[API_KEY_HEADER] = <key value>
  4. Makes the API call with the key in the header

CONFIG COLUMNS USED:
  - SECRET_NAME (references the GENERIC_STRING secret)
  - API_KEY_HEADER (header name, e.g., 'X-Api-Key', 'Authorization')


------------------------------------------------------------------------
3. AUTH_TYPE = 'OAUTH2_BASIC' (Manual OAuth2 Client Credentials)
------------------------------------------------------------------------
Use when you want the procedure to perform the OAuth2 token exchange itself
(POST to token endpoint with client_id/client_secret).
Credentials are stored in a Snowflake PASSWORD secret.

SETUP STEPS:
  1. Create a PASSWORD secret (username=client_id, password=client_secret)
  2. Create a Network Rule for BOTH the token endpoint AND the API host
  3. Add the secret and network rule to EAI_UNIVERSAL_INGESTOR
  4. Insert config row with SECRET_NAME and TOKEN_URL
  5. Rebuild the ingestor

EXAMPLE:
  -- Secret (client_id as username, client_secret as password)
  CREATE OR REPLACE SECRET API_DATA_PIPELINE.METADATA.SK_MY_OAUTH_CREDS
    TYPE = PASSWORD
    USERNAME = 'my_client_id'
    PASSWORD = 'my_client_secret';

  -- Network Rule (must include both token host and API host)
  CREATE OR REPLACE NETWORK RULE API_DATA_PIPELINE.METADATA.NR_MY_OAUTH_API
    MODE = EGRESS
    TYPE = HOST_PORT
    VALUE_LIST = ('auth.example.com', 'api.example.com');

  -- Update EAI
  ALTER EXTERNAL ACCESS INTEGRATION EAI_UNIVERSAL_INGESTOR
    SET ALLOWED_NETWORK_RULES = (...existing..., API_DATA_PIPELINE.METADATA.NR_MY_OAUTH_API)
        ALLOWED_AUTHENTICATION_SECRETS = (...existing..., API_DATA_PIPELINE.METADATA.SK_MY_OAUTH_CREDS);

  -- Config
  INSERT INTO API_DATA_PIPELINE.METADATA.INGESTION_CONFIGS
    (API_NAME, ENDPOINT_URL, HTTP_METHOD, AUTH_TYPE, SECRET_NAME, TOKEN_URL, PAGINATION_TYPE)
  VALUES
    ('MY_OAUTH_API', 'https://api.example.com/data', 'GET', 'OAUTH2_BASIC',
     'SK_MY_OAUTH_CREDS', 'https://auth.example.com/oauth/token', 'PAGE');

  -- Rebuild & Run
  CALL API_DATA_PIPELINE.METADATA.USP_REBUILD_INGESTOR();
  CALL API_DATA_PIPELINE.METADATA.USP_UNIVERSAL_INGESTOR('MY_OAUTH_API');

HOW IT WORKS:
  1. Procedure reads SECRET_NAME from config -> 'SK_MY_OAUTH_CREDS'
  2. Calls _snowflake.get_username_password('sk_my_oauth_creds')
  3. POSTs to TOKEN_URL with grant_type=client_credentials, client_id, client_secret
  4. Extracts access_token from response
  5. Sets Authorization: Bearer <token>
  6. Makes the API call

CONFIG COLUMNS USED:
  - SECRET_NAME (references the PASSWORD secret)
  - TOKEN_URL (the OAuth2 token endpoint)


------------------------------------------------------------------------
4. AUTH_TYPE = 'OAUTH2_INTEGRATION' (Snowflake-Managed OAuth2)
------------------------------------------------------------------------
Use when Snowflake manages the full OAuth2 lifecycle via a Security Integration.
Snowflake handles token exchange, refresh, and caching automatically.
This is the recommended approach for production.

SETUP STEPS:
  1. Create a Security Integration (API_AUTHENTICATION type) clinet id, client secrt, client token url
  2. Create an OAUTH2 secret linked to the integration
  3. Create a Network Rule for BOTH the token endpoint AND the API host
  4. Add the secret and network rule to EAI_UNIVERSAL_INGESTOR
  5. Insert config row with SECRET_NAME, INTEGRATION_NAME, and EXTRA_HEADERS_JSON
  6. Rebuild the ingestor

EXAMPLE (Twitch API):
  -- Security Integration
  CREATE OR REPLACE SECURITY INTEGRATION SEC_INT_TWITCH_TEST
    TYPE = API_AUTHENTICATION
    AUTH_TYPE = OAUTH2
    OAUTH_CLIENT_ID = '<your_client_id>'
    OAUTH_CLIENT_SECRET = '<your_client_secret>'
    OAUTH_TOKEN_ENDPOINT = 'https://id.twitch.tv/oauth2/token'
    OAUTH_CLIENT_AUTH_METHOD = CLIENT_SECRET_POST
    OAUTH_GRANT = CLIENT_CREDENTIALS
    OAUTH_ALLOWED_SCOPES = ('')
    ENABLED = TRUE;

  -- OAUTH2 Secret (linked to integration)
  CREATE OR REPLACE SECRET API_DATA_PIPELINE.METADATA.SK_TWITCH_INT_TEST
    TYPE = OAUTH2
    API_AUTHENTICATION = SEC_INT_TWITCH_TEST;

  -- Network Rule (must include both token host and API host)
  CREATE OR REPLACE NETWORK RULE API_DATA_PIPELINE.METADATA.NR_TWITCH_TEST
    MODE = EGRESS
    TYPE = HOST_PORT
    VALUE_LIST = ('id.twitch.tv', 'api.twitch.tv');

  -- Update EAI
  ALTER EXTERNAL ACCESS INTEGRATION EAI_UNIVERSAL_INGESTOR
    SET ALLOWED_NETWORK_RULES = (...existing..., API_DATA_PIPELINE.METADATA.NR_TWITCH_TEST)
        ALLOWED_AUTHENTICATION_SECRETS = (...existing..., API_DATA_PIPELINE.METADATA.SK_TWITCH_INT_TEST);

  -- Config (note EXTRA_HEADERS_JSON for Twitch Client-Id requirement)
  INSERT INTO API_DATA_PIPELINE.METADATA.INGESTION_CONFIGS
    (API_NAME, ENDPOINT_URL, HTTP_METHOD, AUTH_TYPE, SECRET_NAME, INTEGRATION_NAME,
     PAGINATION_TYPE, MAX_RETRIES, RETRY_DELAY_SEC, TIMEOUT_SEC, EXTRA_HEADERS_JSON)
  VALUES
    ('TWITCH_INT_TEST', 'https://api.twitch.tv/helix/games/top', 'GET',
     'OAUTH2_INTEGRATION', 'SK_TWITCH_INT_TEST', 'SEC_INT_TWITCH_TEST',
     'NONE', 3, 10, 30,
     '{"Client-Id": "<your_client_id>"}');

  -- Rebuild & Run
  CALL API_DATA_PIPELINE.METADATA.USP_REBUILD_INGESTOR();
  CALL API_DATA_PIPELINE.METADATA.USP_UNIVERSAL_INGESTOR('TWITCH_INT_TEST');

HOW IT WORKS:
  1. Procedure reads SECRET_NAME from config -> 'SK_TWITCH_INT_TEST'
  2. Calls _snowflake.get_oauth_access_token('sk_twitch_int_test')
  3. Snowflake automatically handles the token exchange via the Security Integration
  4. Sets Authorization: Bearer <token>
  5. Merges any EXTRA_HEADERS_JSON into the request headers
  6. Makes the API call

CONFIG COLUMNS USED:
  - SECRET_NAME (references the OAUTH2 secret)
  - INTEGRATION_NAME (the Security Integration name, for documentation)
  - EXTRA_HEADERS_JSON (additional headers like Client-Id)

NOTE: The client_id cannot be fetched from the Security Integration at runtime.
      If the API requires it as a header (e.g., Twitch), pass it via EXTRA_HEADERS_JSON.


================================================================================
EXTRA HEADERS (EXTRA_HEADERS_JSON)
================================================================================
Some APIs require additional headers beyond authentication (e.g., Twitch requires
Client-Id). Use the EXTRA_HEADERS_JSON column to pass a JSON object of key-value
pairs that get merged into the request headers after authentication.

  EXTRA_HEADERS_JSON = '{"Client-Id": "abc123", "X-Custom": "value"}'

These headers are applied for ALL auth types, after the auth headers are set.


================================================================================
PAGINATION TYPES
================================================================================

  PAGE   — Appends ?{PAGE_PARAM}=1, 2, 3... (integer increment)
  OFFSET — Appends ?{PAGE_PARAM}=0, 100, 200... (offset increment of 100)
  NONE   — Single request, no pagination

Pagination stops when:
  - PAGINATION_TYPE is NONE (single page only)
  - The response contains {"data": []} (empty data array)
  - The API returns a non-200 status code


================================================================================
RETRY & RESILIENCE
================================================================================
Each API call is retried up to MAX_RETRIES times with RETRY_DELAY_SEC delay
between attempts. Every HTTP call (success or failure) is logged to
INGESTION_RESPONSE_LOG with status code, response time, error message,
and retry count.


================================================================================
DEDUPLICATION
================================================================================
Each response payload is hashed (SHA-256). Before inserting into API_RAW_DATA,
the hash is checked against existing records. Duplicate payloads are skipped.


================================================================================
USP_REBUILD_INGESTOR — DYNAMIC SECRET MANAGEMENT
================================================================================
Snowflake requires SECRETS to be declared statically at procedure creation time.
USP_REBUILD_INGESTOR solves this by:
  1. Reading all active SECRET_NAMEs from INGESTION_CONFIGS
  2. Dynamically generating a CREATE OR REPLACE PROCEDURE statement
  3. Executing it to recreate USP_UNIVERSAL_INGESTOR with the correct SECRETS clause

You MUST call USP_REBUILD_INGESTOR() after:
  - Adding a new API with a new secret
  - Changing an existing API's SECRET_NAME
  - Removing an API


================================================================================
WORKFLOW SUMMARY — ADDING A NEW API
================================================================================

  1. Create the secret (GENERIC_STRING / PASSWORD / OAUTH2)
  2. Create a security integration (only for OAUTH2_INTEGRATION)
  3. Create a network rule for the API host(s)
  4. Add secret + network rule to EAI_UNIVERSAL_INGESTOR
  5. INSERT config row into INGESTION_CONFIGS
  6. CALL USP_REBUILD_INGESTOR()
  7. CALL USP_UNIVERSAL_INGESTOR('<API_NAME>')
  8. Verify: SELECT * FROM RAW_LANDING.API_RAW_DATA WHERE API_NAME = '<API_NAME>'
  9. Audit:  SELECT * FROM INGESTION_RESPONSE_LOG WHERE API_NAME = '<API_NAME>'


================================================================================
INGESTION_CONFIGS — COLUMN REFERENCE
================================================================================

  Column               | Description
  ---------------------|----------------------------------------------------
  API_NAME             | Unique identifier (PRIMARY KEY)
  ENDPOINT_URL         | The API endpoint URL
  HTTP_METHOD          | GET (default) or POST
  AUTH_TYPE            | NONE | API_KEY | OAUTH2_BASIC | OAUTH2_INTEGRATION
  API_KEY_HEADER       | Header name for API_KEY auth (e.g., 'X-Api-Key')
  API_KEY_VALUE        | Unused in active code (legacy column)
  SECRET_NAME          | Snowflake SECRET object name (used as alias)
  INTEGRATION_NAME     | Security Integration name (for OAUTH2_INTEGRATION)
  TOKEN_URL            | Token endpoint (for OAUTH2_BASIC)
  PAGINATION_TYPE      | NONE | PAGE | OFFSET
  PAGE_PARAM           | Query param name (e.g., 'page', 'offset', 'after')
  START_INDEX          | Starting page/offset (default: 1)
  MAX_RETRIES          | Max retry attempts (default: 6)
  RETRY_DELAY_SEC      | Delay between retries in seconds (default: 15)
  TIMEOUT_SEC          | HTTP request timeout in seconds (default: 30)
  EXTRA_HEADERS_JSON   | JSON object of additional headers
  ACTIVE_FLAG          | TRUE/FALSE to enable/disable
  CREATED_TS           | Auto-populated creation timestamp
