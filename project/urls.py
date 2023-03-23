"""audiotwitter URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from collaboration.views import CollaborationViewSet
from fork.views import ForkViewSet
from repository.views import RepositoryViewSet
from star.views import StarViewSet
from user.views import UserViewSet

router = DefaultRouter()
router.register(r"user", UserViewSet, basename="user")
router.register(r"repository", RepositoryViewSet, basename="repository")
router.register(r"collaboration", CollaborationViewSet, basename="collaboration")
router.register(r"fork", ForkViewSet, basename="fork")
router.register(r"star", StarViewSet, basename="star")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include(router.urls)),
    path(
        "repositories/<int:pk>/branch/",
        RepositoryViewSet.as_view(
            {
                "post": "create_branch",
                "delete": "delete_branch",
                "patch": "update_branch",
                "get": "list_branches",
            }
        ),
        name="repository-branch",
    ),
]

# swagger
urlpatterns += [
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]

# Simple JWT
urlpatterns += [
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
]
