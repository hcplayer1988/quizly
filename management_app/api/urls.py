from django.urls import path
from .views import QuizCreateView, QuizListView, QuizDetailView, QuizUpdateView

urlpatterns = [
    path('quizzes/', QuizCreateView.as_view(), name='quiz-create'),
    path('quizzes/', QuizListView.as_view(), name='quiz-list'),
    path('quizzes/<int:id>/', QuizDetailView.as_view(), name='quiz-detail'),
    path('quizzes/<int:id>/', QuizUpdateView.as_view(), name='quiz-update'),
]
