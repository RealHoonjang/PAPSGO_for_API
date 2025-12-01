# streamlit_app.py
from pathlib import Path
import re
import json
import streamlit as st
from streamlit.components.v1 import html as st_html
import streamlit.components.v1 as components
from streamlit_javascript import st_javascript
from dotenv import load_dotenv
from chat_module import PAPSChatbot
import time

# .env 파일 명시적으로 로드
root = Path(__file__).parent
env_path = root / '.env'
load_dotenv(dotenv_path=env_path)

st.set_page_config(page_title="PAPS Calculator", layout="wide", initial_sidebar_state="collapsed")

# 통합된 모던한 스타일 적용
st.markdown("""
<style>
    /* 전체 페이지 스타일 */
    .main {
        padding-top: 1rem;
    }
    
    /* 탭 스타일 개선 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        padding: 10px 0;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 12px 24px;
        font-size: 18px;
        font-weight: 600;
    }
    
    /* iframe 스타일 개선 */
    iframe {
        border: none !important;
        border-radius: 8px;
    }
    
    /* 버튼 스타일 */
    .stButton > button {
        width: 100%;
        font-size: 16px;
        font-weight: 600;
        padding: 12px 24px;
        border-radius: 8px;
        transition: all 0.3s;
    }
    
    .stButton > button:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }
</style>
""", unsafe_allow_html=True)

# 전역 리스너는 st_javascript로 등록하므로 여기서는 제거
# components.html은 iframe에서 실행되어 메인 윈도우 접근이 제한될 수 있음

# 세션 상태 초기화
if "chatbot" not in st.session_state:
    try:
        st.session_state.chatbot = PAPSChatbot()
    except Exception as e:
        st.session_state.chatbot = None
        st.session_state.chatbot_error = str(e)

if "messages" not in st.session_state:
    st.session_state.messages = []

if "user_results" not in st.session_state:
    st.session_state.user_results = {
        "심폐지구력": {"점수": 0, "등급": "-", "기록": None, "평가종목": ""},
        "유연성": {"점수": 0, "등급": "-", "기록": None, "평가종목": ""},
        "근력근지구력": {"점수": 0, "등급": "-", "기록": None, "평가종목": ""},
        "순발력": {"점수": 0, "등급": "-", "기록": None, "평가종목": ""},
        "비만": {"점수": 0, "등급": "-", "기록": None, "평가종목": ""}
    }

if "user_info" not in st.session_state:
    st.session_state.user_info = {
        "학교과정": "",
        "학년": "",
        "성별": ""
    }

if "total_summary" not in st.session_state:
    st.session_state.total_summary = {"총점": 0, "등급": "-"}

if "last_update_time" not in st.session_state:
    st.session_state.last_update_time = 0

if "results_sent_to_chatbot" not in st.session_state:
    st.session_state.results_sent_to_chatbot = False

if "last_calculator_data_hash" not in st.session_state:
    st.session_state.last_calculator_data_hash = None

if "last_js_timestamp" not in st.session_state:
    st.session_state.last_js_timestamp = 0

if "auto_refresh_counter" not in st.session_state:
    st.session_state.auto_refresh_counter = 0

def update_state_from_calculator(data: dict) -> None:
    """계산기 데이터를 세션 상태에 업데이트 (각 종목의 점수 포함)"""
    if not data:
        return

    print(f"[Python] update_state_from_calculator 호출됨: totalScore={data.get('totalScore', 0)}")
    
    results = data.get("results")
    if results:
        print(f"[Python] results 데이터 수신: {len(results)}개 종목")
        for factor, info in results.items():
            score = int(info.get("점수", 0) or 0)
            grade = str(info.get("등급", "-"))
            record = info.get("기록")
            event = info.get("평가종목", "")
            
            st.session_state.user_results[factor] = {
                "점수": score,
                "등급": grade,
                "기록": record,
                "평가종목": event
            }
            print(f"[Python] {factor} 업데이트: 점수={score}, 등급={grade}, 기록={record}, 평가종목={event}")

    user_info = data.get("userInfo")
    if user_info:
        for key in st.session_state.user_info.keys():
            st.session_state.user_info[key] = user_info.get(key, "")
        print(f"[Python] 사용자 정보 업데이트: {user_info}")

    total_score = data.get("totalScore")
    total_grade = data.get("totalGrade")
    if total_score is not None:
        st.session_state.total_summary["총점"] = total_score
    if total_grade is not None:
        st.session_state.total_summary["등급"] = total_grade
    
    print(f"[Python] 총점 업데이트 완료: {total_score}점, 등급: {total_grade}")
    
    # 각 종목의 점수가 모두 저장되었는지 확인
    saved_scores = {k: v.get("점수", 0) for k, v in st.session_state.user_results.items()}
    print(f"[Python] 저장된 각 종목 점수: {saved_scores}")


