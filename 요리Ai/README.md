# AI 요리 시뮬레이터 웹 앱

## Netlify 공개 배포

이 프로젝트는 정적 웹 화면과 Netlify Function API로 구성됩니다. `web_app.py`는 로컬 개발용 Flask 서버입니다. Netlify는 Flask 서버를 직접 실행하지 않으므로, 배포할 때 `netlify/functions/api.mjs`를 사용합니다.

1. 프로젝트의 모든 파일과 폴더를 GitHub 저장소에 올립니다. `templates`, `static`, `netlify/functions` 폴더 구조를 유지하세요. `.env`, API 키, `.venv`, `site` 폴더는 올리지 않습니다.
2. Netlify에 로그인하고 **Add new site → Import an existing project**에서 GitHub 저장소를 연결합니다.
3. 저장소에 있는 `netlify.toml` 설정을 확인합니다. Build command는 `python3 build_netlify.py`, publish directory는 `site`, functions directory는 `netlify/functions`입니다.
4. Netlify 사이트 설정의 **Environment variables**에서 다음 변수를 추가합니다.
   - `SPOONACULAR_API_KEY`
   - `GOOGLE_TRANSLATE_API_KEY`
5. 사이트를 배포하고 제공된 HTTPS 주소를 엽니다. API 키를 코드, GitHub 저장소, 브라우저 코드에 넣지 마세요.

Netlify에 올리는 데는 GitHub 연결 방식이 권장됩니다. `site` 폴더는 빌드 때 `build_netlify.py`가 생성하며 `.gitignore`에서 제외되어 있습니다. Netlify 설정을 바꾼 뒤에는 다시 배포하세요.

## 로컬 실행

Python 3.10 이상에서 프로젝트 폴더의 PowerShell 터미널을 열고 실행합니다.

```powershell
python -m pip install -r requirements.txt
python web_app.py
```

브라우저에서 `http://127.0.0.1:5000`을 엽니다. 서버를 종료하려면 터미널에서 `Ctrl+C`를 누릅니다.

## API 및 비용 안내

Spoonacular 레시피 API와 Google Cloud Translation은 서버 측 환경변수를 사용합니다. 키가 없거나 레시피 API 요청이 실패하면 로컬 샘플 레시피를 사용할 수 있습니다. 번역 API 키가 없으면 한국어 이외의 번역 요청은 오류를 표시합니다.

공개 사이트의 방문자는 서버 Function을 호출할 수 있습니다. Spoonacular 요청 한도와 Google Cloud 결제·사용량 알림을 설정하고, 공개 후 사용량을 확인하세요. 키가 유출되었다고 의심되면 해당 제공자에서 폐기하고 새 키로 교체합니다.

냉장고 재료와 언어 설정은 각 방문자의 브라우저 로컬 저장소에 저장됩니다. 별도 계정이나 서버 측 동기화는 제공하지 않습니다.

## 제공 기능

- 레시피 검색 및 냉장고 재료 기반 최대 5개 추천
- 브라우저에 재료·수량 저장
- 조리 타이머, 화력 조절, 단계 진행 및 결과 평가
- 재료를 냄비로 드래그하고 칼로 재료 자르기
- 한국어·영어·일본어·중국어 UI 자동 번역
