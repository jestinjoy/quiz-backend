from database import SessionLocal, engine
from models import Base, User, Category, Subcategory, Question, Option, Quiz, QuizQuestion, AssignedQuiz
from datetime import datetime, timedelta

# Create tables (if not already done)
Base.metadata.create_all(bind=engine)

# Create session
db = SessionLocal()
now = datetime.utcnow().isoformat()

# Get teacher and student (assuming they're already added)
teacher = db.query(User).filter_by(role="teacher").first()
students = db.query(User).filter_by(role="student").all()

if not teacher:
    print("⚠ No teacher found. Please seed teacher first.")
    exit()

# ----------------------------
# CATEGORY & SUBCATEGORY
# ----------------------------
cat_cs = db.query(Category).filter_by(name="Computer Science").first()
if not cat_cs:
    cat_cs = Category(name="Computer Science")
    db.add(cat_cs)
    db.commit()
    db.refresh(cat_cs)

sub_c = Subcategory(name="C Programming", category=cat_cs)
db.add(sub_c)
db.commit()
db.refresh(sub_c)

# ----------------------------
# QUESTIONS (MCQ)
# ----------------------------
questions_data = [
    {
        "text": "Which of the following is a valid C identifier?",
        "options": ["2variable", "_temp", "int", "#main"],
        "correct": "_temp"
    },
    {
        "text": "What is the output of: printf(\"%d\", 10+5*2);",
        "options": ["30", "20", "25", "None of the above"],
        "correct": "20"
    },
    {
        "text": "Which header file is required for printf()?",
        "options": ["stdlib.h", "conio.h", "stdio.h", "string.h"],
        "correct": "stdio.h"
    },
    {
        "text": "Which operator is used to access value at address stored in a pointer?",
        "options": ["&", "*", "->", "."],
        "correct": "*"
    },
    {
        "text": "What is the keyword to declare a constant in C?",
        "options": ["const", "define", "constant", "immutable"],
        "correct": "const"
    }
]

quiz_questions = []
total_marks = 0

for qdata in questions_data:
    q = Question(
        question_text=qdata["text"],
        question_type="MCQ",
        correct_answer="",  # Not used for MCQ
        created_by=teacher.id,
        created_at=now,
        is_active=True,
        subcategory_id=sub_c.id
    )
    db.add(q)
    db.commit()
    db.refresh(q)

    opts = [
        Option(text=opt, is_correct=(opt == qdata["correct"]), question_id=q.id)
        for opt in qdata["options"]
    ]
    db.add_all(opts)
    db.commit()

    quiz_questions.append(q)
    total_marks += 2  # Assume 2 marks each

# ----------------------------
# CREATE QUIZ
# ----------------------------
quiz = Quiz(
    title="Basics of C Programming",
    total_marks=total_marks,
    duration_minutes=10,
    created_by=teacher.id,
    created_at=now,
    start_time=(datetime.utcnow() + timedelta(minutes=2)).isoformat(),
    is_active=True,
    status="ACTIVE"
)
db.add(quiz)
db.commit()
db.refresh(quiz)

# Add questions to quiz
quiz_question_links = [
    QuizQuestion(quiz_id=quiz.id, question_id=q.id, mark=2)
    for q in quiz_questions
]
db.add_all(quiz_question_links)

# Assign to all students
assignments = [
    AssignedQuiz(quiz_id=quiz.id, student_id=student.id)
    for student in students
]
db.add_all(assignments)

db.commit()
db.close()
print("✅ C Programming quiz added with 5 questions.")