# 메인 레이아웃
st.title("🏃‍♂️ PAPS 체력 평가 시스템")
st.markdown("### 📊 체력 측정 및 평가")

# 파일 읽기
idx = (root / "index.html").read_text(encoding="utf-8")
css = (root / "style.css").read_text(encoding="utf-8")
app = (root / "app.js").read_text(encoding="utf-8")
data = (root / "paps_data.js").read_text(encoding="utf-8")

# <body>만 추출하고, body 안에 있을 수도 있는 중복된 내부 리소스 태그 제거
m = re.search(r"<body[^>]*>(?P<body>.*)</body>", idx, flags=re.I | re.S)
body = m.group("body") if m else idx
body = re.sub(
    r"<script[^>]*src=[\"']?(?:\.\/)?(?:paps_data\.js|app\.js)[\"']?[^>]*></script>",
    "",
    body,
    flags=re.I | re.S,
)
body = re.sub(
    r"<link[^>]*href=[\"']?(?:\.\/)?style\.css[\"']?[^>]*>",
    "",
    body,
    flags=re.I | re.S,
)

# CSS에 추가 스타일 적용 (스크롤 제거 및 높이 자동 조정)
additional_css = """
html, body {
    overflow-x: hidden !important;
    overflow-y: visible !important;
    height: auto !important;
    min-height: auto !important;
    margin: 0;
    padding: 0;
}
.container {
    padding-bottom: 20px;
    max-width: 100%;
}
"""

html_doc = f"""<!doctype html>
<html><head><meta charset="utf-8" />
    <style>{css}</style>
    <style>{additional_css}</style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    </head>
<body>
{body}
<script>{data}</script>
<script>{app}</script>
</body></html>"""

# HTML 컴포넌트로 렌더링 (높이를 충분히 크게 설정하여 스크롤 제거)
components.html(
    html_doc,
    height=1800,  # 충분한 높이로 설정하여 내부 스크롤 제거
    scrolling=False  # 스크롤 제거 - 단일 스크롤 구조
)

