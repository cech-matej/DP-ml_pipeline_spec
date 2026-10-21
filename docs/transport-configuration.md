# Transport configuration

`config/transports/http.yaml` and `config/transports/kafka.yaml` describe transport capabilities and required parameter names. They are transport definitions, not per-phase deployment settings.

A phase selects a transport and supplies its own values in `config/phases/*.yaml`: HTTP uses `host` and `port`; Kafka uses `bootstrap_servers`, `input_topic`, `output_topic`, and `group_id` (with optional `client_id`). This keeps the transport type catalog reusable across phases while allowing each phase to use distinct topics and deployment settings.

The current `scripts/run_lexical_http.py` is an HTTP smoke-test entrypoint. It reads the HTTP parameters directly from the lexical phase config. A Kafka phase should use the interchangeable Kafka wrapper/entrypoint rather than this HTTP-only script.
