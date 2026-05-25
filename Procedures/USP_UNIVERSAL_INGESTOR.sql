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
        "import urllib.parse as _urlparse\\n"
        "\\n"
        "def extract_field(obj, path):\\n"
        "    if obj is None or not path:\\n"
        "        return None\\n"
        "    cur = obj\\n"
        ''    for part in str(path).split("."):\\n''
        "        if isinstance(cur, dict) and part in cur:\\n"
        "            cur = cur[part]\\n"
        "        else:\\n"
        "            return None\\n"
        "    return cur\\n"
        "\\n"
        "def compare_watermarks(a, b):\\n"
        "    if a is None:\\n"
        "        return b\\n"
        "    if b is None:\\n"
        "        return a\\n"
        "    try:\\n"
        "        af = float(a)\\n"
        "        bf = float(b)\\n"
        "        return a if af >= bf else b\\n"
        "    except (TypeError, ValueError):\\n"
        "        return a if str(a) >= str(b) else b\\n"
        "\\n"
        "def log_response(session, api_name, url, status_code, elapsed_sec, error_msg, retries, attempt_number=None, is_final_attempt=None, page_number=None, api_id=None):\\n"
        "    session.sql(\\n"
        ''        "INSERT INTO API_DATA_PIPELINE.METADATA.INGESTION_RESPONSE_LOG "\\n''
        ''        "(API_ID, API_NAME, API_URL, STATUS_CODE, RESPONSE_TIME_SECONDS, ERROR_MESSAGE_TEXT, RETRY_COUNT, "\\n''
        ''        "ATTEMPT_NUMBER, IS_FINAL_ATTEMPT, PAGE_NUMBER) "\\n''
        ''        "SELECT TRY_CAST(? AS NUMBER), ?, ?, TRY_CAST(? AS NUMBER), TRY_CAST(? AS FLOAT), ?, TRY_CAST(? AS NUMBER), "\\n''
        ''        "TRY_CAST(? AS NUMBER), TRY_CAST(? AS BOOLEAN), TRY_CAST(? AS NUMBER)",\\n''
        "        params=[\\n"
        "            str(api_id) if api_id is not None else None,\\n"
        "            api_name or '''',\\n"
        "            url or '''',\\n"
        "            str(status_code) if status_code is not None else None,\\n"
        "            str(elapsed_sec) if elapsed_sec is not None else None,\\n"
        "            str(error_msg) if error_msg is not None else None,\\n"
        "            str(retries) if retries is not None else None,\\n"
        "            str(attempt_number) if attempt_number is not None else None,\\n"
        "            str(is_final_attempt).lower() if is_final_attempt is not None else None,\\n"
        "            str(page_number) if page_number is not None else None\\n"
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
        "    try:\\n"
        ''        _cfg_dict_top = cfg.asDict() if hasattr(cfg, "asDict") else dict(cfg)\\n''
        "    except Exception:\\n"
        "        _cfg_dict_top = {}\\n"
        ''    api_id = _cfg_dict_top.get("API_ID")\\n''
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
        ''            "API_ID NUMBER, "\\n''
        ''            "API_NAME VARCHAR, STATUS_CODE NUMBER, PAYLOAD VARIANT, "\\n''
        ''            "PAYLOAD_HASH VARCHAR, URL_ATTEMPTED VARCHAR)"\\n''
        "        ).collect()\\n"
        "        try:\\n"
        ''            session.sql(f"ALTER TABLE {target_table} ADD COLUMN IF NOT EXISTS API_ID NUMBER").collect()\\n''
        "        except Exception:\\n"
        "            pass\\n"
        "    else:\\n"
        ''        target_table = "API_DATA_PIPELINE.RAW_LANDING.API_RAW_DATA"\\n''
        "\\n"
        "    try:\\n"
        "        authenticate(auth_type, headers, cfg)\\n"
        "    except Exception as e:\\n"
        ''        log_response(session, api_target, None, None, None, f"Auth failed: {str(e)}", 0, api_id=api_id)\\n''
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
        ''    try:\\n''
        ''        _cfg_dict = cfg.asDict() if hasattr(cfg, "asDict") else dict(cfg)\\n''
        ''    except Exception:\\n''
        ''        _cfg_dict = {}\\n''
        ''    incremental_flag = bool(_cfg_dict.get("INCREMENTAL_FLAG")) if "INCREMENTAL_FLAG" in _cfg_dict else False\\n''
        ''    watermark_param = (_cfg_dict.get("WATERMARK_PARAM") or "").strip() if incremental_flag else ""\\n''
        ''    watermark_field = (_cfg_dict.get("WATERMARK_FIELD") or "").strip() if incremental_flag else ""\\n''
        ''    last_sync_value = (_cfg_dict.get("LAST_SYNC_VALUE") or "").strip() if incremental_flag else ""\\n''
        "    new_watermark = last_sync_value or None\\n"
        "\\n"
        "    while True:\\n"
        ''        url = cfg["ENDPOINT_URL"]\\n''
        ''        pagination_type = cfg["PAGINATION_TYPE"] or "NONE"\\n''
        ''        connector = "&" if "?" in url else "?"\\n''
        "\\n"
        "        if incremental_flag and watermark_param and last_sync_value:\\n"
        "            encoded_wm = _urlparse.quote(str(last_sync_value))\\n"
        ''            url = f"{url}{connector}{watermark_param}={encoded_wm}"\\n''
        ''            connector = "&"\\n''
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
        "            attempt_status = None\\n"
        "            attempt_error = None\\n"
        "            attempt_start = time.time()\\n"
        "            try:\\n"
        "                response = requests.request(\\n"
        "                    method=http_method,\\n"
        "                    url=url,\\n"
        "                    headers=headers,\\n"
        "                    timeout=timeout\\n"
        "                )\\n"
        "                attempt_status = response.status_code\\n"
        "                if response.status_code == 200:\\n"
        "                    pass\\n"
        "                else:\\n"
        ''                    attempt_error = f"HTTP {response.status_code}"\\n''
        "                    last_error = attempt_error\\n"
        "            except Exception as ex:\\n"
        "                attempt_error = str(ex)\\n"
        "                last_error = attempt_error\\n"
        "                response = None\\n"
        "\\n"
        "            attempt_elapsed = round(time.time() - attempt_start, 3)\\n"
        "            is_final = (attempt_status == 200) or (attempt == max_retries - 1)\\n"
        "\\n"
        "            log_response(\\n"
        "                session, api_target, url,\\n"
        "                attempt_status, attempt_elapsed,\\n"
        "                attempt_error,\\n"
        "                attempt + 1,\\n"
        "                attempt_number=attempt + 1,\\n"
        "                is_final_attempt=is_final,\\n"
        "                page_number=page,\\n"
        "                api_id=api_id\\n"
        "            )\\n"
        "\\n"
        "            if attempt_status == 200:\\n"
        "                break\\n"
        "            if attempt < max_retries - 1:\\n"
        "                time.sleep(retry_delay)\\n"
        "\\n"
        "        elapsed = round(time.time() - start_time, 3)\\n"
        "        status = response.status_code if response else None\\n"
        "\\n"
        "        # Per-attempt rows already logged inside the retry loop above.\\n"
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
        "        if incremental_flag and watermark_field:\\n"
        "            for rec in data_to_split:\\n"
        "                wm_val = extract_field(rec, watermark_field)\\n"
        "                if wm_val is not None:\\n"
        "                    new_watermark = compare_watermarks(new_watermark, wm_val)\\n"
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
        ''                    "(API_ID, API_NAME, STATUS_CODE, PAYLOAD, PAYLOAD_HASH, URL_ATTEMPTED) "\\n''
        ''                    "SELECT TRY_CAST(? AS NUMBER), ?, ?, PARSE_JSON(?), ?, ?",\\n''
        "                    params=[str(api_id) if api_id is not None else None, api_target, response.status_code, chunk_json, chunk_hash, annotated_url]\\n"
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
        ''    if incremental_flag and new_watermark is not None and str(new_watermark) != str(last_sync_value or ""):\\n''
        "        try:\\n"
        "            session.sql(\\n"
        ''                "UPDATE API_DATA_PIPELINE.METADATA.INGESTION_CONFIGS "\\n''
        ''                "SET LAST_SYNC_VALUE = ? WHERE API_NAME = ?",\\n''
        "                params=[str(new_watermark), api_target]\\n"
        "            ).collect()\\n"
        "        except Exception as _e:\\n"
        ''            log_response(session, api_target, None, None, None, f"Watermark persist failed: {str(_e)}", 0)\\n''
        "\\n"
        ''    incremental_msg = ""\\n''
        "    if incremental_flag:\\n"
        "        incremental_msg = f\\" | Watermark: {last_sync_value or ''(none)''} -> {new_watermark or ''(unchanged)''}\\"\\n"
        "\\n"
        "    return f\\"Success: ''{api_target}'' processed. {pages_processed} page(s) ingested.{incremental_msg}\\"\\n"
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