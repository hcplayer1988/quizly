"""Views for Quiz-Management API endpoints."""
 
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
 
from management_app.models import Quiz
 
from .serializers import QuizBriefSerializer, QuizSerializer
from .services import create_quiz_from_url, get_quiz_for_user
 
 
class QuizListCreateView(APIView):
    permission_classes = [IsAuthenticated]
 
    def get(self, request):
        quizzes = Quiz.objects.filter(user=request.user).order_by('-created_at')
        serializer = QuizBriefSerializer(quizzes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
 
    def post(self, request):
        try:
            quiz = create_quiz_from_url(request.data.get('url'), request.user)
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"detail": f"Error creating quiz: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
 
        serializer = QuizSerializer(quiz)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
 
 
class QuizDetailView(APIView):
    permission_classes = [IsAuthenticated]
 
    def get(self, request, id):
        try:
            quiz = get_quiz_for_user(id, request.user)
        except Quiz.DoesNotExist:
            return Response(
                {"detail": "Quiz not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
 
        serializer = QuizBriefSerializer(quiz)
        return Response(serializer.data, status=status.HTTP_200_OK)
 
    def patch(self, request, id):
        try:
            quiz = get_quiz_for_user(id, request.user)
        except Quiz.DoesNotExist:
            return Response(
                {"detail": "Quiz not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
 
        serializer = QuizBriefSerializer(quiz, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
 
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
 
    def delete(self, request, id):
        try:
            quiz = get_quiz_for_user(id, request.user)
        except Quiz.DoesNotExist:
            return Response(
                {"detail": "Quiz not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
 
        quiz.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)



