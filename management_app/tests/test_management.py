from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch
from management_app.models import Quiz, Question

User = get_user_model()

MOCK_QUIZ_DATA = {
    "title": "Test Quiz",
    "description": "A test quiz description.",
    "questions": [
        {
            "question_title": f"Question {i}?",
            "question_options": ["A", "B", "C", "D"],
            "answer": "A"
        }
        for i in range(10)
    ]
}


class ManagementTestCase(APITestCase):
    """Base setup shared across all management tests."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpassword123'
        )
        self.quiz = Quiz.objects.create(
            user=self.user,
            title='My Quiz',
            description='My Description',
            video_url='https://www.youtube.com/watch?v=6Lef1CRNSCY'
        )
        for i in range(10):
            Question.objects.create(
                quiz=self.quiz,
                question_title=f'Question {i}?',
                question_options=['A', 'B', 'C', 'D'],
                answer='A'
            )
        self.list_url = reverse('quiz-list-create')
        self.detail_url = reverse('quiz-detail', kwargs={'id': self.quiz.id})
        self._authenticate(self.user)

    def _authenticate(self, user):
        refresh = RefreshToken.for_user(user)
        self.client.cookies['access_token'] = str(refresh.access_token)
        self.client.cookies['refresh_token'] = str(refresh)


class QuizListTests(ManagementTestCase):

    def test_get_quizzes_success(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_get_quizzes_unauthenticated(self):
        self.client.cookies.clear()
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 401)

    def test_get_quizzes_only_own(self):
        Quiz.objects.create(
            user=self.other_user,
            title='Other Quiz',
            description='Other Description',
            video_url='https://www.youtube.com/watch?v=6Lef1CRNSCY'
        )
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)


class QuizCreateTests(ManagementTestCase):

    @patch('management_app.api.views.os.remove')
    @patch('management_app.api.views.generate_quiz_with_gemini')
    @patch('management_app.api.views.transcribe_audio')
    @patch('management_app.api.views.download_audio')
    def test_create_quiz_success(self, mock_download, mock_transcribe, mock_gemini, mock_remove):
        import json
        mock_download.return_value = '/tmp/audio.mp3'
        mock_transcribe.return_value = 'Test transcript'
        mock_gemini.return_value = json.dumps(MOCK_QUIZ_DATA)

        response = self.client.post(self.list_url, {
            'url': 'https://www.youtube.com/watch?v=6Lef1CRNSCY'
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['title'], 'Test Quiz')
        self.assertEqual(len(response.data['questions']), 10)

    def test_create_quiz_missing_url(self):
        response = self.client.post(self.list_url, {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['detail'], 'URL is required.')

    def test_create_quiz_invalid_url(self):
        response = self.client.post(self.list_url, {'url': 'https://notyoutube.com/watch'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['detail'], 'Invalid YouTube URL.')

    @patch('management_app.api.views.download_audio', side_effect=Exception('Download failed'))
    def test_create_quiz_download_error(self, mock_download):
        response = self.client.post(self.list_url, {
            'url': 'https://www.youtube.com/watch?v=6Lef1CRNSCY'
        })
        self.assertEqual(response.status_code, 500)
        self.assertIn('Error processing video', response.data['detail'])

    @patch('management_app.api.views.generate_quiz_with_gemini', side_effect=Exception('Gemini failed'))
    @patch('management_app.api.views.transcribe_audio', return_value='transcript')
    @patch('management_app.api.views.os.remove')
    @patch('management_app.api.views.download_audio', return_value='/tmp/audio.mp3')
    def test_create_quiz_gemini_error(self, mock_download, mock_remove, mock_transcribe, mock_gemini):
        response = self.client.post(self.list_url, {
            'url': 'https://www.youtube.com/watch?v=6Lef1CRNSCY'
        })
        self.assertEqual(response.status_code, 500)
        self.assertIn('Error generating quiz', response.data['detail'])

    def test_create_quiz_unauthenticated(self):
        self.client.cookies.clear()
        response = self.client.post(self.list_url, {
            'url': 'https://www.youtube.com/watch?v=6Lef1CRNSCY'
        })
        self.assertEqual(response.status_code, 401)


class QuizDetailGetTests(ManagementTestCase):

    def test_get_quiz_success(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['title'], 'My Quiz')

    def test_get_quiz_not_found(self):
        response = self.client.get(reverse('quiz-detail', kwargs={'id': 9999}))
        self.assertEqual(response.status_code, 404)

    def test_get_quiz_wrong_user(self):
        self._authenticate(self.other_user)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 403)

    def test_get_quiz_unauthenticated(self):
        self.client.cookies.clear()
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 401)


class QuizPatchTests(ManagementTestCase):

    def test_patch_quiz_success(self):
        response = self.client.patch(self.detail_url, {'title': 'Updated Title'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['title'], 'Updated Title')

    def test_patch_quiz_not_found(self):
        response = self.client.patch(reverse('quiz-detail', kwargs={'id': 9999}), {'title': 'X'})
        self.assertEqual(response.status_code, 404)

    def test_patch_quiz_wrong_user(self):
        self._authenticate(self.other_user)
        response = self.client.patch(self.detail_url, {'title': 'Hacked'})
        self.assertEqual(response.status_code, 403)

    def test_patch_quiz_unauthenticated(self):
        self.client.cookies.clear()
        response = self.client.patch(self.detail_url, {'title': 'X'})
        self.assertEqual(response.status_code, 401)


class QuizDeleteTests(ManagementTestCase):

    def test_delete_quiz_success(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Quiz.objects.filter(id=self.quiz.id).exists())

    def test_delete_quiz_not_found(self):
        response = self.client.delete(reverse('quiz-detail', kwargs={'id': 9999}))
        self.assertEqual(response.status_code, 404)

    def test_delete_quiz_wrong_user(self):
        self._authenticate(self.other_user)
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, 403)

    def test_delete_quiz_unauthenticated(self):
        self.client.cookies.clear()
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, 401)