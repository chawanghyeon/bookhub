# Bookhub

평소 소설책을 즐기는 저는 작가들을 위한 협업 플랫폼 프로젝트를 시작하게 되었습니다. 이 플랫폼은 작가들이 이야기 구상, 플롯 개발, 작품 검토 및 수정을 자유롭게 할 수 있는 공간을 제공합니다. 

서로의 아이디어를 공유하고 피드백을 받아 작품을 개선할 수 있으며, 공동 집필이나 크로스오버 협업도 가능합니다. 작가들은 이를 통해 작품의 질을 높이고 독자들에게 더 풍부한 독서 경험을 선사할 수 있습니다.

## 1. 사용한 기술스택

Django RestFramework, RestFramework-SimpleJWT, GitPython, Docker, Nginx, PostgreSQL, Gunicorn

## 2. 데이터베이스 설계

- `User`: 사용자 정보(Django의 AbstractUser상속)
    - id (PK): 사용자 식별자
    - username: 이메일 (unique, 이메일로 회원가입)
- **`Repository`**: 저장소 정보
    - id (PK): 저장소 식별자
    - name: 저장소 이름
    - user_id: 사용자 식별자
    - owners: 저장소 소유자들 (User와 ManyToMany 관계)
    - members: 저장소 멤버들 (User와 ManyToMany 관계)
    - path: 저장소 경로 (unique)
    - created: 생성 시간
    - tags: 저장소 태그들 (Tag와 ManyToMany 관계)
    - star_count: 스타 개수
    - fork_count: 포크 개수
    - private: 비공개 여부
    - fork: 포크 여부
- **`Star`**: 스타 정보
    - id (PK): 스타 식별자
    - user_id: 사용자 식별자
    - repository_id: 저장소 식별자
- **`Tag`**: 태그 정보
    - id (PK): 태그 식별자
    - name: 태그 이름 (unique)
- **`PullRequest`**: 풀 리퀘스트 정보
    - title: 제목
    - text: 설명
    - source_branch: 출처 브랜치
    - source_repository_id: 출처 저장소 (Repository 외래키)
    - target_branch: 목표 브랜치
    - target_repository_id: 목표 저장소 (Repository 외래키)
    - user_id: 사용자 식별자
    - created: 생성 시간
    - updated: 업데이트 시간
    - status: 상태 (open, closed, merged)
- **`Fork`**: 포크 정보
    - id (PK): 포크 식별자
    - user_id: 사용자 식별자
    - source_repository_id: 원본 저장소 (Repository 외래키)
    - target_repository_id: 대상 저장소 (Repository 외래키)
- **`Comment`**: 댓글 정보
    - id (PK): 댓글 식별자
    - user_id: 사용자 식별자
    - repository_id: 댓글이 달린 저장소 (Repository 외래키)
    - commit: 커밋
    - text: 댓글 내용
    - created: 생성 시간

## 3. RESTful API 설계

- User 관련 API
    - `GET /users/<id>`: 특정 유저 조회
    - `DELETE /users/<id>`: 특정 유저 삭제
- Auth 관련 API
    - `POST /auth/signin`: 로그인
    - `POST /auth/signup`: 회원가입
- Repository 관련 API
    - `GET /repositories`: 저장소 목록 조회
    - `POST /repositories`: 저장소 생성
    - `GET /repositories/<id>`: 특정 저장소 조회
    - `DELETE /repositories/<id>`: 특정 저장소 삭제
    - `PATCH /repositories/<id>/file`: 특정 저장소의 파일 업데이트
    - `PATCH /repositories/<id>/structure`: 특정 저장소의 구조 업데이트
    - `PATCH /repositories/<id>/rename`: 특정 저장소의 이름 업데이트
    - `GET /repositories/<id>/workingtree`: 특정 저장소의 워킹트리 조회
    - `GET /repositories/<id>/commits`: 특정 저장소의 커밋 목록 조회
    - `GET /repositories/<id>/content`: 특정 저장소의 파일 내용 조회
    - `PUT /repositories/<id>/rollback`: 특정 저장소의 롤백
- Star 관련 API
    - `GET /users/<id>/stars`: 유저가 좋아요 누른 저장소 목록 조회
    - `POST /repositories/<id>/stars`: 스타 생성
    - `DELETE /repositories/<id>/stars`: 스타 삭제
- Branch 관련 API
    - `GET /repositories/<id>/branches`: 특정 저장소에 브랜치 생성
    - `POST /repositories/<id>/branches`: 특정 저장소에 브랜치 생성
    - `PUT /repositories/<id>/branches/<name>`: 특정 브랜치 업데이트
    - `DELETE /repositories/<id>/branches/<name>`: 특정 브랜치 삭제
- Tag 관련 API
    - `GET /repositories/tags/<name>`: 특정 태그를 포함하는 저장소 목록 조회
- PullRequest 관련 API
    - `POST /repositories/<id>/pull-requests`: 풀 리퀘스트 생성
    - `DELETE /repositories/<id>/pull-requests/<id>`: 특정 풀 리퀘스트 삭제
    - `GET /repositories/<id>/pull-requests/<id>/check`: 특정 풀 리퀘스트 워킹트리 조회
    - `POST /repositories/<id>/pull-requests/<id>/approve`: 특정 풀 리퀘스트 승인
    - `POST /repositories/<id>/pull-requests/<id>/reject`: 특정 풀 리퀘스트 거절
    - `POST /repositories/<id>/pull-requests/<id>/resolve`: 특정 풀 리퀘스트 충돌 해결
