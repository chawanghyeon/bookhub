import os
import shutil

from django.urls import reverse
from git.repo import Repo
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from collaboration.models import Comment
from project.settings import REPO_ROOT
from repository.models import Repository
from user.models import User


class CommentViewSetTestCase(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user1", password="user1_password"
        )
        self.user1_token = RefreshToken.for_user(self.user1)
        contents = os.listdir(REPO_ROOT)

        for item in contents:
            item_path = os.path.join(REPO_ROOT, item)
            if os.path.isfile(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        repo_dir = os.path.join(REPO_ROOT, "test_user", "test_repo")
        file_name = os.path.join(repo_dir, "README.txt")
        repo = Repo.init(repo_dir)
        open(
            file_name,
            "w",
        ).close()
        repo.index.add("*")
        repo.index.commit("initial commit")
        self.repo = Repository.objects.create(
            name="test_repo",
            superuser=self.user1,
            path=os.path.join(REPO_ROOT, "test_user", "test_repo"),
        )

    def test_create_comment(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.user1_token.access_token}"
        )
        repo = Repo(self.repo.path)
        commit_hash = repo.head.commit.hexsha
        response = self.client.post(
            reverse("comment-list"),
            {
                "text": "test comment",
                "commit": commit_hash,
                "repository": self.repo.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(Comment.objects.first().text, "test comment")

    def test_create_comment_without_commit(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.user1_token.access_token}"
        )
        response = self.client.post(
            reverse("comment-list"),
            {
                "text": "test comment",
                "repository": self.repo.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Comment.objects.count(), 0)

    def test_partial_update_comment(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.user1_token.access_token}"
        )
        repo = Repo(self.repo.path)
        commit_hash = repo.head.commit.hexsha
        comment = Comment.objects.create(
            user=self.user1,
            repository=self.repo,
            commit=commit_hash,
            text="test comment",
        )
        response = self.client.patch(
            reverse("comment-detail", kwargs={"pk": comment.id}),
            {
                "text": "updated comment",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(Comment.objects.first().text, "updated comment")

    def test_partial_update_comment_without_text(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.user1_token.access_token}"
        )
        repo = Repo(self.repo.path)
        commit_hash = repo.head.commit.hexsha
        comment = Comment.objects.create(
            user=self.user1,
            repository=self.repo,
            commit=commit_hash,
            text="test comment",
        )
        response = self.client.patch(
            reverse("comment-detail", kwargs={"pk": comment.id}),
            {},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(Comment.objects.first().text, "test comment")
