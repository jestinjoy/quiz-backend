from fastapi import APIRouter, Depends, Query, HTTPException, Path, Body, UploadFile, File
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Question, Option, Category, Subcategory, Quiz, QuizStatus, QuizQuestion, User, AssignedQuiz, StudentQuiz
from schemas.teacher_schemas import QuestionCreateSchema, QuizCreateSchema, QuestionUpdateSchema, UserCreateSchema, CategoryCreateSchema
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
def get_categories_with_subcategories(db: Session = Depends(get_db)):
    categories = db.query(Category).all()
    result = []
    for cat in categories:
        result.append({
            "id": cat.id,
            "name": cat.name,
            "subcategories": [{"id": sub.id, "name": sub.name} for sub in cat.subcategories]
        })
    return result


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
    quiz = Quiz(
        title=data.title,
        duration_minutes=data.duration_minutes,
        total_marks=data.total_marks,
        start_time=data.start_time,
        quiz_end_time=data.quiz_end_time,
        is_active=data.is_active,
        status=QuizStatus[data.status],
        created_by=data.created_by,
        created_at=data.created_at,
        random_order=data.random_order
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
        db.add(QuizQuestion(quiz_id=quiz_id, question_id=qid))
    db.commit()
    return {"message": "Questions assigned to quiz successfully."}

@router.get("/students")
def get_students(
    semester: Optional[int] = Query(None),
    batch: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(User).filter(User.role == "student")
    if semester is not None:
        query = query.filter(User.semester == semester)
    if batch is not None:
        query = query.filter(User.batch == batch)
    return query.all()



@router.post("/assign_students/{quiz_id}")
def assign_students(quiz_id: int = Path(...), data: dict = None, db: Session = Depends(get_db)):
    student_ids = data.get("student_ids", [])
    if not student_ids:
        raise HTTPException(status_code=400, detail="No students selected.")
    for sid in student_ids:
        db.execute(text("INSERT OR IGNORE INTO assigned_quizzes (quiz_id, student_id) VALUES (:quiz_id, :student_id)"), {"quiz_id": quiz_id, "student_id": sid})
    db.commit()
    return {"message": f"{len(student_ids)} students assigned to quiz {quiz_id}."}

@router.get("/quizzes")
def get_quizzes(include_creator: bool = False, db: Session = Depends(get_db)):
    quizzes = db.query(Quiz).all()
    response = []
    for quiz in quizzes:
        creator_name = None
        if include_creator:
            creator = db.query(User).filter(User.id == quiz.created_by).first()
            creator_name = creator.name if creator else None

        attempted = db.query(StudentQuiz).filter_by(quiz_id=quiz.id).first() is not None

        response.append({
            "id": quiz.id,
            "title": quiz.title,
            "total_marks": quiz.total_marks,
            "duration_minutes": quiz.duration_minutes,
            "created_by": quiz.created_by,
            "created_by_name": creator_name,
            "is_active": quiz.is_active,
            "status": quiz.status.value if hasattr(quiz.status, 'value') else quiz.status,
            "attempted": attempted  # ✅ Add this field
        })
    return response


@router.post("/toggle_quiz_status/{quiz_id}")
def toggle_quiz_status(quiz_id: int, db: Session = Depends(get_db)):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    quiz.status = QuizStatus.COMPLETED if quiz.status == QuizStatus.ACTIVE else QuizStatus.ACTIVE
    db.commit()
    return {"message": "Quiz status toggled", "new_status": quiz.status.value}

@router.post("/toggle_quiz_active/{quiz_id}")
def toggle_quiz_active(quiz_id: int, db: Session = Depends(get_db)):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    quiz.is_active = not quiz.is_active
    db.commit()
    return {"message": "Quiz active state toggled", "is_active": quiz.is_active}

@router.post("/bulk_upload_questions")
def bulk_upload_questions(subcategory_id: int = Query(...), created_by: int = Query(...), file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = file.file.read().decode("utf-8")
    questions_added, errors = 0, []
    blocks = content.strip().split("\n\n")
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            errors.append(f"Invalid format: {block}")
            continue
        question_text, options, correct_letter = lines[0], [], None
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
        correct_text = next((text for label, text in options if label.upper() == correct_letter.upper()), None)
        if not correct_text:
            errors.append(f"Correct answer label '{correct_letter}' not found in: {question_text}")
            continue
        q = Question(question_text=question_text, question_type="MCQ", correct_answer=correct_text, subcategory_id=subcategory_id, created_by=created_by, created_at=datetime.utcnow().isoformat(), is_active=True)
        db.add(q)
        db.commit()
        db.refresh(q)
        for _, text in options:
            db.add(Option(text=text, is_correct=(text == correct_text), question_id=q.id))
        db.commit()
        questions_added += 1
    return {"uploaded": questions_added, "errors": errors}

@router.get("/export/aiken", response_class=PlainTextResponse)
def export_aiken(subcategory_id: Optional[int] = Query(None), category_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    query = db.query(Question).filter(Question.question_type == "MCQ")
    if subcategory_id:
        query = query.filter(Question.subcategory_id == subcategory_id)
    elif category_id:
        query = query.join(Subcategory).filter(Subcategory.category_id == category_id)
    questions = query.all()
    if not questions:
        return PlainTextResponse("No MCQ questions found for given filters.", status_code=404)
    lines, option_letters = [], ['A', 'B', 'C', 'D']
    for q in questions:
        lines.append(q.question_text.strip())
        options = sorted(q.options, key=lambda o: o.id)[:4]
        correct = next((option_letters[i] for i, o in enumerate(options) if o.is_correct), None)
        for i, o in enumerate(options):
            lines.append(f"{option_letters[i]}. {o.text.strip()}")
        if correct:
            lines.append(f"ANSWER: {correct}\n")
    return "\n".join(lines)

@router.get("/export/gift", response_class=PlainTextResponse)
def export_gift(category_id: Optional[int] = Query(None), subcategory_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    query = db.query(Question).filter(Question.question_type == "MCQ")
    if subcategory_id:
        query = query.filter(Question.subcategory_id == subcategory_id)
    elif category_id:
        query = query.join(Subcategory).filter(Subcategory.category_id == category_id)
    def escape(text): return text.replace("{", "\\{").replace("}", "\\}").replace("=", "\\=").replace("~", "\\~")
    lines = []
    for q in query.all():
        lines.append(f"::Q{q.id}:: {escape(q.question_text.strip())} {{")
        for o in q.options:
            symbol = "=" if o.is_correct else "~"
            lines.append(f"{symbol}{escape(o.text.strip())}")
        lines.append("}\n")
    return "\n".join(lines)

@router.post("/add_user")
def add_user(user: UserCreateSchema, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    new_user = User(
        name=user.name, email=user.email, password=user.password, role=user.role,
        college=user.college, batch=user.batch, semester=user.semester, course=user.course
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User added successfully", "user_id": new_user.id}

@router.post("/bulk_upload_users")
def bulk_upload_users(file: UploadFile = File(...), db: Session = Depends(get_db)):
    reader = csv.DictReader(codecs.iterdecode(file.file, 'utf-8'))
    created, failed = 0, 0
    for row in reader:
        try:
            user = User(
                name=row["name"],
                email=row["email"],
                password=row["password"],  # 🔒 Consider hashing
                role=row["role"],
                college=row.get("college"),
                batch=row.get("batch"),
                semester=row.get("semester"),
                course=row.get("course")  # ✅ NEW FIELD
            )
            db.add(user)
            created += 1
        except Exception as e:
            print(f"Failed to add {row.get('email', '[no email]')}: {e}")
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
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}

# CRUD for category
@router.post("/category")
def create_category(data: CategoryCreateSchema, db: Session = Depends(get_db)):
    if db.query(Category).filter(Category.name == data.name).first():
        raise HTTPException(status_code=400, detail="Category already exists")

    cat = Category(name=data.name)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat

@router.put("/category/{id}")
def update_category(id: int, name: str = Body(...), db: Session = Depends(get_db)):
    cat = db.query(Category).filter(Category.id == id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Not found")
    cat.name = name
    db.commit()
    return {"message": "Updated"}

@router.delete("/category/{id}")
def delete_category(id: int, db: Session = Depends(get_db)):
    cat = db.query(Category).filter(Category.id == id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(cat)
    db.commit()
    return {"message": "Deleted"}

@router.post("/subcategory")
def create_subcategory(name: str = Body(...), category_id: int = Body(...), db: Session = Depends(get_db)):
    sub = Subcategory(name=name, category_id=category_id)
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub

@router.put("/subcategory/{id}")
def update_subcategory(id: int, name: str = Body(...), db: Session = Depends(get_db)):
    sub = db.query(Subcategory).filter(Subcategory.id == id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Not found")
    sub.name = name
    db.commit()
    return {"message": "Updated"}

@router.delete("/subcategory/{id}")
def delete_subcategory(id: int, db: Session = Depends(get_db)):
    sub = db.query(Subcategory).filter(Subcategory.id == id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(sub)
    db.commit()
    return {"message": "Deleted"}

@router.get("/quiz_report/{quiz_id}")
def quiz_report(quiz_id: int, db: Session = Depends(get_db)):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    creator = db.query(User).filter(User.id == quiz.created_by).first()

    results = db.execute(text("""
        SELECT u.id, u.name, u.email, sq.total_score
        FROM users u
        JOIN student_quizzes sq ON u.id = sq.student_id
        WHERE sq.quiz_id = :quiz_id
    """), {"quiz_id": quiz_id}).fetchall()

    scores = [r.total_score for r in results if r.total_score is not None]
    summary = {
        "quiz_id": quiz.id,
        "title": quiz.title,
        "faculty": creator.name if creator else "N/A",
        "start_time": quiz.start_time,
        "total_marks": quiz.total_marks,
        "students_attempted": len(scores),
        "maximum": max(scores) if scores else 0,
        "minimum": min(scores) if scores else 0,
        "average": round(sum(scores) / len(scores), 2) if scores else 0,
        "median": sorted(scores)[len(scores)//2] if scores else 0
    }

    student_marks = [{"id": r.id, "name": r.name, "mark": r.total_score} for r in results]
    return {"summary": summary, "results": student_marks}

@router.get("/users")
def get_users(
    role: Optional[str] = Query(None),
    batch: Optional[int] = Query(None),
    semester: Optional[int] = Query(None),
    college: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if batch:
        query = query.filter(User.batch == batch)
    if semester:
        query = query.filter(User.semester == semester)
    if college:
        query = query.filter(User.college == college)
    return query.all()

@router.put("/update_user/{user_id}")
def update_user(user_id: int, data: dict, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    for key, value in data.items():
        if hasattr(user, key):
            setattr(user, key, value)
    db.commit()
    return {"message": "User updated successfully"}

@router.delete("/delete_quiz/{quiz_id}")
def delete_quiz(quiz_id: int, db: Session = Depends(get_db)):
    # Check if any students have attempted the quiz
    attempts = db.query(StudentQuiz).filter_by(quiz_id=quiz_id).first()
    if attempts:
        raise HTTPException(status_code=400, detail="Quiz has been attempted and cannot be deleted.")

    # Delete related quiz questions
    db.query(QuizQuestion).filter_by(quiz_id=quiz_id).delete()

    # Delete assigned students
    db.query(AssignedQuiz).filter_by(quiz_id=quiz_id).delete()

    # Delete the quiz itself
    quiz = db.query(Quiz).filter_by(id=quiz_id).first()
    if quiz:
        db.delete(quiz)
        db.commit()
        return {"message": "Quiz deleted successfully."}
    else:
        raise HTTPException(status_code=404, detail="Quiz not found")


@router.put("/update_question/{question_id}")
def update_question(
    question_id: int,
    data: QuestionUpdateSchema,
    db: Session = Depends(get_db)
):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Update question text and feedback
    question.question_text = data.question_text
    question.feedback = data.feedback
    db.commit()

    # Update each MCQ option
    for opt_data in data.options:
        option = db.query(Option).filter(
            Option.id == opt_data.id,
            Option.question_id == question_id
        ).first()
        if option:
            option.text = opt_data.text
            option.is_correct = opt_data.is_correct

    db.commit()
    return {"message": "Question updated successfully"}

@router.get("/get_question/{question_id}")
def get_question(question_id: int, db: Session = Depends(get_db)):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    return {
        "id": question.id,
        "question_text": question.question_text,
        "feedback": question.feedback,
        "options": [
            {"id": o.id, "text": o.text, "is_correct": o.is_correct}
            for o in sorted(question.options, key=lambda x: x.id)
        ]
    }
