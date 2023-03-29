# Bookhub

저는 평소에 소설책을 읽는 것을 즐깁니다. Github은 개발자들의 협업을 위한 사이트니까 작가들을 위한 협업 프로젝트를 만들면 어떨까 하는 생각에 시작하게 되었습니다.

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

## 배포

AWS EC2, Docker

## 실행 방법

```bash
git clone https://github.com/chawanghyeon/bookhub.git
pip install -r requirements.txt
python manage.py test
```
