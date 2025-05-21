from database import SessionLocal, engine
from models import (
    Base, User, Category, Subcategory,
    Question, Option, Quiz, QuizQuestion,
    AssignedQuiz
)
from datetime import datetime, timedelta
import json

# Create tables
Base.metadata.create_all(bind=engine)

# Create DB session
db = SessionLocal()
now = datetime.now().isoformat()

# ----------------------------
# USERS
# ----------------------------
teacher = User(
    name="Alice Teacher",
    email="alice@school.edu",
    password="pass123",
    role="teacher"
)

student1 = User(
    name="Bob Student",
    email="bob@school.edu",
    password="pass123",
    role="student",
    college="St. George", batch="2022", semester="4"
)

student2 = User(
    name="Carol Student",
    email="carol@school.edu",
    password="pass123",
    role="student",
    college="St. George", batch="2022", semester="4"
)

db.add_all([teacher, student1, student2])
db.commit()
db.refresh(teacher)
db.refresh(student1)
db.refresh(student2)

# ----------------------------
# CATEGORIES & SUBCATEGORIES
# ----------------------------
cat_cs = Category(name="Computer Science")
sub_py = Subcategory(name="Python Basics", category=cat_cs)
sub_dt = Subcategory(name="Data Types", category=cat_cs)
db.add_all([cat_cs, sub_py, sub_dt])
db.commit()

# ----------------------------
# QUESTIONS
# ----------------------------
q1 = Question(
    question_text="What is the output of print(2 + 3)?",
    question_type="MCQ",
    correct_answer="",
    feedback="The output is 5 because '+' adds two integers.",
    created_by=teacher.id,
    created_at=now,
    is_active=True,
    subcategory=sub_py
)
db.add(q1)
db.commit()
db.refresh(q1)

opts1 = [
    Option(text="23", is_correct=False, question_id=q1.id),
    Option(text="5", is_correct=True, question_id=q1.id),
    Option(text="Error", is_correct=False, question_id=q1.id),
]
db.add_all(opts1)

q2 = Question(
    question_text="Python was created by ____.",
    question_type="FILL_BLANK",
    correct_answer=json.dumps(["Guido van Rossum"]),
    feedback="Guido van Rossum created Python in the late 1980s.",
    created_by=teacher.id,
    created_at=now,
    is_active=True,
    subcategory=sub_py
)
db.add(q2)

q3 = Question(
    question_text="Python is a statically typed language.",
    question_type="TRUE_FALSE",
    correct_answer="False",
    feedback="Python is dynamically typed, not statically typed.",
    created_by=teacher.id,
    created_at=now,
    is_active=True,
    subcategory=sub_dt
)
db.add(q3)

q4 = Question(
    question_text="Which of the following are Python data types?",
    question_type="MULTI_SELECT",
    correct_answer="",
    feedback="List, Dictionary, and Integer are valid Python data types.",
    created_by=teacher.id,
    created_at=now,
    is_active=True,
    subcategory=sub_dt
)
db.add(q4)
db.commit()
db.refresh(q4)

opts4 = [
    Option(text="List", is_correct=True, question_id=q4.id),
    Option(text="Dictionary", is_correct=True, question_id=q4.id),
    Option(text="Integer", is_correct=True, question_id=q4.id),
    Option(text="Character", is_correct=False, question_id=q4.id)
]
db.add_all(opts4)
db.commit()

# ----------------------------
# QUIZ
# ----------------------------
quiz = Quiz(
    title="Intro to Python",
    total_marks=20,
    duration_minutes=10,
    created_by=teacher.id,
    created_at=now,
    start_time=(datetime.now() + timedelta(minutes=5)).isoformat(),
    is_active=True
)
db.add(quiz)
db.commit()
db.refresh(quiz)

quiz_questions = [
    QuizQuestion(quiz_id=quiz.id, question_id=q1.id, mark=5),
    QuizQuestion(quiz_id=quiz.id, question_id=q2.id, mark=5),
    QuizQuestion(quiz_id=quiz.id, question_id=q3.id, mark=4),
    QuizQuestion(quiz_id=quiz.id, question_id=q4.id, mark=6),
]
db.add_all(quiz_questions)

# ----------------------------
# ASSIGN QUIZ TO STUDENTS
# ----------------------------
assignment1 = AssignedQuiz(quiz_id=quiz.id, student_id=student1.id)
assignment2 = AssignedQuiz(quiz_id=quiz.id, student_id=student2.id)
db.add_all([assignment1, assignment2])

# Final commit
db.commit()
db.close()
print("✅ Seed data inserted successfully.")

