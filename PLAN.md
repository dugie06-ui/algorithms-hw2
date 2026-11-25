# 구현 계획

`SPEC.md`를 읽고 세운 순서다. 코드는 이 계획을 사람이 확인한 뒤에 쓴다.
각 단계는 이슈 하나, `feature/<이슈번호>-<이름>` 브랜치 하나, `Step N: 한 일 (#N)` 커밋이다.

## 지킬 것

- `src/`에서 `dict`, `set`, 내장 `hash()`를 쓰지 않는다. URL→코드 저장도 직접 만든 `HashTable`로 한다.
- 코드는 URL의 해시값이 아니라 **일련번호의 base62**로 만든다.
- **테스트를 먼저** 쓰고(이때 실패는 정상), 구현은 테스트를 고치지 않고 통과시킨다.
- 단계마다 `make test`를 돌리고 결과를 확인한 뒤 커밋한다.

## 4단계 · 테스트 먼저

1. `tests/test_hash_table.py`: SPEC 6절의 해시 테이블 경계 사례를 옮긴다.
   - 공통 동작(넣기, 바꾸기, 찾기, 개수, 적재율, 늘리기, 잘못된 입력)은 `make_table()` 하나로 테이블을 만드는
     클래스에 모은다. 과제에서 선형 탐지 테이블에 그대로 다시 돌리기 위해서다.
   - 체이닝에만 해당하는 것(같은 칸 체인, 비교 노드 수, α > 1)은 따로 둔다.
2. `tests/test_shortener.py`: SPEC 6절의 단축기 경계 사례를 옮긴다.
3. `make test` → 실패 확인 (구현 전이므로 정상).

## 4단계 · 구현

1. `src/hash_table.py`
   1. `horner(key, m)`와 계산 과정을 돌려주는 `horner_steps(key, m)`
   2. `_Node`(키, 값, 다음)와 `HashTable.__init__`(칸 목록은 `[None] * capacity`)
   3. `find` → `get`, `__contains__`, `__len__`, `load_factor`
   4. `put` (체인 끝에 붙이기, 있으면 값 바꾸기)
   5. `_grow` (`2M` 이상 가장 작은 소수, 다시 넣기)
   6. `buckets()`
2. `src/shortener.py`
   1. `validate_url(url)` (앞뒤 공백 제거, scheme, 호스트, 공백·제어 문자, 길이)
   2. `Shortener`: URL→코드, 코드→URL 두 `HashTable`, 일련번호, 예약어(`table`) 건너뛰기
   3. `shorten`, `expand`, `__len__`
3. `make test`가 통과할 때까지 구현만 고친다.

## 5단계 · 규칙 파일

1. `grep -n "dict\|set(\|hash(" src/*.py`로 금지 요소를 찾는다.
2. `.github/copilot-instructions.md`를 만든다.
3. 새 채팅에서 규칙 위반을 검사해 고친다.

## 6단계 · 적재율 실험

1. `experiments/probe_experiment.py`: 칸 수 4093, `HashTable(capacity=4093, max_load=None)`.
2. 적재율 0.25, 0.5, …, 4에서 무작위 URL을 넣고
   - 성공 탐색: 넣은 키 전부를 `find`한 평균 비교 노드 수
   - 실패 탐색: 넣지 않은 키를 `find`한 평균 비교 노드 수
3. 이론값(성공 1 + α/2, 실패 α)과 표로 비교, `experiments/results.csv`와 SVG 그래프 저장. 외부 라이브러리 없이.

## 7단계 · 서버

1. `src/server.py`: `http.server`의 `BaseHTTPRequestHandler`.
2. `/` 폼, `POST /shorten` 결과, `/<코드>` 302, `/table` 시각화, 그 밖 404.
3. 짧은 링크 주소는 `X-Forwarded-Proto`/`X-Forwarded-Host` → `Host` → `localhost:<포트>` 순서.
4. `tests/test_server.py`: 포트 0으로 서버를 띄워 실제 요청으로 확인.

## 과제 · 선형 탐지 (#8)

1. `src/probing_table.py`: `ProbingTable`, `HashTable`과 같은 인터페이스, 같은 호너 해시.
2. 공통 해시 테이블 테스트를 선형 탐지에도 돌리고, 끝 칸→0번 칸, 가득 찬 테이블을 더한다.
3. `Shortener(table="chain" | "probe")`, 단축기 테스트를 두 방식 모두에서 돌린다.
4. `experiments/compare_experiment.py`: 같은 키·같은 크기, α 0.1~0.9, 이론값과 함께 그래프.
5. `/table`에 선형 탐지 테이블 표시 (`make serve TABLE=probe`).
