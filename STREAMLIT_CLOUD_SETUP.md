# Streamlit Cloud 배포 설정 가이드

## 문제 해결: API_KEY 환경변수 설정

Streamlit Cloud에서는 `.env` 파일이 작동하지 않습니다. 대신 **Streamlit Secrets**를 사용해야 합니다.

## 설정 방법

### 1. Streamlit Cloud 대시보드 접속
- [Streamlit Cloud](https://share.streamlit.io/)에 로그인
- 배포된 앱을 선택

### 2. Secrets 설정
1. 좌측 메뉴에서 **"⚙️ Settings"** 클릭
2. **"Secrets"** 탭 선택
3. 다음 형식으로 Secrets 추가:

```toml
API_KEY = "your_actual_api_key_here"
MODEL_NAME = "gpt-4o-mini"
```

4. 필요시 `API_BASE_URL`도 추가:
```toml
API_BASE_URL = "your_api_base_url_here"
```

### 3. 저장 및 재배포
- **"Save"** 버튼 클릭
- 앱이 자동으로 재배포됩니다 (또는 수동으로 재배포)

## 로컬 개발 환경

로컬에서 개발할 때는 `.env` 파일을 사용할 수 있습니다:

1. 프로젝트 루트에 `.env` 파일 생성
2. 다음 내용 추가:
```
API_KEY=your_api_key_here
MODEL_NAME=gpt-4o-mini
API_BASE_URL=your_api_base_url_here  # 선택사항
```

## 코드 변경 사항

코드는 자동으로 다음 순서로 환경변수를 확인합니다:
1. **Streamlit Secrets** (Streamlit Cloud 배포 시)
2. **환경변수** (로컬 개발 시 `.env` 파일)

이제 로컬과 클라우드 모두에서 동일한 코드로 작동합니다!

