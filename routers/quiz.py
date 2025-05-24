# routers/quiz.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import SessionLocal
from models import User, Quiz, QuizQuestion, Question, Option, StudentQuiz, StudentAnswer, AssignedQuiz, QuizStatus, StudentQuizQuestionOrder
from datetime import datetime, timezone
from schemas.quiz_schemas import LoginData
import json
import random

router = APIRouter()

class AnswerSubmission(BaseModel):
    quiz_id: int
    student_id: int
    answers: Dict[int, str]  # question_id: answer (str or JSON string)

@router.post("/submit_quiz")
def submit_quiz(data: AnswerSubmission):
    db: Session = SessionLocal()

    attempt = db.query(StudentQuiz).filter_by(student_id=data.student_id, quiz_id=data.quiz_id).first()
    if not attempt:
        raise HTTPException(status_code=400, detail="Quiz not started")

    if attempt.submitted_at:
        raise HTTPException(status_code=400, detail="Quiz already submitted")

    now = datetime.now(timezone.utc).isoformat()
    attempt.submitted_at = now

    quiz = db.query(Quiz).filter_by(id=data.quiz_id).first()
    ordered_entries = db.query(StudentQuizQuestionOrder).filter_by(student_quiz_id=attempt.id).all()

    raw_score = 0
    max_raw_score = 0

    for entry in ordered_entries:
        q = db.query(Question).filter_by(id=entry.question_id).first()
        qq = db.query(QuizQuestion).filter_by(quiz_id=data.quiz_id, question_id=q.id).first()
        given = data.answers.get(q.id)

        if given is None:
            continue

        correct = q.correct_answer
        is_correct = False
        marks = qq.mark if qq and qq.mark is not None else 1
        max_raw_score += marks

        if q.question_type == "FILL_BLANK":
            correct_vals = json.loads(correct or "[]")
            is_correct = given.strip().lower() in [x.lower() for x in correct_vals]
        elif q.question_type == "TRUE_FALSE":
            is_correct = given.strip().lower() == (correct or "").strip().lower()
        elif q.question_type == "MULTI_SELECT":
            try:
                given_set = set(json.loads(given))
            except:
                given_set = set()
            correct_set = set(o.text for o in db.query(Option).filter_by(question_id=q.id, is_correct=True))
            is_correct = given_set == correct_set
        elif q.question_type == "MCQ":
            correct_option = db.query(Option).filter_by(question_id=q.id, is_correct=True).first()
            is_correct = (given == correct_option.text if correct_option else False)

        awarded = marks if is_correct else 0
        raw_score += awarded

        db.add(StudentAnswer(
            student_quiz_id=attempt.id,
            question_id=q.id,
            given_answer=given,
            is_correct=is_correct,
            marks_awarded=awarded
        ))

    scaled_score = round((raw_score / max_raw_score) * quiz.total_marks, 2) if max_raw_score > 0 else 0
    attempt.total_score = scaled_score

    db.commit()
    db.close()

    return {
        "message": "Quiz submitted!",
        "score": scaled_score
    }

@router.get("/list/{student_id}")
def list_quizzes(student_id: int):
    db: Session = SessionLocal()
    now = datetime.utcnow().isoformat()

    assigned_ids = db.query(AssignedQuiz.quiz_id).filter_by(student_id=student_id).subquery()
    quizzes = db.query(Quiz).filter(Quiz.id.in_(assigned_ids), Quiz.is_active == True).all()

    active, upcoming, completed = [], [], []

    for quiz in quizzes:
        # ✅ Auto-complete if past end time and still ACTIVE
        if quiz.quiz_end_time and quiz.status == QuizStatus.ACTIVE:
            if quiz.quiz_end_time < now:
                quiz.status = QuizStatus.COMPLETED
                db.commit()

        attempted = db.query(StudentQuiz).filter_by(student_id=student_id, quiz_id=quiz.id).first()
        item = {
            "quiz_id": quiz.id,
            "title": quiz.title,
            "start_time": quiz.start_time,
            "duration_minutes": quiz.duration_minutes,
            "total_marks": quiz.total_marks,
            "attempted": attempted is not None,
            "score": attempted.total_score if attempted else None,
            "status": quiz.status
        }

        if attempted:
            if quiz.status == QuizStatus.COMPLETED:
                scores = db.query(StudentQuiz).filter_by(quiz_id=quiz.id).order_by(StudentQuiz.total_score.desc()).all()
                rank = next((i+1 for i, s in enumerate(scores) if s.student_id == student_id), None)
                item["position"] = rank
            completed.append(item)
        elif quiz.start_time > now:
            upcoming.append(item)
        else:
            if quiz.status == QuizStatus.COMPLETED:
                completed.append(item)
            else:
                active.append(item)

    db.close()
    return {
        "active": active,
        "upcoming": upcoming,
        "completed": completed
    }

