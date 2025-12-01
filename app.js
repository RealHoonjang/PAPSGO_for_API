// 전역 변수로 PAPS_DATA 사용 가능 여부 확인
function checkPAPSData() {
    if (typeof window.PAPS_DATA === 'undefined') {
        console.error('PAPS_DATA가 정의되지 않았습니다.');
        return false;
    }
    return true;
}

// 전역 변수
let papsChart = null;
const factors = ['심폐지구력', '유연성', '근력근지구력', '순발력', '비만'];
let currentResults = {
    심폐지구력: { 점수: 0, 등급: '-' },
    유연성: { 점수: 0, 등급: '-' },
    근력근지구력: { 점수: 0, 등급: '-' },
    순발력: { 점수: 0, 등급: '-' },
    비만: { 점수: 0, 등급: '-' }
};
let lastStreamlitPayload = null;

function sendResultsToStreamlit(totalScore = 0, totalGrade = '-') {
    try {
        const userInfo = {
            학교과정: document.getElementById('학교과정')?.value || '',
            학년: document.getElementById('학년')?.value || '',
            성별: document.getElementById('성별')?.value || ''
        };

        const factorDetails = {};
        factors.forEach(factor => {
            const recordInput = document.querySelector(`.기록[data-factor="${factor}"]`);
            const eventSelect = document.querySelector(`.평가종목[data-factor="${factor}"]`);
            const recordValue = recordInput ? recordInput.value : '';
            factorDetails[factor] = {
                점수: currentResults[factor].점수,
                등급: currentResults[factor].등급,
                기록: recordValue ? parseFloat(recordValue) : null,
                평가종목: eventSelect ? eventSelect.value : ''
            };
        });

        const payload = {
            userInfo,
            results: factorDetails,
            totalScore,
            totalGrade
        };

        // localStorage에 저장 (부모 창에서 읽을 수 있도록)
        try {
            localStorage.setItem('paps_calculator_results', JSON.stringify(payload));
            localStorage.setItem('paps_results_timestamp', Date.now().toString());
            console.log('✅ [sendResultsToStreamlit] iframe localStorage에 저장 완료:', payload);
        } catch (e) {
            console.error('❌ [sendResultsToStreamlit] iframe localStorage 저장 실패:', e);
        }

        // 전달 대상 윈도우 수집 (parent, top 등)
        const targetWindows = [];
        if (window.parent && window.parent !== window) {
            targetWindows.push({ win: window.parent, label: 'parent' });
        }
        if (window.top && window.top !== window && window.top !== window.parent) {
            targetWindows.push({ win: window.top, label: 'top' });
        }

        if (targetWindows.length === 0) {
            console.warn('⚠️ [sendResultsToStreamlit] 전달할 상위 윈도우를 찾을 수 없음');
        }

        targetWindows.forEach(({ win, label }) => {
            console.log(`🔵 [sendResultsToStreamlit] ${label} 윈도우로 전송 시도`, {
                totalScore: payload.totalScore,
                totalGrade: payload.totalGrade,
                resultsCount: Object.keys(payload.results).length,
                hasUserInfo: !!payload.userInfo
            });

            try {
                const message = { type: 'papsResults', payload };
                console.log(`🔵 [sendResultsToStreamlit] ${label} 윈도우 정보:`, {
                    winExists: !!win,
                    winType: typeof win,
                    hasPostMessage: typeof win.postMessage === 'function',
                    winLocation: win.location ? win.location.href : 'no location'
                });
                win.postMessage(message, '*');
                console.log(`✅ [sendResultsToStreamlit] ${label} postMessage 전송 완료`, {
                    messageType: message.type,
                    totalScore: message.payload.totalScore,
                    timestamp: Date.now()
                });
            } catch (e) {
                console.error(`❌ [sendResultsToStreamlit] ${label} postMessage 실패:`, e);
            }

            // 전역 변수에 저장 시도
            try {
                win.papsLatestResults = payload;
                win.papsResultsReceived = true;
                win.papsLastUpdateTime = Date.now();
                console.log(`✅ [sendResultsToStreamlit] ${label} 전역 변수 저장 완료`);
            } catch (e) {
                console.error(`❌ [sendResultsToStreamlit] ${label} 전역 변수 저장 실패:`, e);
            }

            // localStorage 저장 시도
            try {
                const timestamp = Date.now().toString();
                win.localStorage.setItem('paps_calculator_results', JSON.stringify(payload));
                win.localStorage.setItem('paps_results_timestamp', timestamp);
                console.log(`✅ [sendResultsToStreamlit] ${label} localStorage 저장 완료`, { timestamp });
            } catch (e) {
                console.error(`❌ [sendResultsToStreamlit] ${label} localStorage 저장 실패:`, e);
            }
        });
    } catch (error) {
        console.error('❌ [sendResultsToStreamlit] 전체 전달 실패:', error);
    }
}

