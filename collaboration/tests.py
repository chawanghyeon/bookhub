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
                "repository": self.repo.id,
                "commit": commit_hash,
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
        branch_name = "new-branch-name"
        new_branch = repo.create_head(branch_name)
        new_branch.checkout()
        repo.index.add(["*"])
        repo.index.commit("initial commit")
        self.repo2 = Repository.objects.create(
            name="test_repo",
            superuser=self.user2,
            path=os.path.join(REPO_ROOT, self.user2.username, "test_repo"),
        )

        self.fork = Fork.objects.create(
            user=self.user1,
            source_repository=self.repo2,
            target_repository=self.repo,
        )

    def test_create_pull_request(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.user2_token.access_token}"
        )

        with open(
            os.path.join(REPO_ROOT, self.user2.username, "test_repo", "README.txt"), "w"
        ) as f:
            f.write("test")

        repo = Repo(self.repo2.path)
        repo.index.add(["*"])
        repo.index.commit("test commit")
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

        remote = repo.remote(name="origin")
        remote.push(refspec=f"refs/heads/new-branch-name:refs/heads/new-branch-name")

        response = self.client.post(reverse("pullrequest-list"), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PullRequest.objects.count(), 1)
        self.assertEqual(PullRequest.objects.first().title, "test pull request")
        self.assertTrue(
            Repo(self.fork.target_repository.path).active_branch.name, "new-branch-name"
        )

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

    def test_check_difference(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.user2_token.access_token}"
        )

        with open(
            os.path.join(REPO_ROOT, self.user2.username, "test_repo", "README.txt"), "w"
        ) as f:
            f.write("test")

        repo = Repo(self.repo2.path)
        repo.index.add(["*"])
        repo.index.commit("test commit")
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

        remote = repo.remote(name="origin")
        remote.push(refspec=f"refs/heads/new-branch-name:refs/heads/new-branch-name")

        response = self.client.post(reverse("pullrequest-list"), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PullRequest.objects.count(), 1)
        self.assertEqual(PullRequest.objects.first().title, "test pull request")
        self.assertTrue(
            Repo(self.fork.target_repository.path).active_branch.name, "new-branch-name"
        )

        response = self.client.post(reverse("pullrequest-check", args=[1]), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue("test" in str(response.data))

    def test_approve_pull_request(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.user1_token.access_token}"
        )

        with open(
            os.path.join(REPO_ROOT, self.user2.username, "test_repo", "README.txt"), "w"
        ) as f:
            f.write("test")

        repo = Repo(self.repo2.path)
        repo.index.add(["*"])
        repo.index.commit("test commit")
        data = {
            "source_branch": "new-branch-name",
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
        self.assertEqual(PullRequest.objects.count(), 1)
        self.assertEqual(PullRequest.objects.first().title, "test pull request")
        self.assertTrue(
            Repo(self.fork.target_repository.path).active_branch.name, "new-branch-name"
        )

        response = self.client.post(reverse("pullrequest-approve", args=[1]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(PullRequest.objects.first().status, "merged")
        with open(
            os.path.join(REPO_ROOT, self.user1.username, "test_repo", "README.txt"), "r"
        ) as f:
            self.assertEqual(f.read(), "test")

    def test_approve_pull_request_with_another_user(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.user2_token.access_token}"
        )
        data = {
            "source_branch": "new-branch-name",
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
        response = self.client.post(reverse("pullrequest-approve", args=[1]), data={})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_approve_pull_request_with_conflict(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.user1_token.access_token}"
        )
        data = {
            "source_branch": "new-branch-name",
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

        with open(
            os.path.join(REPO_ROOT, self.user2.username, "test_repo", "README.txt"), "w"
        ) as f:
            f.write("test")

        repo = Repo(self.repo2.path)
        repo.index.add(["*"])
        repo.index.commit("test commit")

        with open(
            os.path.join(REPO_ROOT, self.user1.username, "test_repo", "README.txt"), "w"
        ) as f:
            f.write("asdfasdf")
        reop = Repo(self.repo.path)
        reop.index.add(["*"])
        reop.index.commit("test commit")

        response = self.client.post(reverse("pullrequest-approve", args=[1]), data={})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_pull_request(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.user1_token.access_token}"
        )
        data = {
            "source_branch": "new-branch-name",
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
        response = self.client.post(reverse("pullrequest-reject", args=[1]), data={})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(PullRequest.objects.first().status, "closed")
