"""Views for Quiz-Management API endpoints."""
import os
import json

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from management_app.models import Quiz, Question
from .serializers import QuizSerializer
from .utils import extract_video_id, build_youtube_url, download_audio, transcribe_audio, generate_quiz_with_gemini


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