// PAPS_DATA 로딩 확인
function waitForPAPSData(callback, maxAttempts = 10) {
    let attempts = 0;
    
    function checkPAPSData() {
        attempts++;
        if (typeof PAPS_DATA !== 'undefined') {
            callback();
        } else if (attempts < maxAttempts) {
            setTimeout(checkPAPSData, 100);
        } else {
            console.error('PAPS_DATA 로딩 실패');
        }
    }
    
    checkPAPSData();
}

// 스크립트 로딩 확인
function checkScriptsLoaded() {
    return new Promise((resolve, reject) => {
        if (typeof Chart !== 'undefined' && typeof PAPS_DATA !== 'undefined') {
            resolve();
        } else {
            reject(new Error('필요한 스크립트가 로드되지 않았습니다.'));
        }
    });
}

// 페이지 로드 완료 시 실행
window.onload = function() {
    console.log('페이지 로드됨');
    
    checkScriptsLoaded()
        .then(() => {
            try {
                initializeChart();
                setupEventListeners();
                
                // 초기 계산 실행 (입력값이 있는 경우)
                setTimeout(() => {
                    factors.forEach(factor => {
                        const 기록Element = document.querySelector(`.기록[data-factor="${factor}"]`);
                        const 평가종목Element = document.querySelector(`.평가종목[data-factor="${factor}"]`);
                        if (기록Element && 기록Element.value && 평가종목Element && 평가종목Element.value) {
                            console.log(`초기 계산 실행: ${factor}`);
                            calculateResult(factor);
                        }
                    });
                }, 500);
                
                const totalScoreEl = document.getElementById('total-score');
                const totalGradeEl = document.getElementById('total-grade');
                const initialScore = totalScoreEl ? parseInt(totalScoreEl.textContent) || 0 : 0;
                const initialGrade = totalGradeEl ? totalGradeEl.textContent || '-' : '-';
                sendResultsToStreamlit(initialScore, initialGrade);
            } catch (error) {
                console.error('초기화 중 오류 발생:', error);
            }
        })
        .catch(error => {
            console.error('스크립트 로딩 실패:', error);
        });
};

// 결과 확인 버튼 및 관련 이벤트(구형 UI용)는 요소가 있을 때만 활성화
const legacyCalculateButton = document.getElementById('계산버튼');
const legacyFactorSelect = document.getElementById('체력요인');
const legacyEventSelect = document.getElementById('평가종목');
const legacyRecordInput = document.getElementById('기록');
const legacyGradeResult = document.getElementById('등급결과');
const legacyScoreResult = document.getElementById('점수결과');

