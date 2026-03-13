"""Business logic for Quiz-Management API."""
 
import json
import os
 
from management_app.models import Question, Quiz
 
from .utils import (
    build_youtube_url,
    download_audio,
    extract_video_id,
    generate_quiz_with_gemini,
    transcribe_audio,
)
 
 
def validate_youtube_url(url):
    """
    Validates and normalizes a YouTube URL.
    Returns the clean URL or raises ValueError.
    """
    if not url:
        raise ValueError("URL is required.")
 
    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError("Invalid YouTube URL.")
 
    return build_youtube_url(video_id)
 
 
def get_quiz_for_user(quiz_id, user):
    """
    Fetches a quiz by ID and verifies ownership.
    Raises Quiz.DoesNotExist or PermissionError accordingly.
    """
    try:
        quiz = Quiz.objects.get(id=quiz_id)
    except Quiz.DoesNotExist:
        raise Quiz.DoesNotExist
 
    if quiz.user != user:
        raise PermissionError("Access denied. This quiz does not belong to you.")
 
    return quiz
 
 
def create_quiz_from_url(url, user):
    """
    Orchestrates the full quiz creation pipeline:
    validate → download → transcribe → generate → save to DB.
    """
    clean_url = validate_youtube_url(url)
    audio_path = download_audio(clean_url)
 
    try:
        transcript = transcribe_audio(audio_path)
        raw = generate_quiz_with_gemini(transcript)
        quiz_data = json.loads(raw)
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)
 
    quiz = Quiz.objects.create(
        user=user,
        title=quiz_data['title'],
        description=quiz_data['description'],
        video_url=clean_url,
    )
 
    for q in quiz_data['questions']:
        Question.objects.create(
            quiz=quiz,
            question_title=q['question_title'],
            question_options=q['question_options'],
            answer=q['answer'],
        )
 
    return quiz