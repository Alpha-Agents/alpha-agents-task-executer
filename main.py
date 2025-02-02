import asyncio
from config import logger
from trading_view_extension.queue.sqs_queue_consumer import SqsQueueConsumer
from trading_view_extension.queue.sqs_queue_publisher import SQSQueuePublisher
from trading_view_extension.workers.analysis_worker import AnalysisWorker
from trading_view_extension.queue.sqs_queue_consumer import SqsQueueConsumer
from trading_view_extension.orchestrators.ai_orchestrator import AiOrchestrator
from config import logger

async def main():
    iqp = SQSQueuePublisher()
    sqs_consumer = SqsQueueConsumer()        # handles SQS polling in run_in_executor
    ai_orchestrator = AiOrchestrator(iqp)
    
    analysis_worker = AnalysisWorker(
        queue_consumer=sqs_consumer,
        orchestrator=ai_orchestrator
    )
    await analysis_worker.start_listening()

if __name__ == "__main__":
    logger.info("Starting standalone ResponseWorker...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down ResponseWorker...")
