import logging
import json
import os


from foundry.orchestrators.deep_research_orchestrator import DeepResearchOrchestrator
# Foundry orchestrators (hosted agents)
from foundry.orchestrators.foundry_banking_orchestrator import FoundryBankingOrchestrator
from foundry.orchestrators.foundry_insurance_orchestrator import FoundryInsuranceOrchestrator
# OpenAI orchestrators (in-memory agents)
from foundry.orchestrators.open_ai_banking_orchestrator import OpenAIBankingOrchestrator
from foundry.orchestrators.open_ai_insurance_orchestrator import OpenAIInsuranceOrchestrator


class Handler:
    def __init__(self, history_db, use_foundry: bool = None):
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Agentic Handler init")

        self.history_db = history_db
        
        # Determine use_foundry from env variable if not explicitly provided
        if use_foundry is None:
            use_foundry_env = os.getenv("USE_FOUNDRY", "false").lower()
            self.use_foundry = use_foundry_env in ("true", "1", "yes")
        else:
            self.use_foundry = use_foundry
        
        self.orchestrators = {}
        
        # Select orchestrator based on USE_FOUNDRY setting
        if self.use_foundry:
            # Use Foundry orchestrators (hosted agents in Microsoft Foundry)
            self.orchestrators['fsi_insurance'] = FoundryInsuranceOrchestrator()
            self.logger.info("Using FoundryInsuranceOrchestrator for fsi_insurance (Foundry hosted agents)")
            
            self.orchestrators['fsi_banking'] = FoundryBankingOrchestrator()
            self.logger.info("Using FoundryBankingOrchestrator for fsi_banking (Foundry hosted agents)")
        else:
            # Use OpenAI orchestrators (in-memory agents with Azure OpenAI)
            self.orchestrators['fsi_insurance'] = OpenAIInsuranceOrchestrator()
            self.logger.info("Using OpenAIInsuranceOrchestrator for fsi_insurance (Azure OpenAI in-memory agents)")
            
            self.orchestrators['fsi_banking'] = OpenAIBankingOrchestrator()
            self.logger.info("Using OpenAIBankingOrchestrator for fsi_banking (Azure OpenAI in-memory agents)")
        
        self.logger.info(f"Handler initialized with USE_FOUNDRY={self.use_foundry}")

        self.orchestrators['deep_research'] = DeepResearchOrchestrator()

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


    async def handle_request(self, user_id, chat_id, user_message, load_history, usecase_type, user_data, is_deep_research):
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
        
        #TODO not elegant..
        if is_deep_research:
            orchestrator = self.orchestrators['deep_research']
        else:
            orchestrator = self.orchestrators[usecase_type]
        reply = await orchestrator.process_conversation(user_id, conversation_messages, session_id=chat_id)

        # Store updated conversation
        conversation_messages.append(reply)
        user_data['chat_histories'][chat_id] = {'messages': conversation_messages}

        self.history_db.update_user_info(user_id, user_data)

        return {"status_code": 200, "chat_id": chat_id, "reply": [reply]}
