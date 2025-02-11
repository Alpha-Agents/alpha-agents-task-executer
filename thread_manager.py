
import asyncio
import threading
from config import logger, input_tasks_queue
from trading_view_extension.queue.sqs_queue_consumer import SqsQueueConsumer
from trading_view_extension.workers.analysis_worker import AnalysisWorker


def process_message_sync(analysis_worker: AnalysisWorker, job: dict):
    """
    A blocking wrapper that spins up a fresh event loop 
    to run the async process_message code for a single job.
    """
    asyncio.run(analysis_worker.process_message(job))


def delete_message_sync(queue_consumer: SqsQueueConsumer, queue_url: str, job: dict):
    """
    A blocking wrapper for the async delete_message call.
    """
    asyncio.run(queue_consumer.delete_message(queue_url, job))


class ThreadManager:
    """
    Manages dynamic threads. Each job gets its own OS thread.
    Once a thread finishes, it is removed from the registry.
    """
    def __init__(self):
        self.threads = {}
        self.lock = threading.Lock()
        self.thread_count = 0

    def start_thread(self, analysis_worker, queue_consumer, queue_url, job):
        """
        Creates a new thread for the given job and keeps track of it.
        """
        with self.lock:
            self.thread_count += 1
            t_name = f"WorkerThread-{self.thread_count}"

        t = threading.Thread(
            name=t_name,
            target=self.run_job,
            args=(analysis_worker, queue_consumer, queue_url, job),
            daemon=True  # daemon=True means it won't block process exit if main finishes
        )

        with self.lock:
            self.threads[t_name] = t

        t.start()

    def run_job(self, analysis_worker, queue_consumer, queue_url, job):
        """
        The function each thread executes.
        It processes the message, logs errors, and finally deletes the message from SQS.
        """
        msg_id = job.get("MessageId")
        thread_name = threading.current_thread().name
        try:
            logger.info(f"[Threaded] Processing job {msg_id} in {thread_name}")
            process_message_sync(analysis_worker, job)
        except Exception as exc:
            logger.exception(f"[Threaded] Failed to process job {msg_id} in {thread_name}: {exc}")
        finally:
            delete_message_sync(queue_consumer, queue_url, job)
            with self.lock:
                self.threads.pop(thread_name, None)
            logger.info(f"[Threaded] Finished job {msg_id} in {thread_name}")

    def active_thread_count(self) -> int:
        with self.lock:
            return len(self.threads)

    def wait_for_all(self):
        """
        Block until all tracked threads have finished.
        Useful if you want a graceful shutdown after 
        your main loop stops.
        """
        while True:
            with self.lock:
                running_threads = list(self.threads.values())
            if not running_threads:
                break
            for t in running_threads:
                t.join(timeout=0.2)