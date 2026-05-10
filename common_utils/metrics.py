"""
Unified metrics infrastructure for all modules.

This module provides a centralized metrics collection system that can be used
by all independent modules while maintaining module independence.
"""

import asyncio
import time
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Union

# Placeholder for prometheus_client
try:
    from prometheus_client import Counter, Gauge, Histogram, Summary, generate_latest
except ImportError:
    # Create placeholder metrics for development
    class Counter:
        def __init__(self, name, documentation=None):
            self.name = name
            self.documentation = documentation
        
        def inc(self, amount=1, labels=None):
            pass
        
        def labels(self, **labels):
            return self
    
    class Gauge:
        def __init__(self, name, documentation=None):
            self.name = name
            self.documentation = documentation
        
        def set(self, value, labels=None):
            pass
        
        def labels(self, **labels):
            return self
    
    class Histogram:
        def __init__(self, name, documentation=None):
            self.name = name
            self.documentation = documentation
        
        def observe(self, amount, labels=None):
            pass
        
        def labels(self, **labels):
            return self
    
    class Summary:
        def __init__(self, name, documentation=None):
            self.name = name
            self.documentation = documentation
        
        def observe(self, amount, labels=None):
            pass
        
        def labels(self, **labels):
            return self
    
    def generate_latest(name, registry, **kwargs):
        return ""

from .logger import get_logger

logger = get_logger(__name__)


