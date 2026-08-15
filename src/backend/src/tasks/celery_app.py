"""Celery configuration for async tasks."""

import os
from celery import Celery

# Create Celery app
app = Celery('ollp_tasks')

# Configuration from environment
broker_url = os.getenv('REDIS_URL', 'redis://redis:6379/0')
result_backend = os.getenv('REDIS_URL', 'redis://redis:6379/0')

app.conf.broker_url = broker_url
app.conf.result_backend = result_backend
app.conf.broker_connection_retry_on_startup = True

# Worker settings
app.conf.worker_concurrency = int(os.getenv('CELERY_WORKER_CONCURRENCY', '4'))
app.conf.worker_max_tasks_per_child = int(os.getenv('CELERY_WORKER_MAX_TASKS_PER_CHILD', '1000'))
app.conf.task_ignore_result = False
app.conf.task_store_errors_even_if_ignored = True

# Task routing
app.conf.task_routes = {
    'tasks.chapter.*': {'queue': 'tasks'},
    'tasks.outline.*': {'queue': 'tasks'},
    'tasks.export.*': {'queue': 'tasks'},
}

# Default queue
app.conf.task_default_queue = 'tasks'
app.conf.task_default_exchange = 'tasks'
app.conf.task_default_routing_key = 'tasks.default'

# Autodiscover tasks from src.tasks module
import sys
sys.path.insert(0, '/app/src/backend')

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request}')
