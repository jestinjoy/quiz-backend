from datetime import datetime, timedelta, timezone
from database import SessionLocal, engine
from models import Base, User, Category, Subcategory, Question, Option, Quiz, QuizQuestion, AssignedQuiz

# Step 1: Create tables if not already created
Base.metadata.create_all(bind=engine)
db = SessionLocal()
now = datetime.now(timezone.utc).isoformat()

# Step 2: Get or create teacher
teacher = db.query(User).filter_by(email="alice@school.edu").first()
if not teacher:
    teacher = User(
        name="Alice Teacher",
        email="alice@school.edu",
        password="pass123",
        role="teacher"
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)

# Step 3: Get or create student
student = db.query(User).filter_by(email="bob@school.edu").first()
if not student:
    student = User(
        name="Bob Student",
        email="bob@school.edu",
        password="pass123",
        role="student",
        college="SGC", batch="2022", semester="4"
    )
    db.add(student)
    db.commit()
    db.refresh(student)

# Step 4: Create category & subcategory
math_cat = Category(name="Mathematics")
binomial_sub = Subcategory(name="Binomial Theorem", category=math_cat)
db.add_all([math_cat, binomial_sub])
db.commit()
db.refresh(binomial_sub)

# Step 5: Create questions
q1 = Question(
    question_text="What is the coefficient of x^2 in the expansion of (1 + x)^5?",
    question_type="MCQ",
    correct_answer="10",
    created_by=teacher.id,
    created_at=now,
    is_active=True,
    subcategory_id=binomial_sub.id
)
q2 = Question(
    question_text="How many terms are there in the expansion of (a + b)^n?",
    question_type="MCQ",
    correct_answer="n + 1",
    created_by=teacher.id,
    created_at=now,
    is_active=True,
    subcategory_id=binomial_sub.id
)
q3 = Question(
    question_text="In the expansion of (x + y)^4, what is the sum of all coefficients?",
    question_type="MCQ",
    correct_answer="16",
    created_by=teacher.id,
    created_at=now,
    is_active=True,
    subcategory_id=binomial_sub.id
)

db.add_all([q1, q2, q3])
db.commit()
db.refresh(q1)
db.refresh(q2)
db.refresh(q3)

# Step 6: Add options
options = [
    Option(text="10", is_correct=True, question_id=q1.id),
    Option(text="5", is_correct=False, question_id=q1.id),
    Option(text="15", is_correct=False, question_id=q1.id),

    Option(text="n", is_correct=False, question_id=q2.id),
    Option(text="n + 1", is_correct=True, question_id=q2.id),
    Option(text="2n", is_correct=False, question_id=q2.id),

    Option(text="8", is_correct=False, question_id=q3.id),
    Option(text="16", is_correct=True, question_id=q3.id),
    Option(text="32", is_correct=False, question_id=q3.id),
]
db.add_all(options)

# Step 7: Create quiz
quiz = Quiz(
    title="Quiz on Binomial Theorem",
    total_marks=15,
    duration_minutes=5,
    created_by=teacher.id,
    created_at=now,
    start_time=(datetime.now(timezone.utc) + timedelta(minutes=2)).isoformat(),
    is_active=True,
    status="ACTIVE"
)
db.add(quiz)
db.commit()
db.refresh(quiz)

# Step 8: Link quiz to questions
qqs = [
    QuizQuestion(quiz_id=quiz.id, question_id=q1.id, mark=5),
    QuizQuestion(quiz_id=quiz.id, question_id=q2.id, mark=5),
    QuizQuestion(quiz_id=quiz.id, question_id=q3.id, mark=5),
]
db.add_all(qqs)

# Step 9: Assign to student
assignment = AssignedQuiz(student_id=student.id, quiz_id=quiz.id)
db.add(assignment)

db.commit()
db.close()
print("✅ Binomial Theorem quiz seeded successfully.")
