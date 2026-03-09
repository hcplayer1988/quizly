import os
import re
import tempfile
import whisper
import google.generativeai as genai
import yt_dlp
import json

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from management_app.models import Quiz, Question
from .serializers import QuizSerializer


def extract_video_id(url):
    pattern = r'(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None


def build_youtube_url(video_id):
    return f'https://www.youtube.com/watch?v={video_id}'


def download_audio(youtube_url):
    tmp_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
    tmp_filename = tmp_file.name
    tmp_file.close()

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": tmp_filename,
        "quiet": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])

    return tmp_filename


def transcribe_audio(file_path):
    model = whisper.load_model("base")
    result = model.transcribe(file_path)
    return result["text"]


def generate_quiz_with_gemini(transcript):
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = f"""Based on the following transcript, generate a quiz in valid JSON format.
The quiz must follow this exact structure:
{{
  "title": "Create a concise quiz title based on the topic of the transcript.",
  "description": "Summarize the transcript in no more than 150 characters. Do not include any quiz questions or answers.",
  "questions": [
    {{
      "question_title": "The question goes here.",
      "question_options": ["Option A", "Option B", "Option C", "Option D"],
      "answer": "The correct answer from the above options"
    }},
    ...
    (exactly 10 questions)
  ]
}}
Requirements:
- Each question must have exactly 4 distinct answer options.
- Only one correct answer is allowed per question, and it must be present in 'question_options'.
- The output must be valid JSON and parsable as-is (e.g., using Python's json.loads).
- Do not include explanations, comments, or any text outside the JSON.

Transcript:
{transcript}"""

    response = model.generate_content(prompt)
    raw = response.text.strip()

    # Markdown Code-Blöcke entfernen
    raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.IGNORECASE)
    raw = re.sub(r'\s*```$', '', raw)
    raw = raw.strip()

    return raw


class QuizCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        url = request.data.get('url')

        if not url:
            return Response(
                {"detail": "URL is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        video_id = extract_video_id(url)
        if not video_id:
            return Response(
                {"detail": "Invalid YouTube URL."},
                status=status.HTTP_400_BAD_REQUEST
            )

        clean_url = build_youtube_url(video_id)

        try:
            audio_path = download_audio(clean_url)
            transcript = transcribe_audio(audio_path)
            os.remove(audio_path)
        except Exception as e:
            return Response(
                {"detail": f"Error processing video: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            raw = generate_quiz_with_gemini(transcript)
            quiz_data = json.loads(raw)
        except Exception as e:
            return Response(
                {"detail": f"Error generating quiz: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            quiz = Quiz.objects.create(
                user=request.user,
                title=quiz_data['title'],
                description=quiz_data['description'],
                video_url=clean_url
            )

            for q in quiz_data['questions']:
                Question.objects.create(
                    quiz=quiz,
                    question_title=q['question_title'],
                    question_options=q['question_options'],
                    answer=q['answer']
                )

            serializer = QuizSerializer(quiz)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"detail": f"Error saving quiz: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class QuizListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        quizzes = Quiz.objects.filter(user=request.user).order_by('-created_at')
        serializer = QuizSerializer(quizzes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class QuizDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        try:
            quiz = Quiz.objects.get(id=id)
        except Quiz.DoesNotExist:
            return Response(
                {"detail": "Quiz not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if quiz.user != request.user:
            return Response(
                {"detail": "Access denied. This quiz does not belong to you."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = QuizSerializer(quiz)
        return Response(serializer.data, status=status.HTTP_200_OK)