- Fork 관련 API
    - `POST /repositories/<id>/forks`: 포크 생성
    - `DELETE /repositories/<id>/forks`: 포크 삭제
- Comment 관련 API
    - `POST /repositories/<id>/comments`: 댓글 생성
    - `PATCH /repositories/<id>/comments/<id>`: 특정 댓글 부분 업데이트
    - `DELETE /repositories/<id>/comments/<id>`: 특정 댓글 삭제
    - `POST /repositories/<id>/comments/<id>`: 특정 댓글 삭제

## 4. 문제해결

1. 경로충돌
    - @action를 사용할 때 경로이름을 같게 설정해 오류가 발생했습니다. urlpatterns에 경로를 명시적으로 등록해 해결했습니다.
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
            
2. Docker [localhost](http://localhost)주소 오류
    - nginx에서 gunicorn으로 연결할 때 오류가 발생했습니다. 도커는 독립된 공간이라 [localhost](http://localhost) 주소로 다른 컨테이너에 접근하지 못해 발생했다고 생각합니다. gunicorn 시작명령에 -bind 0.0.0.0:8000을 추가해 해결했습니다.
        - 오류가 발생한 부분
            
            ```python
            gunicorn project.wsgi:application --workers=4
            ```
            
        - 해결한 방법
            
            ```python
            gunicorn project.wsgi:application --workers=4 --bind 0.0.0.0:8000
            ```
            
3. 속도 개선
    - 장고 자체는 싱글스레드로 작동해서 많은 요청이 들어오면 속도가 굉장히 느립니다. 그래서 gunicorn같은 wsgi 서버를 사용해 worker들을 만들어 해결했습니다
        - workers=2
            
            ![2](https://user-images.githubusercontent.com/53591258/228712228-7b465999-e42e-478a-98ee-8bb8fae5bb67.png)
            
        - workers=4
            
            ![4](https://user-images.githubusercontent.com/53591258/228712320-322f01e7-353d-4c15-907f-c69c550db91b.png)
            
4. is_active 설정
    - Django의 로그인 기능을 사용하기 위해서는 **AbstractUser를 사용해야 하는데 유저를 만들 때 username과 password만 입력해서 가입은 되지만 로그인이 안되는 문제가 발생했습니다. 기본 데이터와 함께 is_active=True도 함께 넘겨줘 로그인이 가능하게 만들어 해결했습니다.**
        - 해결한 방법
            
            ```python
            serializer.save(
                password=make_password(request.data.get("password")), is_active=True
            )
            ```
            
5. 충돌 해결이 안되는 오류
    - pullrequest를 merge할 때 발생한 충돌을 해결한 뒤 다시 커밋할 때 아직 충돌이 해결이 안됐다는 문제가 발생했습니다 커밋하기 전에 target_repo.index.remove([path]) 이 부분을 추가해 git 저장소에서 삭제한 후 다시 add하고 커밋을 해서 해결했습니다.
6. 도커 이미지 빌드 오류
    - m1 맥북에서 빌드한 도커 이미지가 AWS EC2 linux/amd64 instance에서 실행할 수 없는 문제가 발생했었습니다. 도커 이미지를 빌드할 때 —platform=linux/amd64명령을 추가해 해결했습니다.
7. URL구조 개선
    - 프로젝트를 진행하면서 REST API 설계에 대한 이해가 깊어졌다고 느꼈습니다. 처음에는 단순히 앱 별로 API를 나누는 것만으로도 REST API를 만들 수 있다고 생각했지만, 문서 작성 과정에서 기존의 API 설계가 적절하지 않음을 깨달았습니다. RESTful API를 만들기 위해서는 리소스의 효율적인 사용과 직관적인 계층 구조를 잘 고려해야 한다는 것을 알게 되었습니다.

## 5. 프로젝트를 진행하면서 느낀점

1. 설계의 중요성
    - 프로젝트를 진행하면서 제대로 된 설계 문서의 중요성을 깨닫게 되었습니다. 초보적인 수준의 설계보다는 보다 체계적이고 명확하게 문서화된 설계가 프로젝트의 성공에 큰 도움이 된다는 것을 알게 되었습니다.
2. 파이썬 라이브러리의 다양성
    - 프로젝트를 성공적으로 진행하기 위해 버전 관리 시스템의 구현이 필요했습니다. 처음에는 그 구현이 매우 어려워 보여서 포기할까 생각했습니다. 그러나 여러 방안을 탐색하는 과정에서 Python을 활용하여 Git을 사용할 수 있는 방법이 없을까 조사하였습니다. 이 과정에서 GitPython이라는 강력한 라이브러리를 발견하여, 이를 활용해 프로젝트를 성공적으로 완수할 수 있었습니다.
3. 비지니스 로직 분리
    - 이전 프로젝트인 Babble에서는 `utils.py`파일을 만들어 복잡한 비즈니스 로직을 분리하여 코드를 관리했습니다. 반면, 최근 프로젝트에서는 `views.py`의 각 함수를 중첩 함수로 구현하여 복잡한 비즈니스 로직을 분리해 보았습니다. 개인적인 생각으로는 `utils.py`파일을 생성하여 `views.py`를 가볍게 만드는 것이 더 좋은 방법이라고 느꼈습니다. 더 좋은 방법을 가르쳐주시면 감사하겠습니다!
