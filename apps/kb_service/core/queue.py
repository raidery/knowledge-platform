"""
Redis Queue 配置和任务定义
"""
from redis import Redis
from rq import Queue

from apps.kb_service.core.config import kb_settings


class QueueManager:
    """队列管理器"""

    def __init__(self, host=None, port=None, db=None, password=None):
        self.host = host or kb_settings.REDIS_HOST
        self.port = port or kb_settings.REDIS_PORT
        self.db = db or kb_settings.REDIS_DB
        self.password = password or kb_settings.REDIS_PASSWORD

        self.redis_conn = Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password
        )
        self.queues = {}

    def get_queue(self, queue_name: str = "default") -> Queue:
        """获取指定名称的队列"""
        if queue_name not in self.queues:
            self.queues[queue_name] = Queue(queue_name, connection=self.redis_conn)
        return self.queues[queue_name]

    def enqueue_task(self, func, *args, queue_name: str = "default", **kwargs):
        """将任务加入队列"""
        queue = self.get_queue(queue_name)
        return queue.enqueue(func, *args, **kwargs)

    def get_job(self, job_id: str):
        """根据作业ID获取作业"""
        return self.redis_conn.hgetall(f"rq:job:{job_id}")

    def get_queue_length(self, queue_name: str = "default"):
        """获取队列长度"""
        queue = self.get_queue(queue_name)
        return len(queue)