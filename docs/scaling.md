# Phase scaling and batching

## Goals

The deployment model supports both:

1. multiple domains per request; and
2. multiple instances of the same phase.

These are separate mechanisms and can be tuned independently.

## Batch size

The service contract contains `domains[]`. Every item has a `domain_id` and its input facts.

A request containing 100 domains is still one transport message, but the phase should not be required to process all 100 simultaneously.

`execution.max_concurrent_domains` bounds per-instance domain concurrency.

### What happens when the batch is larger than `max_concurrent_domains`?

The limit is a concurrency limit, not a maximum batch size. For example:

```yaml
execution:
  max_concurrent_domains: 4
```

with 10 domains means:

```text
start:   [D1 D2 D3 D4]  running
         [D5 D6 D7 D8 D9 D10] waiting

when slots free:
         [D5 D6 D7 D8]    running
         [D9 D10]          waiting

finally:
         [D9 D10]          running
```

The service does not create 10 concurrent domain jobs and does not reject the request merely because it contains 10 domains. Remaining domains wait for an execution slot. This keeps memory/CPU pressure bounded per instance.

If the request is so large that its total processing time becomes undesirable, the caller/deployment can choose a smaller batch size. That is an operational decision separate from the phase contract.

## Horizontal replicas

A phase can run as N identical instances. Replica count is **not** part of the phase manifest because it is a deployment property. Configure it in the environment/orchestrator.

This repository includes example deployment configuration in `configs/deployments/`. For local Docker Compose, the desired replica count can be represented there and applied with:

```bash
docker compose up --build --scale html-phase=3
```

The phase containers do not publish their port directly. The HTTP load balancer is the only public entry point and forwards requests to the available `html-phase` replicas.

For Kubernetes, the same concept is represented by `spec.replicas` in a Deployment. For Kafka, the equivalent is simply running multiple consumers of the same phase with the same `group_id`.

## HTTP

```text
                 HTTP load balancer
                  /      |      \
                 /       |       \
        instance-1  instance-2  instance-3
             |          |          |
             +----------+----------+
                        |
                   same phase
```

The load balancer chooses an available replica for each HTTP request. It does not change the phase implementation.

A concrete local setup using HAProxy is documented in `docs/http-load-balancing.md`.

## Kafka

```text
                 input topic
                /     |     \
               /      |      \
          consumer  consumer  consumer
          instance  instance  instance
               \      |      /
                \     |     /
                 output topic
```

Kafka replicas of the same phase share the same consumer group. They must have sufficient topic partitions to make additional replicas useful.

## Uneven replica counts by pipeline depth

Replica count is configured per deployed phase, not globally for the ML package.

For example, a deployment may intentionally use many instances for an early, high-volume phase and fewer instances for a later phase reached by only a subset of domains.

```text
                    domain volume

Phase 1     ████████████████████    12 instances
Phase 2     ███████████              8 instances
Phase 3     ███                      3 instances
Phase 4     █                        1 instance
```

_Those numbers are illustrative, not recommended values._

The ML phase code does not contain assumptions about the number of replicas.

## Resource planning

The useful capacity of a phase depends on:

- average domains per request;
- `max_concurrent_domains`;
- classifier concurrency;
- feature extraction cost;
- explanation cost when enabled;
- number of replicas;
- Kafka partition count when Kafka is used;
- available CPU/GPU/memory.

Measure these independently before choosing replica counts.

## Backpressure

The transport/deployment layer should provide backpressure rather than allowing unbounded in-process work. In particular, a large Kafka backlog should not cause one phase instance to create an unbounded number of threads.
