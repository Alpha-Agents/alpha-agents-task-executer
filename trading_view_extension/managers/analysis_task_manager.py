from typing import List
from trading_view_extension.queue.sqs_queue_publisher_interface import IQueuePublisher
from trading_view_extension.queue.sqs_queue_publisher import SQSQueuePublisher

from config import logger

class AnalysisTaskManager:
    """
    Business facade for orchestrating creation and publication of new analysis tasks.
    """
    def __init__(self,queue_publisher: SQSQueuePublisher):
        self.queue_publisher = queue_publisher
        logger.info("AnalysisTaskManager initialized")

    async def publish_analysis_task(self,
                                    user_id: str,
                                    tab_id: str,
                                    job_id: str,
                                    s3_urls: List[str],
                                    agent: str,
                                    action_type: str,
                                    status:str,
                                    websocket_id:str,
                                    filenames:List[str],
                                    file_paths:List[str]) -> None:
        """
        Publish a new analysis job to the “analysis-tasks” queue.
        """
        job = {
            "task_type": "analysis_task",
            "job_id": job_id,
            "user_id": user_id,
            "tab_id": tab_id,
            "s3_urls": s3_urls,
            "agent": agent,
            "action_type": action_type,
            "status": status,
            "websocket_id": websocket_id,
            "filenames" : filenames,
            "file_paths":file_paths
        }
        await self.queue_publisher.publish_task(job)
        logger.info(f"Published analysis task for job {job_id}")