if (legacyCalculateButton && legacyFactorSelect && legacyEventSelect && legacyRecordInput && legacyGradeResult && legacyScoreResult) {
    console.info('구형 단일 계산기 UI 활성화');
    
    legacyCalculateButton.addEventListener('click', function() {
        console.log('버튼 클릭됨');
        
        // 입력값 가져오기 및 공백 제거
        const 체력요인 = legacyFactorSelect.value.trim();
        const 평가종목 = legacyEventSelect.value.trim();
        const 학년 = document.getElementById('학년').value.trim();
        const 성별 = document.getElementById('성별').value.trim();
        const 학교과정 = document.getElementById('학교과정').value.trim();
        const 기록 = parseFloat(legacyRecordInput.value);

        console.log('입력값:', {체력요인, 평가종목, 학년, 성별, 학교과정, 기록});

        // 입력값 검증
        if (!체력요인 || !평가종목 || !학년 || !성별 || !학교과정 || isNaN(기록)) {
            alert('모든 항목을 입력해주세요.');
            return;
        }

        // 평가 결과 찾기
        const 평가결과 = PAPS_DATA.평가기준.find(item => {
            const itemMatch = 
                item.체력요인.trim() === 체력요인 &&
                item.평가종목.trim() === 평가종목 &&
                item.학년.trim() === 학년 &&
                item.성별.trim() === 성별 &&
                item.학교과정.trim() === 학교과정;

            if (!itemMatch) return false;

            const [최소값, 최대값] = item.기록.split('~').map(str => parseFloat(str.trim()));
            const 기록범위일치 = 기록 >= 최소값 && 기록 <= 최대값;

            return itemMatch && 기록범위일치;
        });

        console.log('찾은 평가결과:', 평가결과);

        if (평가결과) {
            legacyGradeResult.textContent = 평가결과.등급;
            legacyScoreResult.textContent = 평가결과.점수;
            console.log('결과 표시:', 평가결과.등급, 평가결과.점수);
        } else {
            legacyGradeResult.textContent = '해당 없음';
            legacyScoreResult.textContent = '-';
            console.log('해당하는 결과를 찾을 수 없음');
        }
    });

    legacyFactorSelect.addEventListener('change', function() {
        const 선택된체력요인 = this.value;
        const 평가종목Select = legacyEventSelect;
        const optgroups = 평가종목Select.getElementsByTagName('optgroup');
        
        for (let optgroup of optgroups) {
            optgroup.style.display = 'none';
            const options = optgroup.getElementsByTagName('option');
            for (let option of options) {
                option.style.display = 'none';
            }
        }
        
        if (선택된체력요인) {
            const selectedOptgroup = 평가종목Select.querySelector(`optgroup[label="${선택된체력요인}"]`);
            if (selectedOptgroup) {
                selectedOptgroup.style.display = '';
                const options = selectedOptgroup.getElementsByTagName('option');
                for (let option of options) {
                    option.style.display = '';
                }
            }
        }
        
        평가종목Select.value = '';
    });

    legacyEventSelect.addEventListener('change', function() {
        const 체력요인 = legacyFactorSelect.value;
        const 평가종목 = this.value;
        const 학교과정 = document.getElementById('학교과정').value;
        const 학년 = document.getElementById('학년').value;
        const 성별 = document.getElementById('성별').value;

        if (!체력요인 || !평가종목 || !학교과정 || !학년 || !성별) return;

        const 관련기준 = PAPS_DATA.평가기준.filter(item => 
            item.체력요인.trim() === 체력요인 &&
            item.평가종목.trim() === 평가종목 &&
            item.학교과정.trim() === 학교과정 &&
            item.학년.trim() === 학년 &&
            item.성별.trim() === 성별
        );

        if (관련기준.length > 0) {
            const 범위 = 관련기준.map(item => item.기록).join(', ');
            legacyRecordInput.placeholder = `가능 범위: ${범위}`;
        }
    });
}
// 구형 단일 계산기 UI는 현재 사용하지 않으므로 조용히 건너뜁니다.

// 평가종목 업데이트 함수 (사용처에서 요소가 존재할 때만 호출)
function updatePapsItems(선택된체력요인) {
    const 평가종목Select = document.getElementById('평가종목');
    if (!평가종목Select) return;
    평가종목Select.innerHTML = '<option value="">평가종목 선택</option>';
    
    if (선택된체력요인) {
        const 평가종목매핑 = {
            "심폐지구력": ["왕복오래달리기", "스텝검사", "오래달리기-걷기"],
            "유연성": ["앉아윗몸앞으로굽히기", "종합유연성검사"],
            "근력근지구력": ["(무릎대고)팔굽혀펴기", "윗몸말아올리기", "악력"],
            "순발력": ["50m달리기", "제자리멀리뛰기"],
            "비만": ["체질량지수"]
        };
        
        if (평가종목매핑[선택된체력요인]) {
            평가종목매핑[선택된체력요인].forEach(종목 => {
                const option = document.createElement('option');
                option.value = 종목;
                option.textContent = 종목;
                평가종목Select.appendChild(option);
            });
        }
    }
}