class UnifiedMetricsCollector:
    """
    Unified metrics collector that supports both Prometheus and custom metrics.

    This collector provides a single interface for all modules to collect metrics,
    while maintaining the flexibility to use different backend systems.
    """

    def __init__(self) -> None:
        self._prometheus_metrics: Dict[
            str, Union[Counter, Gauge, Histogram, Summary]
        ] = {}
        self._modules: Dict[str, Dict[str, Any]] = {}

    def register_module_metrics(
        self, module_name: str, metrics_definitions: Dict[str, Dict[str, Any]]
    ) -> None:
        """
        Register metrics for a specific module.

        Note: Registration is OPTIONAL. Metrics will be auto-registered on first use
        if not explicitly registered. However, explicit registration is recommended for:
        - Better descriptions (vs generic "Auto-registered {type} metric")
        - Custom histogram buckets
        - Documentation and visibility of all metrics upfront

        Args:
            module_name: Name of the module
            metrics_definitions: Dictionary of metric definitions
        """
        if module_name not in self._modules:
            self._modules[module_name] = {}

        for metric_name, definition in metrics_definitions.items():
            metric_type: str = definition.get("type", "counter")
            description: str = definition.get("description", "")
            labels: List[str] = definition.get("labels", [])

            full_metric_name = f"{module_name}_{metric_name}"

            # Skip if metric is already registered to prevent duplicates
            if full_metric_name in self._prometheus_metrics:
                logger.debug(
                    f"Metric '{full_metric_name}' already registered, skipping"
                )
                continue

            if metric_type == "counter":
                self._prometheus_metrics[full_metric_name] = Counter(
                    full_metric_name, description, labels
                )
            elif metric_type == "gauge":
                self._prometheus_metrics[full_metric_name] = Gauge(
                    full_metric_name, description, labels
                )
            elif metric_type == "histogram":
                # Support custom buckets for histograms (e.g., for size metrics)
                buckets: Optional[List[float]] = definition.get("buckets")
                if buckets is not None:
                    self._prometheus_metrics[full_metric_name] = Histogram(
                        full_metric_name, description, labels, buckets=buckets
                    )
                else:
                    self._prometheus_metrics[full_metric_name] = Histogram(
                        full_metric_name, description, labels
                    )
            elif metric_type == "summary":
                self._prometheus_metrics[full_metric_name] = Summary(
                    full_metric_name, description, labels
                )

            self._modules[module_name][metric_name] = {
                "type": metric_type,
                "description": description,
                "labels": labels,
            }

    def _auto_register_metric(
        self,
        module_name: str,
        metric_name: str,
        metric_type: str,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Auto-register a metric at runtime if it doesn't exist.

        This allows metrics to be created on first use without explicit registration.
        Uses sensible defaults: generic description, labels extracted from first use,
        default histogram buckets.

        For better descriptions and custom buckets, use explicit registration via
        register_module_metrics().

        Args:
            module_name: Name of the module
            metric_name: Name of the metric
            metric_type: Type of metric (counter, gauge, histogram, summary)
            labels: Labels from first use (will be used to determine label names)
        """
        full_metric_name = f"{module_name}_{metric_name}"

        # Skip if already registered
        if full_metric_name in self._prometheus_metrics:
            return

        # Extract label names from the labels dict
        label_names: List[str] = list(labels.keys()) if labels else []

        # Use sensible defaults
        description = f"Auto-registered {metric_type} metric"

        # Register the metric definition first
        if module_name not in self._modules:
            self._modules[module_name] = {}
        self._modules[module_name][metric_name] = {
            "type": metric_type,
            "description": description,
            "labels": label_names,
        }

        # Create the Prometheus metric
        try:
            if metric_type == "counter":
                self._prometheus_metrics[full_metric_name] = Counter(
                    full_metric_name, description, label_names
                )
            elif metric_type == "gauge":
                self._prometheus_metrics[full_metric_name] = Gauge(
                    full_metric_name, description, label_names
                )
            elif metric_type == "histogram":
                self._prometheus_metrics[full_metric_name] = Histogram(
                    full_metric_name, description, label_names
                )
            elif metric_type == "summary":
                self._prometheus_metrics[full_metric_name] = Summary(
                    full_metric_name, description, label_names
                )

            logger.debug(
                f"Auto-registered {metric_type} metric '{full_metric_name}' with labels: {label_names}"
            )
        except Exception as e:
            # If auto-registration fails, log and continue
            logger.debug(f"Failed to auto-register metric '{full_metric_name}': {e}")
            # Remove from modules dict if metric creation failed
            if (
                module_name in self._modules
                and metric_name in self._modules[module_name]
            ):
                del self._modules[module_name][metric_name]

    async def increment_counter(
        self,
        module_name: str,
        metric_name: str,
        value: float = 1.0,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Increment a counter metric for a specific module."""
        try:
            full_name = f"{module_name}_{metric_name}"
            if full_name not in self._prometheus_metrics:
                # Auto-register the metric at runtime
                self._auto_register_metric(module_name, metric_name, "counter", labels)
                # If still not registered after auto-registration attempt, skip
                if full_name not in self._prometheus_metrics:
                    return

            metric = self._prometheus_metrics[full_name]
            if not isinstance(metric, Counter):
                logger.debug(f"Metric '{full_name}' is not a Counter, skipping")
                return

            if labels:
                metric.labels(**labels).inc(value)
            else:
                metric.inc(value)
        except Exception as e:
            # Silently fail - don't let metric tracking disrupt business logic
            full_name = f"{module_name}_{metric_name}"
            expected_labels = (
                self._modules.get(module_name, {})
                .get(metric_name, {})
                .get("labels", [])
            )
            actual_labels = list(labels.keys()) if labels else []

            logger.debug(
                f"Failed to increment counter '{full_name}' with labels: {e}",
                extra={
                    "metric_name": full_name,
                    "metric_type": "counter",
                    "expected_labels": expected_labels,
                    "actual_labels": actual_labels,
                    "labels_dict": labels,
                    "value": value,
                    "error": str(e),
                },
            )
            # Silently fail - do not re-raise

    async def set_gauge(
        self,
        module_name: str,
        metric_name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Set a gauge metric for a specific module."""
        try:
            full_name = f"{module_name}_{metric_name}"
            if full_name not in self._prometheus_metrics:
                # Auto-register the metric at runtime
                self._auto_register_metric(module_name, metric_name, "gauge", labels)
                # If still not registered after auto-registration attempt, skip
                if full_name not in self._prometheus_metrics:
                    return

            metric = self._prometheus_metrics[full_name]
            if not isinstance(metric, Gauge):
                logger.debug(f"Metric '{full_name}' is not a Gauge, skipping")
                return

            if labels:
                metric.labels(**labels).set(value)
            else:
                metric.set(value)
        except Exception as e:
            # Silently fail - don't let metric tracking disrupt business logic
            full_name = f"{module_name}_{metric_name}"
            expected_labels = (
                self._modules.get(module_name, {})
                .get(metric_name, {})
                .get("labels", [])
            )
            actual_labels = list(labels.keys()) if labels else []

            logger.debug(
                f"Failed to set gauge '{full_name}' with labels: {e}",
                extra={
                    "metric_name": full_name,
                    "metric_type": "gauge",
                    "expected_labels": expected_labels,
                    "actual_labels": actual_labels,
                    "labels_dict": labels,
                    "value": value,
                    "error": str(e),
                },
            )
            # Silently fail - do not re-raise

    async def inc_gauge(
        self,
        module_name: str,
        metric_name: str,
        value: float = 1.0,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Increment a gauge metric for a specific module."""
        try:
            full_name = f"{module_name}_{metric_name}"
            if full_name not in self._prometheus_metrics:
                # Auto-register the metric at runtime
                self._auto_register_metric(module_name, metric_name, "gauge", labels)
                # If still not registered after auto-registration attempt, skip
                if full_name not in self._prometheus_metrics:
                    return

            metric = self._prometheus_metrics[full_name]
            if not isinstance(metric, Gauge):
                logger.debug(f"Metric '{full_name}' is not a Gauge, skipping")
                return

            if labels:
                metric.labels(**labels).inc(value)
            else:
                metric.inc(value)
        except Exception as e:
            # Silently fail - don't let metric tracking disrupt business logic
            full_name = f"{module_name}_{metric_name}"
            expected_labels = (
                self._modules.get(module_name, {})
                .get(metric_name, {})
                .get("labels", [])
            )
            actual_labels = list(labels.keys()) if labels else []

            logger.debug(
                f"Failed to increment gauge '{full_name}' with labels: {e}",
                extra={
                    "metric_name": full_name,
                    "metric_type": "gauge",
                    "expected_labels": expected_labels,
                    "actual_labels": actual_labels,
                    "labels_dict": labels,
                    "value": value,
                    "error": str(e),
                },
            )
            # Silently fail - do not re-raise

    async def dec_gauge(
        self,
        module_name: str,
        metric_name: str,
        value: float = 1.0,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Decrement a gauge metric for a specific module."""
        try:
            full_name = f"{module_name}_{metric_name}"
            if full_name not in self._prometheus_metrics:
                # Auto-register the metric at runtime
                self._auto_register_metric(module_name, metric_name, "gauge", labels)
                # If still not registered after auto-registration attempt, skip
                if full_name not in self._prometheus_metrics:
                    return

            metric = self._prometheus_metrics[full_name]
            if not isinstance(metric, Gauge):
                logger.debug(f"Metric '{full_name}' is not a Gauge, skipping")
                return

            if labels:
                metric.labels(**labels).dec(value)
            else:
                metric.dec(value)
        except Exception as e:
            # Silently fail - don't let metric tracking disrupt business logic
            full_name = f"{module_name}_{metric_name}"
            expected_labels = (
                self._modules.get(module_name, {})
                .get(metric_name, {})
                .get("labels", [])
            )
            actual_labels = list(labels.keys()) if labels else []

            logger.debug(
                f"Failed to decrement gauge '{full_name}' with labels: {e}",
                extra={
                    "metric_name": full_name,
                    "metric_type": "gauge",
                    "expected_labels": expected_labels,
                    "actual_labels": actual_labels,
                    "labels_dict": labels,
                    "value": value,
                    "error": str(e),
                },
            )
            # Silently fail - do not re-raise

    async def record_histogram(
        self,
        module_name: str,
        metric_name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record a value in a histogram for a specific module."""
        try:
            full_name = f"{module_name}_{metric_name}"
            if full_name not in self._prometheus_metrics:
                # Auto-register the metric at runtime
                self._auto_register_metric(
                    module_name, metric_name, "histogram", labels
                )
                # If still not registered after auto-registration attempt, skip
                if full_name not in self._prometheus_metrics:
                    return

            metric = self._prometheus_metrics[full_name]
            if not isinstance(metric, Histogram):
                logger.debug(f"Metric '{full_name}' is not a Histogram, skipping")
                return

            if labels:
                metric.labels(**labels).observe(value)
            else:
                metric.observe(value)
        except Exception as e:
            # Silently fail - don't let metric tracking disrupt business logic
            full_name = f"{module_name}_{metric_name}"
            expected_labels = (
                self._modules.get(module_name, {})
                .get(metric_name, {})
                .get("labels", [])
            )
            actual_labels = list(labels.keys()) if labels else []

            logger.debug(
                f"Failed to record histogram '{full_name}' with labels: {e}",
                extra={
                    "metric_name": full_name,
                    "metric_type": "histogram",
                    "expected_labels": expected_labels,
                    "actual_labels": actual_labels,
                    "labels_dict": labels,
                    "value": value,
                    "error": str(e),
                },
            )
            # Silently fail - do not re-raise

    async def record_summary(
        self,
        module_name: str,
        metric_name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record a value in a summary for a specific module."""
        try:
            full_name = f"{module_name}_{metric_name}"
            if full_name not in self._prometheus_metrics:
                # Auto-register the metric at runtime
                self._auto_register_metric(module_name, metric_name, "summary", labels)
                # If still not registered after auto-registration attempt, skip
                if full_name not in self._prometheus_metrics:
                    return

            metric = self._prometheus_metrics[full_name]
            if not isinstance(metric, Summary):
                logger.debug(f"Metric '{full_name}' is not a Summary, skipping")
                return

            if labels:
                metric.labels(**labels).observe(value)
            else:
                metric.observe(value)
        except Exception as e:
            # Silently fail - don't let metric tracking disrupt business logic
            full_name = f"{module_name}_{metric_name}"
            expected_labels = (
                self._modules.get(module_name, {})
                .get(metric_name, {})
                .get("labels", [])
            )
            actual_labels = list(labels.keys()) if labels else []

            logger.debug(
                f"Failed to record summary '{full_name}' with labels: {e}",
                extra={
                    "metric_name": full_name,
                    "metric_type": "summary",
                    "expected_labels": expected_labels,
                    "actual_labels": actual_labels,
                    "labels_dict": labels,
                    "value": value,
                    "error": str(e),
                },
            )
            # Silently fail - do not re-raise

    def get_prometheus_metrics(self) -> bytes:
        """Get Prometheus-formatted metrics."""
        return generate_latest()


# Global metrics collector instance
_metrics_collector = UnifiedMetricsCollector()


def get_metrics_collector() -> UnifiedMetricsCollector:
    """Get the global metrics collector instance."""
    return _metrics_collector


def get_metric_expected_labels(module_name: str, metric_name: str) -> List[str]:
    """Get the expected labels for a metric."""
    return (
        _metrics_collector._modules.get(module_name, {})
        .get(metric_name, {})
        .get("labels", [])
    )


def filter_and_validate_metric_labels(
    module_name: str, metric_name: str, labels: Optional[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Filter and validate labels for a metric in a single operation.

    This function:
    1. If metric is registered: Filters labels to only include registered ones and validates required labels
    2. If metric is not registered: Returns all labels as-is (for auto-registration)
    3. Returns the filtered labels

    Args:
        module_name: Name of the module
        metric_name: Name of the metric
        labels: Labels to filter and validate (can be None)

    Returns:
        Filtered dictionary with only expected labels, or all labels if metric not registered, or None if input was None
    """
    if labels is None:
        return None

    expected_labels = get_metric_expected_labels(module_name, metric_name)

    # If metric is not registered yet, return all labels as-is for auto-registration
    if not expected_labels:
        # Check if metric exists in Prometheus metrics (might be registered but not in modules dict)
        full_name = f"{module_name}_{metric_name}"
        if full_name not in _metrics_collector._prometheus_metrics:
            # Metric not registered - return all labels for auto-registration
            return labels
        else:
            # Metric exists but has no labels defined - return empty dict
            return {}

    # Metric is registered - filter to only include expected labels
    filtered = {k: v for k, v in labels.items() if k in expected_labels}

    # Log if labels were filtered out (for debugging)
    extra_labels = set(labels.keys()) - set(expected_labels)
    if extra_labels:
        logger.debug(
            f"Metric '{module_name}_{metric_name}' filtered out extra labels: {extra_labels}. "
            f"Expected: {expected_labels}, Passed: {list(labels.keys())}"
        )

    # Validate that all required labels are present
    actual_labels = list(filtered.keys())
    missing_labels = set(expected_labels) - set(actual_labels)
    if missing_labels:
        raise ValueError(
            f"Metric '{module_name}_{metric_name}' is missing required labels: {missing_labels}. "
            f"Expected: {expected_labels}, Got: {actual_labels}"
        )

    return filtered


# Centralized metrics registration
_module_metrics_registry: Dict[str, Dict[str, Dict[str, Any]]] = {}


def register_module_metrics(
    module_name: str, metrics_definitions: Dict[str, Dict[str, Any]]
) -> None:
    """
    Register metrics for a module.

    Note: Registration is OPTIONAL. Metrics will be auto-registered on first use
    if not explicitly registered. However, explicit registration is recommended for:
    - Better descriptions (vs generic "Auto-registered {type} metric")
    - Custom histogram buckets
    - Documentation and visibility of all metrics upfront
    """
    # Skip if module metrics are already registered to prevent duplicates
    if module_name in _module_metrics_registry:
        logger.debug(f"Module '{module_name}' metrics already registered, skipping")
        return

    # Store in centralized registry
    _module_metrics_registry[module_name] = metrics_definitions
    # Also register with the collector
    _metrics_collector.register_module_metrics(module_name, metrics_definitions)


def get_registered_module_metrics() -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Get all registered module metrics."""
    return _module_metrics_registry.copy()


def ensure_all_metrics_registered() -> None:
    """Ensure all metrics from the registry are registered with the collector."""
    for module_name, metrics_definitions in _module_metrics_registry.items():
        _metrics_collector.register_module_metrics(module_name, metrics_definitions)


async def track_metric_internal(
    module_name: str,
    metric_type: str,
    metric_name: str,
    value: float = 1.0,
    labels: Optional[Dict[str, str]] = None,
    operation: str = "set",  # New parameter: "set", "inc", "dec"
) -> None:
    """
    Track a metric for a specific module.

    This function automatically filters labels to only include those registered
    for the metric, ensuring that extra labels are silently ignored.
    """
    try:
        # Filter and validate labels in a single operation
        filtered_labels = filter_and_validate_metric_labels(
            module_name, metric_name, labels
        )

        # Use filtered labels for all metric operations
        if metric_type == "counter":
            await _metrics_collector.increment_counter(
                module_name, metric_name, value, filtered_labels
            )
        elif metric_type == "gauge":
            if operation == "inc":
                await _metrics_collector.inc_gauge(
                    module_name, metric_name, value, filtered_labels
                )
            elif operation == "dec":
                await _metrics_collector.dec_gauge(
                    module_name, metric_name, value, filtered_labels
                )
            else:  # default to "set"
                await _metrics_collector.set_gauge(
                    module_name, metric_name, value, filtered_labels
                )
        elif metric_type == "histogram":
            await _metrics_collector.record_histogram(
                module_name, metric_name, value, filtered_labels
            )
        elif metric_type == "summary":
            await _metrics_collector.record_summary(
                module_name, metric_name, value, filtered_labels
            )
    except Exception as e:
        # Silently fail - don't let metric tracking disrupt business logic
        # Log at debug level to avoid noise, but include details for troubleshooting
        full_metric_name = f"{module_name}_{metric_name}"
        expected_labels = (
            _metrics_collector._modules.get(module_name, {})
            .get(metric_name, {})
            .get("labels", [])
        )
        actual_labels = list(labels.keys()) if labels else []

        logger.debug(
            f"Failed to track metric '{full_metric_name}' (type: {metric_type}): {e}",
            extra={
                "metric_name": full_metric_name,
                "metric_type": metric_type,
                "expected_labels": expected_labels,
                "actual_labels": actual_labels,
                "labels_dict": labels,
                "value": value,
                "error": str(e),
            },
        )
        # Silently fail - do not re-raise


def track_metric_sync(
    module_name: str,
    metric_type: str,
    metric_name: str,
    value: float = 1.0,
    labels: Optional[Dict[str, str]] = None,
    operation: str = "set",
) -> None:
    """
    Safely track metrics from sync context without creating unawaited tasks.

    This function should be used in sync contexts where we can't await.
    It will either track the metric if there's a running event loop (by scheduling
    it properly) or skip it if there's no event loop.

    Args:
        module_name: Name of the module
        metric_type: Type of metric (counter, gauge, histogram, summary)
        metric_name: Name of the metric
        value: Metric value
        labels: Optional labels
        operation: Operation for gauge metrics (set, inc, dec)
    """
    try:
        # Try to get the running event loop
        try:
            loop = asyncio.get_running_loop()
            # There's a running loop - schedule the task properly
            # Use call_soon_threadsafe if needed, but for now just skip
            # to avoid creating unawaited tasks
            logger.debug(
                f"Skipping metric tracking from sync context with running loop: {module_name}.{metric_name}"
            )
        except RuntimeError:
            # No running loop - safe to create a new one temporarily
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    # Loop is closed, can't use it
                    logger.debug(
                        f"Skipping metric tracking - event loop is closed: {module_name}.{metric_name}"
                    )
                else:
                    # Use existing loop
                    loop.run_until_complete(
                        track_metric_internal(
                            module_name,
                            metric_type,
                            metric_name,
                            value,
                            labels,
                            operation,
                        )
                    )
            except RuntimeError:
                # No event loop at all - skip metrics
                logger.debug(
                    f"Skipping metric tracking - no event loop: {module_name}.{metric_name}"
                )
    except Exception as e:
        # Don't let metrics break the application
        logger.debug(f"Error tracking metric safely: {e}")


async def track_metric_async(
    module_name: str,
    metric_type: str,
    metric_name: str,
    value: float = 1.0,
    labels: Optional[Dict[str, str]] = None,
    operation: str = "set",
) -> None:
    """
    Safely track metrics from async context.

    This is a wrapper around track_metric that catches exceptions
    to prevent metrics from breaking the application.

    Args:
        module_name: Name of the module
        metric_type: Type of metric (counter, gauge, histogram, summary)
        metric_name: Name of the metric
        value: Metric value
        labels: Optional labels
        operation: Operation for gauge metrics (set, inc, dec)
    """
    try:
        await track_metric_internal(
            module_name, metric_type, metric_name, value, labels, operation
        )
    except Exception as e:
        # Don't let metrics break the application
        logger.debug(f"Error tracking metric safely: {e}")


async def inc_gauge_metric(
    module_name: str,
    metric_name: str,
    value: float = 1.0,
    labels: Optional[Dict[str, str]] = None,
) -> None:
    """Increment a gauge metric for a specific module."""
    await track_metric_internal(module_name, "gauge", metric_name, value, labels, "inc")


async def dec_gauge_metric(
    module_name: str,
    metric_name: str,
    value: float = 1.0,
    labels: Optional[Dict[str, str]] = None,
) -> None:
    """Decrement a gauge metric for a specific module."""
    await track_metric_internal(module_name, "gauge", metric_name, value, labels, "dec")


def track_inflight_requests_dynamic(
    module_name: str,
    metric_name: str = "inflight_requests",
    labels: Optional[Dict[str, str]] = None,
    extract_labels: Optional[Dict[str, str]] = None,
):
    """
    Enhanced decorator to track in-flight requests with both static and dynamic labels.

    Args:
        module_name: Name of the module (e.g., "rest_client", "model_bridge")
        metric_name: Name of the metric (defaults to "inflight_requests")
        labels: Static labels with fixed values (e.g., {"operation": "http_post", "method": "POST"})
        extract_labels: Dynamic labels with key=path pairs (e.g., {"client": "client_identifier", "path": "path_identifier"})
                       The path should match the parameter name in the function signature

    Example:
        @track_inflight_requests_dynamic(
            "rest_client",
            labels={"operation": "http_post", "method": "POST"},
            extract_labels={"client": "client_identifier", "path": "path_identifier"}
        )
        async def post(self, client_identifier: str, path_identifier: str, ...):
            # This will create labels: operation="http_post", method="POST", client="echo", path="reflect-anything"
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Start with static labels
            final_labels = labels.copy() if labels else {}

            # Extract dynamic labels from function arguments
            if extract_labels:
                for label_key, param_name in extract_labels.items():
                    if param_name in kwargs:
                        final_labels[label_key] = str(kwargs[param_name])
                    else:
                        # Try to find in args by parameter position (basic support)
                        # This is a simplified approach - for more complex cases, use inspect.signature
                        try:
                            import inspect

                            sig = inspect.signature(func)
                            param_names = list(sig.parameters.keys())
                            if param_name in param_names:
                                param_index = param_names.index(param_name)
                                if param_index < len(args):
                                    final_labels[label_key] = str(args[param_index])
                        except Exception:
                            # If we can't extract the value, skip this label
                            pass

            # Increment on request start
            await inc_gauge_metric(module_name, metric_name, 1.0, final_labels)

            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                # Decrement on request end (guaranteed execution)
                await dec_gauge_metric(module_name, metric_name, 1.0, final_labels)

        return wrapper

    return decorator


def track_inflight_requests_sync_dynamic(
    module_name: str,
    metric_name: str = "inflight_requests",
    labels: Optional[Dict[str, str]] = None,
    extract_labels: Optional[Dict[str, str]] = None,
):
    """
    Synchronous version of track_inflight_requests_dynamic decorator.

    Note: This creates a new event loop for metric operations, which may not be ideal
    for high-performance scenarios. Consider using the async version when possible.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Start with static labels
            final_labels = labels.copy() if labels else {}

            # Extract dynamic labels from function arguments
            if extract_labels:
                for label_key, param_name in extract_labels.items():
                    if param_name in kwargs:
                        final_labels[label_key] = str(kwargs[param_name])
                    else:
                        # Try to find in args by parameter position
                        try:
                            import inspect

                            sig = inspect.signature(func)
                            param_names = list(sig.parameters.keys())
                            if param_name in param_names:
                                param_index = param_names.index(param_name)
                                if param_index < len(args):
                                    final_labels[label_key] = str(args[param_index])
                        except Exception:
                            pass

            # Increment on request start - use safe sync version
            track_metric_sync(
                module_name, "gauge", metric_name, 1.0, final_labels, "inc"
            )

            try:
                result = func(*args, **kwargs)
                return result
            finally:
                # Decrement on request end - use safe sync version
                track_metric_sync(
                    module_name, "gauge", metric_name, 1.0, final_labels, "dec"
                )

        return wrapper

    return decorator


def track_inflight_requests(
    module_name: str,
    metric_name: str = "inflight_requests",
    **labels: Any,
):
    """
    Decorator to track in-flight requests using gauge metrics.

    Automatically increments the gauge when a request starts and decrements when it ends.

    Args:
        module_name: Name of the module (e.g., "rest_client", "model_bridge")
        metric_name: Name of the metric (defaults to "inflight_requests")
        **labels: Additional labels to apply to the metric

    Example:
        @track_inflight_requests("rest_client", endpoint="/api/v1/users")
        async def get_users():
            # This will increment inflight_requests on entry
            # and decrement on exit (even if exception occurs)
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Increment on request start
            await inc_gauge_metric(module_name, metric_name, 1.0, labels)

            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                # Decrement on request end (guaranteed execution)
                await dec_gauge_metric(module_name, metric_name, 1.0, labels)

        return wrapper

    return decorator


def track_inflight_requests_sync(
    module_name: str,
    metric_name: str = "inflight_requests",
    **labels: Any,
):
    """
    Synchronous version of track_inflight_requests decorator.

    Note: This creates a new event loop for metric operations, which may not be ideal
    for high-performance scenarios. Consider using the async version when possible.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Increment on request start - use safe sync version
            track_metric_sync(module_name, "gauge", metric_name, 1.0, labels, "inc")

            try:
                result = func(*args, **kwargs)
                return result
            finally:
                # Decrement on request end - use safe sync version
                track_metric_sync(module_name, "gauge", metric_name, 1.0, labels, "dec")

        return wrapper

    return decorator


def track_async_metrics(metric_tracker: Callable, **labels: Any):
    """
    Decorator to track metrics for async functions.

    Args:
        metric_tracker: Function to track metrics
        **labels: Labels to apply to all metrics

    Returns:
        Decorated function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                # Check if metric_tracker expects specific parameters
                import inspect

                sig = inspect.signature(metric_tracker)
                param_names = list(sig.parameters.keys())

                if (
                    len(param_names) >= 2
                    and param_names[0] == "operation"
                    and param_names[1] == "collection"
                ):
                    # For functions like track_database_operation that expect operation, collection, status, duration
                    await metric_tracker(
                        labels.get("operation", "unknown"),
                        labels.get("collection", "unknown"),
                        "success",
                        time.time() - start_time,
                    )
                else:
                    # For functions that expect status, duration, **labels
                    await metric_tracker("success", time.time() - start_time, **labels)
                return result
            except Exception:
                # Check if metric_tracker expects specific parameters
                import inspect

                sig = inspect.signature(metric_tracker)
                param_names = list(sig.parameters.keys())

                if (
                    len(param_names) >= 2
                    and param_names[0] == "operation"
                    and param_names[1] == "collection"
                ):
                    # For functions like track_database_operation that expect operation, collection, status, duration
                    await metric_tracker(
                        labels.get("operation", "unknown"),
                        labels.get("collection", "unknown"),
                        "error",
                        time.time() - start_time,
                    )
                else:
                    # For functions that expect status, duration, **labels
                    await metric_tracker("error", time.time() - start_time, **labels)
                raise

        return wrapper

    return decorator


def track_sync_metrics(metric_logger: Optional[Callable] = None, **labels: Any):
    """
    Generic decorator to track metrics for sync function execution.
    This decorator should ONLY be used on sync functions.

    Note: This decorator logs metrics but does not track them asynchronously
    to avoid crossing async/sync boundaries. For proper metric tracking,
    consider using track_async_metrics on async functions instead.

    Args:
        metric_logger: Optional function to call for custom logging
        **labels: Labels to include in the metric info
    """

    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            raise ValueError(
                f"track_sync_metrics decorator can only be used on sync functions. "
                f"Function {func.__name__} is async. Use track_async_metrics instead."
            )

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                logger.error(f"Error in {func.__name__}: {e}")
                raise
            finally:
                duration = time.time() - start_time

                # Log metrics instead of tracking them asynchronously
                # This avoids crossing async/sync boundaries
                metric_info = {
                    "status": status,
                    "duration": duration,
                    "function": func.__name__,
                    **labels,
                }

                if metric_logger:
                    try:
                        metric_logger(metric_info)
                    except Exception as e:
                        logger.error(f"Failed to log metrics for {func.__name__}: {e}")
                else:
                    logger.info(f"Sync function metrics: {metric_info}")

        return sync_wrapper

    return decorator


def track_duration(
    module_name: str,
    metric_name: str,
    **labels: Any,
) -> Callable:
    """
    Generic decorator to track execution duration as a histogram metric.

    This decorator can be used on any async function to automatically track
    its execution time as a histogram metric. It works across all modules.

    Args:
        module_name: Name of the module (e.g., "ticket_resolution", "model_bridge")
        metric_name: Name of the histogram metric to record duration to
        **labels: Additional labels to apply to the metric

    Example:
        @track_duration("ticket_resolution", "intent_detection_duration_seconds", intent_type="intent_classification")
        async def classify_intent(...):
            # Function execution time will be automatically tracked
            pass

        @track_duration("model_bridge", "invocation_duration_seconds", model_name="gpt-4")
        async def invoke_model(...):
            # Function execution time will be automatically tracked
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time: float = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration: float = time.time() - start_time
                await track_metric_internal(
                    module_name, "histogram", metric_name, duration, labels
                )

        return wrapper

    return decorator


def track_request_metrics(
    module_name: str,
    duration_metric_name: Optional[str] = None,
    inflight_metric_name: str = "inflight_requests",
    **labels: Any,
) -> Callable:
    """
    Combined decorator to track both in-flight requests and execution duration.

    This decorator combines the functionality of track_inflight_requests and
    track_duration into a single decorator for convenience. It can be used
    on any async endpoint to automatically track both metrics.

    Args:
        module_name: Name of the module (e.g., "ticket_resolution", "model_bridge")
        duration_metric_name: Name of the histogram metric to record duration to.
                            If None, duration tracking is disabled.
        inflight_metric_name: Name of the gauge metric for in-flight requests
                             (defaults to "inflight_requests")
        **labels: Additional labels to apply to both metrics

    Example:
        @track_request_metrics(
            "ticket_resolution",
            duration_metric_name="intent_detection_duration_seconds",
            intent_type="intent_classification",
            operation="intent_detection_evaluation"
        )
        async def evaluate(...):
            # Both in-flight requests and duration will be tracked
            pass

        # Track only in-flight requests (no duration)
        @track_request_metrics("ticket_resolution", operation="file_upload")
        async def upload_file(...):
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Increment in-flight requests (labels will be automatically filtered)
            await inc_gauge_metric(module_name, inflight_metric_name, 1.0, labels)

            start_time: float = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                # Decrement in-flight requests (labels will be automatically filtered)
                await dec_gauge_metric(module_name, inflight_metric_name, 1.0, labels)

                # Track duration if metric name is provided (labels will be automatically filtered)
                if duration_metric_name:
                    duration: float = time.time() - start_time
                    await track_metric_internal(
                        module_name, "histogram", duration_metric_name, duration, labels
                    )

        return wrapper

    return decorator


@asynccontextmanager
async def request_timer(
    module_name: str, metric_name: str, **labels: Any
) -> AsyncGenerator[None, None]:
    """Context manager for timing operations."""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        await track_metric_internal(
            module_name, "histogram", metric_name, duration, labels
        )


# Convenience functions for common_utils metric types
async def track_http_request(
    module_name: str, method: str, endpoint: str, status: int, duration: float
) -> None:
    """Track HTTP request metrics."""
    labels = {"method": method, "endpoint": endpoint, "status": str(status)}
    await track_metric_internal(
        module_name, "counter", "http_requests_total", 1, labels
    )
    await track_metric_internal(
        module_name,
        "histogram",
        "http_request_duration_seconds",
        duration,
        {"method": method, "endpoint": endpoint},
    )
