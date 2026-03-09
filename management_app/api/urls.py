from django.urls import path
from .views import QuizCreateView, QuizListView

urlpatterns = [
    path('quizzes/', QuizCreateView.as_view(), name='quiz-create'),
    path('quizzes/', QuizListView.as_view(), name='quiz-list'),
]