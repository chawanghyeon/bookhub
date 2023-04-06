# Bookhub

저는 평소에 소설책을 읽는 것을 즐깁니다. 평소에 책에 관심이 많던 저는 Github은 개발자들의 협업을 위한 사이트니까 작가들을 위한 협업 프로젝트를 만들면 어떨까 하는 생각에 시작하게 되었습니다.

## 사용한 기술스택

Django restframework, restframework-simplejwt, GitPython, Docker, nginx, postgresql, gunicorn

## 구현기능

- comment
    - 특정 커밋 해쉬에 코멘트 추가, 삭제, 업데이트
- fork
    - 특정 레파지토리를 클론, 삭제
- pullrequest
    - 추가, 삭제, 워킹트리의 차이점 보기, 승인, 거절, 충돌 해결
- repository
    - 추가, 검색, 삭제, 파일 업데이트, 폴더구조 업데이트, 이름 업데이트, 워킹트리 보기, 커밋 리스트, 특정 커밋으로 되돌아가기, 파일 내용 가져오기
- star
    - 추가, 삭제
- branch
    - 추가, 삭제, 업데이트, 리스트
- user
    - 가입, 로그인, 검색, 삭제

## 문제해결

1. @action를 사용할 때 경로이름을 같게 설정해 오류가 발생했습니다. urlpatterns에 경로를 명시적으로 등록해 해결했습니다.
    - 오류가 발생한 부분
        
        ```python
        @action(detail=True, methods=["post"], url_path="branch", url_name="branch")
        @action(detail=True, methods=["delete"], url_path="branch", url_name="branch")
        ```
        
    - 해결한 방법
        
        ```python
        urlpatterns = [
        	path("", include(router.urls)),
        	path("repositories/int:pk/branch/", RepositoryViewSet.as_view({"post": "create_branch", "delete": "delete_branch"}), name="repository-branch"),
        ]
        ```
        
2. nginx에서 gunicorn으로 연결할 때 오류가 발생했습니다. 도커는 독립된 공간이라 [localhost](http://localhost) 주소로 다른 컨테이너에 접근하지 못해 발생했다고 생각합니다. gunicorn 시작명령에 -bind 0.0.0.0:8000을 추가해 해결했습니다.
    - 오류가 발생한 부분
        
        ```python
        gunicorn project.wsgi:application --workers=4
        ```
        
    - 해결한 방법
        
        ```python
        gunicorn project.wsgi:application --workers=4 --bind 0.0.0.0:8000
        ```
        
3. 장고 자체는 싱글스레드로 작동해서 많은 요청이 들어오면 속도가 굉장히 느립니다. 그래서 gunicorn같은 wsgi 서버를 사용해 worker들을 만들어 해결했습니다
    - workers=2
        
        ![2](https://user-images.githubusercontent.com/53591258/228712228-7b465999-e42e-478a-98ee-8bb8fae5bb67.png)
        
    - workers=4
        
        ![4](https://user-images.githubusercontent.com/53591258/228712320-322f01e7-353d-4c15-907f-c69c550db91b.png)
        
4. Django의 로그인 기능을 사용하기 위해서는 **AbstractUser를 사용해야 하는데 유저를 만들 때 username과 password만 입력해서 가입은 되지만 로그인이 안되는 문제가 발생했습니다. 기본 데이터와 함께 is_active=True도 함께 넘겨줘 로그인이 가능하게 만들어 해결했습니다.**
    - 해결한 방법
        
        ```python
        serializer.save(
        	password=make_password(request.data.get("password")), is_active=True
        )
        ```
        
5. pullrequest를 merge할 때 발생한 충돌을 해결한 뒤 다시 커밋할 때 아직 충돌이 해결이 안됐다는 문제가 발생했습니다 커밋하기 전에 target_repo.index.remove([path]) 이 부분을 추가해 git 저장소에서 삭제한 후 다시 add하고 커밋을 해서 해결했습니다.
6. m1 맥북에서 빌드한 도커 이미지가 AWS EC2 linux/amd64 instance에서 실행할 수 없는 문제가 발생했었습니다. 도커 이미지를 빌드할 때 —platform=linux/amd64명령을 추가해 해결했습니다.

## 배포

AWS EC2, Docker
