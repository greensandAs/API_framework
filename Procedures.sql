--==============================================================================================

-- Framework

--================================================================================================
CREATE OR REPLACE PROCEDURE API_DATA_PIPELINE.METADATA.USP_UNIVERSAL_INGESTOR("API_TARGET" VARCHAR)
RETURNS VARCHAR
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES = ('snowflake-snowpark-python','requests')
HANDLER = 'main'
EXTERNAL_ACCESS_INTEGRATIONS = (EAI_UNIVERSAL_INGESTOR)
SECRETS = ()
EXECUTE AS CALLER
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

    landing_table = (cfg["LANDING_TABLE"] or "").strip()
    if landing_table and landing_table.lower() not in ("none", "null"):
        import re
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_.]*$", landing_table):
            return f"Error: Invalid LANDING_TABLE name ''{landing_table}''"
        if "." not in landing_table:
            target_table = f"API_DATA_PIPELINE.RAW_LANDING.{landing_table}"
        else:
            target_table = landing_table
        session.sql(
            f"CREATE TABLE IF NOT EXISTS {target_table} ("
            "INGEST_TS TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(), "
            "API_NAME VARCHAR, STATUS_CODE NUMBER, PAYLOAD VARIANT, "
            "PAYLOAD_HASH VARCHAR, URL_ATTEMPTED VARCHAR)"
        ).collect()
    else:
        target_table = "API_DATA_PIPELINE.RAW_LANDING.API_RAW_DATA"

    try:
        authenticate(auth_type, headers, cfg)
    except Exception as e:
        log_response(session, api_target, None, None, None, f"Auth failed: {str(e)}", 0)
        return f"Authentication failed for ''{api_target}'': {str(e)}"

    try:
        extra_headers = (cfg["EXTRA_HEADERS_JSON"] or "").strip()
        if extra_headers and extra_headers.lower() not in ("none", "null", "undefined"):
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

        data_to_split = []
        if isinstance(payload, dict) and "data" in payload and isinstance(payload["data"], list):
            data_to_split = payload["data"]
        elif isinstance(payload, list):
            data_to_split = payload
        else:
            data_to_split = [payload]

        CHUNK_SIZE = 2500
        total_chunks = max(1, (len(data_to_split) + CHUNK_SIZE - 1) // CHUNK_SIZE)

        for i in range(0, len(data_to_split), CHUNK_SIZE):
            chunk_index = (i // CHUNK_SIZE) + 1
            chunk_data = data_to_split[i : i + CHUNK_SIZE]

            chunk_payload = {
                "data": chunk_data,
                "_chunk_meta": {"page": page, "chunk": chunk_index, "total_chunks": total_chunks}
            }

            chunk_json = json.dumps(chunk_payload, sort_keys=True)
            chunk_hash = hashlib.sha256(chunk_json.encode()).hexdigest()

            exists = session.sql(
                f"SELECT 1 FROM {target_table} WHERE PAYLOAD_HASH = ?",
                params=[chunk_hash]
            ).collect()

            if not exists:
                annotated_url = f"{url} [Chunk {chunk_index}/{total_chunks}]"
                session.sql(
                    f"INSERT INTO {target_table} "
                    "(API_NAME, STATUS_CODE, PAYLOAD, PAYLOAD_HASH, URL_ATTEMPTED) "
                    "SELECT ?, ?, PARSE_JSON(?), ?, ?",
                    params=[api_target, response.status_code, chunk_json, chunk_hash, annotated_url]
                ).collect()

        pages_processed += 1

        if pagination_type == "NONE":
            break

        if not data_to_split:
            break

        page += 1

    return f"Success: ''{api_target}'' processed. {pages_processed} page(s) ingested."

';



--==============================================================================================

-- Wrapper

--================================================================================================


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
        ''    landing_table = (cfg["LANDING_TABLE"] or "").strip()\\n''
        ''    if landing_table and landing_table.lower() not in ("none", "null"):\\n''
        "        import re\\n"
        ''        if not re.match(r"^[A-Za-z_][A-Za-z0-9_.]*$", landing_table):\\n''
        "            return f\\"Error: Invalid LANDING_TABLE name ''{landing_table}''\\"\\n"
        ''        if "." not in landing_table:\\n''
        ''            target_table = f"API_DATA_PIPELINE.RAW_LANDING.{landing_table}"\\n''
        "        else:\\n"
        "            target_table = landing_table\\n"
        "        session.sql(\\n"
        ''            f"CREATE TABLE IF NOT EXISTS {target_table} ("\\n''
        ''            "INGEST_TS TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(), "\\n''
        ''            "API_NAME VARCHAR, STATUS_CODE NUMBER, PAYLOAD VARIANT, "\\n''
        ''            "PAYLOAD_HASH VARCHAR, URL_ATTEMPTED VARCHAR)"\\n''
        "        ).collect()\\n"
        "    else:\\n"
        ''        target_table = "API_DATA_PIPELINE.RAW_LANDING.API_RAW_DATA"\\n''
        "\\n"
        "    try:\\n"
        "        authenticate(auth_type, headers, cfg)\\n"
        "    except Exception as e:\\n"
        ''        log_response(session, api_target, None, None, None, f"Auth failed: {str(e)}", 0)\\n''
        "        return f\\"Authentication failed for ''{api_target}'': {str(e)}\\"\\n"
        "\\n"
        "    try:\\n"
        ''        extra_headers = (cfg["EXTRA_HEADERS_JSON"] or "").strip()\\n''
        ''        if extra_headers and extra_headers.lower() not in ("none", "null", "undefined"):\\n''
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
        "\\n"
        "        data_to_split = []\\n"
        ''        if isinstance(payload, dict) and "data" in payload and isinstance(payload["data"], list):\\n''
        ''            data_to_split = payload["data"]\\n''
        "        elif isinstance(payload, list):\\n"
        "            data_to_split = payload\\n"
        "        else:\\n"
        "            data_to_split = [payload]\\n"
        "\\n"
        "        CHUNK_SIZE = 2500\\n"
        "        total_chunks = max(1, (len(data_to_split) + CHUNK_SIZE - 1) // CHUNK_SIZE)\\n"
        "\\n"
        "        for i in range(0, len(data_to_split), CHUNK_SIZE):\\n"
        "            chunk_index = (i // CHUNK_SIZE) + 1\\n"
        "            chunk_data = data_to_split[i : i + CHUNK_SIZE]\\n"
        "\\n"
        "            chunk_payload = {\\n"
        ''                "data": chunk_data,\\n''
        ''                "_chunk_meta": {"page": page, "chunk": chunk_index, "total_chunks": total_chunks}\\n''
        "            }\\n"
        "\\n"
        "            chunk_json = json.dumps(chunk_payload, sort_keys=True)\\n"
        "            chunk_hash = hashlib.sha256(chunk_json.encode()).hexdigest()\\n"
        "\\n"
        "            exists = session.sql(\\n"
        ''                f"SELECT 1 FROM {target_table} WHERE PAYLOAD_HASH = ?",\\n''
        "                params=[chunk_hash]\\n"
        "            ).collect()\\n"
        "\\n"
        "            if not exists:\\n"
        ''                annotated_url = f"{url} [Chunk {chunk_index}/{total_chunks}]"\\n''
        "                session.sql(\\n"
        ''                    f"INSERT INTO {target_table} "\\n''
        ''                    "(API_NAME, STATUS_CODE, PAYLOAD, PAYLOAD_HASH, URL_ATTEMPTED) "\\n''
        ''                    "SELECT ?, ?, PARSE_JSON(?), ?, ?",\\n''
        "                    params=[api_target, response.status_code, chunk_json, chunk_hash, annotated_url]\\n"
        "                ).collect()\\n"
        "\\n"
        "        pages_processed += 1\\n"
        "\\n"
        ''        if pagination_type == "NONE":\\n''
        "            break\\n"
        "\\n"
        "        if not data_to_split:\\n"
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