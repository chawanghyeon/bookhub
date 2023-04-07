import os
import shutil

from django.urls import reverse
from git.repo import Repo
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from comments.models import Comment
from project.settings import REPO_ROOT
from repositories.models import Repository
from users.models import User


class CommentViewSetTestCase(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create(
            username="user1@user1.com", password="user1_password"
        )
        self.user1_token = RefreshToken.for_user(self.user1).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.user1_token}")

        for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
            for file in filenames:
                os.remove(os.path.join(dirpath, file))
            for dirname in dirnames:
                shutil.rmtree(os.path.join(dirpath, dirname))

        repo_path = os.path.join(REPO_ROOT, self.user1.username, "test_repo")
        file_path = os.path.join(repo_path, "README.txt")

        repo = Repo.init(repo_path)
        open(file_path, "w").close()
        repo.index.add(["*"])
        repo.index.commit("initial commit")

        self.repo = Repository.objects.create(
            name="test_repo",
            user=self.user1,
            path=os.path.join(REPO_ROOT, self.user1.username, "test_repo"),
        )

    def test_create_comment(self):
        response = self.client.post(
            reverse("comments-list"),
            {
                "text": "test comment",
                "repository": self.repo.id,
                "commit": Repo(self.repo.path).head.commit.hexsha,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(Comment.objects.first().text, "test comment")

    def test_create_comment_without_commit(self):
        response = self.client.post(
            reverse("comments-list"),
            {
                "text": "test comment",
                "repository": self.repo.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Comment.objects.count(), 0)

    def test_partial_update_comment(self):
        self.test_create_comment()
        response = self.client.patch(
            reverse("comments-detail", args=[1]),
            {
                "text": "updated comment",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(Comment.objects.first().text, "updated comment")

    def test_partial_update_comment_without_text(self):
        self.test_create_comment()
        response = self.client.patch(
            reverse("comments-detail", args=[1]),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(Comment.objects.first().text, "test comment")

    def test_delete_comment(self):
        self.test_create_comment()
        response = self.client.delete(reverse("comments-detail", args=[1]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Comment.objects.count(), 0)
