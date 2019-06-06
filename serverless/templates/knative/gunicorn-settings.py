import os

# then in the Gunicorn config file:
from prometheus_flask_exporter.multiprocess import GunicornPrometheusMetrics


def when_ready(server):
    GunicornPrometheusMetrics.start_http_server_when_ready(9090)


def child_exit(server, worker):
    GunicornPrometheusMetrics.mark_process_dead_on_child_exit(worker.pid)
