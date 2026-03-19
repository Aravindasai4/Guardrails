from pydantic import BaseModel
from typing import List, Optional

class ChatCompletionRequest(BaseModel):
    model: str
    input: str
    user_id: Optional[str] = None

class ChatCompletionResponse(BaseModel):
    output: str
    model: str
    rules_triggered: List[str] = []
