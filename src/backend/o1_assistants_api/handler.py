import logging
import json

from o1_assistants_api.banking.banking_orchestrator import O1BankingOrchestrator
import o1_assistants_api.banking.banking_tools

class O1Handler:
    def __init__(self, history_db):
        self.logger = logging.getLogger(__name__)
        self.logger.debug("o1 Handler init")

        self.history_db = history_db
        self.orchestrators = {}
        self.orchestrators['fsi_insurance'] = None #not implmented yet
        self.orchestrators['fsi_banking'] = O1BankingOrchestrator()

    def load_history(self, user_id):
        user_data = self.history_db.read_user_info(user_id)
        conversation_list = []
        chat_histories = user_data.get('chat_histories')
        if chat_histories:
            for chat_id_key, conversation_data in chat_histories.items():
                messages = conversation_data.get('messages', [])
                conversation_object = {
                    "name": chat_id_key,
                    "messages": messages
                }
                conversation_list.append(conversation_object)
        self.logger.info(f"user history: {json.dumps(conversation_list)}")
        return {"status_code": 200, "data": conversation_list}

    async def handle_request(self, user_id, chat_id, user_message, load_history, usecase_type, user_data):
        # Additional Use Case - load history
        if load_history is True:
            return self.load_history(user_id=user_id)

        # CORE use case
        conversation_messages = []

        # Continue existing chat if chat_id is provided
        if chat_id:
            conversation_data = user_data.get('chat_histories', {}).get(chat_id)
            self.logger.debug(f"Conversation data={conversation_data}")
            if conversation_data:
                conversation_messages = conversation_data.get('messages', [])
            else:
                return {"status_code": 404, "error": "chat_id not found"}
        else:
            # Start a new chat
            chat_id = self.history_db.generate_chat_id()
            conversation_messages = []
            user_data.setdefault('chat_histories', {})
            user_data['chat_histories'][chat_id] = {'messages': conversation_messages}
            self.history_db.update_user_info(user_id, user_data)

        # Append user message
        conversation_messages.append({'role': 'user', 'name': 'user', 'content': user_message})

        if not usecase_type in self.orchestrators: 
            return {"status_code": 400, "error": "Use case not recognized"}
        
        orchestrator = self.orchestrators[usecase_type]
        reply, metrics = await orchestrator.process_conversation(conversation_messages)

        # Store updated conversation
        conversation_messages.append(reply)
        user_data['chat_histories'][chat_id] = {'messages': conversation_messages}
        # Store updated metrics (tokens)
        user_data['chat_histories'][chat_id]['metrics'] = metrics

        self.history_db.update_user_info(user_id, user_data)

        return {"status_code": 200, "chat_id": chat_id, "reply": [reply]}

