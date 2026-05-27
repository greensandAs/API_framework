-- ============================================================================
-- API_DATA_PIPELINE — Canonical Setup
-- Creates the database, schemas, and core tables for the metadata-driven
-- API ingestion framework. Idempotent: schemas use IF NOT EXISTS; tables use
-- CREATE OR REPLACE (run only on a fresh setup or when intentionally resetting).
-- ============================================================================

-- Use the top-level admin role for setup
-- USE ROLE ACCOUNTADMIN;

-- ─── Database & Schemas ─────────────────────────────────────────────────────
CREATE DATABASE IF NOT EXISTS API_DATA_PIPELINE;

CREATE SCHEMA IF NOT EXISTS API_DATA_PIPELINE.METADATA;
CREATE SCHEMA IF NOT EXISTS API_DATA_PIPELINE.RAW_LANDING;

USE SCHEMA API_DATA_PIPELINE.METADATA;

-- ─── INGESTION_CONFIGS ──────────────────────────────────────────────────────
-- Central registry: one row per managed API endpoint.
--   API_ID            : auto-incrementing surrogate key (rename-safe)
--   API_NAME          : human-readable unique business key
--   INCREMENTAL_FLAG  : enables watermark-based incremental sync
--   WATERMARK_PARAM   : query-string parameter to send (e.g. 'since')
--   WATERMARK_FIELD   : dotted JSON path to read the high-water mark from
--   LAST_SYNC_VALUE   : last successful watermark value
CREATE OR REPLACE TABLE API_DATA_PIPELINE.METADATA.INGESTION_CONFIGS (
    API_ID              NUMBER(38,0) AUTOINCREMENT START 1 INCREMENT 1,
    API_NAME            VARCHAR(16777216) NOT NULL,
    ENDPOINT_URL        VARCHAR(16777216),
    HTTP_METHOD         VARCHAR(16777216) DEFAULT 'GET',
    AUTH_TYPE           VARCHAR(16777216),
    API_KEY_HEADER      VARCHAR(16777216),
    SECRET_NAME         VARCHAR(16777216),
    TOKEN_URL           VARCHAR(16777216),
    PAGINATION_TYPE     VARCHAR(16777216),
    PAGE_PARAM          VARCHAR(16777216),
    START_INDEX         NUMBER(38,0) DEFAULT 1,
    MAX_RETRIES         NUMBER(38,0) DEFAULT 6,
    RETRY_DELAY_SEC     NUMBER(38,0) DEFAULT 15,
    TIMEOUT_SEC         NUMBER(38,0) DEFAULT 30,
    EXTRA_HEADERS_JSON  VARCHAR(16777216),
    LANDING_TABLE       VARCHAR(16777216),
    INCREMENTAL_FLAG    BOOLEAN DEFAULT FALSE,
    WATERMARK_PARAM     VARCHAR(16777216),
    WATERMARK_FIELD     VARCHAR(16777216),
    LAST_SYNC_VALUE     VARCHAR(16777216),
    ACTIVE_FLAG         BOOLEAN DEFAULT TRUE,
    CREATED_TS          TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (API_NAME),
    UNIQUE      (API_ID)
);

-- ─── INGESTION_RESPONSE_LOG ─────────────────────────────────────────────────
-- One row per HTTP attempt (including retries). Powers the Ingestion Console
-- and the Retry Drill-Down panel.
--   ATTEMPT_NUMBER    : 1..MAX_RETRIES; the attempt this row represents
--   IS_FINAL_ATTEMPT  : TRUE for the last attempt of a page (success or exhausted)
--   PAGE_NUMBER       : page index this attempt belongs to
CREATE OR REPLACE TABLE API_DATA_PIPELINE.METADATA.INGESTION_RESPONSE_LOG (
    INSERT_DATETIME_UTC     TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP(),
    API_ID                  NUMBER(38,0),
    API_NAME                VARCHAR(16777216),
    API_URL                 VARCHAR(16777216),
    STATUS_CODE             NUMBER(38,0),
    RESPONSE_TIME_SECONDS   FLOAT,
    ERROR_MESSAGE_TEXT      VARCHAR(16777216),
    RETRY_COUNT             NUMBER(38,0),
    ATTEMPT_NUMBER          NUMBER(38,0),
    IS_FINAL_ATTEMPT        BOOLEAN,
    PAGE_NUMBER             NUMBER(38,0)
);

-- ─── API_RAW_DATA ───────────────────────────────────────────────────────────
-- Default landing table for ingested JSON payloads. Custom landing tables
-- created on demand by USP_UNIVERSAL_INGESTOR follow the same shape.
CREATE OR REPLACE TABLE API_DATA_PIPELINE.RAW_LANDING.API_RAW_DATA (
    INGEST_TS       TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP(),
    API_ID          NUMBER(38,0),
    API_NAME        VARCHAR(16777216),
    STATUS_CODE     NUMBER(38,0),
    PAYLOAD         VARIANT,
    PAYLOAD_HASH    VARCHAR(16777216),
    URL_ATTEMPTED   VARCHAR(16777216)
);


SHOW TASKS;

SELECT * FROM TABLE(API_DATA_PIPELINE.INFORMATION_SCHEMA.TASK_HISTORY()) LIMIT 10 ;