from sqlalchemy import Column, Integer, String, ForeignKey, Text, Boolean, Enum as SqlEnum
from sqlalchemy.orm import relationship
from database import Base
import enum

class QuizStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # 'student' or 'teacher'
    college = Column(String, nullable=True)
    course = Column(String, nullable=True)
    batch = Column(String, nullable=True)
    semester = Column(String, nullable=True)

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    subcategories = relationship("Subcategory", back_populates="category")

class Subcategory(Base):
    __tablename__ = "subcategories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"))
    category = relationship("Category", back_populates="subcategories")
    questions = relationship("Question", back_populates="subcategory")

class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    question_text = Column(Text, nullable=False)
    question_type = Column(String, nullable=False)  # 'MCQ', 'MULTI_SELECT', 'FILL_BLANK', 'TRUE_FALSE'
    correct_answer = Column(Text)
    feedback = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(String, nullable=False)  # ISO datetime string
    is_active = Column(Boolean, default=True)
    subcategory_id = Column(Integer, ForeignKey("subcategories.id"))
    subcategory = relationship("Subcategory", back_populates="questions")
    options = relationship("Option", back_populates="question")

class Option(Base):
    __tablename__ = "options"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False)
    question_id = Column(Integer, ForeignKey("questions.id"))
    question = relationship("Question", back_populates="options")

class Quiz(Base):
    __tablename__ = "quizzes"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    total_marks = Column(Integer, nullable=True)
    duration_minutes = Column(Integer, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(String, nullable=False)
    start_time = Column(String, nullable=True)
    quiz_end_time = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    status = Column(SqlEnum(QuizStatus), default=QuizStatus.ACTIVE)
    random_order = Column(Boolean, default=False)
    questions = relationship("QuizQuestion", back_populates="quiz")

class QuizQuestion(Base):
    __tablename__ = "quiz_questions"
    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"))
    question_id = Column(Integer, ForeignKey("questions.id"))
    mark = Column(Integer, default=1)
    quiz = relationship("Quiz", back_populates="questions")
    question = relationship("Question")

class AssignedQuiz(Base):
    __tablename__ = "assigned_quizzes"
    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"))
    student_id = Column(Integer, ForeignKey("users.id"))

class StudentQuiz(Base):
    __tablename__ = "student_quizzes"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    quiz_id = Column(Integer, ForeignKey("quizzes.id"))
    started_at = Column(String, nullable=False)
    submitted_at = Column(String, nullable=True)
    total_score = Column(Integer, default=0)
    answers = relationship("StudentAnswer", back_populates="attempt")
    question_order = relationship("StudentQuizQuestionOrder", back_populates="student_quiz")

class StudentAnswer(Base):
    __tablename__ = "student_answers"
    id = Column(Integer, primary_key=True, index=True)
    student_quiz_id = Column(Integer, ForeignKey("student_quizzes.id"))
    question_id = Column(Integer, ForeignKey("questions.id"))
    given_answer = Column(Text)
    is_correct = Column(Boolean, default=False)
    marks_awarded = Column(Integer, default=0)
    attempt = relationship("StudentQuiz", back_populates="answers")

class StudentQuizQuestionOrder(Base):
    __tablename__ = "student_quiz_question_order"
    id = Column(Integer, primary_key=True, index=True)
    student_quiz_id = Column(Integer, ForeignKey("student_quizzes.id"))
    question_id = Column(Integer, ForeignKey("questions.id"))
    position = Column(Integer)  # 0-based index

    student_quiz = relationship("StudentQuiz", back_populates="question_order")
    question = relationship("Question")
