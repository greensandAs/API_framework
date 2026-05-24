-- Use the top-level admin role for setup
-- USE ROLE ACCOUNTADMIN;

-- Create a dedicated database for all ingestion activities
CREATE DATABASE IF NOT EXISTS API_DATA_PIPELINE;

-- Create a logically named schema for the framework components
CREATE SCHEMA IF NOT EXISTS API_DATA_PIPELINE.METADATA;
USE SCHEMA API_DATA_PIPELINE.METADATA;


CREATE OR REPLACE TABLE INGESTION_CONFIGS (
    api_name STRING PRIMARY KEY,
    endpoint_url STRING,
    http_method STRING DEFAULT 'GET',
    
    -- Authentication Strategy
    auth_type STRING,              -- NONE | API_KEY | OAUTH2_BASIC | OAUTH2_INTEGRATION
    
    -- For Basic API Key
    api_key_header STRING,
    api_key_value STRING,          -- (Use only for non-sensitive trial keys)
    
    -- For Enterprise OAuth2 (The 'New' Vision)
    secret_name STRING,            -- The Snowflake SECRET object name
    integration_name STRING,       -- The External Access Integration name [cite: 23]
    token_url STRING,              -- Required for Manual OAuth Handshake
    
    -- Pagination & Resilience
    pagination_type STRING,        -- NONE | PAGE | OFFSET
    page_param STRING,             -- e.g., 'page' or 'offset'
    start_index INTEGER DEFAULT 1,
    max_retries INTEGER DEFAULT 6, -- Expanded per AlsoEnergy reference
    retry_delay_sec INTEGER DEFAULT 15,
    timeout_sec INTEGER DEFAULT 30,
    
    -- Extra Headers (JSON object for additional headers like Client-Id)
    extra_headers_json STRING,         -- e.g., '{"Client-Id": "abc123"}'
    
    active_flag BOOLEAN DEFAULT TRUE,
    created_ts TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

ALTER TABLE API_DATA_PIPELINE.METADATA.INGESTION_CONFIGS ADD COLUMN LANDING_TABLE VARCHAR DEFAULT NULL;

CREATE SCHEMA IF NOT EXISTS RAW_LANDING;
USE SCHEMA API_DATA_PIPELINE.METADATA;
-- Centralized Landing Table
CREATE OR REPLACE TABLE RAW_LANDING.API_RAW_DATA (
    ingest_ts TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    api_name STRING,
    status_code INTEGER,
    payload VARIANT,               -- Stores the raw JSON response [cite: 6, 16]
    payload_hash STRING,           -- Used for deduplication
    url_attempted STRING
);


USE SCHEMA API_DATA_PIPELINE.METADATA;
-- Response Log (The 'Black Box' recorder)
CREATE OR REPLACE TABLE INGESTION_RESPONSE_LOG (
    insert_datetime_utc TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    api_name STRING,
    api_url STRING,
    status_code INTEGER,
    response_time_seconds FLOAT,
    error_message_text STRING,
    retry_count INTEGER
);


-- CREATE OR REPLACE PROCEDURE sp_ingest_api_data(api_target STRING)
-- RETURNS STRING
-- LANGUAGE PYTHON
-- RUNTIME_VERSION = '3.9'
-- PACKAGES = ('snowflake-snowpark-python','requests')
-- HANDLER = 'main'
-- EXTERNAL_ACCESS_INTEGRATIONS = (eai_api_framework)
-- AS
-- $$
-- from snowflake.snowpark import Session
-- import requests, json, hashlib
-- from datetime import datetime

-- def main(session: Session, api_target: str):
--     # 1. Fetch Configuration [cite: 8]
--     cfg = session.sql(f"SELECT * FROM ingestion_configs WHERE api_name = '{api_target}' AND active_flag = TRUE").collect()
--     if not cfg: return f"Error: Config for {api_target} not found."
--     row = cfg[0]

--     headers = json.loads(row["HEADERS_JSON"]) if row["HEADERS_JSON"] else {}
    
--     # 2. Handle Authentication [cite: 9, 10]
--     if row["AUTH_TYPE"] == "API_KEY":
--         headers[row["API_KEY_HEADER"]] = row["API_KEY_VALUE"]
--     elif row["AUTH_TYPE"] == "OAUTH2":
--         token_resp = requests.post(row["OAUTH_TOKEN_URL"], data={"grant_type": "client_credentials", "client_id": row["OAUTH_CLIENT_ID"], "client_secret": row["OAUTH_CLIENT_SECRET"]})
--         headers["Authorization"] = f"Bearer {token_resp.json()['access_token']}"

--     # 3. Ingestion & Pagination Loop [cite: 11, 12]
--     page = row["START_PAGE"] or 1
--     pages_processed = 0
    
--     while True:
--         url = row["ENDPOINT_URL"]
--         if row["PAGINATION_TYPE"] == "PAGE":
--             url += f"{'&' if '?' in url else '?'}{row['PAGE_PARAM']}={page}"

--         response = requests.request(method=row["HTTP_METHOD"], url=url, headers=headers, timeout=row["TIMEOUT_SEC"])
--         if response.status_code != 200: break

--         # 4. Deduplication & Save [cite: 13, 14, 15]
--         payload = response.json()
--         payload_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        
--         # Check if hash already exists
--         exists = session.sql(f"SELECT 1 FROM raw_landing_zone WHERE payload_hash = '{payload_hash}'").collect()
        
--         if not exists:
--             payload_str = json.dumps(payload)
--             session.sql(
--                 "INSERT INTO raw_landing_zone (api_name, status_code, payload, payload_hash) "
--                 "SELECT ?, ?, PARSE_JSON(?), ?",
--                 params=[api_target, response.status_code, payload_str, payload_hash]
--             ).collect()

--         pages_processed += 1
--         if row["PAGINATION_TYPE"] == "NONE" or (isinstance(payload, dict) and "data" in payload and len(payload["data"]) == 0): break
--         page += 1

--     return f"Success: {api_target} ingested. Pages: {pages_processed}"
-- $$;


-- CREATE OR REPLACE PROCEDURE API_DATA_PIPELINE.METADATA.USP_UNIVERSAL_INGESTOR(API_TARGET STRING)
-- RETURNS STRING
-- LANGUAGE PYTHON
-- RUNTIME_VERSION = '3.10'
-- PACKAGES = ('snowflake-snowpark-python','requests')
-- HANDLER = 'main'
-- EXTERNAL_ACCESS_INTEGRATIONS = (EAI_UNIVERSAL_INGESTOR)
-- AS
-- $$
-- import _snowflake
-- import requests
-- import json
-- import hashlib
-- import time

-- def main(session, api_target):
--     # 1. Fetch Configuration (Brain Lookup)
--     # Using relative table name to avoid Database/Schema existence errors
--     cfg_query = f"SELECT * FROM INGESTION_CONFIGS WHERE API_NAME = '{api_target}'"
--     cfg_res = session.sql(cfg_query).collect()
    
--     if not cfg_res:
--         return f"Error: Configuration for {api_target} not found in INGESTION_CONFIGS."
    
--     cfg = cfg_res[0]
--     headers = {"Accept": "application/json"}
--     auth_type = cfg["AUTH_TYPE"]

--     # 2. THE AUTHENTICATION SWITCHBOARD (Fixed for Uppercase DDL)
--     try:
--         if auth_type == "NONE":
--             pass 
            
--         elif auth_type == "API_KEY":
--             headers[cfg["API_KEY_HEADER"]] = cfg["API_KEY_VALUE"]
            
--         elif auth_type == "OAUTH2_BASIC":
--             # Manual Handshake (Postman Test Case)
--             token_payload = {
--                 "grant_type": "client_credentials",
--                 "client_id": cfg["OAUTH_CLIENT_ID"],
--                 "client_secret": cfg["OAUTH_CLIENT_SECRET"]
--             }
--             token_resp = requests.post(cfg["TOKEN_URL"], data=token_payload, timeout=cfg["TIMEOUT_SEC"])
--             token_resp.raise_for_status()
--             # Extract token - Postman returns 'access_token'
--             token = token_resp.json().get("access_token")
--             headers["Authorization"] = f"Bearer {token}"
            
--         elif auth_type == "OAUTH2_INTEGRATION":
--             # Enterprise Vision: Secure Snowflake Secret retrieval
--             token = _snowflake.get_oauth_access_token(cfg["SECRET_NAME"])
--             headers["Authorization"] = f"Bearer {token}"
            
--     except Exception as e:
--         return f"Authentication Failed for {api_target}: {str(e)}"

--     # 3. THE EXECUTION ENGINE (Pagination + 6-Tier Retry)
--     page = cfg["START_INDEX"] or 1
--     pages_processed = 0
    
--     while True:
--         url = cfg["ENDPOINT_URL"]
--         # Simple Pagination logic
--         if cfg["PAGINATION_TYPE"] == "PAGE":
--             connector = "&" if "?" in url else "?"
--             url = f"{url}{connector}{cfg['PAGE_PARAM']}={page}"

--         # Resilience: Retry Loop
--         response = None
--         for attempt in range(cfg["MAX_RETRIES"]):
--             try:
--                 response = requests.get(url, headers=headers, timeout=cfg["TIMEOUT_SEC"])
--                 if response.status_code == 200: 
--                     break
--             except Exception:
--                 pass
--             time.sleep(cfg["RETRY_DELAY_SEC"])

--         if not response or response.status_code != 200:
--             break
        
--         # 4. DATA LANDING & DEDUPLICATION (Hashing)
--         payload = response.json()
--         payload_json = json.dumps(payload, sort_keys=True)
--         payload_hash = hashlib.sha256(payload_json.encode()).hexdigest()
        
--         # Check for existing hash to prevent duplicates
--         exists = session.sql(f"SELECT 1 FROM API_DATA_PIPELINE.RAW_LANDING.API_RAW_DATA WHERE PAYLOAD_HASH = '{payload_hash}'").collect()
        
--         if not exists:
--             # Insert into Landing Table (Assumes API_RAW_DATA is in same schema)
--             insert_sql = f"""
--                 INSERT INTO API_DATA_PIPELINE.RAW_LANDING.API_RAW_DATA (API_NAME, STATUS_CODE, PAYLOAD, PAYLOAD_HASH)
--                 SELECT '{api_target}', {response.status_code}, PARSE_JSON('{payload_json.replace("'", "''")}'), '{payload_hash}'
--             """
--             session.sql(insert_sql).collect()

--         pages_processed += 1
        
--         # Exit if no pagination or if data list is empty
--         if cfg["PAGINATION_TYPE"] == "NONE":
--             break
        
--         # Exit if API returns an empty list in 'data' key
--         if isinstance(payload, dict) and "data" in payload and len(payload["data"]) == 0:
--             break
            
--         page += 1

--     return f"Success: {api_target} processed. {pages_processed} page(s) ingested."
-- $$;



CREATE OR REPLACE PROCEDURE API_DATA_PIPELINE.METADATA.USP_UNIVERSAL_INGESTOR("API_TARGET" VARCHAR)
RETURNS VARCHAR
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES = ('snowflake-snowpark-python','requests')
HANDLER = 'main'
EXTERNAL_ACCESS_INTEGRATIONS = (EAI_UNIVERSAL_INGESTOR)
SECRETS = ('sk_twitch_int_test'=API_DATA_PIPELINE.METADATA.SK_TWITCH_INT_TEST)
EXECUTE AS OWNER
AS '
import _snowflake
import requests
import json
import hashlib
import time

def log_response(session, api_name, url, status_code, elapsed_sec, error_msg, retries):
    session.sql(
        "INSERT INTO API_DATA_PIPELINE.METADATA.INGESTION_RESPONSE_LOG "
        "(API_NAME, API_URL, STATUS_CODE, RESPONSE_TIME_SECONDS, ERROR_MESSAGE_TEXT, RETRY_COUNT) "
        "SELECT ?, ?, TRY_CAST(? AS NUMBER), TRY_CAST(? AS FLOAT), ?, TRY_CAST(? AS NUMBER)",
        params=[
            api_name or '''',
            url or '''',
            str(status_code) if status_code is not None else None,
            str(elapsed_sec) if elapsed_sec is not None else None,
            str(error_msg) if error_msg is not None else None,
            str(retries) if retries is not None else None
        ]
    ).collect()

def authenticate(auth_type, headers, cfg):
    secret_alias = (cfg["SECRET_NAME"] or "").lower().strip()
    if not secret_alias and auth_type != "NONE":
        raise ValueError(f"SECRET_NAME not configured for auth_type={auth_type}")

    if auth_type == "NONE":
        return

    elif auth_type == "API_KEY":
        api_key = _snowflake.get_generic_secret_string(secret_alias)
        header_name = cfg["API_KEY_HEADER"] or "X-Api-Key"
        headers[header_name] = api_key

    elif auth_type == "OAUTH2_BASIC":
        creds = _snowflake.get_username_password(secret_alias)
        token_payload = {
            "grant_type": "client_credentials",
            "client_id": creds.username,
            "client_secret": creds.password
        }
        token_resp = requests.post(
            cfg["TOKEN_URL"],
            data=token_payload,
            timeout=cfg["TIMEOUT_SEC"]
        )
        token_resp.raise_for_status()
        token = token_resp.json().get("access_token")
        if not token:
            raise ValueError("No access_token in token response")
        headers["Authorization"] = f"Bearer {token}"

    elif auth_type == "OAUTH2_INTEGRATION":
        token = _snowflake.get_oauth_access_token(secret_alias)
        headers["Authorization"] = f"Bearer {token}"

    else:
        raise ValueError(f"Unknown auth_type: {auth_type}")

def main(session, api_target):
    cfg_res = session.sql(
        "SELECT * FROM API_DATA_PIPELINE.METADATA.INGESTION_CONFIGS "
        "WHERE API_NAME = ? AND ACTIVE_FLAG = TRUE",
        params=[api_target]
    ).collect()

    if not cfg_res:
        return f"Error: Configuration for ''{api_target}'' not found or inactive."

    cfg = cfg_res[0]
    headers = {"Accept": "application/json"}
    auth_type = cfg["AUTH_TYPE"]
    http_method = cfg["HTTP_METHOD"] or "GET"
    max_retries = cfg["MAX_RETRIES"] or 6
    retry_delay = cfg["RETRY_DELAY_SEC"] or 15
    timeout = cfg["TIMEOUT_SEC"] or 30

    try:
        authenticate(auth_type, headers, cfg)
    except Exception as e:
        log_response(session, api_target, None, None, None, f"Auth failed: {str(e)}", 0)
        return f"Authentication failed for ''{api_target}'': {str(e)}"

    try:
        extra_headers = cfg["EXTRA_HEADERS_JSON"]
        if extra_headers:
            headers.update(json.loads(extra_headers))
    except (KeyError, IndexError):
        pass
    except Exception as e:
        return f"Error parsing EXTRA_HEADERS_JSON: {str(e)}"

    page = cfg["START_INDEX"] or 1
    pages_processed = 0

    while True:
        url = cfg["ENDPOINT_URL"]
        pagination_type = cfg["PAGINATION_TYPE"] or "NONE"
        connector = "&" if "?" in url else "?"

        if pagination_type == "PAGE":
            url = f"{url}{connector}{cfg[''PAGE_PARAM'']}={page}"
        elif pagination_type == "OFFSET":
            offset_val = (page - 1) * 100
            url = f"{url}{connector}{cfg[''PAGE_PARAM'']}={offset_val}"

        response = None
        last_error = None
        retries_used = 0
        start_time = time.time()

        for attempt in range(max_retries):
            retries_used = attempt
            try:
                response = requests.request(
                    method=http_method,
                    url=url,
                    headers=headers,
                    timeout=timeout
                )
                if response.status_code == 200:
                    break
                last_error = f"HTTP {response.status_code}"
            except Exception as ex:
                last_error = str(ex)
                response = None
            if attempt < max_retries - 1:
                time.sleep(retry_delay)

        elapsed = round(time.time() - start_time, 3)
        status = response.status_code if response else None

        log_response(session, api_target, url, status, elapsed, last_error if status != 200 else None, retries_used)

        if not response or response.status_code != 200:
            return (
                f"Error: ''{api_target}'' failed on page {page}. "
                f"URL: {url} | Status: {status} | Last error: {last_error} | "
                f"Pages ingested before failure: {pages_processed}"
            )

        payload = response.json()
        payload_json = json.dumps(payload, sort_keys=True)
        payload_hash = hashlib.sha256(payload_json.encode()).hexdigest()

        exists = session.sql(
            "SELECT 1 FROM API_DATA_PIPELINE.RAW_LANDING.API_RAW_DATA WHERE PAYLOAD_HASH = ?",
            params=[payload_hash]
        ).collect()

        if not exists:
            session.sql(
                "INSERT INTO API_DATA_PIPELINE.RAW_LANDING.API_RAW_DATA "
                "(API_NAME, STATUS_CODE, PAYLOAD, PAYLOAD_HASH, URL_ATTEMPTED) "
                "SELECT ?, ?, PARSE_JSON(?), ?, ?",
                params=[api_target, response.status_code, payload_json, payload_hash, url]
            ).collect()

        pages_processed += 1

        if pagination_type == "NONE":
            break

        if isinstance(payload, dict) and "data" in payload and len(payload["data"]) == 0:
            break

        page += 1

    return f"Success: ''{api_target}'' processed. {pages_processed} page(s) ingested."

';


select * from ingestion_configs;


-- ============================================================================
-- STEP 1: Ensure SECRET_NAME is populated for every API that requires auth.
--         Each API's SECRET_NAME must match the Snowflake SECRET object name.
-- ============================================================================
UPDATE API_DATA_PIPELINE.METADATA.INGESTION_CONFIGS
SET SECRET_NAME = 'APIKEY_SECRET'
WHERE AUTH_TYPE = 'API_KEY' AND (SECRET_NAME IS NULL OR SECRET_NAME = '');

UPDATE API_DATA_PIPELINE.METADATA.INGESTION_CONFIGS
SET SECRET_NAME = 'CLIENT_CREDENTIALS_SECRET'
WHERE AUTH_TYPE = 'OAUTH2_BASIC' AND (SECRET_NAME IS NULL OR SECRET_NAME = '');

UPDATE API_DATA_PIPELINE.METADATA.INGESTION_CONFIGS
SET SECRET_NAME = 'SK_TWITCH_OAUTH'
WHERE API_NAME = 'TWITCH_INTEGRATION_TEST' AND AUTH_TYPE = 'OAUTH2_INTEGRATION' AND (SECRET_NAME IS NULL OR SECRET_NAME = '');


-- ============================================================================
-- STEP 2: Helper procedure — USP_REBUILD_INGESTOR
--         Reads all active secrets from INGESTION_CONFIGS, then dynamically
--         recreates USP_UNIVERSAL_INGESTOR with the correct SECRETS clause.
-- ============================================================================
CREATE OR REPLACE PROCEDURE API_DATA_PIPELINE.METADATA.USP_REBUILD_INGESTOR()
RETURNS VARCHAR
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'main'
EXECUTE AS CALLER
AS '
def main(session):
    rows = session.sql("""
        SELECT DISTINCT SECRET_NAME
        FROM API_DATA_PIPELINE.METADATA.INGESTION_CONFIGS
        WHERE ACTIVE_FLAG = TRUE
          AND AUTH_TYPE != ''NONE''
          AND SECRET_NAME IS NOT NULL
          AND SECRET_NAME != ''''
        ORDER BY SECRET_NAME
    """).collect()

    if not rows:
        return "Error: No active APIs with SECRET_NAME found in INGESTION_CONFIGS. Nothing to rebuild."

    secret_entries = []
    for r in rows:
        sname = r["SECRET_NAME"]
        alias = sname.lower()
        fqn = "API_DATA_PIPELINE.METADATA." + sname
        secret_entries.append("    ''" + alias + "'' = " + fqn)

    secrets_clause = ",\\n".join(secret_entries)

    dollar = chr(36) * 2

    handler_code = (
        "import _snowflake\\n"
        "import requests\\n"
        "import json\\n"
        "import hashlib\\n"
        "import time\\n"
        "\\n"
        "def log_response(session, api_name, url, status_code, elapsed_sec, error_msg, retries):\\n"
        "    session.sql(\\n"
        ''        "INSERT INTO API_DATA_PIPELINE.METADATA.INGESTION_RESPONSE_LOG "\\n''
        ''        "(API_NAME, API_URL, STATUS_CODE, RESPONSE_TIME_SECONDS, ERROR_MESSAGE_TEXT, RETRY_COUNT) "\\n''
        ''        "SELECT ?, ?, TRY_CAST(? AS NUMBER), TRY_CAST(? AS FLOAT), ?, TRY_CAST(? AS NUMBER)",\\n''
        "        params=[\\n"
        "            api_name or '''',\\n"
        "            url or '''',\\n"
        "            str(status_code) if status_code is not None else None,\\n"
        "            str(elapsed_sec) if elapsed_sec is not None else None,\\n"
        "            str(error_msg) if error_msg is not None else None,\\n"
        "            str(retries) if retries is not None else None\\n"
        "        ]\\n"
        "    ).collect()\\n"
        "\\n"
        "def authenticate(auth_type, headers, cfg):\\n"
        ''    secret_alias = (cfg["SECRET_NAME"] or "").lower().strip()\\n''
        ''    if not secret_alias and auth_type != "NONE":\\n''
        ''        raise ValueError(f"SECRET_NAME not configured for auth_type={auth_type}")\\n''
        "\\n"
        ''    if auth_type == "NONE":\\n''
        "        return\\n"
        "\\n"
        ''    elif auth_type == "API_KEY":\\n''
        "        api_key = _snowflake.get_generic_secret_string(secret_alias)\\n"
        ''        header_name = cfg["API_KEY_HEADER"] or "X-Api-Key"\\n''
        "        headers[header_name] = api_key\\n"
        "\\n"
        ''    elif auth_type == "OAUTH2_BASIC":\\n''
        "        creds = _snowflake.get_username_password(secret_alias)\\n"
        "        token_payload = {\\n"
        ''            "grant_type": "client_credentials",\\n''
        ''            "client_id": creds.username,\\n''
        ''            "client_secret": creds.password\\n''
        "        }\\n"
        "        token_resp = requests.post(\\n"
        ''            cfg["TOKEN_URL"],\\n''
        "            data=token_payload,\\n"
        ''            timeout=cfg["TIMEOUT_SEC"]\\n''
        "        )\\n"
        "        token_resp.raise_for_status()\\n"
        ''        token = token_resp.json().get("access_token")\\n''
        "        if not token:\\n"
        ''            raise ValueError("No access_token in token response")\\n''
        ''        headers["Authorization"] = f"Bearer {token}"\\n''
        "\\n"
        ''    elif auth_type == "OAUTH2_INTEGRATION":\\n''
        "        token = _snowflake.get_oauth_access_token(secret_alias)\\n"
        ''        headers["Authorization"] = f"Bearer {token}"\\n''
        "\\n"
        "    else:\\n"
        ''        raise ValueError(f"Unknown auth_type: {auth_type}")\\n''
        "\\n"
        "def main(session, api_target):\\n"
        "    cfg_res = session.sql(\\n"
        ''        "SELECT * FROM API_DATA_PIPELINE.METADATA.INGESTION_CONFIGS "\\n''
        ''        "WHERE API_NAME = ? AND ACTIVE_FLAG = TRUE",\\n''
        "        params=[api_target]\\n"
        "    ).collect()\\n"
        "\\n"
        "    if not cfg_res:\\n"
        "        return f\\"Error: Configuration for ''{api_target}'' not found or inactive.\\"\\n"
        "\\n"
        "    cfg = cfg_res[0]\\n"
        ''    headers = {"Accept": "application/json"}\\n''
        ''    auth_type = cfg["AUTH_TYPE"]\\n''
        ''    http_method = cfg["HTTP_METHOD"] or "GET"\\n''
        ''    max_retries = cfg["MAX_RETRIES"] or 6\\n''
        ''    retry_delay = cfg["RETRY_DELAY_SEC"] or 15\\n''
        ''    timeout = cfg["TIMEOUT_SEC"] or 30\\n''
        "\\n"
        "    try:\\n"
        "        authenticate(auth_type, headers, cfg)\\n"
        "    except Exception as e:\\n"
        ''        log_response(session, api_target, None, None, None, f"Auth failed: {str(e)}", 0)\\n''
        "        return f\\"Authentication failed for ''{api_target}'': {str(e)}\\"\\n"
        "\\n"
        "    try:\\n"
        ''        extra_headers = cfg["EXTRA_HEADERS_JSON"]\\n''
        "        if extra_headers:\\n"
        "            headers.update(json.loads(extra_headers))\\n"
        "    except (KeyError, IndexError):\\n"
        "        pass\\n"
        "    except Exception as e:\\n"
        "        return f\\"Error parsing EXTRA_HEADERS_JSON: {str(e)}\\"\\n"
        "\\n"
        ''    page = cfg["START_INDEX"] or 1\\n''
        "    pages_processed = 0\\n"
        "\\n"
        "    while True:\\n"
        ''        url = cfg["ENDPOINT_URL"]\\n''
        ''        pagination_type = cfg["PAGINATION_TYPE"] or "NONE"\\n''
        ''        connector = "&" if "?" in url else "?"\\n''
        "\\n"
        ''        if pagination_type == "PAGE":\\n''
        "            url = f\\"{url}{connector}{cfg[''PAGE_PARAM'']}={page}\\"\\n"
        ''        elif pagination_type == "OFFSET":\\n''
        "            offset_val = (page - 1) * 100\\n"
        "            url = f\\"{url}{connector}{cfg[''PAGE_PARAM'']}={offset_val}\\"\\n"
        "\\n"
        "        response = None\\n"
        "        last_error = None\\n"
        "        retries_used = 0\\n"
        "        start_time = time.time()\\n"
        "\\n"
        "        for attempt in range(max_retries):\\n"
        "            retries_used = attempt\\n"
        "            try:\\n"
        "                response = requests.request(\\n"
        "                    method=http_method,\\n"
        "                    url=url,\\n"
        "                    headers=headers,\\n"
        "                    timeout=timeout\\n"
        "                )\\n"
        "                if response.status_code == 200:\\n"
        "                    break\\n"
        ''                last_error = f"HTTP {response.status_code}"\\n''
        "            except Exception as ex:\\n"
        "                last_error = str(ex)\\n"
        "                response = None\\n"
        "            if attempt < max_retries - 1:\\n"
        "                time.sleep(retry_delay)\\n"
        "\\n"
        "        elapsed = round(time.time() - start_time, 3)\\n"
        "        status = response.status_code if response else None\\n"
        "\\n"
        "        log_response(session, api_target, url, status, elapsed, last_error if status != 200 else None, retries_used)\\n"
        "\\n"
        "        if not response or response.status_code != 200:\\n"
        "            return (\\n"
        "                f\\"Error: ''{api_target}'' failed on page {page}. \\"\\n"
        ''                f"URL: {url} | Status: {status} | Last error: {last_error} | "\\n''
        ''                f"Pages ingested before failure: {pages_processed}"\\n''
        "            )\\n"
        "\\n"
        "        payload = response.json()\\n"
        "        payload_json = json.dumps(payload, sort_keys=True)\\n"
        "        payload_hash = hashlib.sha256(payload_json.encode()).hexdigest()\\n"
        "\\n"
        "        exists = session.sql(\\n"
        ''            "SELECT 1 FROM API_DATA_PIPELINE.RAW_LANDING.API_RAW_DATA WHERE PAYLOAD_HASH = ?",\\n''
        "            params=[payload_hash]\\n"
        "        ).collect()\\n"
        "\\n"
        "        if not exists:\\n"
        "            session.sql(\\n"
        ''                "INSERT INTO API_DATA_PIPELINE.RAW_LANDING.API_RAW_DATA "\\n''
        ''                "(API_NAME, STATUS_CODE, PAYLOAD, PAYLOAD_HASH, URL_ATTEMPTED) "\\n''
        ''                "SELECT ?, ?, PARSE_JSON(?), ?, ?",\\n''
        "                params=[api_target, response.status_code, payload_json, payload_hash, url]\\n"
        "            ).collect()\\n"
        "\\n"
        "        pages_processed += 1\\n"
        "\\n"
        ''        if pagination_type == "NONE":\\n''
        "            break\\n"
        "\\n"
        ''        if isinstance(payload, dict) and "data" in payload and len(payload["data"]) == 0:\\n''
        "            break\\n"
        "\\n"
        "        page += 1\\n"
        "\\n"
        "    return f\\"Success: ''{api_target}'' processed. {pages_processed} page(s) ingested.\\"\\n"
    )

    ddl = (
        "CREATE OR REPLACE PROCEDURE API_DATA_PIPELINE.METADATA.USP_UNIVERSAL_INGESTOR(API_TARGET STRING)\\n"
        "RETURNS STRING\\n"
        "LANGUAGE PYTHON\\n"
        "RUNTIME_VERSION = ''3.10''\\n"
        "PACKAGES = (''snowflake-snowpark-python'',''requests'')\\n"
        "HANDLER = ''main''\\n"
        "EXTERNAL_ACCESS_INTEGRATIONS = (EAI_UNIVERSAL_INGESTOR)\\n"
        "SECRETS = (\\n"
        + secrets_clause + "\\n"
        + ")\\n"
        + "AS\\n"
        + dollar + "\\n"
        + handler_code + "\\n"
        + dollar
    )

    try:
        session.sql(ddl).collect()
    except Exception as e:
        return "Error rebuilding procedure: " + str(e)

    secret_names = [r["SECRET_NAME"] for r in rows]
    return "Success: USP_UNIVERSAL_INGESTOR rebuilt with " + str(len(secret_names)) + " secret(s): " + ", ".join(secret_names)
';
-- ============================================================================
-- USAGE:
--   1. Add a new API to INGESTION_CONFIGS with its SECRET_NAME populated
--   2. Create the SECRET and add it to EAI_UNIVERSAL_INGESTOR allowed list
--   3. CALL API_DATA_PIPELINE.METADATA.USP_REBUILD_INGESTOR();
--      -> This recreates USP_UNIVERSAL_INGESTOR with all active secrets
--   4. CALL API_DATA_PIPELINE.METADATA.USP_UNIVERSAL_INGESTOR('MY_NEW_API');
-- ============================================================================

--==============================================================================
-- New workflow for adding an API:
-- -- 1. Create the secret
-- CREATE SECRET API_DATA_PIPELINE.METADATA.MY_NEW_SECRET TYPE = GENERIC_STRING SECRET_STRING = '...';

-- -- 2. Add it to the EAI allowed list
-- ALTER EXTERNAL ACCESS INTEGRATION EAI_UNIVERSAL_INGESTOR
--   SET ALLOWED_AUTHENTICATION_SECRETS = (...existing..., API_DATA_PIPELINE.METADATA.MY_NEW_SECRET);

-- -- 3. Insert config row with SECRET_NAME populated
-- INSERT INTO API_DATA_PIPELINE.METADATA.INGESTION_CONFIGS (API_NAME, AUTH_TYPE, SECRET_NAME, ...)
-- VALUES ('MY_NEW_API', 'API_KEY', 'MY_NEW_SECRET', ...);

-- -- 4. Rebuild the ingestor (picks up the new secret automatically)
-- CALL API_DATA_PIPELINE.METADATA.USP_REBUILD_INGESTOR();

-- -- 5. Run it
-- CALL API_DATA_PIPELINE.METADATA.USP_UNIVERSAL_INGESTOR('MY_NEW_API');
--==============================================================================


-- ===================== SECURITY INTEGRATIONS =====================

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

-- ===================== SECRETS =====================

CREATE OR REPLACE SECRET API_DATA_PIPELINE.METADATA.SK_TWITCH_INT_TEST
  TYPE = OAUTH2
  API_AUTHENTICATION = SEC_INT_TWITCH_TEST;

CREATE OR REPLACE SECRET API_DATA_PIPELINE.METADATA.SK_TWITCH_OAUTH
  TYPE = OAUTH2
  API_AUTHENTICATION = TWITCH_OAUTH_INTEGRATION;

-- ===================== NETWORK RULES =====================

CREATE OR REPLACE NETWORK RULE API_DATA_PIPELINE.METADATA.NR_TWITCH_API
  MODE = EGRESS
  TYPE = HOST_PORT
  VALUE_LIST = ('id.twitch.tv', 'api.twitch.tv');

CREATE OR REPLACE NETWORK RULE API_DATA_PIPELINE.METADATA.NR_TWITCH_TEST
  MODE = EGRESS
  TYPE = HOST_PORT
  VALUE_LIST = ('id.twitch.tv', 'api.twitch.tv');

-- ===================== EXTERNAL ACCESS INTEGRATION =====================

CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION EAI_UNIVERSAL_INGESTOR
  ALLOWED_NETWORK_RULES = (
      API_DATA_PIPELINE.METADATA.NR_TWITCH_API,
      API_DATA_PIPELINE.METADATA.NR_TWITCH_TEST
  )
  ALLOWED_AUTHENTICATION_SECRETS = (
      API_DATA_PIPELINE.METADATA.SK_TWITCH_INT_TEST,
      API_DATA_PIPELINE.METADATA.SK_TWITCH_OAUTH
  )
  ENABLED = TRUE;

-- ===================== CONFIG DATA =====================

INSERT INTO API_DATA_PIPELINE.METADATA.INGESTION_CONFIGS
  (API_NAME, ENDPOINT_URL, HTTP_METHOD, AUTH_TYPE, SECRET_NAME, INTEGRATION_NAME,
   PAGINATION_TYPE, START_INDEX, MAX_RETRIES, RETRY_DELAY_SEC, TIMEOUT_SEC, EXTRA_HEADERS_JSON)
VALUES
  ('TWITCH_INT_TEST',
   'https://api.twitch.tv/helix/games/top',
   'GET',
   'OAUTH2_INTEGRATION',
   'SK_TWITCH_INT_TEST',
   'SEC_INT_TWITCH_TEST',
   'NONE',
   1, 3, 10, 30,
   '{"Client-Id": "utos47l0dh1foqld40510f4ttsgouj"}');



   select * from raw_landing.api_raw_data;

   show secrets in schema metadata;