"""
팝스 챗봇 모듈
API를 활용하여 팝스 관련 질문에 답변하는 기능 제공
"""
import os
import json
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv
from openai import OpenAI

# Streamlit이 있는지 확인 (Streamlit Cloud 배포 시)
try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

# 환경변수 로드 (프로젝트 루트의 .env 파일) - 로컬 개발용
root = Path(__file__).parent
env_path = root / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

class PAPSChatbot:
    """팝스 챗봇 클래스"""
    
    def __init__(self):
        """챗봇 초기화"""
        # Streamlit Secrets 우선 사용 (Streamlit Cloud 배포 시)
        if HAS_STREAMLIT:
            try:
                # Streamlit Secrets에서 가져오기
                api_key = st.secrets.get("API_KEY", None)
                api_base_url = st.secrets.get("API_BASE_URL", None)
                model_name = st.secrets.get("MODEL_NAME", "gpt-4o-mini")
            except (AttributeError, KeyError, FileNotFoundError):
                # Secrets가 없으면 환경변수로 폴백
                api_key = None
                api_base_url = None
                model_name = "gpt-4o-mini"
        
        # Streamlit Secrets가 없거나 Streamlit이 없는 경우 환경변수 사용
        if not api_key:
            # .env 파일 경로 명시적으로 지정하여 다시 로드
            env_path = Path(__file__).parent / '.env'
            if env_path.exists():
                load_dotenv(dotenv_path=env_path, override=True)
            
            api_key = os.getenv("API_KEY")
            if not api_base_url:
                api_base_url = os.getenv("API_BASE_URL")
            if model_name == "gpt-4o-mini":
                model_name = os.getenv("MODEL_NAME", "gpt-4o-mini")
        
        if not api_key:
            error_msg = "API_KEY가 설정되지 않았습니다. "
            if HAS_STREAMLIT:
                error_msg += "Streamlit Cloud에서는 'Secrets' 메뉴에서 API_KEY를 설정하거나, "
            error_msg += "로컬 개발 시 .env 파일을 확인하세요."
            raise ValueError(error_msg)
        
        # OpenAI 클라이언트 초기화
        client_kwargs = {"api_key": api_key}
        if api_base_url:
            client_kwargs["base_url"] = api_base_url
        
        self.client = OpenAI(**client_kwargs)
        self.model_name = model_name
        self.conversation_history = []
        
        # 프로젝트 루트 경로 설정
        self.root = Path(__file__).parent
    
    def _load_paps_data(self) -> Dict:
        """팝스 데이터 로드"""
        try:
            paps_data_path = self.root / 'paps_data.js'
            with open(paps_data_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # const PAPS_DATA = ... 부분에서 JSON 추출
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                json_str = content[json_start:json_end]
                return json.loads(json_str)
        except Exception as e:
            print(f"팝스 데이터 로드 실패: {e}")
            return {}
    
    def _create_system_prompt(
        self,
        paps_data: Dict,
        user_results: Optional[Dict] = None,
        total_summary: Optional[Dict] = None
    ) -> str:
        """시스템 프롬프트 생성"""
        system_prompt = """당신은 학생건강체력평가(PAPS) 전문 상담사입니다. 
학생들의 체력 측정 결과를 분석하고, 부족한 부분을 파악하며, 다음 등급으로 발전하기 위한 구체적인 개선 방안을 제시하는 것이 주요 역할입니다.

주요 역할:
1. 학생의 측정 결과를 분석하여 어떤 체력요인이 부족한지 파악
2. 각 체력요인의 등급과 점수를 확인하고 개선이 필요한 부분 식별
3. 다음 등급으로 발전하기 위해 필요한 기록 개선량 계산 및 제시
4. 각 평가종목을 더 잘 측정할 수 있는 방법과 운동 방법 안내
5. 전반적인 체력 향상을 위한 종합적인 조언 제공

체력요인:
- 심폐지구력: 심장과 폐의 지구력
- 유연성: 관절과 근육의 유연성
- 근력근지구력: 근육의 힘과 지구력
- 순발력: 빠른 힘 발휘 능력
- 비만: 체질량지수 기반 평가

응답 시 주의사항:
- 친절하고 격려하는 톤으로 답변
- 구체적이고 실천 가능한 조언 제공
- 학생의 현재 등급과 목표 등급을 명확히 비교
- 운동 방법은 안전하고 효과적인 것만 제시
- 전문 용어 사용 시 쉬운 설명 추가
"""
        
        if user_results:
            system_prompt += f"\n\n현재 학생의 측정 결과:\n"
            for factor, result in user_results.items():
                if result.get('점수', 0) > 0:
                    detail_parts = [
                        f"- {factor}: 점수 {result.get('점수', 0)}점, 등급 {result.get('등급', '-')}"
                    ]
                    record = result.get('기록')
                    event = result.get('평가종목')
                    extra = []
                    if event:
                        extra.append(f"평가종목 {event}")
                    if record is not None:
                        extra.append(f"기록 {record}")
                    if extra:
                        detail_parts.append(f"({' / '.join(extra)})")
                    system_prompt += " ".join(detail_parts) + "\n"

        if total_summary:
            system_prompt += (
                f"\n전체 점수는 {total_summary.get('총점', 0)}점이며 "
                f"{total_summary.get('등급', '-')} 등급입니다.\n"
            )
        
        return system_prompt
    
    def _get_next_grade_info(self, paps_data: Dict, factor: str, current_grade: str, 
                             current_record: float, school_level: str, grade: str, gender: str, 
                             test_item: str) -> Optional[Dict]:
        """다음 등급으로 발전하기 위한 정보 계산"""
        try:
            # 현재 등급의 숫자값
            current_grade_num = int(current_grade.replace('등급', '').strip())
            if current_grade_num >= 1:
                return None  # 이미 최고 등급
            
            next_grade_num = current_grade_num - 1
            
            # 다음 등급의 기준 찾기
            next_grade_criteria = None
            for item in paps_data.get('평가기준', []):
                if (item['체력요인'].strip() == factor and
                    item['평가종목'].strip() == test_item and
                    item['학년'].strip() == grade and
                    item['성별'].strip() == gender and
                    item['학교과정'].strip() == school_level and
                    item['등급'].strip() == str(next_grade_num)):
                    
                    # 기록 범위 파싱
                    record_range = item['기록'].split('~')
                    if len(record_range) == 2:
                        min_record = float(record_range[0].strip())
                        max_record = float(record_range[1].strip())
                        
                        # 기록이 높을수록 좋은 종목인지 판단 (비만은 낮을수록 좋음)
                        if factor == '비만':
                            # 비만은 낮을수록 좋으므로 현재 기록보다 낮아야 함
                            target_record = min_record
                            improvement_needed = current_record - target_record
                        else:
                            # 대부분의 종목은 높을수록 좋음
                            target_record = max_record
                            improvement_needed = target_record - current_record
                        
                        return {
                            'next_grade': next_grade_num,
                            'target_record': target_record,
                            'improvement_needed': improvement_needed,
                            'current_record': current_record
                        }
            
            return None
        except Exception as e:
            print(f"다음 등급 정보 계산 실패: {e}")
            return None
    
    def get_response(
        self,
        user_message: str,
        user_results: Optional[Dict] = None,
        user_info: Optional[Dict] = None,
        total_summary: Optional[Dict] = None
    ) -> str:
        """사용자 메시지에 대한 응답 생성"""
        try:
            paps_data = self._load_paps_data()
            system_prompt = self._create_system_prompt(paps_data, user_results, total_summary)
            
            # 컨텍스트 메시지 구성
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # 대화 기록 추가
            messages.extend(self.conversation_history)
            
            # 사용자 메시지 추가
            context_message = user_message
            
            # 사용자 정보가 있으면 컨텍스트에 추가
            if user_info:
                context_message += f"\n\n[학생 정보]\n"
                context_message += f"- 학교과정: {user_info.get('학교과정', '')}\n"
                context_message += f"- 학년: {user_info.get('학년', '')}\n"
                context_message += f"- 성별: {user_info.get('성별', '')}\n"
            
            # 측정 결과가 있으면 컨텍스트에 추가
            if user_results:
                context_message += f"\n[현재 측정 결과]\n"
                for factor, result in user_results.items():
                    if result.get('점수', 0) > 0:
                        detail = f"- {factor}: 점수 {result.get('점수', 0)}점, 등급 {result.get('등급', '-')}"
                        record = result.get('기록')
                        event = result.get('평가종목')
                        extras = []
                        if event:
                            extras.append(f"평가종목 {event}")
                        if record is not None:
                            extras.append(f"기록 {record}")
                        if extras:
                            detail += f" ({', '.join(extras)})"
                        context_message += detail + "\n"
                
                # 다음 등급 정보 추가
                if user_info:
                    for factor, result in user_results.items():
                        current_grade = result.get('등급', '')
                        current_record = result.get('기록')
                        test_item = result.get('평가종목', '')
                        if (
                            result.get('점수', 0) > 0 and
                            current_grade and
                            current_grade != '-' and
                            current_record is not None and
                            test_item
                        ):
                            next_grade_info = self._get_next_grade_info(
                                paps_data, factor, current_grade,
                                current_record,
                                user_info.get('학교과정', ''),
                                user_info.get('학년', ''),
                                user_info.get('성별', ''),
                                test_item
                            )
                            if next_grade_info:
                                context_message += f"\n{factor}의 다음 등급({next_grade_info['next_grade']}등급)을 위해서는 "
                                context_message += f"기록을 {next_grade_info['improvement_needed']:.1f}만큼 개선해야 합니다.\n"

            if total_summary:
                context_message += (
                    f"\n[전체 결과]\n총점: {total_summary.get('총점', 0)}점, "
                    f"등급: {total_summary.get('등급', '-')}\n"
                )
            
            messages.append({"role": "user", "content": context_message})
            
            # API 호출
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            assistant_message = response.choices[0].message.content
            
            # 대화 기록 업데이트 (최근 10개만 유지)
            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-10:]
            
            return assistant_message
            
        except Exception as e:
            return f"오류가 발생했습니다: {str(e)}\nAPI 키와 환경변수 설정을 확인해주세요."
    
    def reset_conversation(self):
        """대화 기록 초기화"""
        self.conversation_history = []

