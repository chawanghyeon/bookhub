import os
import shutil

from django.urls import reverse
from git.repo import Repo
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from collaboration.models import Comment, PullRequest
from fork.models import Fork
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
        repo.index.add(["*"])
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

    def test_delete_comment(self):
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
        response = self.client.delete(reverse("comment-detail", args=[comment.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Comment.objects.count(), 0)


class PullRequestViewSetTestCase(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user1", password="user1_password"
        )
        self.user2 = User.objects.create_user(
            username="user2", password="user2_password"
        )
        self.user1_token = RefreshToken.for_user(self.user1)
        self.user2_token = RefreshToken.for_user(self.user2)
        contents = os.listdir(REPO_ROOT)

        for item in contents:
            item_path = os.path.join(REPO_ROOT, item)
            if os.path.isfile(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        repo_dir = os.path.join(REPO_ROOT, self.user1.username, "test_repo")
        file_name = os.path.join(repo_dir, "README.txt")
        repo = Repo.init(repo_dir)
        open(
            file_name,
            "w",
        ).close()
        repo.index.add(["*"])
        repo.index.commit("initial commit")
        self.repo = Repository.objects.create(
            name="test_repo",
            superuser=self.user1,
            path=os.path.join(REPO_ROOT, self.user1.username, "test_repo"),
        )
        repo = Repo.clone_from(
            self.repo.path, os.path.join(REPO_ROOT, self.user2.username, "test_repo")
        )
        repo.index.add(["*"])
        repo.index.commit("initial commit")
        self.repo2 = Repository.objects.create(
            name="test_repo",
            superuser=self.user2,
            path=os.path.join(REPO_ROOT, self.user2.username, "test_repo"),
        )

        self.fork = Fork.objects.create(
            user=self.user1,
            source_repository=self.repo,
            target_repository=self.repo2,
        )

    def test_create_pull_request(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.user2_token.access_token}"
        )
        data = {
            "source_branch": "main",
            "target_branch": "main",
            "source_repository": self.fork.source_repository.id,
            "target_repository": self.fork.target_repository.id,
            "title": "test pull request",
            "text": "test pull request",
            "status": "open",
            "user": self.user2.id,
        }
        response = self.client.post(reverse("pullrequest-list"), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_pull_request_without_source_branch(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.user2_token.access_token}"
        )
        data = {
            "target_branch": "main",
            "source_repository": self.fork.source_repository.id,
            "target_repository": self.fork.target_repository.id,
            "title": "test pull request",
            "text": "test pull request",
            "status": "open",
            "user": self.user2.id,
        }
        response = self.client.post(reverse("pullrequest-list"), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_destory_pull_request(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.user2_token.access_token}"
        )
        data = {
            "source_branch": "main",
            "target_branch": "main",
            "source_repository": self.fork.source_repository.id,
            "target_repository": self.fork.target_repository.id,
            "title": "test pull request",
            "text": "test pull request",
            "status": "open",
            "user": self.user2.id,
        }
        response = self.client.post(reverse("pullrequest-list"), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        pull_request = PullRequest.objects.first()
        response = self.client.delete(
            reverse("pullrequest-detail", args=[pull_request.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(PullRequest.objects.count(), 0)
