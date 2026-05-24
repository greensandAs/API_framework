-- Define the allowed destinations
CREATE OR REPLACE NETWORK RULE nr_api_egress
  MODE = EGRESS
  TYPE = HOST_PORT
  VALUE_LIST = ('jsonplaceholder.typicode.com', 'reqres.in');

-- Create the integration 'bridge'
CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION eai_api_framework
  ALLOWED_NETWORK_RULES = (nr_api_egress)
  ENABLED = TRUE;

  SHOW NETWORK RULES;
  DESC NETWORK RULE nr_api_egress;