if True:
    # 자동 새로고침을 위한 카운터 증가
    st.session_state.auto_refresh_counter += 1
    
    # 전역 리스너 등록 (st_javascript를 사용하여 메인 윈도우에서 실행)
    _ = st_javascript("""
    (() => {
        try {
            const mainWindow = window.top || window.parent || window;
            
            // 이미 리스너가 등록되어 있는지 확인
            if (mainWindow._papsListenerRegistered) {
                return 'already_registered';
            }
            
            // postMessage 리스너 함수
            function handlePapsMessage(event) {
                if (event.data && event.data.type === 'papsResults') {
                    try {
                        const payload = event.data.payload;
                        const timestamp = Date.now();
                        
                        console.log('🔵 [Streamlit JS] papsResults 데이터 수신:', {
                            totalScore: payload.totalScore,
                            totalGrade: payload.totalGrade
                        });
                        
                        // localStorage에 저장
                        mainWindow.localStorage.setItem('paps_calculator_results', JSON.stringify(payload));
                        mainWindow.localStorage.setItem('paps_results_timestamp', timestamp.toString());
                        
                        // 전역 변수에 저장
                        mainWindow.papsLatestResults = payload;
                        mainWindow.papsResultsReceived = true;
                        mainWindow.papsLastUpdateTime = timestamp;
                        
                        // DOM 신호
                        const mainDoc = mainWindow.document || document;
                        let signal = mainDoc.getElementById('paps-refresh-signal');
                        if (!signal) {
                            signal = mainDoc.createElement('div');
                            signal.id = 'paps-refresh-signal';
                            signal.style.display = 'none';
                            mainDoc.body.appendChild(signal);
                        }
                        signal.setAttribute('data-timestamp', timestamp.toString());
                        signal.setAttribute('data-totalscore', payload.totalScore.toString());
                        
                        console.log('✅ [Streamlit JS] 데이터 저장 완료');
                    } catch (e) {
                        console.error('❌ [Streamlit JS] 데이터 처리 실패:', e);
                    }
                }
            }
            
            // 리스너 등록
            mainWindow.addEventListener('message', handlePapsMessage);
            mainWindow._papsListenerRegistered = true;
            console.log('✅ [Streamlit JS] postMessage 리스너 등록 완료');
            
            return 'registered';
        } catch (e) {
            console.error('❌ [Streamlit JS] 리스너 등록 실패:', e);
            return 'error';
        }
    })();
    """, key=f"register_listener_{st.session_state.auto_refresh_counter % 100}")
    
    # 계산기에서 전송된 데이터 자동 감지 및 업데이트
    # window.top을 통해 메인 윈도우에 접근 (iframe 내부에서 실행될 수 있으므로)
    js_data = st_javascript("""
    (() => {
        try {
            console.log('🔵 [Streamlit st_javascript] 데이터 확인 시작');
            console.log('🔵 [Streamlit st_javascript] 현재 window:', {
                isTop: window === window.top,
                hasParent: window.parent !== window,
                hasTop: window.top !== window
            });
            
            // 메인 윈도우 참조 (여러 방법 시도)
            let mainWindow = null;
            try {
                mainWindow = window.top;
            } catch(e1) {
                try {
                    mainWindow = window.parent;
                } catch(e2) {
                    mainWindow = window;
                }
            }
            if (!mainWindow) mainWindow = window;
            
            console.log('🔵 [Streamlit st_javascript] mainWindow:', {
                windowType: window === window.top ? 'top' : 'iframe',
                mainWindowExists: !!mainWindow,
                hasPapsLatestResults: !!mainWindow.papsLatestResults,
                papsLatestResults: mainWindow.papsLatestResults ? {
                    totalScore: mainWindow.papsLatestResults.totalScore,
                    totalGrade: mainWindow.papsLatestResults.totalGrade
                } : null
            });
            
            // 1. 전역 변수에서 확인 (메인 윈도우)
            try {
                if (mainWindow.papsLatestResults && mainWindow.papsLatestResults.totalScore > 0) {
                    const result = mainWindow.papsLatestResults;
                    const timestamp = mainWindow.papsLastUpdateTime || Date.now();
                    console.log('✅ [Streamlit st_javascript] 전역 변수에서 데이터 발견:', {
                        totalScore: result.totalScore,
                        totalGrade: result.totalGrade,
                        resultsCount: Object.keys(result.results || {}).length
                    });
                    return JSON.stringify({data: result, timestamp: timestamp});
                }
            } catch (e) {
                console.log('⚠️ [Streamlit st_javascript] 전역 변수 접근 실패:', e.message);
            }
            
            // 2. localStorage에서 확인 (메인 윈도우의 localStorage)
            try {
                const stored = mainWindow.localStorage.getItem('paps_calculator_results');
                const timestamp = mainWindow.localStorage.getItem('paps_results_timestamp');
                if (stored && timestamp) {
                    const dataTime = parseInt(timestamp);
                    const now = Date.now();
                    if (now - dataTime < 300000) { // 5분 이내
                        const data = JSON.parse(stored);
                        if (data.totalScore && data.totalScore > 0) {
                            console.log('✅ [Streamlit st_javascript] localStorage에서 데이터 발견:', {
                                totalScore: data.totalScore,
                                resultsCount: Object.keys(data.results || {}).length
                            });
                            return JSON.stringify({data: data, timestamp: dataTime});
                        }
                    }
                }
            } catch (e) {
                console.log('⚠️ [Streamlit st_javascript] localStorage 접근 실패, 현재 윈도우 localStorage 시도:', e);
                // 현재 윈도우의 localStorage도 시도
                try {
                    const stored = localStorage.getItem('paps_calculator_results');
                    const timestamp = localStorage.getItem('paps_results_timestamp');
                    if (stored && timestamp) {
                        const dataTime = parseInt(timestamp);
                        const now = Date.now();
                        if (now - dataTime < 300000) {
                            const data = JSON.parse(stored);
                            if (data.totalScore && data.totalScore > 0) {
                                console.log('✅ [Streamlit st_javascript] 현재 윈도우 localStorage에서 데이터 발견');
                                return JSON.stringify({data: data, timestamp: dataTime});
                            }
                        }
                    }
                } catch (e2) {
                    console.error('❌ [Streamlit st_javascript] 현재 윈도우 localStorage도 실패:', e2);
                }
            }
            
            console.log('❌ [Streamlit st_javascript] 데이터를 찾을 수 없음');
            return null;
        } catch (e) {
            console.error('❌ [Streamlit st_javascript] 데이터 읽기 실패:', e);
            return null;
        }
    })();
    """, key=f"data_check_{st.session_state.auto_refresh_counter % 10}")

    # 자동 전송 기능 제거 - 사용자가 분석지를 직접 복사하여 붙여넣도록 변경
    
    # 데이터가 있으면 세션 상태에 자동 업데이트 (기존 로직 유지)
    data_updated = False
    should_rerun = False
    
    if js_data and js_data not in ("null", "", "undefined"):
        try:
            js_parsed = json.loads(js_data)
            if isinstance(js_parsed, dict) and "data" in js_parsed:
                calculator_data = js_parsed["data"]
                data_timestamp = js_parsed.get("timestamp", 0)
            else:
                calculator_data = js_parsed
                data_timestamp = 0
            
            new_total = calculator_data.get("totalScore", 0)
            current_total = st.session_state.total_summary.get("총점", 0)
            
            results_count = len(calculator_data.get("results", {}))
            results_detail = {k: v.get("점수", 0) for k, v in calculator_data.get("results", {}).items()}
            print(f"[Python] js_data 파싱 완료: totalScore={new_total}, results 개수={results_count}, 상세={results_detail}")
            
            if new_total > 0:
                data_hash = hash(str(calculator_data))
                last_hash = st.session_state.last_calculator_data_hash
                
                if current_total != new_total or last_hash != data_hash:
                    print(f"[Python] 데이터 업데이트 시작: {current_total} -> {new_total}")
                    update_state_from_calculator(calculator_data)
                    st.session_state.last_update_time = time.time()
                    st.session_state.last_calculator_data_hash = data_hash
                    st.session_state.results_sent_to_chatbot = True
                    data_updated = True
                    if current_total == 0 and new_total > 0:
                        should_rerun = True
                else:
                    print(f"[Python] 데이터 변경 없음 (동일한 해시)")
        except json.JSONDecodeError as e:
            print(f"[Python] JSON 파싱 오류: {e}")
            pass
    else:
        print(f"[Python] js_data가 없거나 유효하지 않음: {js_data}")
        # 디버깅: st_javascript가 실제로 무엇을 반환하는지 확인
        debug_js = st_javascript("""
        (() => {
            try {
                const mainWindow = window.top || window.parent || window;
                return JSON.stringify({
                    windowIsTop: window === window.top,
                    mainWindowHasPaps: !!mainWindow.papsLatestResults,
                    mainWindowPapsScore: mainWindow.papsLatestResults?.totalScore || 0,
                    localStorageExists: !!mainWindow.localStorage.getItem('paps_calculator_results'),
                    localStorageScore: (() => {
                        try {
                            const stored = mainWindow.localStorage.getItem('paps_calculator_results');
                            if (stored) {
                                const data = JSON.parse(stored);
                                return data.totalScore || 0;
                            }
                            return 0;
                        } catch(e) { return -1; }
                    })()
                });
            } catch(e) {
                return JSON.stringify({error: e.message});
            }
        })();
        """, key=f"debug_check_{st.session_state.auto_refresh_counter}")
        if debug_js:
            try:
                debug_info = json.loads(debug_js)
                print(f"[Python] 디버깅 정보: {debug_info}")
            except:
                print(f"[Python] 디버깅 정보 파싱 실패: {debug_js}")
    
    # 타임스탬프 확인으로 추가 체크
    js_timestamp = st_javascript("""
    (() => {
        try {
            const mainWindow = window.top || window.parent || window;
            const mainDoc = mainWindow.document || document;
            
            const signal = mainDoc.getElementById('paps-refresh-signal');
            if (signal) {
                return signal.getAttribute('data-timestamp');
            }
            
            // localStorage에서 확인
            try {
                return mainWindow.localStorage.getItem('paps_results_timestamp');
            } catch (e) {
                return localStorage.getItem('paps_results_timestamp');
            }
        } catch (e) {
            return null;
        }
    })();
    """, key=f"timestamp_check_{st.session_state.auto_refresh_counter % 10}")
    
    if js_timestamp and js_timestamp not in ("null", "", "undefined"):
        try:
            new_timestamp = int(js_timestamp)
            last_timestamp = st.session_state.get("last_js_timestamp", 0)
            if new_timestamp > last_timestamp + 100:  # 100ms 이상 차이날 때만
                st.session_state.last_js_timestamp = new_timestamp
                if js_data and js_data not in ("null", "", "undefined"):
                    try:
                        js_parsed = json.loads(js_data)
                        if isinstance(js_parsed, dict) and "data" in js_parsed:
                            calculator_data = js_parsed["data"]
                        else:
                            calculator_data = js_parsed
                        if calculator_data.get("totalScore", 0) > 0:
                            update_state_from_calculator(calculator_data)
                            st.session_state.results_sent_to_chatbot = True
                            data_updated = True
                            should_rerun = True
                    except:
                        pass
        except:
            pass
    
    # 데이터가 새로 업데이트되었으면 자동 새로고침
    if should_rerun:
        time.sleep(0.2)
        st.rerun()
    
    # 주기적 자동 새로고침 (2초마다, 데이터가 있을 때만)
    total_score = st.session_state.total_summary.get("총점", 0)
    if total_score == 0:
        # 데이터가 없으면 2초마다 체크
        if st.session_state.auto_refresh_counter % 5 == 0:  # 약 2초마다 (0.4초 * 5)
            time.sleep(0.1)
            st.rerun()
    
    # 상담하기 버튼 (항상 표시, 계산 결과가 있으면 활성화)
    st.markdown("---")
    
    # 현재 총점 확인
    total_score = st.session_state.total_summary.get("총점", 0)
    
    # 추가 확인: 전역 변수와 localStorage에서 직접 확인
    js_total_check = st_javascript("""
    (() => {
        try {
            const mainWindow = window.top || window.parent || window;
            
            if (mainWindow.papsLatestResults && mainWindow.papsLatestResults.totalScore > 0) {
                return JSON.stringify({
                    totalScore: mainWindow.papsLatestResults.totalScore,
                    totalGrade: mainWindow.papsLatestResults.totalGrade,
                    data: mainWindow.papsLatestResults
                });
            }
            
            try {
                const stored = mainWindow.localStorage.getItem('paps_calculator_results');
                if (stored) {
                    const data = JSON.parse(stored);
                    if (data.totalScore && data.totalScore > 0) {
                        return JSON.stringify({
                            totalScore: data.totalScore,
                            totalGrade: data.totalGrade,
                            data: data
                        });
                    }
                }
            } catch (e) {
                const stored = localStorage.getItem('paps_calculator_results');
                if (stored) {
                    const data = JSON.parse(stored);
                    if (data.totalScore && data.totalScore > 0) {
                        return JSON.stringify({
                            totalScore: data.totalScore,
                            totalGrade: data.totalGrade,
                            data: data
                        });
                    }
                }
            }
            return null;
        } catch (e) {
            return null;
        }
    })();
    """, key=f"total_check_{st.session_state.auto_refresh_counter % 10}")
    
    if js_total_check and js_total_check not in ("null", "", "undefined"):
        try:
            check_data = json.loads(js_total_check)
            check_total = check_data.get("totalScore", 0)
            if check_total > 0 and check_total != total_score:
                total_score = check_total
                if check_data.get("data"):
                    update_state_from_calculator(check_data["data"])
                    st.session_state.results_sent_to_chatbot = True
                    data_updated = True
                    should_rerun = True
        except:
            pass
    
    # 계산 결과 안내
    if total_score > 0:
        st.info(f"ℹ️ 계산 결과: 총점 {total_score}점. 계산기에서 '상담 분석지 생성' 버튼을 눌러 분석지를 생성하고 복사한 후, 아래 챗봇에 붙여넣어 상담하세요.")
        
        # 디버깅 정보
        with st.expander("🔍 데이터 상태 확인", expanded=False):
            col_debug1, col_debug2, col_debug3 = st.columns(3)
            with col_debug1:
                st.write("**세션 상태 총점:**", st.session_state.total_summary.get("총점", 0))
                st.write("**확인된 총점:**", total_score)
                st.write("**각 종목 점수:**")
                for factor, result in st.session_state.user_results.items():
                    score = result.get("점수", 0)
                    if score > 0:
                        st.write(f"  - {factor}: {score}점")
            with col_debug2:
                js_debug_global = st_javascript("""
                (() => {
                    try {
                        if (window.papsLatestResults) {
                            const data = window.papsLatestResults;
                            let result = '총점: ' + data.totalScore + '\\n';
                            if (data.results) {
                                result += '종목별: ';
                                const factors = Object.keys(data.results);
                                factors.forEach(factor => {
                                    const score = data.results[factor].점수 || 0;
                                    if (score > 0) {
                                        result += factor + ':' + score + ' ';
                                    }
                                });
                            }
                            return result;
                        }
                        return '없음';
                    } catch (e) {
                        return '오류: ' + e.message;
                    }
                })();
                """, key="debug_global")
                st.write("**전역 변수:**")
                st.code(js_debug_global if js_debug_global else "없음", language=None)
            with col_debug3:
                js_debug_storage = st_javascript("""
                (() => {
                    try {
                        const stored = localStorage.getItem('paps_calculator_results');
                        if (stored) {
                            const data = JSON.parse(stored);
                            let result = '총점: ' + data.totalScore + '\\n';
                            if (data.results) {
                                result += '종목별: ';
                                const factors = Object.keys(data.results);
                                factors.forEach(factor => {
                                    const score = data.results[factor].점수 || 0;
                                    if (score > 0) {
                                        result += factor + ':' + score + ' ';
                                    }
                                });
                            }
                            return result;
                        }
                        return '없음';
                    } catch (e) {
                        return '오류: ' + e.message;
                    }
                })();
                """, key="debug_storage")
                st.write("**localStorage:**")
                st.code(js_debug_storage if js_debug_storage else "없음", language=None)
            
            if st.button("🔄 수동 새로고침", use_container_width=True, key="manual_refresh"):
                st.rerun()

