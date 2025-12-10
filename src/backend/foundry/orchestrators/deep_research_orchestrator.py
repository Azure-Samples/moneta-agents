import os
import math
import asyncio
import logging
import json
import datetime
from typing import List, Optional, Dict, Any, Callable

from abc import ABC, abstractmethod

import azure.ai.inference.aio as aio_inference
import azure.identity.aio as aio_identity
from azure.ai.inference.models import SystemMessage, UserMessage

from dotenv import load_dotenv

# Setup logging.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class ResearchResult:
    def __init__(self, learnings: List[str], visited_urls: List[str]):
        self.learnings = learnings
        self.visited_urls = visited_urls


class DeepResearchOrchestrator:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Deep Research Orchestrator Handler init")
        self.llm_client = self.init_llm_client()  

        
    def init_llm_client(self) -> Any:
        """Initialize the global Azure OpenAI LLM client if not already initialized."""
    
        endpoint_name = os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        credential = aio_identity.DefaultAzureCredential()
        llm_client = aio_inference.ChatCompletionsClient(
            endpoint=f"{endpoint_name.strip('/')}/openai/deployments/{deployment_name}",
            credential=credential,
            credential_scopes=["https://cognitiveservices.azure.com/.default"],
        )
        logger.info("Azure OpenAI LLM client initialized.")
        return llm_client
    

    async def azure_generate(self, prompt: str) -> Dict[str, Any]:
        """
        Calls the Azure OpenAI LLM directly with the given prompt.
        Assumes the LLM's reply is a JSON-formatted string which is then parsed.
        """
        now = datetime.datetime.now() 
        system_prompt = f"""You are an expert researcher. Today is {now}. Follow these instructions when responding:
        - You may be asked to research subjects that is after your knowledge cutoff, assume the user is right when presented with news.
        - The user is a highly experienced analyst, no need to simplify it, be as detailed as possible and make sure your response is correct.
        - Be highly organized.
        - Suggest solutions that I didn't think about.
        - Be proactive and anticipate my needs.
        - Treat me as an expert in all subject matter.
        - Mistakes erode my trust, so be accurate and thorough.
        - Provide detailed explanations, I'm comfortable with lots of detail."""
        
        global total_input_tokens, total_output_tokens

        response = await self.llm_client.complete(
                messages=[
                    SystemMessage(content=system_prompt),
                    UserMessage(content=prompt),
                ],
                response_format="json_object"
        )
        #print(f"azure_generate> raw LLM response= {response}")
        
        # Retrieve usage info from the response (if available).
        usage = response.get("usage", {}) if isinstance(response, dict) else {}
        if usage:
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_input_tokens += prompt_tokens
            total_output_tokens += completion_tokens
        
        try:
            # The response is assumed to have a 'choices' list where we take the first result.
            content = response.choices[0].message.content
            # Remove markdown code fences if present.
            content = content.strip()
            if content.startswith("```json"):
                content = content[len("```json"):].strip()
            if content.endswith("```"):
                content = content[:-3].strip()
            result = json.loads(content)
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            result = {"error": str(e), "raw": content}
        return result


    #############################################
    # Utility Functions
    #############################################
    def trim_prompt(self, prompt: str, max_length: int = 80000) -> str:
        """Trim the prompt if it exceeds the maximum allowed length."""
        return prompt[:max_length]

    async def azure_search(self, query: str, timeout: int = 15000, limit: int = 5) -> Dict[str, Any]:
        """
        Search using Azure OpenAI LLM by formulating a search prompt.
        The LLM is expected to return search results in markdown format.
        The response is expected to be a JSON object with a key "data".
        """
        prompt_text = (
            f"Search for the topic: {query}. "
            "Return the results in markdown format including any URLs. "
            "Output a valid JSON object with a key 'data' that is a list of items, each containing at least 'markdown' and 'url'."
        )
        prompt_text = self.trim_prompt(prompt_text)
        response = await self.azure_generate(prompt_text)
        return response
    

    #############################################
    # SERP Queries
    #############################################
    async def generate_serp_queries(self, query: str, num_queries: int = 3, learnings: Optional[List[str]] = None) -> List[Dict[str, str]]:
        """
        Generate a list of search queries for the given topic.
        The LLM must output ONLY a valid JSON object with a key 'queries' that is a list of objects.
        Each object must have keys 'query' and 'researchGoal'. Do not include any extra text.
        """
        learnings_text = ""
        if learnings:
            learnings_text = "Here are some learnings from previous research:\n" + "\n".join(learnings)
        prompt_text = (
            f"Generate a list of up to {num_queries} unique search queries for the following topic:\n"
            f"<prompt>{query}</prompt>\n"
            f"{learnings_text}\n"
            "Output ONLY a valid JSON object with a key 'queries' that is a list of objects. "
            "Each object must have the keys 'query' and 'researchGoal', with no additional commentary or text."
        )
        prompt_text = self.trim_prompt(prompt_text)
        res = await self.azure_generate(prompt_text)
        queries = res.get("queries", [])
        logger.info(f"Created {len(queries)} queries: {queries}")
        return queries[:num_queries]


    async def process_serp_result(self, query: str, result: Dict[str, Any],
                                num_learnings: int = 3, num_follow_up_questions: int = 3) -> Dict[str, Any]:
        """
        Process the search results to extract detailed learnings and follow-up questions.
        The LLM must output ONLY a valid JSON object with two keys:
        - "learnings": a list of objects, each with a key "learning" (plus optional additional metadata),
        - "followUpQuestions": a list of plain strings representing follow-up research questions.
        No extra commentary or markdown is allowed.
        """
        data = result.get("data", [])
        contents = [self.trim_prompt(item.get("markdown", ""), 25000) for item in data if item.get("markdown")]
        logger.info(f"Processed query '{query}': found {len(contents)} content items")
        contents_formatted = "\n".join([f"<content>\n{content}\n</content>" for content in contents])
        prompt_text = (
            f"For the search results corresponding to the query <query>{query}</query>, extract up to {num_learnings} detailed learnings "
            f"(including entities, numbers, dates, etc.) and up to {num_follow_up_questions} follow-up research questions from the contents below.\n\n"
            f"<contents>\n{contents_formatted}\n</contents>\n"
            "Output ONLY a valid JSON object with keys 'learnings' and 'followUpQuestions'. "
            "In this output, 'learnings' should be a list of objects, each with a key 'learning', and "
            "'followUpQuestions' should be a list of plain strings."
        )
        prompt_text = self.trim_prompt(prompt_text)
        res = await self.azure_generate(prompt_text)
        logger.info(f"Generated learnings: {res.get('learnings', [])}")
        return res


    async def write_final_report(self, prompt: str, learnings: List[str], visited_urls: List[str]) -> str:
        """
        Generate a final detailed report in Markdown using all research learnings and the source URLs.
        The LLM must output ONLY a valid JSON object with a key 'reportMarkdown' that contains the full report in Markdown.
        """
        learnings_str = "\n".join([f"<learning>\n{learning}\n</learning>" for learning in learnings])
        prompt_text = (
            f"Write a final detailed report on the following prompt using all the provided research learnings. "
            "Include as much details as possible (aim for 5+ pages).\n\n"
            f"<prompt>{prompt}</prompt>\n\n"
            f"Learnings:\n<learnings>\n{learnings_str}\n</learnings>\n"
            "Output ONLY a valid JSON object with a key 'reportMarkdown' that contains the full report in Markdown, and no extra text."
        )
        prompt_text = self.trim_prompt(prompt_text)
        res = await self.azure_generate(prompt_text)
        urls_section = "\n\n## Sources\n\n" + "\n".join([f"- {url}" for url in visited_urls])
        final_report = res.get("reportMarkdown", "") + urls_section
        return final_report
    

    #############################################
    # Recursive Deep Research Orchestrator
    #############################################
    async def deep_research(self,
                            query: str,
                            breadth: int,
                            depth: int,
                            learnings: Optional[List[str]] = None,
                            visited_urls: Optional[List[str]] = None,
                            on_progress: Optional[Callable[[Dict[str, Any]], None]] = None) -> 'ResearchResult':
        """
        Recursively research a topic by generating search queries, processing search results,
        and iterating further if more depth is requested.
        """

        if learnings is None:
            learnings = []
        if visited_urls is None:
            visited_urls = []
        
        progress: Dict[str, Any] = {
            "currentDepth": depth,
            "totalDepth": depth,
            "currentBreadth": breadth,
            "totalBreadth": breadth,
            "totalQueries": 0,
            "completedQueries": 0,
            "currentQuery": None,
        }
        
        def report_progress(update: Dict[str, Any]):
            progress.update(update)
            if on_progress:
                on_progress(progress)
        
        # Use an environment variable to set the concurrency limit; default is 2.
        CONCURRENCY_LIMIT = int(os.getenv("AZURE_OPENAI_CONCURRENCY", 2))
        serp_queries = await self.generate_serp_queries(query=query, num_queries=breadth, learnings=learnings)
        if serp_queries:
            progress["totalQueries"] = len(serp_queries)
            progress["currentQuery"] = serp_queries[0].get("query")
        else:
            progress["totalQueries"] = 0

        semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
        
        async def process_query(serp_query: Dict[str, str]) -> 'ResearchResult':
            async with semaphore:
                try:
                    search_result = await self.azure_search(serp_query.get("query"), timeout=15000, limit=5)
                    new_urls = [item.get("url") for item in search_result.get("data", []) if item.get("url")]
                    new_breadth = math.ceil(breadth / 2)
                    new_depth = depth - 1

                    new_learnings_response = await self.process_serp_result(
                        query=serp_query.get("query"),
                        result=search_result,
                        num_learnings=3,
                        num_follow_up_questions=new_breadth
                    )
                    # Convert each learning to a string if it is a dict by extracting the 'learning' field.
                    new_learnings = new_learnings_response.get("learnings", [])
                    new_learnings_text = [
                        x if isinstance(x, str) else x.get("learning", "") for x in new_learnings
                    ]
                    all_learnings = learnings + new_learnings_text
                    all_urls = visited_urls + new_urls
                    
                    if new_depth > 0:
                        report_progress({
                            "currentDepth": new_depth,
                            "currentBreadth": new_breadth,
                            "completedQueries": progress["completedQueries"] + 1,
                            "currentQuery": serp_query.get("query"),
                        })
                        followup = new_learnings_response.get("followUpQuestions", [])
                        # Safely convert each follow-up question to string.
                        followup_questions = ''.join(['\n' + (q if isinstance(q, str) else str(q)) for q in followup])
                        next_query = (
                            f"Previous research goal: {serp_query.get('researchGoal', '')}\n"
                            f"Follow-up research directions: {followup_questions}"
                        ).strip()
                        
                        #Recursion
                        return await self.deep_research(query=next_query,
                                                breadth=new_breadth,
                                                depth=new_depth,
                                                learnings=all_learnings,
                                                visited_urls=all_urls,
                                                on_progress=on_progress)
                    else:
                        report_progress({
                            "currentDepth": 0,
                            "completedQueries": progress["completedQueries"] + 1,
                            "currentQuery": serp_query.get("query"),
                        })
                        return ResearchResult(learnings=all_learnings, visited_urls=all_urls)
                except Exception as e:
                    logger.error(f"Error processing query '{serp_query.get('query')}': {e}")
                    return ResearchResult(learnings=[], visited_urls=[])
        
        tasks = [process_query(serp_query) for serp_query in serp_queries]
        results = await asyncio.gather(*tasks)
        # Merge learnings ensuring each is a string.
        merged_learnings = list(set(
            l if isinstance(l, str) else l.get("learning", "") 
            for res in results for l in res.learnings
        ))
        merged_urls = list(set(url for res in results for url in res.visited_urls))
        
        return ResearchResult(learnings=merged_learnings, visited_urls=merged_urls)


    async def process_conversation(self, user_id, conversation_messages):
        
        logging.info("Deep Research Orchestrator: process_conversation ")
        #TODO clarifications questions before triggering the depp search is NOT yet implemented

        #TODO add back the history?
        
        #deep research user query:
        last_user_message = next(
                    (m["content"] for m in reversed(conversation_messages)
                    if m.get("role") == "user"),
                    None
                )
        logging.info(f"Deep research inquiry={last_user_message}")
        #invoke
        try:
            result = await self.deep_research(last_user_message, breadth=5, depth=3)

            logger.debug("Learnings:", result.learnings)
            logger.debug("Visited URLs:", result.visited_urls)
        except Exception as e:
            logger.error(f"Error in calling deep_research(): {e}")
        
        res_md = await self.write_final_report(last_user_message, result.learnings, result.visited_urls)

        reply = {
            'role': 'assistant',
            'name': 'deep_search',
            'content': res_md
        }

        return reply
    