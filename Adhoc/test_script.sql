SELECT * FROM INGESTION_CONFIGS;

SELECT * FROM RAW_LANDING.API_RAW_DATA;
SELECT * FROM RAW_LANDING.DEMO_CAT1;
select * from ingestion_response_log;


--- capture the response type

-- each retry capture the failure log

SHOW network rules;
show security integrations;
show secrets;

-- DROP NETWORK RULE API_DATA_PIPELINE.METADATA.NR_TWITCH_TEST;
-- DROP NETWORK RULE API_DATA_PIPELINE.METADATA.NR_JSONPLACEHOLDER_API;
-- DROP NETWORK RULE API_DATA_PIPELINE.METADATA.NR_DEMO_GAUNTLET;
-- DROP NETWORK RULE API_DATA_PIPELINE.METADATA.NR_TWITCH_API;


-- DROP SECRET API_DATA_PIPELINE.METADATA.SK_TWITCH_INT_TEST;
-- DROP SECURITY INTEGRATION SEC_INT_TWITCH_TEST;
-- DROP SECRET API_DATA_PIPELINE.METADATA.SK_TWITCH_OAUTH;
-- DROP SECURITY INTEGRATION API_DATA_PIPELINE.METADATA.TWITCH_OAUTH_INTEGRATION;
-- DROP SECURITY INTEGRATION API_DATA_PIPELINE.METADATA.SEC_INT_TWITCH;
-- DROP SECURITY INTEGRATION API_DATA_PIPELINE.METADATA.SEC_INT_POSTMAN_MOCK;



-- truncate table raw_landing.api_raw_data;
SELECT
    base.INGEST_TS,
    base.API_NAME,
    base.STATUS_CODE,
    base.URL_ATTEMPTED,
    rec.value:author::STRING AS AUTHOR,
    rec.value:author:avatar_url::STRING AS AUTHOR_AVATAR_URL,
    rec.value:author:events_url::STRING AS AUTHOR_EVENTS_URL,
    rec.value:author:followers_url::STRING AS AUTHOR_FOLLOWERS_URL,
    rec.value:author:following_url::STRING AS AUTHOR_FOLLOWING_URL,
    rec.value:author:gists_url::STRING AS AUTHOR_GISTS_URL,
    rec.value:author:gravatar_id::STRING AS AUTHOR_GRAVATAR_ID,
    rec.value:author:html_url::STRING AS AUTHOR_HTML_URL,
    rec.value:author:id::NUMBER AS AUTHOR_ID,
    rec.value:author:login::STRING AS AUTHOR_LOGIN,
    rec.value:author:node_id::STRING AS AUTHOR_NODE_ID,
    rec.value:author:organizations_url::STRING AS AUTHOR_ORGANIZATIONS_URL,
    rec.value:author:received_events_url::STRING AS AUTHOR_RECEIVED_EVENTS_URL,
    rec.value:author:repos_url::STRING AS AUTHOR_REPOS_URL,
    rec.value:author:site_admin::BOOLEAN AS AUTHOR_SITE_ADMIN,
    rec.value:author:starred_url::STRING AS AUTHOR_STARRED_URL,
    rec.value:author:subscriptions_url::STRING AS AUTHOR_SUBSCRIPTIONS_URL,
    rec.value:author:type::STRING AS AUTHOR_TYPE,
    rec.value:author:url::STRING AS AUTHOR_URL,
    rec.value:author:user_view_type::STRING AS AUTHOR_USER_VIEW_TYPE,
    rec.value:comments_url::STRING AS COMMENTS_URL,
    rec.value:commit:author:date::TIMESTAMP_TZ AS COMMIT_AUTHOR_DATE,
    rec.value:commit:author:email::STRING AS COMMIT_AUTHOR_EMAIL,
    rec.value:commit:author:name::STRING AS COMMIT_AUTHOR_NAME,
    rec.value:commit:comment_count::NUMBER AS COMMIT_COMMENT_COUNT,
    rec.value:commit:committer:date::TIMESTAMP_TZ AS COMMIT_COMMITTER_DATE,
    rec.value:commit:committer:email::STRING AS COMMIT_COMMITTER_EMAIL,
    rec.value:commit:committer:name::STRING AS COMMIT_COMMITTER_NAME,
    rec.value:commit:message::STRING AS COMMIT_MESSAGE,
    rec.value:commit:tree:sha::STRING AS COMMIT_TREE_SHA,
    rec.value:commit:tree:url::STRING AS COMMIT_TREE_URL,
    rec.value:commit:url::STRING AS COMMIT_URL,
    rec.value:commit:verification:payload::STRING AS COMMIT_VERIFICATION_PAYLOAD,
    rec.value:commit:verification:reason::STRING AS COMMIT_VERIFICATION_REASON,
    rec.value:commit:verification:signature::STRING AS COMMIT_VERIFICATION_SIGNATURE,
    rec.value:commit:verification:verified::BOOLEAN AS COMMIT_VERIFICATION_VERIFIED,
    rec.value:commit:verification:verified_at::TIMESTAMP_TZ AS COMMIT_VERIFICATION_VERIFIED_AT,
    rec.value:committer:avatar_url::STRING AS COMMITTER_AVATAR_URL,
    rec.value:committer:events_url::STRING AS COMMITTER_EVENTS_URL,
    rec.value:committer:followers_url::STRING AS COMMITTER_FOLLOWERS_URL,
    rec.value:committer:following_url::STRING AS COMMITTER_FOLLOWING_URL,
    rec.value:committer:gists_url::STRING AS COMMITTER_GISTS_URL,
    rec.value:committer:gravatar_id::STRING AS COMMITTER_GRAVATAR_ID,
    rec.value:committer:html_url::STRING AS COMMITTER_HTML_URL,
    rec.value:committer:id::NUMBER AS COMMITTER_ID,
    rec.value:committer:login::STRING AS COMMITTER_LOGIN,
    rec.value:committer:node_id::STRING AS COMMITTER_NODE_ID,
    rec.value:committer:organizations_url::STRING AS COMMITTER_ORGANIZATIONS_URL,
    rec.value:committer:received_events_url::STRING AS COMMITTER_RECEIVED_EVENTS_URL,
    rec.value:committer:repos_url::STRING AS COMMITTER_REPOS_URL,
    rec.value:committer:site_admin::BOOLEAN AS COMMITTER_SITE_ADMIN,
    rec.value:committer:starred_url::STRING AS COMMITTER_STARRED_URL,
    rec.value:committer:subscriptions_url::STRING AS COMMITTER_SUBSCRIPTIONS_URL,
    rec.value:committer:type::STRING AS COMMITTER_TYPE,
    rec.value:committer:url::STRING AS COMMITTER_URL,
    rec.value:committer:user_view_type::STRING AS COMMITTER_USER_VIEW_TYPE,
    rec.value:html_url::STRING AS HTML_URL,
    rec.value:node_id::STRING AS NODE_ID,
    rec.value:parents::ARRAY AS PARENTS,
    rec.value:sha::STRING AS SHA,
    rec.value:url::STRING AS URL
FROM API_DATA_PIPELINE.RAW_LANDING.API_RAW_DATA base,
     LATERAL FLATTEN(input => base.PAYLOAD:data) rec
WHERE base.API_NAME = 'TEST_GITHUB_INCR';

