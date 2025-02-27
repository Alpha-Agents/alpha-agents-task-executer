
from services.openrouter_client import query_conversation, get_consensus
from services.structured_output_service import StructuredOutputService
from trading_view_extension.queue.sqs_queue_publisher import SQSQueuePublisher
from config import OBSERVATION_MODEL_NAME

class Reasoner:
    def __init__(self, job, system_prompt, questions, image_urls):
        self.system_prompt = system_prompt
        self.questions = questions
        self.image_urls = image_urls
        self.job = job
        # Start conversation history with the system prompt.
        self.conversation_history = [{"role": "system", "content": system_prompt}]
        self.structured_service = StructuredOutputService()
        self.sqs_queue_publisher = SQSQueuePublisher()

    
    async def run_reasoning(self):
        """
        Runs the conversation: for each question, it queries the assistant,
        appends the responses to the history, and finally invokes consensus.
        Returns the final consensus response and parsed trade signal.
        """
        for question in self.questions:
            self.conversation_history.append({"role": "user", "content": question})
            try:
                if question == self.questions[0]:  # This checks if it's the first question
                    # Add special handling for first question if needed
                    response = query_conversation(self.conversation_history, self.image_urls, specified_model=OBSERVATION_MODEL_NAME)
                else:
                    # Handling for subsequent questions
                    response = query_conversation(self.conversation_history, self.image_urls)
            except Exception as e:
                print(f"Error during conversation for question '{question}': {e}")
                response = "Error"
            
            self.conversation_history.append({"role": "assistant", "content": response})

            self.job["question"] = question
            self.job["response"] = response
            self.job["result"] = []
            self.job["status"] = "RUNNING"
            await self.sqs_queue_publisher.publish_task(self.job)

        # After processing all questions, run the consensus step.
        consensus_response = get_consensus(self.conversation_history)
        trade_signal = self.structured_service.get_trade_signal(consensus_response, self.job["asset"])

        return consensus_response, trade_signal

