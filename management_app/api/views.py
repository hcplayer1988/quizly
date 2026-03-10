import os
import re
import tempfile
import whisper
import yt_dlp
import json

from google import genai

from django.conf import settings

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
    tmp_dir = tempfile.mkdtemp()
    tmp_filename = os.path.join(tmp_dir, 'audio.%(ext)s')

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": tmp_filename,
        "quiet": True,
        "noplaylist": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])

    output_path = os.path.join(tmp_dir, 'audio.mp3')
    return output_path


def transcribe_audio(file_path):
    model = whisper.load_model("base")
    result = model.transcribe(file_path)
    return result["text"]


def generate_quiz_with_gemini(transcript):
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

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

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=prompt
    )

    raw = response.text.strip()

    raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.IGNORECASE)
    raw = re.sub(r'\s*```$', '', raw)
    raw = raw.strip()

    return raw


class QuizListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        quizzes = Quiz.objects.filter(user=request.user).order_by('-created_at')
        serializer = QuizSerializer(quizzes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

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

    def patch(self, request, id):
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

        serializer = QuizSerializer(quiz, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
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

        quiz.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)



