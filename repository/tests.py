import os
import shutil

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from git.repo import Repo
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from project.settings import REPO_ROOT
from repository.models import Repository, Tag
from user.models import User


class RepositoryViewSetTestCase(APITestCase):
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
        repo_dir = os.path.join(REPO_ROOT, "test_repo")
        file_name = os.path.join(repo_dir, "README.txt")
        repo = Repo.init(repo_dir)
        open(
            file_name,
            "w",
        ).close()
        repo.index.add("*")
        repo.index.commit("initial commit")

    def test_create_repository(self):
        if os.path.exists(os.path.join(REPO_ROOT, "test_repo")):
            shutil.rmtree(os.path.join(REPO_ROOT, "test_repo"))

        response = self.client.post(
            reverse("repository-list"),
            data={"name": "test_repo"},
            HTTP_AUTHORIZATION=f"Bearer {self.user1_token.access_token}",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Repository.objects.count(), 1)
        self.assertEqual(Repository.objects.first().name, "test_repo")

    def test_retrieve_repository(self):
        repository = Repository.objects.create(
            name="test_repo",
            superuser=self.user1,
            path=os.path.join(REPO_ROOT, "test_repo"),
        )

        response = self.client.get(
            reverse("repository-detail", args=[repository.id]),
            HTTP_AUTHORIZATION=f"Bearer {self.user1_token.access_token}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "test_repo")

    def test_partial_update(self):
        new_content = "This is some new content."
        new_file = SimpleUploadedFile("README.txt", bytes(new_content, "utf-8"))

        repository = Repository.objects.create(
            name="test_repo",
            superuser=self.user1,
            path=os.path.join(REPO_ROOT, "test_repo"),
        )

        data = {"file": new_file, "message": "Updated README.txt"}
        response = self.client.patch(
            reverse("repository-file", args=[repository.id]),
            data,
            format="multipart",
            HTTP_AUTHORIZATION=f"Bearer {self.user1_token.access_token}",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        with open(os.path.join(repository.path, "README.txt"), "r") as f:
            file_content = f.read()
            self.assertIn(new_content, file_content)

        repo = Repo(repository.path)
        self.assertFalse(repo.is_dirty())
        self.assertEqual(repo.head.commit.message, data["message"])

    def test_partial_update_structure(self):
        repository = Repository.objects.create(
            name="test_repo",
            superuser=self.user1,
            path=os.path.join(REPO_ROOT, "test_repo"),
        )

        data = {
            "structure": '{"README.txt": "blob", "test": {"README.txt": "blob"}}',
            "message": "Updated README.txt",
        }
        response = self.client.patch(
            reverse("repository-structure", args=[repository.id]),
            data,
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {self.user1_token.access_token}",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(
            reverse("repository-detail", args=[repository.id]),
            HTTP_AUTHORIZATION=f"Bearer {self.user1_token.access_token}",
        )

        self.assertEqual(response.data["tree"], data["structure"])

    def test_destroy_repository(self):
        repository = Repository.objects.create(
            name="test_repo",
            superuser=self.user1,
            path=os.path.join(REPO_ROOT, "test_repo"),
        )

        response = self.client.delete(
            reverse("repository-detail", args=[repository.id]),
            HTTP_AUTHORIZATION=f"Bearer {self.user1_token.access_token}",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Repository.objects.count(), 0)
        self.assertFalse(os.path.exists(repository.path))

    def test_list_repositories(self):
        Repository.objects.bulk_create(
            [
                Repository(
                    name=f"test_repo{i}",
                    superuser=self.user1,
                    path=os.path.join(REPO_ROOT, f"test_repo{i}"),
                    star_count=i,
                )
                for i in range(10)
            ]
        )

        response = self.client.get(
            reverse("repository-list"),
            HTTP_AUTHORIZATION=f"Bearer {self.user1_token.access_token}",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 5)
        self.assertEqual(response.data["results"][0]["name"], "test_repo9")

    def test_list_repositories_by_tag(self):
        tag1 = Tag.objects.create(name="test1")
        tag2 = Tag.objects.create(name="test2")

        for i in range(6):
            repository = Repository.objects.create(
                name=f"test_repo{i}",
                superuser=self.user1,
                path=os.path.join(REPO_ROOT, f"test_repo{i}"),
            )
            repository.tags.set([tag1])

        for i in range(6, 10):
            repository = Repository.objects.create(
                name=f"test_repo{i}",
                superuser=self.user1,
                path=os.path.join(REPO_ROOT, f"test_repo{i}"),
            )
            repository.tags.set([tag2])

        response = self.client.get(
            reverse("repository-tag"),
            data={"tag": "test1"},
            HTTP_AUTHORIZATION=f"Bearer {self.user1_token.access_token}",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 5)

        response = self.client.get(
            reverse("repository-tag"),
            data={"tag": "test2"},
            HTTP_AUTHORIZATION=f"Bearer {self.user1_token.access_token}",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 4)

    def test_list_repositories_by_name(self):
        for i in range(10):
            Repository.objects.create(
                name=f"test_repo{i}",
                superuser=self.user1,
                path=os.path.join(REPO_ROOT, f"test_repo{i}"),
            )

        response = self.client.get(
            reverse("repository-name"),
            data={"name": "test_repo1"},
            HTTP_AUTHORIZATION=f"Bearer {self.user1_token.access_token}",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "test_repo1")

    def test_update_name(self):
        repository = Repository.objects.create(
            name="test_repo",
            superuser=self.user1,
            path=os.path.join(REPO_ROOT, "test_repo"),
        )

        data = {
            "old_name": "README.txt",
            "new_name": "AFTER.txt",
            "message": "test_update",
        }
        response = self.client.patch(
            reverse("repository-name", args=[repository.id]),
            data,
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {self.user1_token.access_token}",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(os.path.exists(os.path.join(repository.path, "AFTER.txt")))

    def test_create_branch(self):
        repository = Repository.objects.create(
            name="test_repo",
            superuser=self.user1,
            path=os.path.join(REPO_ROOT, "test_repo"),
        )

        data = {"branch_name": "test_branch", "message": "test_create_branch"}
        response = self.client.post(
            reverse("repository-branch", args=[repository.id]),
            data,
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {self.user1_token.access_token}",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            os.path.exists(
                os.path.join(repository.path, ".git", "refs", "heads", "test_branch")
            )
        )
