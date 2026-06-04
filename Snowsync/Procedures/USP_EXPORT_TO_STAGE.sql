-- ============================================================================
-- USP_EXPORT_TO_STAGE — Flatten RAW_LANDING and COPY INTO an external stage
-- (S3 / ADLS). Supports INCREMENTAL (current run), FULL, and SNAPSHOT modes.
-- Credential-free via Storage Integration bound to the stage.
-- ============================================================================

CREATE OR REPLACE PROCEDURE API_DATA_PIPELINE.METADATA.USP_EXPORT_TO_STAGE(
    "API_TARGET" VARCHAR,
    "RUN_ID" VARCHAR,
    "EXPORT_ID" NUMBER
)
RETURNS VARCHAR
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'main'
EXECUTE AS OWNER
AS
$$
import json
import time
import re
from datetime import datetime, timezone


def safe_str(v):
    return str(v) if v is not None else None


def quote_col(name):
    return f'"{name.upper()}"'


def build_flatten_select(fields):
    if not fields:
        return "rec.value AS RECORD"
    cols = []
    for field_path in fields:
        parts = field_path.strip().split(".")
        access = "rec.value"
        for part in parts:
            access += f":{part}"
        alias = re.sub(r"[^A-Za-z0-9_]", "_", field_path).upper()
        cols.append(f"{access} AS {quote_col(alias)}")
    return ",\n       ".join(cols)


def build_flatten_query(target_table, records_path, fields, load_mode, run_id, api_name):
    select_cols = build_flatten_select(fields)
    rp = (records_path or "data").strip()
    if rp and rp.lower() not in ("none", "null", ""):
        flatten_expr = f"base.PAYLOAD:{rp}"
    else:
        flatten_expr = "base.PAYLOAD"

    base_select = f"""
        SELECT base.INGEST_TS, base.API_NAME, base.STATUS_CODE, base.URL_ATTEMPTED,
               {select_cols}
        FROM {target_table} base,
             LATERAL FLATTEN(input => {flatten_expr}) rec
    """

    if load_mode == "INCREMENTAL" and run_id:
        where_clause = f"""
        WHERE base.API_NAME = '{api_name}'
          AND base.PAYLOAD_HASH IN (
              SELECT DISTINCT PAYLOAD_HASH
              FROM API_DATA_PIPELINE.METADATA.INGESTION_RESPONSE_LOG
              WHERE RUN_ID = '{run_id}'
          )
        """
    else:
        where_clause = f"WHERE base.API_NAME = '{api_name}'"

    return base_select + where_clause


def get_partition_path(partition_by_date, api_name, load_mode, run_id):
    parts = [api_name.lower().replace("_", "-")]
    if partition_by_date:
        dt = datetime.now(timezone.utc)
        parts += [str(dt.year), f"{dt.month:02d}", f"{dt.day:02d}"]
    if load_mode == "INCREMENTAL" and run_id:
        parts.append(str(run_id)[:8])
    elif load_mode == "FULL":
        parts.append("full")
    elif load_mode == "SNAPSHOT":
        parts.append(f"snapshot_{int(time.time())}")
    return "/".join(parts) + "/"


