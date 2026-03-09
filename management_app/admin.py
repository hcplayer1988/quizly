from django.contrib import admin
from management_app.models import Quiz, Question


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    fields = ['question_title', 'question_options', 'answer', 'created_at', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'user', 'video_url', 'created_at', 'updated_at']
    search_fields = ['title', 'description', 'user__username']
    list_filter = ['created_at', 'user']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'question_title', 'quiz', 'answer', 'created_at']
    search_fields = ['question_title', 'quiz__title']
    list_filter = ['created_at', 'quiz']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']