// 차트 초기화
function initializeChart() {
    const ctx = document.getElementById('papsChart');
    if (!ctx) {
        console.error('차트 캔버스를 찾을 수 없습니다.');
        return;
    }

    try {
        papsChart = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: factors,
                datasets: [{
                    label: '체력 평가 결과',
                    data: [0, 0, 0, 0, 0],
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    pointBackgroundColor: 'rgba(54, 162, 235, 1)',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: 'rgba(54, 162, 235, 1)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 5,
                        min: 1,
                        ticks: {
                            stepSize: 1,
                            callback: function(value) {
                                return (6 - value) + '등급';
                            }
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const factor = context.chart.data.labels[context.dataIndex];
                                const grade = 6 - context.raw;
                                const score = currentResults[factor].점수;
                                return `${grade}등급 (${score}점)`;
                            }
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('차트 생성 중 오류 발생:', error);
    }
}

// 이벤트 리스너 설정
function setupEventListeners() {
    // 학생 정보 변경 시 모든 결과 초기화
    ['학교과정', '학년', '성별'].forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.addEventListener('change', () => {
                resetAllResults();
                // 기존 기록이 입력되어 있다면 즉시 재계산
                factors.forEach(factor => calculateResult(factor));
            });
        }
    });

    // 각 체력요인별 입력 필드에 이벤트 리스너 추가
    factors.forEach(factor => {
        const select = document.querySelector(`.평가종목[data-factor="${factor}"]`);
        const input = document.querySelector(`.기록[data-factor="${factor}"]`);

        if (!select || !input) {
            console.warn(`체력요인 "${factor}" 입력 요소를 찾을 수 없습니다.`);
            return;
        }

        // 기본값이 없으면 첫 번째 유효 옵션 자동 선택
        const firstOption = Array.from(select.options).find(option => option.value);
        if (!select.value && firstOption) {
            select.value = firstOption.value;
        }

        const triggerCalculation = () => calculateResult(factor);

        select.addEventListener('change', triggerCalculation);
        input.addEventListener('input', triggerCalculation);
        input.addEventListener('change', triggerCalculation);
    });
    
    // 상담 분석지 생성 버튼 이벤트
    const generateAnalysisBtn = document.getElementById('generate-analysis-btn');
    if (generateAnalysisBtn) {
        generateAnalysisBtn.addEventListener('click', generateAnalysisReport);
    }
    
    // 분석지 복사 버튼 이벤트
    const copyAnalysisBtn = document.getElementById('copy-analysis-btn');
    if (copyAnalysisBtn) {
        copyAnalysisBtn.addEventListener('click', copyAnalysisReport);
    }
}

// 상담 분석지 생성 함수
function generateAnalysisReport() {
    const totalScore = factors.reduce((sum, factor) => sum + currentResults[factor].점수, 0);
    const totalGrade = calculateTotalGrade(totalScore);
    
    const userInfo = {
        학교과정: document.getElementById('학교과정')?.value || '',
        학년: document.getElementById('학년')?.value || '',
        성별: document.getElementById('성별')?.value || ''
    };

    // 분석지 텍스트 생성
    let analysisText = '=== PAPS 체력 평가 상담 분석지 ===\n\n';
    analysisText += `[기본 정보]\n`;
    analysisText += `학교과정: ${userInfo.학교과정 || '미입력'}\n`;
    analysisText += `학년: ${userInfo.학년 || '미입력'}\n`;
    analysisText += `성별: ${userInfo.성별 || '미입력'}\n\n`;
    
    analysisText += `[체력요인별 평가 결과]\n`;
    analysisText += `${'='.repeat(40)}\n`;
    
    factors.forEach(factor => {
        const recordInput = document.querySelector(`.기록[data-factor="${factor}"]`);
        const eventSelect = document.querySelector(`.평가종목[data-factor="${factor}"]`);
        const recordValue = recordInput ? recordInput.value : '';
        const eventName = eventSelect ? eventSelect.value : '미선택';
        
        analysisText += `\n${factor}\n`;
        analysisText += `  평가종목: ${eventName}\n`;
        if (recordValue) {
            analysisText += `  기록: ${recordValue}\n`;
        }
        analysisText += `  점수: ${currentResults[factor].점수}점\n`;
        analysisText += `  등급: ${currentResults[factor].등급}등급\n`;
    });
    
    analysisText += `\n${'='.repeat(40)}\n`;
    analysisText += `[전체 평가 결과]\n`;
    analysisText += `총점: ${totalScore}점\n`;
    analysisText += `전체 등급: ${totalGrade}\n\n`;
    
    analysisText += `위 결과를 바탕으로 체력 개선 방안을 제시해주세요.\n`;
    
    // 분석지 표시
    const container = document.getElementById('analysis-report-container');
    const reportDiv = document.getElementById('analysis-report');
    const copyFeedback = document.getElementById('copy-feedback');
    
    if (container && reportDiv) {
        reportDiv.textContent = analysisText;
        container.style.display = 'block';
        if (copyFeedback) {
            copyFeedback.style.display = 'none';
        }
        
        // 스크롤하여 분석지 영역으로 이동
        container.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    
    console.log('✅ [generateAnalysisReport] 상담 분석지 생성 완료');
}

// 분석지 복사 함수
function copyAnalysisReport() {
    const reportDiv = document.getElementById('analysis-report');
    const copyFeedback = document.getElementById('copy-feedback');
    
    if (!reportDiv) return;
    
    const text = reportDiv.textContent || reportDiv.innerText;
    
    // 클립보드에 복사
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            if (copyFeedback) {
                copyFeedback.style.display = 'block';
                setTimeout(() => {
                    copyFeedback.style.display = 'none';
                }, 3000);
            }
            console.log('✅ [copyAnalysisReport] 클립보드에 복사 완료');
        }).catch(err => {
            console.error('❌ [copyAnalysisReport] 클립보드 복사 실패:', err);
            // Fallback: 선택 영역으로 복사
            fallbackCopyTextToClipboard(text, copyFeedback);
        });
    } else {
        // Fallback: 선택 영역으로 복사
        fallbackCopyTextToClipboard(text, copyFeedback);
    }
}