@router.get("/quiz/{quiz_id}/questions/{student_id}")
def get_ordered_questions(quiz_id: int, student_id: int):
    db: Session = SessionLocal()

    quiz = db.query(Quiz).filter_by(id=quiz_id, is_active=True).first()
    if not quiz:
        db.close()
        raise HTTPException(status_code=404, detail="Quiz not found")

    attempt = db.query(StudentQuiz).filter_by(quiz_id=quiz_id, student_id=student_id).first()
    if not attempt:
        db.close()
        raise HTTPException(status_code=400, detail="Quiz not started")

    question_order = db.query(StudentQuizQuestionOrder).filter_by(student_quiz_id=attempt.id).order_by(StudentQuizQuestionOrder.position).all()

    questions_data = []
    for entry in question_order:
        q = db.query(Question).filter_by(id=entry.question_id).first()
        opts = db.query(Option).filter_by(question_id=q.id).all() if q.question_type in ["MCQ", "MULTI_SELECT", "TRUE_FALSE"] else []
        questions_data.append({
            "question_id": q.id,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "options": [{"text": o.text} for o in opts]
        })

    db.close()
    return {
        "quiz_id": quiz_id,
        "title": quiz.title,
        "duration_minutes": quiz.duration_minutes,
        "total_marks": quiz.total_marks,
        "questions": questions_data
    }

@router.get("/quiz/{quiz_id}/summary/{student_id}")
def get_quiz_summary(quiz_id: int, student_id: int):
    db: Session = SessionLocal()
    quiz = db.query(Quiz).filter_by(id=quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    attempt = db.query(StudentQuiz).filter_by(quiz_id=quiz_id, student_id=student_id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")

    total_attempts = db.query(StudentQuiz).filter_by(quiz_id=quiz_id).count()
    scores = [s.total_score for s in db.query(StudentQuiz).filter_by(quiz_id=quiz_id).all()]
    average = sum(scores) / len(scores) if scores else 0
    median = sorted(scores)[len(scores)//2] if scores else 0

    answers = (
        db.query(StudentAnswer, Question)
        .join(Question, StudentAnswer.question_id == Question.id)
        .filter(StudentAnswer.student_quiz_id == attempt.id)
        .all()
    )

    answer_list = []

    for a, q in answers:
        correct = None
        if q.question_type in ["MCQ", "MULTI_SELECT"]:
            opts = db.query(Option).filter_by(question_id=q.id, is_correct=True).all()
            correct = [o.text for o in opts]
            if q.question_type == "MCQ" and correct:
                correct = correct[0]
        elif q.question_type == "TRUE_FALSE":
            correct = q.correct_answer
        elif q.question_type == "FILL_BLANK":
            correct_vals = json.loads(q.correct_answer or "[]")
            correct = ", ".join(correct_vals)

        answer_list.append({
            "question": q.question_text,
            "correct_answer": correct,
            "your_answer": a.given_answer,
            "is_correct": a.is_correct,
            "feedback": q.feedback
        })

    db.close()
    return {
        "quiz_title": quiz.title,
        "total_marks": quiz.total_marks,
        "your_score": attempt.total_score,
        "students_attended": total_attempts,
        "average_marks": round(average, 2),
        "median_marks": median,
        "answers": answer_list
    }

@router.post("/login")
def login(data: LoginData):
    db: Session = SessionLocal()
    user = db.query(User).filter_by(email=data.email).first()
    db.close()

    if not user or user.password != data.password:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return {"id": user.id, "name": user.name, "email": user.email}

@router.post("/start_quiz/{quiz_id}/{student_id}")
def start_quiz(quiz_id: int, student_id: int):
    db: Session = SessionLocal()

    quiz = db.query(Quiz).filter_by(id=quiz_id).first()
    if quiz.status == QuizStatus.COMPLETED:
        db.close()
        raise HTTPException(status_code=403, detail="Quiz is already marked as completed.")

    existing = db.query(StudentQuiz).filter_by(student_id=student_id, quiz_id=quiz_id).first()
    if existing:
        db.close()
        return {"message": "Quiz already started"}

    now = datetime.now(timezone.utc).isoformat()
    student_quiz = StudentQuiz(
        student_id=student_id,
        quiz_id=quiz_id,
        started_at=now,
        submitted_at=None,
        total_score=0
    )
    db.add(student_quiz)
    db.commit()
    db.refresh(student_quiz)

    quiz_questions = db.query(QuizQuestion).filter_by(quiz_id=quiz_id).all()
    question_ids = [qq.question_id for qq in quiz_questions]
    if quiz.random_order:
        random.shuffle(question_ids)

    for pos, qid in enumerate(question_ids):
        db.add(StudentQuizQuestionOrder(
            student_quiz_id=student_quiz.id,
            question_id=qid,
            position=pos
        ))

    db.commit()
    db.close()
    return {"message": "Quiz started"}
