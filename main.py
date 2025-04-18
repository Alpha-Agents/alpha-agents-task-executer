import asyncio
from config import logger
from trading_view_extension.queue.sqs_queue_consumer import SqsQueueConsumer
from trading_view_extension.queue.sqs_queue_publisher import SQSQueuePublisher
import os
from dotenv import load_dotenv
load_dotenv()
SQS_INPUT_QUEUE_URL = os.getenv("SQS_INPUT_QUEUE_URL")

async def main():
    iqp = SQSQueuePublisher()
    sqs_consumer = SqsQueueConsumer(iqp)
    logger.info(f"Starting SQS Consumer loop on {SQS_INPUT_QUEUE_URL}")

    while True:
        try:
            sqs_consumer.start_polling(SQS_INPUT_QUEUE_URL)
            await asyncio.sleep(float('inf'))  # Just to hold main alive, remove tight link to polling

        except Exception as e:
            logger.error(f"SQS Polling crashed: {e}, restarting in 5 seconds...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    logger.info("Starting standalone ResponseWorker...")

    loop = asyncio.new_event_loop()  # Create a new event loop
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(main())  # Run main coroutine
    except KeyboardInterrupt:
        logger.info("Shutting down ResponseWorker...")
    finally:
        loop.close()  # Ensure event loop is properly closed
