from django.urls import path
from .views import QuizCreateView, QuizListView, QuizDetailView

urlpatterns = [
    path('quizzes/', QuizCreateView.as_view(), name='quiz-create'),
    path('quizzes/', QuizListView.as_view(), name='quiz-list'),
    path('quizzes/<int:id>/', QuizDetailView.as_view(), name='quiz-detail'),
]