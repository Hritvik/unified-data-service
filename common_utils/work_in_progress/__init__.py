"""
Work-in-progress packages in common_utils.

These packages are not yet ready for production use. They are kept here for
development and experimentation. Import from subpackages explicitly, e.g.:

    from common_utils.work_in_progress.kpi_store import KPIStoreFactory
    from common_utils.work_in_progress.message_queue import MessageQueueFactory
    from common_utils.work_in_progress.events import EventBroadcastService, EventRegistry

Available WIP packages:
- events: Event broadcast, registry, and handlers (Redis Pub/Sub).
- kpi_store: KPI/metric store with support for counters, gauges, histograms,
  derived metrics, and multiple storage backends.
- message_queue: Message queue abstraction with Kafka backend, DLQ, lifecycle,
  and monitoring.
"""
