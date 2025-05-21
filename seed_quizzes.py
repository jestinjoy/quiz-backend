from datetime import datetime, timedelta
from database import SessionLocal, engine
from models import Base, User, Category, Subcategory, Question, Option, Quiz, QuizQuestion, AssignedQuiz
import random

# Recreate tables (if needed)
Base.metadata.create_all(bind=engine)

db = SessionLocal()
now = datetime.utcnow()

# ----------------------------
# USERS
# ----------------------------
teacher = User(
    name="Quiz Maker",
    email="quiz@college.edu",
    password="test123",
    role="teacher"
)
student = User(
    name="Test Student",
    email="student@college.edu",
    password="test123",
    role="student",
    college="Test College",
    batch="2023",
    semester="5"
)
db.add_all([teacher, student])
db.commit()
db.refresh(teacher)
db.refresh(student)

# ----------------------------
# CATEGORY & SUBCATEGORY
# ----------------------------
category = Category(name="General Knowledge")
subcategory = Subcategory(name="GK - Level 1", category=category)
db.add_all([category, subcategory])
db.commit()
db.refresh(subcategory)

# ----------------------------
# QUIZZES
# ----------------------------
quizzes = [
    Quiz(
        title="Current Affairs Quiz",
        total_marks=10,
        duration_minutes=5,
        created_by=teacher.id,
        created_at=now.isoformat(),
        start_time=(now - timedelta(minutes=10)).isoformat(),
        is_active=True
    ),
    Quiz(
        title="Science Facts Quiz",
        total_marks=10,
        duration_minutes=5,
        created_by=teacher.id,
        created_at=now.isoformat(),
        start_time=(now - timedelta(minutes=20)).isoformat(),
        is_active=True
    ),
    Quiz(
        title="World Capitals (Upcoming)",
        total_marks=10,
        duration_minutes=5,
        created_by=teacher.id,
        created_at=now.isoformat(),
        start_time=(now + timedelta(minutes=30)).isoformat(),
        is_active=True
    )
]
db.add_all(quizzes)
db.commit()

# ----------------------------
# QUESTIONS & OPTIONS
# ----------------------------
quiz_questions_data = [
    ("Who is the Prime Minister of India?", ["Narendra Modi", "Rahul Gandhi", "Amit Shah", "Manmohan Singh"], 0),
    ("Which planet is known as the Red Planet?", ["Earth", "Mars", "Venus", "Jupiter"], 1),
    ("What is the capital of France?", ["Berlin", "Madrid", "Paris", "Rome"], 2),
    ("Water freezes at what temperature?", ["0°C", "100°C", "10°C", "50°C"], 0),
    ("Who wrote the Indian national anthem?", ["Rabindranath Tagore", "Subhash Chandra Bose", "Mahatma Gandhi", "Nehru"], 0),
    ("What is H2O?", ["Oxygen", "Hydrogen", "Water", "Carbon Dioxide"], 2),
    ("Which gas do plants absorb?", ["Oxygen", "Carbon Dioxide", "Nitrogen", "Hydrogen"], 1),
    ("Which is the largest ocean?", ["Atlantic", "Indian", "Pacific", "Arctic"], 2),
    ("Capital of Australia?", ["Canberra", "Sydney", "Melbourne", "Perth"], 0),
]

question_objects = []
quiz_question_objects = []

for quiz in quizzes:
    selected = random.sample(quiz_questions_data, 3)
    total_marks = 0
    for text, choices, correct_index in selected:
        q = Question(
            question_text=text,
            question_type="MCQ",
            correct_answer="",
            created_by=teacher.id,
            created_at=now.isoformat(),
            is_active=True,
            subcategory_id=subcategory.id
        )
        db.add(q)
        db.commit()
        db.refresh(q)

        opts = []
        for idx, opt_text in enumerate(choices):
            opts.append(Option(
                text=opt_text,
                is_correct=(idx == correct_index),
                question_id=q.id
            ))
        db.add_all(opts)

        qq = QuizQuestion(
            quiz_id=quiz.id,
            question_id=q.id,
            mark=3
        )
        quiz_question_objects.append(qq)
        total_marks += 3

    quiz.total_marks = total_marks  # update total marks
    db.commit()

db.add_all(quiz_question_objects)

# Assign all quizzes to student
assignments = [AssignedQuiz(quiz_id=q.id, student_id=student.id) for q in quizzes]
db.add_all(assignments)

db.commit()
db.close()

print("✅ Seeded 3 quizzes (2 active, 1 upcoming) with questions and assignments.")
