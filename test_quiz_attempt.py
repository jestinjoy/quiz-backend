from database import SessionLocal
from models import User, Quiz, QuizQuestion, Question, Option, StudentQuiz, StudentAnswer
from datetime import datetime
import json

# Open DB session
db = SessionLocal()
now = datetime.utcnow().isoformat()

# Step 1: Get a student and a quiz
student = db.query(User).filter_by(email="bob@school.edu").first()
quiz = db.query(Quiz).filter_by(title="Intro to Python").first()

if not student or not quiz:
    print("❌ Student or Quiz not found.")
    exit()

# Step 2: Check if student already attempted
existing = db.query(StudentQuiz).filter_by(student_id=student.id, quiz_id=quiz.id).first()
if existing:
    print("⚠️ Student already attempted this quiz.")
    exit()

# Step 3: Create a new quiz attempt
attempt = StudentQuiz(
    student_id=student.id,
    quiz_id=quiz.id,
    started_at=now,
    submitted_at=now
)
db.add(attempt)
db.commit()
db.refresh(attempt)

# Step 4: Simulate student answers (hardcoded for now)
# You can later randomize or input from a form
given_answers = {}

for qmap in db.query(QuizQuestion).filter_by(quiz_id=quiz.id).all():
    q = db.query(Question).filter_by(id=qmap.question_id).first()

    # Dummy answers for simulation (feel free to modify these)
    if q.question_type == "MCQ":
        # Pick the first option as given answer
        first_option = db.query(Option).filter_by(question_id=q.id).first()
        given_answers[q.id] = first_option.text
    elif q.question_type == "FILL_BLANK":
        given_answers[q.id] = "Guido van Rossum"
    elif q.question_type == "TRUE_FALSE":
        given_answers[q.id] = "False"
    elif q.question_type == "MULTI_SELECT":
        given_answers[q.id] = json.dumps(["List", "Dictionary", "Integer"])  # as stringified list

# Step 5: Evaluate and store answers
total_score = 0

for qmap in db.query(QuizQuestion).filter_by(quiz_id=quiz.id).all():
    q = db.query(Question).filter_by(id=qmap.question_id).first()
    given = given_answers[q.id]
    correct = q.correct_answer
    mark = qmap.mark
    is_correct = False

    # Logic for correctness
    if q.question_type == "FILL_BLANK":
        correct_vals = json.loads(correct) if correct else []
        is_correct = given.strip().lower() in [x.lower() for x in correct_vals]
    elif q.question_type == "TRUE_FALSE":
        is_correct = (given.strip().lower() == correct.strip().lower())
    elif q.question_type == "MULTI_SELECT":
        given_set = set(json.loads(given))
        correct_options = db.query(Option).filter_by(question_id=q.id, is_correct=True).all()
        correct_set = set([o.text for o in correct_options])
        is_correct = (given_set == correct_set)
    elif q.question_type == "MCQ":
        correct_option = db.query(Option).filter_by(question_id=q.id, is_correct=True).first()
        is_correct = (given == correct_option.text)

    awarded = mark if is_correct else 0
    total_score += awarded

    ans = StudentAnswer(
        student_quiz_id=attempt.id,
        question_id=q.id,
        given_answer=given,
        is_correct=is_correct,
        marks_awarded=awarded
    )
    db.add(ans)

# Finalize attempt
attempt.total_score = total_score
db.commit()
print(f"✅ Quiz attempted by {student.name}. Score: {total_score}/{quiz.total_marks}")
db.close()
