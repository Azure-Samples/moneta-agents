import logging
import json

from gbb.genai_vanilla_agents.conversation import Conversation
from gbb.genai_vanilla_agents.workflow import Workflow

#Vanilla Agents implementation
class VanillaAgenticHandler:
    def __init__(self, db):
        self.db = db

    async def handle_request(self, user_id, chat_id, user_message, load_history, usecase_type, user_data):
        from gbb.agents.fsi_insurance.group_chat import create_group_chat_insurance
        from gbb.agents.fsi_banking.group_chat import create_group_chat_banking

        # Initialize conversation history
        conversation_history = Conversation(messages=[], variables={})

        if load_history is True:
            # Handle load_history request
            conversation_list = []
            chat_histories = user_data.get('chat_histories')
            if chat_histories:
                logging.debug(list(chat_histories.keys()))
                for chat_id_key, conversation_history_data in chat_histories.items():
                    conversation_object = {
                        "name": chat_id_key,
                        "messages": Conversation.from_dict(conversation_history_data).messages
                    }
                    conversation_list.append(conversation_object)
            logging.debug(f"user history: {json.dumps(conversation_list)}")
            return {"status_code": 200, "data": conversation_list}

        # If the API was called with a message, initiate or continue chat
        if chat_id:
            # Continue existing chat
            conversation_data = user_data.get('chat_histories', {}).get(chat_id)
            logging.debug(f"Conversation data={conversation_data}")
            if conversation_data:
                conversation_history = Conversation.from_dict(conversation_data)
            else:
                return {"status_code": 404, "error": "chat_id not found"}
        else:
            # Start a new chat
            chat_id = self.db.generate_chat_id()
            conversation_history = Conversation(messages=[], variables={})
            user_data.setdefault('chat_histories', {})
            user_data['chat_histories'][chat_id] = conversation_history.to_dict()
            self.db.update_user_info(user_id, user_data)

        # Proceed with the conversation
        history_count = len(conversation_history.messages)

        # Select use case group chat
        if 'fsi_insurance' == usecase_type:
            team = create_group_chat_insurance(user_message)
        elif 'fsi_banking' == usecase_type:
            team = create_group_chat_banking(user_message)
        else:
            return {"status_code": 400, "error": "Use case not recognized"}

        workflow = Workflow(askable=team, conversation=conversation_history)
        run_result = workflow.run(user_message)
        logging.info(f"run_result = {run_result}")

        if "agent-error" == run_result:
            return {"status_code": 400, "chat_id": chat_id, "reply": run_result}

        previous_history = user_data['chat_histories'].get(chat_id)
        merged_history = {**previous_history, **workflow.conversation.to_dict()}
        user_data['chat_histories'][chat_id] = merged_history
        self.db.update_user_info(user_id, user_data)

        delta = len(workflow.conversation.messages) - history_count
        new_messages = workflow.conversation.messages[-delta:]

        # Return the chat_id and reply to the client
        return {"status_code": 200, "chat_id": chat_id, "reply": new_messages}