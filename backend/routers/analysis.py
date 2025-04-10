from fastapi import APIRouter, HTTPException
from core.schemas import UserQuery, ProcessedResponse
from services.agent_selector import AgentSelector
from services.aggregator import ResultAggregator
from services.explainer import ExplainabilityEngine
from core.logging import log_execution, log_exception
import logging
import asyncio

router = APIRouter()
logger = logging.getLogger("analysis_router")

@router.post("/query", response_model=ProcessedResponse)
@log_execution
async def process_query(query: UserQuery):
    logger.info(f"Received request body: {query.dict()}")  
    selector = AgentSelector()
    aggregator = ResultAggregator()
    explainer = ExplainabilityEngine()
    
    try:

        agents, response = await selector.select_agents(query.text)
        if not agents:
            raise HTTPException(status_code=400, detail="No suitable agents found for query")

        # Process query with selected agents
        agent_tasks = [
            asyncio.create_task(agent.process(response["paraphrased_queries"][agent.__class__.__name__], response))
            for agent in agents
        ]
        results = await asyncio.gather(*agent_tasks)

        processed_results = await aggregator.aggregate(results)

        # Generate explanation
        explanation = await explainer.explain(processed_results,user_query=query.text)

        return ProcessedResponse(
            results=results,
            explanation=explanation,
            session_id=query.session_id
        )
    except Exception as e:
        log_exception(logger, e)
        raise HTTPException(status_code=500, detail=str(e))
