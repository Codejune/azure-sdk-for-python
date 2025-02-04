# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------

from ._logs_query_client import LogsQueryClient
from ._metrics_query_client import MetricsQueryClient

from ._models import (
    MetricAggregationType,
    LogsBatchQueryResult,
    LogsQueryResult,
    LogsTable,
    LogsTableColumn,
    MetricsResult,
    LogsBatchQuery,
    MetricNamespace,
    MetricNamespaceClassification,
    MetricDefinition,
    TimeSeriesElement,
    Metric,
    MetricValue,
    MetricClass,
    MetricAvailability
)

from ._version import VERSION

__all__ = [
    "MetricAggregationType",
    "LogsQueryClient",
    "LogsBatchQueryResult",
    "LogsQueryResult",
    "LogsTableColumn",
    "LogsTable",
    "LogsBatchQuery",
    "MetricsQueryClient",
    "MetricNamespace",
    "MetricNamespaceClassification",
    "MetricDefinition",
    "MetricsResult",
    "TimeSeriesElement",
    "Metric",
    "MetricValue",
    "MetricClass",
    "MetricAvailability"
]

__version__ = VERSION
