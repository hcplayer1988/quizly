"""Serializers for Quiz-Management API endpoints."""
 
from rest_framework import serializers
 
from management_app.models import Question, Quiz
 
 
class QuestionSerializer(serializers.ModelSerializer):
    """Question serializer with timestamps — used for POST /api/quizzes/."""
 
    class Meta:
        model = Question
        fields = [
            'id',
            'question_title',
            'question_options',
            'answer',
            'created_at',
            'updated_at',
        ]
 
 
class QuestionBriefSerializer(serializers.ModelSerializer):
    """Question serializer without timestamps — used for GET and PATCH."""
 
    class Meta:
        model = Question
        fields = [
            'id',
            'question_title',
            'question_options',
            'answer',
        ]
 
 
class QuizSerializer(serializers.ModelSerializer):
    """Quiz serializer with full question details including timestamps."""
 
    questions = QuestionSerializer(many=True, read_only=True)
 
    class Meta:
        model = Quiz
        fields = [
            'id',
            'title',
            'description',
            'created_at',
            'updated_at',
            'video_url',
            'questions',
        ]
 
 
class QuizBriefSerializer(serializers.ModelSerializer):
    """Quiz serializer with brief question details (no timestamps on questions)."""
 
    questions = QuestionBriefSerializer(many=True, read_only=True)
 
    class Meta:
        model = Quiz
        fields = [
            'id',
            'title',
            'description',
            'created_at',
            'updated_at',
            'video_url',
            'questions',
        ]