// Fallback 복사 함수 (구형 브라우저 지원)
function fallbackCopyTextToClipboard(text, feedbackElement) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        const successful = document.execCommand('copy');
        if (successful) {
            if (feedbackElement) {
                feedbackElement.style.display = 'block';
                setTimeout(() => {
                    feedbackElement.style.display = 'none';
                }, 3000);
            }
            console.log('✅ [fallbackCopyTextToClipboard] 복사 완료');
        } else {
            console.error('❌ [fallbackCopyTextToClipboard] 복사 실패');
            alert('복사에 실패했습니다. 분석지를 직접 선택하여 복사해주세요.');
        }
    } catch (err) {
        console.error('❌ [fallbackCopyTextToClipboard] 오류:', err);
        alert('복사에 실패했습니다. 분석지를 직접 선택하여 복사해주세요.');
    }
    
    document.body.removeChild(textArea);
}

// 결과 초기화
function resetAllResults() {
    factors.forEach(factor => {
        currentResults[factor] = { 점수: 0, 등급: '-' };
        updateResultDisplay(factor);
    });
    updateChart();
    updateTotalResult();
}

// 개별 결과 계산
function calculateResult(factor) {
    const 학교과정Element = document.getElementById('학교과정');
    const 학년Element = document.getElementById('학년');
    const 성별Element = document.getElementById('성별');
    const 평가종목Element = document.querySelector(`.평가종목[data-factor="${factor}"]`);
    const 기록Element = document.querySelector(`.기록[data-factor="${factor}"]`);

    if (!학교과정Element || !학년Element || !성별Element || !평가종목Element || !기록Element) {
        console.warn(`[${factor}] 필수 입력 요소를 찾을 수 없습니다.`);
        return;
    }

    const 학교과정 = 학교과정Element.value.trim();
    const 학년 = 학년Element.value.trim();
    const 성별 = 성별Element.value.trim();
    const 평가종목 = 평가종목Element.value.trim();
    const 기록값 = 기록Element.value.trim();
    const 기록 = 기록값 === '' ? NaN : parseFloat(기록값);

    // 디버깅 로그
    console.log(`[${factor}] 계산 시도:`, {
        학교과정, 학년, 성별, 평가종목, 기록값, 기록
    });

    if (!학교과정 || !학년 || !성별 || !평가종목 || isNaN(기록)) {
        console.warn(`[${factor}] 입력값이 불완전합니다:`, {
            학교과정: !!학교과정, 학년: !!학년, 성별: !!성별, 
            평가종목: !!평가종목, 기록유효: !isNaN(기록)
        });
        currentResults[factor] = { 점수: 0, 등급: '-' };
        updateResultDisplay(factor);
        updateChart();
        updateTotalResult();
        return;
    }

    // PAPS_DATA 확인
    if (!PAPS_DATA || !PAPS_DATA.평가기준) {
        console.error('PAPS_DATA가 로드되지 않았습니다.');
        return;
    }

    const 평가결과 = PAPS_DATA.평가기준.find(item => {
        const 체력요인일치 = item.체력요인 && item.체력요인.trim() === factor;
        const 평가종목일치 = item.평가종목 && item.평가종목.trim() === 평가종목;
        const 학년일치 = item.학년 && item.학년.trim() === 학년;
        const 성별일치 = item.성별 && item.성별.trim() === 성별;
        const 학교과정일치 = item.학교과정 && item.학교과정.trim() === 학교과정;
        const 기록범위일치 = item.기록 && isInRange(기록, item.기록);
        
        return 체력요인일치 && 평가종목일치 && 학년일치 && 성별일치 && 학교과정일치 && 기록범위일치;
    });

    if (평가결과) {
        currentResults[factor] = {
            점수: parseInt(평가결과.점수) || 0,
            등급: 평가결과.등급 || '-'
        };
        console.log(`[${factor}] 계산 완료:`, currentResults[factor]);
    } else {
        console.warn(`[${factor}] 일치하는 평가기준을 찾을 수 없습니다.`);
        // 디버깅: 일치하는 항목이 있는지 확인
        const 일치하는항목 = PAPS_DATA.평가기준.filter(item => {
            return item.체력요인 && item.체력요인.trim() === factor &&
                   item.평가종목 && item.평가종목.trim() === 평가종목 &&
                   item.학년 && item.학년.trim() === 학년 &&
                   item.성별 && item.성별.trim() === 성별 &&
                   item.학교과정 && item.학교과정.trim() === 학교과정;
        });
        console.log(`[${factor}] 조건 일치 항목 수:`, 일치하는항목.length);
        if (일치하는항목.length > 0) {
            console.log(`[${factor}] 기록 범위 확인:`, 일치하는항목.map(item => ({
                기록범위: item.기록,
                기록값: 기록,
                범위내: isInRange(기록, item.기록)
            })));
        }
        currentResults[factor] = { 점수: 0, 등급: '-' };
    }

    updateResultDisplay(factor);
    updateChart();
    updateTotalResult();
    // updateTotalResult에서 이미 전송하므로 여기서는 중복 전송하지 않음
}

