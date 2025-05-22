from fastapi import APIRouter, Depends, Query, HTTPException, Path, Body, UploadFile, File
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Question, Option, Category, Subcategory, Quiz, QuizStatus, QuizQuestion, User, AssignedQuiz
from schemas.teacher_schemas import QuestionCreateSchema, QuizCreateSchema, AssignQuestionsSchema, UserCreateSchema
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import text
from datetime import datetime
import csv
import codecs


router = APIRouter(prefix="/teacher", tags=["Teacher"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/add_question")
def add_question(question_data: QuestionCreateSchema, db: Session = Depends(get_db)):
    new_question = Question(
        question_text=question_data.question_text,
        question_type=question_data.question_type,
        correct_answer=question_data.correct_answer,
        feedback=question_data.feedback,
        subcategory_id=question_data.subcategory_id,
        created_by=question_data.created_by,
        created_at=question_data.created_at,
        is_active=question_data.is_active
    )
    db.add(new_question)
    db.commit()
    db.refresh(new_question)

    if question_data.options:
        for opt in question_data.options:
            option = Option(
                text=opt.text,
                is_correct=opt.is_correct,
                question_id=new_question.id
            )
            db.add(option)
        db.commit()

    return {"message": "Question added", "question_id": new_question.id}

@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    return db.query(Category).all()

@router.get("/subcategories/{category_id}")
def get_subcategories(category_id: int, db: Session = Depends(get_db)):
    return db.query(Subcategory).filter(Subcategory.category_id == category_id).all()

@router.get("/questions")
def get_all_questions(
    subcategory_id: int = Query(None),
    category_id: int = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Question)

    if subcategory_id:
        query = query.filter(Question.subcategory_id == subcategory_id)
    elif category_id:
        query = query.join(Subcategory).filter(Subcategory.category_id == category_id)

    questions = query.all()
    return [{"id": q.id, "question_text": q.question_text} for q in questions]

@router.post("/create_quiz")
def create_quiz(data: QuizCreateSchema, db: Session = Depends(get_db)):
    # Validate status or assign default
    status = "ACTIVE"

    quiz = Quiz(
        title=data.title,
        duration_minutes=data.duration_minutes,
        total_marks=data.total_marks,
        start_time=data.start_time,
        is_active=data.is_active,
        status=status,
        created_by=data.created_by,
        created_at=data.created_at
    )

    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return {"id": quiz.id, "title": quiz.title}

@router.post("/assign_questions")
def assign_questions(data: dict, db: Session = Depends(get_db)):
    quiz_id = data["quiz_id"]
    question_ids = data["question_ids"]

    for qid in question_ids:
        db.add(QuizQuestion(quiz_id=quiz_id, question_id=qid))  # mark will default to 1
    db.commit()
    return {"message": "Questions assigned to quiz successfully."}

@router.get("/students")
def get_students(db: Session = Depends(get_db)):
    # Fetch all users with role='student'
    return db.query(User).filter(User.role == "student").all()

@router.post("/assign_students/{quiz_id}")
def assign_students(
    quiz_id: int = Path(...),
    data: dict = None,
    db: Session = Depends(get_db)
):
    student_ids = data.get("student_ids", [])

    if not student_ids:
        raise HTTPException(status_code=400, detail="No students selected.")

    for sid in student_ids:
        db.execute(
            text("INSERT OR IGNORE INTO assigned_quizzes (quiz_id, student_id) VALUES (:quiz_id, :student_id)"),
            {"quiz_id": quiz_id, "student_id": sid}
        )

    db.commit()
    return {"message": f"{len(student_ids)} students assigned to quiz {quiz_id}."}


@router.get("/quizzes")
def get_quizzes_by_teacher(
    created_by: Optional[int] = Query(None),
    include_creator: bool = Query(False),
    db: Session = Depends(get_db)
):
    query = db.query(Quiz)
    if created_by:
        query = query.filter(Quiz.created_by == created_by)

    quizzes = query.order_by(Quiz.created_at.desc()).all()

    result = []
    for q in quizzes:
        creator = db.query(User).filter(User.id == q.created_by).first() if include_creator else None
        result.append({
            "id": q.id,
            "title": q.title,
            "total_marks": q.total_marks,
            "duration_minutes": q.duration_minutes,
            "is_active": q.is_active,
            "status": q.status.value,
            "created_by": q.created_by,
            "created_by_name": creator.name if creator else None
        })
    return result

@router.post("/toggle_quiz_status/{quiz_id}")
def toggle_quiz_status(
    quiz_id: int,
    db: Session = Depends(get_db)
):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    # Toggle the status
    quiz.status = QuizStatus.COMPLETED if quiz.status == QuizStatus.ACTIVE else QuizStatus.ACTIVE
    db.commit()
    return {"message": "Quiz status toggled", "new_status": quiz.status.value}


@router.post("/toggle_quiz_active/{quiz_id}")
def toggle_quiz_active(
    quiz_id: int,
    db: Session = Depends(get_db)
):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    quiz.is_active = not quiz.is_active
    db.commit()
    return {"message": "Quiz active state toggled", "is_active": quiz.is_active}

@router.post("/bulk_upload_questions")
def bulk_upload_questions(
    subcategory_id: int = Query(...),
    created_by: int = Query(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    content = file.file.read().decode("utf-8")
    questions_added = 0
    errors = []

    blocks = content.strip().split("\n\n")
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            errors.append(f"Invalid format: {block}")
            continue

        question_text = lines[0]
        options = []
        correct_letter = None

        for line in lines[1:]:
            if line.strip().startswith("ANSWER:"):
                correct_letter = line.split("ANSWER:")[1].strip()
            else:
                parts = line.strip().split(")", 1)
                if len(parts) == 2:
                    options.append((parts[0].strip(), parts[1].strip()))

        if correct_letter is None or len(options) < 2:
            errors.append(f"Missing ANSWER or too few options: {block}")
            continue

        correct_text = None
        for label, text in options:
            if label.upper() == correct_letter.upper():
                correct_text = text

        if not correct_text:
            errors.append(f"Correct answer label '{correct_letter}' not found in options for: {question_text}")
            continue

        question = Question(
            question_text=question_text,
            question_type="MCQ",
            correct_answer=correct_text,
            subcategory_id=subcategory_id,
            created_by=created_by,
            created_at=datetime.utcnow().isoformat(),
            is_active=True
        )
        db.add(question)
        db.commit()
        db.refresh(question)

        for _, text in options:
            db.add(Option(text=text, is_correct=(text == correct_text), question_id=question.id))

        db.commit()
        questions_added += 1

    return {"uploaded": questions_added, "errors": errors}

@router.get("/export/aiken", response_class=PlainTextResponse)
def export_aiken(
    subcategory_id: Optional[int] = Query(None),
    category_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Question).filter(Question.question_type == "MCQ")

    if subcategory_id:
        query = query.filter(Question.subcategory_id == subcategory_id)
    elif category_id:
        query = query.join(Subcategory).filter(Subcategory.category_id == category_id)

    questions = query.all()
    if not questions:
        return PlainTextResponse("No MCQ questions found for given filters.", status_code=404)

    export_lines = []
    for q in questions:
        export_lines.append(q.question_text.strip())

        options = sorted(q.options, key=lambda o: o.id)[:4]  # Only first 4 options supported
        option_letters = ['A', 'B', 'C', 'D']

        correct_letter = None
        for i, opt in enumerate(options):
            line = f"{option_letters[i]}. {opt.text.strip()}"
            export_lines.append(line)
            if opt.is_correct:
                correct_letter = option_letters[i]

        if correct_letter:
            export_lines.append(f"ANSWER: {correct_letter}")
            export_lines.append("")  # blank line

    aiken_text = "\n".join(export_lines)
    return PlainTextResponse(content=aiken_text, media_type="text/plain")


    return "\n".join(output)

@router.get("/export/gift", response_class=PlainTextResponse)
def export_gift_format(
    category_id: Optional[int] = Query(None),
    subcategory_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Question).filter(Question.question_type == "MCQ")

    if subcategory_id:
        query = query.filter(Question.subcategory_id == subcategory_id)
    elif category_id:
        query = query.join(Subcategory).filter(Subcategory.category_id == category_id)

    questions = query.all()
    lines = []

    for q in questions:
        # Escape characters used in GIFT
        def escape(text):
            return text.replace("{", "\\{").replace("}", "\\}").replace("=", "\\=").replace("~", "\\~")

        q_text = escape(q.question_text.strip())
        gift_line = f"::Q{q.id}:: {q_text} {{\n"

        for opt in q.options:
            symbol = "=" if opt.is_correct else "~"
            opt_text = escape(opt.text.strip())
            gift_line += f"{symbol}{opt_text}\n"

        gift_line += "}\n"
        lines.append(gift_line)

    return "\n".join(lines)

@router.post("/add_user")
def add_user(user: UserCreateSchema, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    new_user = User(
        name=user.name,
        email=user.email,
        password=user.password,
        role=user.role,
        college=user.college,
        batch=user.batch,
        semester=user.semester
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User added successfully", "user_id": new_user.id}

@router.post("/bulk_upload_users")
def bulk_upload_users(file: UploadFile = File(...), db: Session = Depends(get_db)):
    reader = csv.DictReader(codecs.iterdecode(file.file, 'utf-8'))

    created = 0
    failed = 0
    for row in reader:
        try:
            user = User(
                name=row["name"],
                email=row["email"],
                password=row["password"],  # Plain text for now
                role=row["role"],
                college=row.get("college"),
                batch=row.get("batch"),
                semester=row.get("semester")
            )
            db.add(user)
            created += 1
        except Exception as e:
            print(f"Failed to add {row.get('email')}: {e}")
            failed += 1

    db.commit()
    return {"created": created, "failed": failed}

@router.post("/login")
def login(data: dict, db: Session = Depends(get_db)):
    email = data.get("email")
    password = data.get("password")

    user = db.query(User).filter(User.email == email).first()

    if not user or user.password != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role  # ✅ Make sure this line exists
    }
