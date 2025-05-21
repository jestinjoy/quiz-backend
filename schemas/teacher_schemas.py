from pydantic import BaseModel
from typing import List, Optional

class OptionCreateSchema(BaseModel):
    text: str
    is_correct: bool

class QuestionCreateSchema(BaseModel):
    question_text: str
    question_type: str  # Example: "MCQ", "FITB"
    correct_answer: Optional[str] = None  # Only if not MCQ
    feedback: Optional[str] = None
    subcategory_id: int
    created_by: int  # User ID of teacher
    created_at: str  # ISO format timestamp string
    is_active: Optional[bool] = True
    options: Optional[List[OptionCreateSchema]] = None  # Required if MCQ

class QuizCreateSchema(BaseModel):
    title: str
    duration_minutes: int
    total_marks: int
    start_time: str
    created_at: str
    created_by: int
    is_active: bool
    status: Optional[str] = "ACTIVE"
    
class AssignQuestionsSchema(BaseModel):
    quiz_id: int
    question_ids: List[int]