
from services.openrouter_client import query_conversation, get_consensus
from services.structured_output_service import StructuredOutputService
from trading_view_extension.queue.sqs_queue_publisher import SQSQueuePublisher
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
                response = query_conversation(self.conversation_history, self.image_urls)  # 🛠 FIX: await added
            except Exception as e:
                print(f"Error during conversation for question '{question}': {e}")
                response = "Error"
            
            self.conversation_history.append({"role": "assistant", "content": response})

            self.job["question"] = question
            self.job["response"] = response
            self.job["result"] = []
            self.job["status"] = "RUNNING"
            await self.sqs_queue_publisher.publish_task(self.job)

            # self.conversation_history.append({"role": "user", "content": "Understand the images and provide me the current price in numbers of the given stock in the image, dont add any additional text. Example: 100.00, 2563.8, 98345.78"})
            # try:
            #     response = query_conversation(self.conversation_history, self.image_urls) 
            # except Exception as e:
            #     print(f"Error during conversation for question '{question}': {e}")
            #     response = "Error"
            # self.conversation_history.append({"role": "assistant", "content": response})

            # summarized_msg = f""" For your context the above analisys is for {self.job['asset']} stock. The current price of the stock is {response}"""
            # self.conversation_history.append({"role": "user", "content": summarized_msg})

        # After processing all questions, run the consensus step.
        consensus_response = get_consensus(self.conversation_history)
        trade_signal = self.structured_service.get_trade_signal(consensus_response, self.job["asset"])

        return consensus_response, trade_signal

