# HTTP load balancing for multiple phase instances

This document shows how to run multiple copies of the same phase and expose them through one HTTP address. You do not need to change the phase code, extractor code, or classifier code.

## Why a load balancer is needed

Suppose three identical HTML phase instances are running:

```text
                    +----------------+
client ------------>|    HAProxy     |
                    +-------+--------+
                            |
                 +----------+----------+
                 |          |          |
                 v          v          v
              phase-1    phase-2    phase-3
```

The client sends every request to HAProxy. HAProxy chooses one healthy phase instance and forwards the HTTP request to it. If one instance becomes unhealthy, HAProxy can stop sending requests to it.

The phase instances should not publish their HTTP port to the host. Only HAProxy needs a host port.

## Local Docker Compose example

The repository includes an example HAProxy configuration in `docker/haproxy.cfg` and a deployment-oriented Compose example in `docker-compose.http-scaled.yml`.

The intended flow is:

```bash
docker compose -f docker-compose.http-scaled.yml up --build --scale html-phase=3
```

This creates three `html-phase` containers. The HAProxy container exposes port `8080` on the host and forwards requests to the phase service.

Then a client calls:

```bash
curl http://localhost:8080/health
```

or:

```bash
curl -X POST http://localhost:8080/predict \
  -H 'Content-Type: application/json' \
  -d '{"domains":[{"domain_id":"example.com","facts":{}}]}'
```

## How the Compose service name works

All containers in the Compose network can resolve the service name `html-phase`. When Compose scales that service, Docker's internal DNS exposes the addresses of the replicas. HAProxy uses Docker DNS to discover those addresses.

The HAProxy configuration uses `server-template` so that several possible replica slots can resolve the same service name. This avoids hard-coding container IP addresses, which would be fragile because container IPs can change.

## HAProxy configuration

The important part is:

```haproxy
global
    log stdout format raw local0

resolvers docker
    nameserver dns 127.0.0.11:53
    resolve_retries 3
    timeout resolve 1s
    timeout retry 1s
    hold valid 10s

frontend http_in
    bind *:8080
    default_backend html_phase

backend html_phase
    balance roundrobin
    option httpchk GET /health
    server-template phase 5 html-phase:8080 check resolvers docker init-addr libc,none
```

`balance roundrobin` distributes requests across healthy instances. `option httpchk GET /health` makes HAProxy check the phase health endpoint. `server-template phase 5` provides five possible backend slots; if you run fewer than five replicas, only the addresses that resolve are active.

## Choosing the number of replicas

The replica count is not configured in `config/phases/example_html.yaml`. That file describes the phase itself. Replica count belongs to deployment configuration:

```yaml
deployment:
  phase: html
  transport: http
  replicas: 3
  load_balancer: haproxy
```

For the included local Docker example, the actual number of containers is controlled by the Compose command:

```bash
docker compose -f docker-compose.http-scaled.yml up --build --scale html-phase=3
```

Change `3` to `1`, `2`, `4`, etc. without changing the phase code. In a production orchestrator, the equivalent setting is normally called the replica count (for example, Kubernetes `spec.replicas`).

## Relationship with `max_concurrent_domains`

These settings control different levels of parallelism:

```text
                 HTTP load balancer
                         |
              +----------+----------+
              |          |          |
           replica 1  replica 2  replica 3
              |          |          |
           max 4       max 4       max 4
           domains     domains     domains
```

With 3 replicas and `max_concurrent_domains: 4`, up to 12 domains can be processed concurrently across the deployment, subject to CPU/GPU/memory and classifier concurrency.

A request containing 10 domains sent to one replica does not bypass the per-instance limit: that instance processes at most 4 at a time and queues the remaining work inside the request until slots become available.

## Important production considerations

- Use health checks so unhealthy replicas are removed from rotation.
- Do not expose every phase container directly to the outside network.
- Keep the phase instances identical; deployment configuration should be the only difference.
- Set replica counts according to measured throughput and resource usage.
- If a phase is GPU-bound, make sure the deployment actually schedules enough GPU resources for the chosen number of replicas.
- The load balancer is only responsible for HTTP delivery. It does not know anything about classifiers, phases, or THOR rules.