with st.container():
    st.markdown("---")
    st.subheader("💬 PAPS 챗봇 상담")
    st.markdown("""
    **사용 방법:**
    1. 위 계산기에서 측정값을 입력하고 **'상담 분석지 생성'** 버튼을 클릭하세요.
    2. 생성된 분석지를 **'분석지 복사하기'** 버튼으로 복사하세요.
    3. 아래 채팅창에 붙여넣기(Ctrl+V) 후 상담을 시작하세요.
    """)
    
    # 챗봇 초기화 확인
    if st.session_state.chatbot is None:
        st.error(f"챗봇 초기화 실패: {st.session_state.get('chatbot_error', '알 수 없는 오류')}")
        st.info("""
        **해결 방법:**
        1. 프로젝트 루트에 `.env` 파일을 생성하세요
        2. `.env` 파일에 다음 내용을 추가하세요:
           ```
           API_KEY=your_api_key_here
           MODEL_NAME=gpt-4o-mini
           ```
        3. 필요시 `API_BASE_URL`도 추가할 수 있습니다
        """)
    else:
        
        # 대화 기록 표시
        chat_container = st.container()
        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        
        # 사용자 입력
        if prompt := st.chat_input("팝스에 대해 궁금한 점을 물어보세요..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("답변을 생성하는 중..."):
                    try:
                        # 사용자가 붙여넣은 분석지 내용을 기반으로 상담 진행
                        # 챗봇이 사용자 메시지에서 직접 정보를 추출하도록 함
                        response = st.session_state.chatbot.get_response(
                            prompt,
                            user_results=None,
                            user_info=None,
                            total_summary=None
                        )
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                    except Exception as e:
                        error_msg = f"오류가 발생했습니다: {str(e)}"
                        st.error(error_msg)
                        st.session_state.messages.append({"role": "assistant", "content": error_msg})
        
        # 하단 버튼들
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🔄 대화 초기화", use_container_width=True):
                st.session_state.messages = []
                if st.session_state.chatbot:
                    st.session_state.chatbot.reset_conversation()
                st.rerun()
        
        # 예시 질문
        with st.expander("💡 예시 질문", expanded=False):
            example_questions = [
                "내 체력요인 중 어떤 부분이 부족한가요?",
                "다음 등급으로 올라가려면 어떻게 해야 하나요?",
                "심폐지구력을 향상시키는 방법을 알려주세요",
                "왕복오래달리기를 더 잘 할 수 있는 팁을 주세요",
                "전체적으로 체력을 향상시키려면 어떻게 해야 하나요?"
            ]
            
            for question in example_questions:
                if st.button(f"❓ {question}", key=f"example_{question}", use_container_width=True):
                    st.session_state.messages.append({"role": "user", "content": question})
                    with st.chat_message("user"):
                        st.markdown(question)
                    
                    with st.chat_message("assistant"):
                        with st.spinner("답변을 생성하는 중..."):
                            try:
                                # 사용자가 붙여넣은 분석지 내용을 기반으로 상담 진행
                                response = st.session_state.chatbot.get_response(
                                    question,
                                    user_results=None,
                                    user_info=None,
                                    total_summary=None
                                )
                                st.markdown(response)
                                st.session_state.messages.append({"role": "assistant", "content": response})
                            except Exception as e:
                                error_msg = f"오류가 발생했습니다: {str(e)}"
                                st.error(error_msg)
                                st.session_state.messages.append({"role": "assistant", "content": error_msg})
                    st.rerun()
