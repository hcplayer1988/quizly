"""Url's for Quiz-Management API endpoints."""
from django.urls import path
from .views import QuizListCreateView, QuizDetailView

urlpatterns = [
    path('quizzes/', QuizListCreateView.as_view(), name='quiz-list-create'),
    path('quizzes/<int:id>/', QuizDetailView.as_view(), name='quiz-detail'),
]

