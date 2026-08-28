Hermes is configured to use Hindsight as its memory provider in hermes/config.yaml:1:

  - memory.provider: hindsight
  - memory.url: http://hindsight:8888
  - memory banks:
      - core: memory:core
      - portfolio: studio:portfolio
      - opco_pattern: opco:<name>

  So the Hermes side is simple:

  - point Hermes at a reachable Hindsight HTTP endpoint
  - set provider: hindsight
  - define the banks you want

  The Hindsight service itself is self-hosted in docker-compose.yml:32:

  - container image: ghcr.io/vectorize-io/hindsight:latest
  - API port inside the Docker network: 8888
  - host port mapping: 8001:8888
  - database: Postgres at postgresql://hindsight:hindsight@postgres:5432/hindsight

  Important part about API keys:

  - this setup does not depend on Hindsight Cloud
  - Hindsight is run locally/self-hosted
  - the container is intentionally started with:
      - HINDSIGHT_API_LLM_PROVIDER=none
      - HINDSIGHT_API_LLM_API_KEY=local-dummy-key

  That means:

  - Hermes talks to Hindsight over HTTP
  - Hindsight does not need a real external LLM API key just to exist in this setup
  - the local-dummy-key is just a placeholder because the container expects a value

  If another LLM is trying to reproduce this without Docker, the minimum setup is:

  1. Run a reachable Hindsight server
  2. Run a reachable Postgres database for Hindsight
  3. Point Hindsight at that Postgres DB
  4. Set Hermes memory.provider to hindsight
  5. Set Hermes memory.url to the Hindsight server URL
  6. If Hindsight requires those env vars, set:
      - HINDSIGHT_API_LLM_PROVIDER=none
      - HINDSIGHT_API_LLM_API_KEY=local-dummy-key

  So the key files are:

  - Hermes memory config: hermes/config.yaml:1
  - Hindsight service wiring: docker-compose.yml:32

  I'll keep going on the calendar connector work now.
