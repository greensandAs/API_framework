-- ============================================================================
-- USP_REBUILD_INGESTOR — Dynamically rebuilds USP_UNIVERSAL_INGESTOR with
-- the current SECRETS clause from all secrets in the METADATA schema.
-- Call after adding/removing secrets or when deploying procedure changes.
-- ============================================================================

CREATE OR REPLACE PROCEDURE API_DATA_PIPELINE.METADATA.USP_REBUILD_INGESTOR()
RETURNS VARCHAR
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'main'
EXECUTE AS OWNER
AS
$$
def main(session):
    import textwrap

    META = "API_DATA_PIPELINE.METADATA"

    secrets = []
    try:
        sec_df = session.sql(f"SHOW SECRETS IN SCHEMA {META}").collect()
        for row in sec_df:
            r = row.asDict() if hasattr(row, "asDict") else dict(row)
            name = r.get("name") or r.get("NAME")
            if name:
                alias = name.lower()
                secrets.append(f"'{alias}'={META}.{name}")
    except Exception:
        pass

    secrets_clause = ""
    if secrets:
        secrets_clause = "SECRETS = (" + ", ".join(secrets) + ")"

    proc_body = textwrap.dedent('''
import _snowflake
import requests
import json
import hashlib
import time
import re
import uuid
import urllib.parse as _urlparse

RETRYABLE_CODES   = {429, 500, 502, 503, 504}
FETCH_METHODS     = {"GET", "POST"}
DEFAULT_PAGE_SIZE = 100
MAX_PAGES_DEFAULT = 10000
CHUNK_SIZE        = 2500
PROGRESS_LOG_INTERVAL = 100


def extract_field(obj, path):
    if obj is None or not path:
        return None
    cur = obj
    for part in str(path).split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit():
            idx = int(part)
            cur = cur[idx] if idx < len(cur) else None
        else:
            return None
    return cur


def extract_records(payload, records_path):
    if not records_path or records_path.lower() in ("none", "null", ""):
        return payload if isinstance(payload, list) else [payload]
    cur = payload
    for part in records_path.strip().split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list):
            return cur
        else:
            if isinstance(payload, list):
                return payload
            return [payload]
    if isinstance(cur, list):
        return cur
    if isinstance(cur, dict):
        return [cur]
    if isinstance(payload, list):
        return payload
    return [payload]


def compare_watermarks(a, b):
    if a is None:
        return b
    if b is None:
        return a
    try:
        return a if float(a) >= float(b) else b
    except (TypeError, ValueError):
        pass
    try:
        from datetime import datetime
        def _parse_dt(s):
            s = str(s).strip().replace("Z", "+00:00")
            return datetime.fromisoformat(s)
        return a if _parse_dt(a) >= _parse_dt(b) else b
    except Exception:
        pass
    return a if str(a) >= str(b) else b


def build_filter_url(base_url, filter_params_raw):
    if not filter_params_raw:
        return base_url
    try:
        filters = json.loads(filter_params_raw) if isinstance(filter_params_raw, str) else filter_params_raw
        if not isinstance(filters, dict):
            return base_url
    except Exception:
        return base_url
    connector = "&" if "?" in base_url else "?"
    parts = []
    for key, value in filters.items():
        if isinstance(value, list):
            for v in value:
                parts.append(f"{_urlparse.quote(str(key))}={_urlparse.quote(str(v))}")
        else:
            parts.append(f"{_urlparse.quote(str(key))}={_urlparse.quote(str(value))}")
    if parts:
        base_url += connector + "&".join(parts)
    return base_url


def safe_str(v):
    return str(v) if v is not None else None


def log_attempt(session, run_id, api_name, api_id, url, status_code, elapsed_sec,
                error_msg, retry_count, attempt_number, is_final_attempt, page_number):
    try:
        session.sql(
            "INSERT INTO API_DATA_PIPELINE.METADATA.INGESTION_RESPONSE_LOG "
            "(RUN_ID, API_ID, API_NAME, API_URL, STATUS_CODE, RESPONSE_TIME_SECONDS, "
            " ERROR_MESSAGE_TEXT, RETRY_COUNT, ATTEMPT_NUMBER, IS_FINAL_ATTEMPT, PAGE_NUMBER) "
            "SELECT ?, TRY_CAST(? AS NUMBER), ?, ?, TRY_CAST(? AS NUMBER), "
            "       TRY_CAST(? AS FLOAT), ?, TRY_CAST(? AS NUMBER), "
            "       TRY_CAST(? AS NUMBER), TRY_CAST(? AS BOOLEAN), TRY_CAST(? AS NUMBER)",
            params=[
                run_id,
                safe_str(api_id), api_name or '', url or '',
                safe_str(status_code), safe_str(elapsed_sec),
                safe_str(error_msg), safe_str(retry_count),
                safe_str(attempt_number),
                str(is_final_attempt).lower() if is_final_attempt is not None else None,
                safe_str(page_number)
            ]
        ).collect()
    except Exception:
        pass


def log_run_summary(session, run_id, api_name, api_id, run_start, pages_processed,
                    total_chunks, records_ingested, records_skipped, status,
                    watermark_from, watermark_to, pagination_type, error_message=None):
    try:
        run_start_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(run_start))
        session.sql(
            "INSERT INTO API_DATA_PIPELINE.METADATA.INGESTION_RUN_SUMMARY "
            "(RUN_ID, API_NAME, API_ID, RUN_START_UTC, RUN_END_UTC, PAGES_PROCESSED, TOTAL_CHUNKS, "
            " RECORDS_INGESTED, RECORDS_SKIPPED, STATUS, WATERMARK_FROM, WATERMARK_TO, "
            " FINAL_PAGE_TYPE, ERROR_MESSAGE) "
            "SELECT ?, ?, TRY_CAST(? AS NUMBER), TRY_CAST(? AS TIMESTAMP_NTZ), CURRENT_TIMESTAMP(), "
            "       ?, ?, ?, ?, ?, ?, ?, ?, ?",
            params=[
                run_id, api_name, safe_str(api_id), run_start_str,
                safe_str(pages_processed), safe_str(total_chunks),
                safe_str(records_ingested), safe_str(records_skipped),
                status, safe_str(watermark_from), safe_str(watermark_to),
                pagination_type or 'NONE', safe_str(error_message)
            ]
        ).collect()
    except Exception:
        pass


def authenticate(auth_type, headers, cfg_dict):
    secret_alias = (cfg_dict.get("SECRET_NAME") or "").lower().strip()
    if auth_type == "NONE":
        return
    if not secret_alias:
        raise ValueError(f"AUTH_TYPE='{auth_type}' but SECRET_NAME is not set.")

    if auth_type == "API_KEY":
        api_key = _snowflake.get_generic_secret_string(secret_alias)
        header_name = cfg_dict.get("API_KEY_HEADER") or "X-Api-Key"
        headers[header_name] = api_key

    elif auth_type == "OAUTH2_BASIC":
        creds = _snowflake.get_username_password(secret_alias)
        token_url = cfg_dict.get("TOKEN_URL")
        if not token_url:
            raise ValueError("TOKEN_URL is required for OAUTH2_BASIC auth.")
        token_resp = requests.post(
            token_url,
            data={"grant_type": "client_credentials", "client_id": creds.username, "client_secret": creds.password},
            timeout=int(cfg_dict.get("TIMEOUT_SEC") or 30)
        )
        token_resp.raise_for_status()
        token = token_resp.json().get("access_token")
        if not token:
            raise ValueError("Token endpoint returned 200 but no access_token.")
        headers["Authorization"] = f"Bearer {token}"

    elif auth_type == "OAUTH2_INTEGRATION":
        token = _snowflake.get_oauth_access_token(secret_alias)
        headers["Authorization"] = f"Bearer {token}"

    else:
        raise ValueError(f"Unknown AUTH_TYPE '{auth_type}'.")


def make_request_with_retry(session, run_id, api_name, api_id, url, http_method, headers,
                            body_json, max_retries, retry_delay, timeout, page_number):
    response = None
    retries_used = 0
    run_start = time.time()

    for attempt in range(max_retries):
        retries_used = attempt
        attempt_status = None
        attempt_error = None
        attempt_start = time.time()

        try:
            kwargs = {"method": http_method, "url": url, "headers": headers, "timeout": timeout}
            if http_method == "POST" and body_json:
                kwargs["json"] = body_json
            response = requests.request(**kwargs)
            attempt_status = response.status_code
            if response.status_code != 200:
                attempt_error = f"HTTP {response.status_code}"
        except Exception as ex:
            attempt_error = str(ex)
            response = None

        attempt_elapsed = round(time.time() - attempt_start, 3)
        is_non_retryable = (attempt_status is not None and attempt_status not in RETRYABLE_CODES and attempt_status != 200)
        is_final = (attempt_status == 200 or attempt == max_retries - 1 or is_non_retryable)

        log_attempt(session, run_id, api_name, api_id, url, attempt_status, attempt_elapsed,
                    attempt_error, attempt + 1, attempt + 1, is_final, page_number)

        if attempt_status == 200:
            break
        if is_non_retryable:
            return response, retries_used, round(time.time() - run_start, 3)
        if attempt < max_retries - 1:
            sleep_sec = retry_delay
            if response is not None and attempt_status == 429:
                try:
                    sleep_sec = int(response.headers.get("Retry-After", retry_delay))
                except Exception:
                    sleep_sec = retry_delay
            time.sleep(sleep_sec)

    return response, retries_used, round(time.time() - run_start, 3)


def main(session, api_target):
    run_start = time.time()
    run_id = str(uuid.uuid4())

    cfg_res = session.sql(
        "SELECT * FROM API_DATA_PIPELINE.METADATA.INGESTION_CONFIGS WHERE API_NAME = ? AND ACTIVE_FLAG = TRUE",
        params=[api_target]
    ).collect()

    if not cfg_res:
        return f"Error: Configuration for '{api_target}' not found or inactive."

    cfg = cfg_res[0]
    try:
        _cfg = cfg.asDict() if hasattr(cfg, "asDict") else dict(cfg)
    except Exception:
        _cfg = {}

    api_id          = _cfg.get("API_ID")
    auth_type       = _cfg.get("AUTH_TYPE") or "NONE"
    http_method     = (_cfg.get("HTTP_METHOD") or "GET").upper()
    max_retries     = int(_cfg.get("MAX_RETRIES") or 6)
    retry_delay     = int(_cfg.get("RETRY_DELAY_SEC") or 15)
    timeout         = int(_cfg.get("TIMEOUT_SEC") or 30)
    pagination_type = (_cfg.get("PAGINATION_TYPE") or "NONE").upper()
    page_param      = (_cfg.get("PAGE_PARAM") or "page").strip()
    page_size       = int(_cfg.get("PAGE_SIZE") or DEFAULT_PAGE_SIZE)
    limit_param     = (_cfg.get("LIMIT_PARAM") or "").strip()
    start_index     = int(_cfg.get("START_INDEX") or 1)
    max_pages       = int(_cfg.get("MAX_PAGES") or MAX_PAGES_DEFAULT)
    records_path    = (_cfg.get("RECORDS_PATH") or "data").strip()
    cursor_param    = (_cfg.get("CURSOR_PARAM") or "").strip()
    cursor_path     = (_cfg.get("CURSOR_PATH") or "").strip()
    has_more_path   = (_cfg.get("HAS_MORE_PATH") or "").strip()
    total_pg_path   = (_cfg.get("TOTAL_PAGES_PATH") or "").strip()

    incremental_flag = bool(_cfg.get("INCREMENTAL_FLAG", False))
    watermark_param  = (_cfg.get("WATERMARK_PARAM") or "").strip()
    watermark_field  = (_cfg.get("WATERMARK_FIELD") or "").strip()
    last_sync_value  = (_cfg.get("LAST_SYNC_VALUE") or "").strip()
    new_watermark    = last_sync_value or None

    request_body_raw = (_cfg.get("REQUEST_BODY_JSON") or "").strip()
    body_json = None
    if request_body_raw and request_body_raw.lower() not in ("none", "null", ""):
        try:
            body_json = json.loads(request_body_raw)
        except Exception as e:
            return f"Error parsing REQUEST_BODY_JSON: {str(e)}"

    filter_params_raw = _cfg.get("FILTER_PARAMS")
    if filter_params_raw is not None:
        if isinstance(filter_params_raw, str):
            try:
                _test = json.loads(filter_params_raw)
                filter_params_raw = json.dumps(_test)
            except Exception:
                filter_params_raw = None
        elif isinstance(filter_params_raw, dict):
            filter_params_raw = json.dumps(filter_params_raw)
        else:
            filter_params_raw = None
    else:
        filter_params_raw = None

    if http_method not in FETCH_METHODS:
        return f"Error: HTTP_METHOD '{http_method}' not supported. Only GET and POST are permitted."

    landing_table_cfg = (_cfg.get("LANDING_TABLE") or "").strip()
    if landing_table_cfg and landing_table_cfg.lower() not in ("none", "null", ""):
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_.]*$", landing_table_cfg):
            return f"Error: Invalid LANDING_TABLE '{landing_table_cfg}'."
        target_table = landing_table_cfg if "." in landing_table_cfg else f"API_DATA_PIPELINE.RAW_LANDING.{landing_table_cfg}"
    else:
        target_table = "API_DATA_PIPELINE.RAW_LANDING.API_RAW_DATA"

    try:
        session.sql(
            f"CREATE TABLE IF NOT EXISTS {target_table} ("
            "INGEST_TS TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(), "
            "API_ID NUMBER, API_NAME VARCHAR, STATUS_CODE NUMBER, "
            "PAYLOAD VARIANT, PAYLOAD_HASH VARCHAR, URL_ATTEMPTED VARCHAR)"
        ).collect()
    except Exception as e:
        return f"Error creating landing table '{target_table}': {str(e)}"

    headers = {"Accept": "application/json"}
    try:
        authenticate(auth_type, headers, _cfg)
    except Exception as e:
        log_attempt(session, run_id, api_target, api_id, None, None, None, f"Auth failed: {str(e)}", 0, None, True, None)
        log_run_summary(session, run_id, api_target, api_id, run_start, 0, 0, 0, 0, "ERROR",
                        last_sync_value, None, pagination_type, f"Auth failed: {str(e)}")
        return f"Authentication failed for '{api_target}': {str(e)}"

    extra_headers_raw = (_cfg.get("EXTRA_HEADERS_JSON") or "").strip()
    if extra_headers_raw and extra_headers_raw.lower() not in ("none", "null", "undefined"):
        try:
            headers.update(json.loads(extra_headers_raw))
        except Exception as e:
            return f"Error parsing EXTRA_HEADERS_JSON: {str(e)}"

    if pagination_type == "CURSOR" and not cursor_path:
        err = (f"Error: PAGINATION_TYPE=CURSOR but CURSOR_PATH is not configured for '{api_target}'.")
        log_run_summary(session, run_id, api_target, api_id, run_start, 0, 0, 0, 0, "ERROR",
                        last_sync_value, None, pagination_type, err)
        return err

    if pagination_type == "CURSOR" and not cursor_param:
        err = (f"Error: PAGINATION_TYPE=CURSOR but CURSOR_PARAM is not configured for '{api_target}'.")
        log_run_summary(session, run_id, api_target, api_id, run_start, 0, 0, 0, 0, "ERROR",
                        last_sync_value, None, pagination_type, err)
        return err

    page = start_index
    page_counter = 0
    cursor_token = None
    is_first_cursor_page = True
    pages_processed = 0
    total_chunks_all = 0
    records_ingested = 0
    records_staged = 0
    records_skipped = 0
    base_url = _cfg.get("ENDPOINT_URL") or ""

    staging_table = f"API_DATA_PIPELINE.RAW_LANDING._STG_{api_target}_{int(run_start)}"
    try:
        session.sql(
            f"CREATE OR REPLACE TRANSIENT TABLE {staging_table} ("
            "API_ID NUMBER, API_NAME VARCHAR, STATUS_CODE NUMBER, "
            "PAYLOAD VARIANT, PAYLOAD_HASH VARCHAR, URL_ATTEMPTED VARCHAR) "
            "DATA_RETENTION_TIME_IN_DAYS = 0"
        ).collect()
    except Exception as e:
        return f"Error creating staging table: {str(e)}"

    while True:
        if pages_processed >= max_pages:
            msg = f"Warning: '{api_target}' reached MAX_PAGES ({max_pages})."
            log_run_summary(session, run_id, api_target, api_id, run_start, pages_processed, total_chunks_all,
                            records_ingested, records_skipped, "WARNING",
                            last_sync_value, safe_str(new_watermark), pagination_type, msg)
            return msg

        url = base_url
        connector = "&" if "?" in url else "?"

        if pagination_type == "LINK" and pages_processed > 0:
            pass
        else:
            url = build_filter_url(url, filter_params_raw)
            connector = "&" if "?" in url else "?"

            if incremental_flag and watermark_param and last_sync_value:
                if pagination_type != "CURSOR" or is_first_cursor_page:
                    try:
                        from datetime import datetime as _dt, timedelta as _td
                        _wm_dt = _dt.fromisoformat(str(last_sync_value).replace("Z", "+00:00"))
                        _overlap_wm = (_wm_dt - _td(seconds=7200)).isoformat().replace("+00:00", "Z")
                    except Exception:
                        _overlap_wm = last_sync_value
                    url = f"{url}{connector}{watermark_param}={_urlparse.quote(str(_overlap_wm))}"
                    connector = "&"

        if pagination_type == "PAGE":
            url = f"{url}{connector}{page_param}={page}"
            connector = "&"
            if _cfg.get("LIMIT_PARAM"):
                url = f"{url}&{limit_param}={page_size}"
        elif pagination_type == "OFFSET":
            offset_val = (page - start_index) * page_size
            url = f"{url}{connector}{page_param}={offset_val}"
            connector = "&"
            if _cfg.get("LIMIT_PARAM"):
                url = f"{url}&{limit_param}={page_size}"
        elif pagination_type == "CURSOR":
            if cursor_token is not None:
                encoded_cursor = _urlparse.quote(str(cursor_token), safe='%=+')
                url = f"{url}{connector}{cursor_param}={encoded_cursor}"
                connector = "&"
            if _cfg.get("LIMIT_PARAM"):
                url = f"{url}{connector}{limit_param}={page_size}"

        response, retries_used, elapsed = make_request_with_retry(
            session, run_id, api_target, api_id, url, http_method, headers,
            body_json, max_retries, retry_delay, timeout, page_counter
        )

        status = response.status_code if response else None
        if not response or status != 200:
            display_page = page_counter if pagination_type in ("LINK", "CURSOR") else page
            err_msg = f"Error: '{api_target}' failed page {display_page}. Status: {status}"
            log_run_summary(session, run_id, api_target, api_id, run_start, pages_processed, total_chunks_all,
                            records_ingested, records_skipped, "ERROR",
                            last_sync_value, safe_str(new_watermark), pagination_type, err_msg)
            return err_msg

        try:
            payload = response.json()
        except Exception as json_err:
            err_msg = f"Error: non-JSON response. {str(json_err)}"
            log_run_summary(session, run_id, api_target, api_id, run_start, pages_processed, total_chunks_all,
                            records_ingested, records_skipped, "ERROR",
                            last_sync_value, None, pagination_type, err_msg)
            return err_msg

        data_to_split = extract_records(payload, records_path)

        if incremental_flag and watermark_field:
            for rec in data_to_split:
                wm_val = extract_field(rec, watermark_field)
                if wm_val is not None:
                    new_watermark = compare_watermarks(new_watermark, wm_val)
            if new_watermark is not None and str(new_watermark) != str(last_sync_value or ""):
                try:
                    session.sql(
                        "UPDATE API_DATA_PIPELINE.METADATA.INGESTION_CONFIGS SET LAST_SYNC_VALUE = ? WHERE API_NAME = ?",
                        params=[str(new_watermark), api_target]
                    ).collect()
                    last_sync_value = str(new_watermark)
                except Exception:
                    pass

        if data_to_split:
            total_chunks_page = max(1, (len(data_to_split) + CHUNK_SIZE - 1) // CHUNK_SIZE)
            for i in range(0, len(data_to_split), CHUNK_SIZE):
                chunk_index = (i // CHUNK_SIZE) + 1
                chunk_data = data_to_split[i:i + CHUNK_SIZE]
                content_for_hash = json.dumps({"data": chunk_data}, sort_keys=True)
                chunk_hash = hashlib.sha256(content_for_hash.encode()).hexdigest()
                chunk_payload = {
                    "data": chunk_data,
                    "_chunk_meta": {"page": page, "chunk": chunk_index, "total_chunks": total_chunks_page}
                }
                chunk_json = json.dumps(chunk_payload)
                annotated_url = f"{url} [Page {page} Chunk {chunk_index}/{total_chunks_page}]"
                session.sql(
                    f"INSERT INTO {staging_table} (API_ID, API_NAME, STATUS_CODE, PAYLOAD, PAYLOAD_HASH, URL_ATTEMPTED) "
                    "SELECT TRY_CAST(? AS NUMBER), ?, ?, PARSE_JSON(?), ?, ?",
                    params=[safe_str(api_id), api_target, response.status_code, chunk_json, chunk_hash,
                            annotated_url]
                ).collect()
                records_staged += len(chunk_data)
                total_chunks_all += 1

        pages_processed += 1
        page_counter += 1

        if pages_processed % PROGRESS_LOG_INTERVAL == 0:
            log_attempt(session, run_id, api_target, api_id, '__PROGRESS__', None, None,
                        f"Progress: {pages_processed} pages, {records_staged:,} records staged",
                        0, None, False, page_counter)

        if pagination_type == "NONE":
            break

        if not data_to_split:
            if has_more_path:
                has_more = extract_field(payload, has_more_path)
                if bool(has_more):
                    page += 1
                    continue
            break

        if has_more_path:
            has_more = extract_field(payload, has_more_path)
            if has_more is not None and not bool(has_more):
                break
        if total_pg_path:
            total_pages_api = extract_field(payload, total_pg_path)
            if total_pages_api is not None:
                try:
                    last_page = int(total_pages_api) - 1 + start_index
                    if page >= last_page:
                        break
                except Exception:
                    pass
        if pagination_type == "CURSOR":
            cursor_token = extract_field(payload, cursor_path)
            is_first_cursor_page = False
            if cursor_token is None:
                break
            if isinstance(cursor_token, str) and not cursor_token.strip():
                break
            if has_more_path:
                has_more_val = extract_field(payload, has_more_path)
                if has_more_val is not None and not bool(has_more_val):
                    break
        elif pagination_type == "LINK":
            link_header = response.headers.get("Link", "")
            next_url = None
            for part in link_header.split(","):
                part = part.strip()
                if 'rel="next"' in part:
                    match = re.search(r'<([^>]+)>', part)
                    if match:
                        next_url = match.group(1)
                        break
            if next_url:
                try:
                    parsed_link = _urlparse.urlparse(next_url)
                    if parsed_link.scheme in ('http', 'https') and parsed_link.netloc:
                        base_url = next_url
                    else:
                        log_attempt(session, run_id, api_target, api_id, url, 200, 0,
                                    f"Invalid next URL in Link header: {next_url}", 0, None, True, page)
                        break
                except Exception:
                    break
            else:
                break
        elif pagination_type in ("PAGE", "OFFSET"):
            page += 1

    try:
        merge_result = session.sql(
            f"MERGE INTO {target_table} tgt "
            f"USING {staging_table} stg "
            f"ON tgt.PAYLOAD_HASH = stg.PAYLOAD_HASH "
            f"WHEN NOT MATCHED THEN INSERT "
            f"(API_ID, API_NAME, STATUS_CODE, PAYLOAD, PAYLOAD_HASH, URL_ATTEMPTED) "
            f"VALUES (stg.API_ID, stg.API_NAME, stg.STATUS_CODE, stg.PAYLOAD, stg.PAYLOAD_HASH, stg.URL_ATTEMPTED)"
        ).collect()
        if merge_result and merge_result[0]:
            r = merge_result[0].asDict() if hasattr(merge_result[0], "asDict") else {}
            records_ingested = int(r.get("number of rows inserted", 0) or 0)
    except Exception as merge_err:
        log_attempt(session, run_id, api_target, api_id, None, None, None,
                    f"MERGE failed: {str(merge_err)}", 0, None, True, None)

    try:
        stg_count = session.sql(f"SELECT COUNT(*) AS C FROM {staging_table}").collect()
        total_staged = int(stg_count[0][0]) if stg_count else 0
        records_skipped = max(0, total_staged - records_ingested)
    except Exception:
        pass

    try:
        session.sql(f"DROP TABLE IF EXISTS {staging_table}").collect()
    except Exception:
        pass

    watermark_persisted = bool(
        incremental_flag and new_watermark is not None and str(new_watermark) != str(_cfg.get("LAST_SYNC_VALUE") or "")
    )

    log_run_summary(session, run_id, api_target, api_id, run_start, pages_processed, total_chunks_all,
                    records_ingested, records_skipped, "SUCCESS",
                    _cfg.get("LAST_SYNC_VALUE") or None, safe_str(new_watermark) if watermark_persisted else None,
                    pagination_type)

    wm_msg = ""
    if incremental_flag:
        wm_msg = f" | Watermark: {last_sync_value or '(none)'} -> {new_watermark or '(unchanged)'}"
    dup_msg = f" | {records_skipped:,} dup(s) skipped" if records_skipped else ""

    export_msg = ""
    if bool(_cfg.get("EXPORT_ENABLED", False)):
        try:
            exp_cnt = session.sql(
                "SELECT COUNT(*) AS C FROM API_DATA_PIPELINE.METADATA.EXPORT_CONFIGS "
                "WHERE API_NAME = ? AND ACTIVE_FLAG = TRUE",
                params=[api_target]
            ).collect()
            has_export_config = bool(exp_cnt and int(exp_cnt[0][0]) > 0)
        except Exception:
            has_export_config = False

        if has_export_config:
            try:
                export_result = session.sql(
                    "CALL API_DATA_PIPELINE.METADATA.USP_EXPORT_TO_STAGE(?, ?, NULL)",
                    params=[api_target, run_id]
                ).collect()
                export_msg = export_result[0][0] if export_result else "no result"
                if "FAILED" in str(export_msg):
                    log_attempt(session, run_id, api_target, api_id, '__EXPORT_ERROR__', None, None,
                                export_msg, 0, None, True, None)
            except Exception as exp_err:
                export_msg = f"Export failed: {str(exp_err)}"
                log_attempt(session, run_id, api_target, api_id, '__EXPORT_ERROR__', None, None,
                            export_msg, 0, None, True, None)
        else:
            export_msg = "pending — no export destination configured yet"
            log_attempt(session, run_id, api_target, api_id, '__EXPORT_PENDING__', None, None,
                        export_msg, 0, None, False, None)
    export_suffix = f" | Export: {export_msg}" if export_msg else ""
    return f"Success: '{api_target}' — {pages_processed} page(s) · {records_ingested:,} records{dup_msg}{wm_msg}{export_suffix}"
''').strip()

    ddl = f"""CREATE OR REPLACE PROCEDURE API_DATA_PIPELINE.METADATA.USP_UNIVERSAL_INGESTOR("API_TARGET" VARCHAR)
RETURNS VARCHAR
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES = ('snowflake-snowpark-python','requests')
HANDLER = 'main'
EXTERNAL_ACCESS_INTEGRATIONS = (EAI_UNIVERSAL_INGESTOR)
{secrets_clause}
EXECUTE AS OWNER
AS
${'$'}${'$'}
{proc_body}
${'$'}${'$'}"""

    try:
        session.sql(ddl).collect()
        return f"USP_UNIVERSAL_INGESTOR rebuilt with {len(secrets)} secret(s) bound."
    except Exception as e:
        return f"Rebuild failed: {str(e)}"
$$;