def main(session, api_target, run_id, export_id):
    if export_id is not None:
        query = ("SELECT * FROM API_DATA_PIPELINE.METADATA.EXPORT_CONFIGS "
                 "WHERE EXPORT_ID = ? AND API_NAME = ? AND ACTIVE_FLAG = TRUE")
        params = [str(export_id), api_target]
    else:
        query = ("SELECT * FROM API_DATA_PIPELINE.METADATA.EXPORT_CONFIGS "
                 "WHERE API_NAME = ? AND ACTIVE_FLAG = TRUE ORDER BY EXPORT_ID")
        params = [api_target]

    export_rows = session.sql(query, params=params).collect()
    if not export_rows:
        return f"No active export configs found for '{api_target}'."

    cfg_res = session.sql(
        "SELECT LANDING_TABLE, RECORDS_PATH FROM API_DATA_PIPELINE.METADATA.INGESTION_CONFIGS WHERE API_NAME = ?",
        params=[api_target]
    ).collect()
    if not cfg_res:
        return f"Error: Ingestion config for '{api_target}' not found."

    ingest_cfg = cfg_res[0].asDict() if hasattr(cfg_res[0], "asDict") else dict(cfg_res[0])
    landing_raw = (ingest_cfg.get("LANDING_TABLE") or "").strip()
    ingest_rpath = (ingest_cfg.get("RECORDS_PATH") or "data").strip()

    if landing_raw and landing_raw.lower() not in ("none", "null", ""):
        target_table = landing_raw if "." in landing_raw else f"API_DATA_PIPELINE.RAW_LANDING.{landing_raw}"
    else:
        target_table = "API_DATA_PIPELINE.RAW_LANDING.API_RAW_DATA"

    results = []
    for export_row in export_rows:
        exp = export_row.asDict() if hasattr(export_row, "asDict") else dict(export_row)
        exp_id = exp.get("EXPORT_ID")
        try:
            stage_name = exp.get("STAGE_NAME") or ""
            export_path = (exp.get("EXPORT_PATH") or "").rstrip("/") + "/"
            export_format = (exp.get("EXPORT_FORMAT") or "PARQUET").upper()
            records_path = (exp.get("RECORDS_PATH") or ingest_rpath).strip()
            load_mode = (exp.get("LOAD_MODE") or "INCREMENTAL").upper()
            partition_by = bool(exp.get("PARTITION_BY_DATE", True))
            file_prefix = exp.get("FILE_PREFIX") or "data"
            max_file_mb = int(exp.get("MAX_FILE_SIZE_MB") or 256)
            flatten_fields_raw = exp.get("FLATTEN_FIELDS")

            flatten_fields = None
            if flatten_fields_raw is not None:
                try:
                    ff = json.loads(flatten_fields_raw) if isinstance(flatten_fields_raw, str) else flatten_fields_raw
                    if isinstance(ff, list):
                        flatten_fields = [str(f).strip() for f in ff if f]
                except Exception:
                    pass

            partition_suffix = get_partition_path(partition_by, api_target, load_mode, run_id)
            stage_ref = stage_name if stage_name.startswith("@") else f"@{stage_name}"
            full_path = f"{stage_ref}/{export_path}{partition_suffix}"

            flatten_sql = build_flatten_query(target_table, records_path, flatten_fields, load_mode, run_id, api_target)

            if export_format == "CSV":
                format_clause = ("FILE_FORMAT = (TYPE=CSV COMPRESSION=GZIP "
                                 "FIELD_OPTIONALLY_ENCLOSED_BY='\"' NULL_IF=('NULL','null','') "
                                 "EMPTY_FIELD_AS_NULL=TRUE)")
            elif export_format == "JSON":
                format_clause = "FILE_FORMAT = (TYPE=JSON COMPRESSION=GZIP)"
            else:
                format_clause = "FILE_FORMAT = (TYPE=PARQUET SNAPPY_COMPRESSION=TRUE)"

            copy_sql = f"""
                COPY INTO '{full_path}{file_prefix}_'
                FROM ({flatten_sql})
                {format_clause}
                MAX_FILE_SIZE = {max_file_mb * 1024 * 1024}
                OVERWRITE = FALSE
                HEADER = TRUE
            """

            copy_result = session.sql(copy_sql).collect()

            rows_unloaded = 0
            files_written = 0
            if copy_result:
                for r in copy_result:
                    r_dict = r.asDict() if hasattr(r, "asDict") else {}
                    rows_unloaded += int(r_dict.get("rows_unloaded", 0) or 0)
                    files_written += 1

            session.sql(
                "UPDATE API_DATA_PIPELINE.METADATA.EXPORT_CONFIGS "
                "SET LAST_EXPORT_UTC = CURRENT_TIMESTAMP(), LAST_RUN_ID = ?, UPDATED_AT = CURRENT_TIMESTAMP() "
                "WHERE EXPORT_ID = ?",
                params=[safe_str(run_id), safe_str(exp_id)]
            ).collect()

            results.append(
                f"Export '{exp.get('EXPORT_NAME')}' -> {full_path} | "
                f"{rows_unloaded:,} rows | {files_written} file(s) | {export_format}"
            )
        except Exception as e:
            results.append(f"Export '{exp.get('EXPORT_NAME', exp_id)}' FAILED: {str(e)}")

    return "\n".join(results)
$$;
