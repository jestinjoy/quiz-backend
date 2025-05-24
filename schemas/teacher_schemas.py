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
    total_marks: Optional[int] = None
    start_time: str
    is_active: bool
    status: str
    created_by: int
    created_at: str
    quiz_end_time: Optional[str] = None
    random_order: Optional[bool] = False  # ✅ NEW FIELD
    
class AssignQuestionsSchema(BaseModel):
    quiz_id: int
    question_ids: List[int]

class UserCreateSchema(BaseModel):
    name: str
    email: str
    password: str
    role: str
    college: Optional[str] = None
    batch: Optional[str] = None
    semester: Optional[str] = None
    course: Optional[str] = None  # ✅ Add this line
