-- ── AWS S3 ────────────────────────────────────────────────────
CREATE STORAGE INTEGRATION SI_S3_API_EXPORTS
    TYPE = EXTERNAL_STAGE
    STORAGE_PROVIDER = 'S3'
    ENABLED = TRUE
    STORAGE_AWS_ROLE_ARN = 'arn:aws:iam::208107894437:role/snowflake_s3_role'
    STORAGE_ALLOWED_LOCATIONS = ('s3://snowsync-208107894437-ap-southeast-2-an/');

-- Get the IAM values to configure AWS trust policy
DESC INTEGRATION SI_S3_API_EXPORTS;
-- Note: STORAGE_AWS_IAM_USER_ARN and STORAGE_AWS_EXTERNAL_ID
-- → Add these to your S3 bucket's IAM trust relationship

-- ── S3 Stage ──────────────────────────────────────────────────
CREATE STAGE IF NOT EXISTS API_DATA_PIPELINE.PUBLIC.STG_S3_EXPORTS
    URL = 's3://snowsync-208107894437-ap-southeast-2-an/'
    STORAGE_INTEGRATION = SI_S3_API_EXPORTS
    COMMENT = 'S3 export stage for flattened API data';

-- ── Azure ADLS Gen2 ───────────────────────────────────────────
CREATE STORAGE INTEGRATION SI_ADLS_API_EXPORTS
    TYPE = EXTERNAL_STAGE
    STORAGE_PROVIDER = 'AZURE'
    ENABLED = TRUE
    AZURE_TENANT_ID = '<your-tenant-id>'
    STORAGE_ALLOWED_LOCATIONS = (
        'azure://youraccount.blob.core.windows.net/api-exports/'
    );

-- Get consent URL for Azure
DESC INTEGRATION SI_ADLS_API_EXPORTS;
-- Note: AZURE_CONSENT_URL → visit this URL to grant Snowflake access