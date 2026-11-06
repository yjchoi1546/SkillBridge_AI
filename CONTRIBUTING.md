# Git Convention

## Commit 메시지

형식: `type: 작업 내용`

- `feat`: 새로운 기능 구현
- `add`: 파일 및 리소스 추가
- `fix`: 버그 및 오류 수정
- `refactor`: 기능 변경 없는 코드 구조 개선
- `docs`: 문서 작성 및 수정
- `test`: 테스트 코드 작성 및 수정
- `chore`: 설정 및 기타 작업
- `remove`: 불필요한 파일 및 코드 삭제

## Branch Convention

형식: `type/작업명`

- `feat/기능명`: 신규 기능 개발
- `fix/기능명`: 버그 수정
- `refactor/기능명`: 코드 리팩토링
- `docs/작업명`: 문서 수정
- `chore/작업명`: 설정 및 기타 작업

예시: `feat/user-login`

## Note

1. **개인 브랜치 사용** — 각자 작업 브랜치를 생성하여 개발
2. **PR 생략** — 별도의 Pull Request 및 코드 리뷰 과정 없음
3. **작업 시작 전** — `main` 브랜치 최신 코드 pull
4. **작업 완료 후** — 개인 브랜치에 commit 및 push
5. **Merge 전** — 최신 main 반영 및 충돌 여부 확인
6. **Force Push 금지** — `--force`, `-f` 사용 금지
7. **Merge 완료 후** — 사용한 작업 브랜치 삭제

## 작업 순서

1. `git switch main`
2. `git pull origin main`
3. `git switch -c feat/기능명`
4. 코드 작업
5. `git add .`
6. `git commit -m "feat: 작업 내용"`
7. `git push origin feat/기능명`
8. 최신 main 반영
9. main에 Merge 및 Push
10. 작업 브랜치 삭제