// 기록 범위 확인
function isInRange(기록, rangeStr) {
    const [min, max] = rangeStr.split('~').map(str => parseFloat(str.trim()));
    return 기록 >= min && 기록 <= max;
}

// 결과 표시 업데이트
function updateResultDisplay(factor) {
    const resultDisplay = document.querySelector(`.input-group[data-factor="${factor}"] .result-display`);
    if (resultDisplay) {
        resultDisplay.querySelector('.점수').textContent = currentResults[factor].점수 + '점';
        resultDisplay.querySelector('.등급').textContent = currentResults[factor].등급;
    }
}

// 차트 업데이트
function updateChart() {
    papsChart.data.datasets[0].data = factors.map(factor => {
        const 등급 = currentResults[factor].등급;
        if (등급 === '-') return 0;
        // 등급을 반대로 변환 (1등급 -> 5점, 5등급 -> 1점)
        const 등급숫자 = parseInt(등급.replace('등급', ''));
        return 6 - 등급숫자; // 6에서 등급을 빼서 반대로 변환
    });
    papsChart.update();
}

// 전체 결과 업데이트
function updateTotalResult() {
    const totalScore = factors.reduce((sum, factor) => sum + currentResults[factor].점수, 0);
    const totalGrade = calculateTotalGrade(totalScore);

    document.getElementById('total-score').textContent = totalScore;
    document.getElementById('total-grade').textContent = totalGrade;
    
    // 결과가 변경되고 총점이 0보다 크면 자동으로 Streamlit에 전송
    if (totalScore > 0) {
        sendResultsToStreamlit(totalScore, totalGrade);
    }
}

// 전체 등급 계산
function calculateTotalGrade(score) {
    if (score >= 80) return '1등급';
    if (score >= 60) return '2등급';
    if (score >= 40) return '3등급';
    if (score >= 20) return '4등급';
    return '5등급';
}