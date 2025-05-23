from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import Base, User, Quiz, Question, Option, QuizQuestion, AssignedQuiz, QuizStatus, Category, Subcategory
from datetime import datetime, timezone

# Recreate the database tables
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

db: Session = SessionLocal()

now = datetime.now(timezone.utc).isoformat()

# 1. Create a test teacher and student
teacher = User(name="Teacher1", email="teacher1@example.com", password="123", role="teacher")
student1 = User(name="Student1", email="student1@example.com", password="123", role="student")
student2 = User(name="Student2", email="student2@example.com", password="123", role="student")
student3 = User(name="Student3", email="student3@example.com", password="123", role="student")
db.add_all([teacher, student1, student2, student3])
db.commit()
db.refresh(teacher)
db.refresh(student1)
db.refresh(student2)
db.refresh(student3)

# 2. Create a category and subcategory for the questions
category = Category(name="Computer Science")
subcategory = Subcategory(name="Python Basics", category=category)
db.add_all([category, subcategory])
db.commit()
db.refresh(subcategory)

# 3. Create a quiz with random_order = True
quiz = Quiz(
    title="Python Basics MCQ Quiz",
    total_marks=10,
    duration_minutes=5,
    created_by=teacher.id,
    created_at=now,
    start_time=now,
    is_active=True,
    status=QuizStatus.ACTIVE,
    random_order=True
)
db.add(quiz)
db.commit()
db.refresh(quiz)

# 4. Create MCQ Questions and associate with quiz
questions_data = [
    {
        "question": "Which keyword is used to define a function in Python?",
        "options": ["func", "define", "def", "function"],
        "correct": "def"
    },
    {
        "question": "What is the output of: print(2 ** 3)?",
        "options": ["5", "6", "8", "9"],
        "correct": "8"
    },
    {
        "question": "Which data type is immutable in Python?",
        "options": ["list", "dict", "set", "tuple"],
        "correct": "tuple"
    }
]

for item in questions_data:
    q = Question(
        question_text=item["question"],
        question_type="MCQ",
        correct_answer=item["correct"],
        feedback="",
        created_by=teacher.id,
        created_at=now,
        subcategory_id=subcategory.id
    )
    db.add(q)
    db.flush()  # Get q.id

    for opt_text in item["options"]:
        option = Option(text=opt_text, is_correct=(opt_text == item["correct"]), question=q)
        db.add(option)

    quiz_question = QuizQuestion(
        quiz_id=quiz.id,
        question_id=q.id,
        mark=1
    )
    db.add(quiz_question)

# 5. Assign the quiz to the student
# Assign quiz to all three students
assignments = [
    AssignedQuiz(quiz_id=quiz.id, student_id=student1.id),
    AssignedQuiz(quiz_id=quiz.id, student_id=student2.id),
    AssignedQuiz(quiz_id=quiz.id, student_id=student3.id),
]
db.add_all(assignments)


db.commit()
db.close()
print("✅ Random order quiz with MCQs seeded successfully.")
