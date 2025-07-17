# main.py
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import openai
import uvicorn

# .env 파일 로드
load_dotenv()

# 환경 변수에서 OpenAI API 키 가져오기
openai_api_key = os.getenv("OPENAI_API_KEY")

# API 키가 없으면 오류 발생
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다. .env 파일에 API 키를 추가해주세요.")

# OpenAI 클라이언트 초기화
# 최신 OpenAI 라이브러리 (1.x.x 버전 이상)에서는 이 방식으로 클라이언트를 초기화합니다.
client = openai.OpenAI(api_key=openai_api_key)

# FastAPI 애플리케이션 인스턴스 생성
app = FastAPI(
    title="방 가구 배치 이미지 생성기",
    description="사용자의 텍스트 설명을 기반으로 방에 가구가 배치된 이미지를 OpenAI DALL-E로 생성합니다.",
    version="1.0.0"
)

# 이미지 생성을 위한 요청 본문(request body) 모델 정의
class FurniturePlacementRequest(BaseModel):
    # 배치할 가구에 대한 상세한 텍스트 설명
    # 예: "파란색 3인용 벨벳 소파, 중간 크기의 원형 유리 커피 테이블, 65인치 벽걸이 TV, 두 개의 키 큰 스탠드 조명"
    furniture_description: str # Form 제거
    
    # 방의 크기, 스타일, 특징에 대한 텍스트 설명
    # 예: "현대적인 스타일의 5미터 x 4미터 크기 거실, 큰 창문과 밝은 나무 바닥"
    room_details: str # Form 제거

@app.get("/")
async def read_root():
    """
    루트 경로에 대한 간단한 환영 메시지를 반환합니다.
    """
    return {"message": "방 가구 배치 이미지 생성기에 오신 것을 환영합니다! /generate-room-image/ 엔드포인트를 사용하세요."}

@app.post("/generate-room-image/")
async def generate_room_image(request: FurniturePlacementRequest):
    """
    사용자가 제공한 가구 설명과 방 세부 정보를 기반으로 방에 가구가 배치된 이미지를 생성합니다.
    """
    try:
        # DALL-E 모델을 위한 프롬프트 생성
        # 사용자의 설명을 조합하여 상세하고 구체적인 프롬프트를 만듭니다.
        prompt = (
            f"{request.room_details}에 다음 가구들이 배치된 모습: {request.furniture_description}. "
            "현실적이고, 자연스러운 조명과 그림자가 있는 고품질 실내 디자인 사진."
        )
        
        print(f"생성될 프롬프트: {prompt}") # 디버깅을 위해 생성될 프롬프트 출력

        # OpenAI DALL-E API 호출
        # 'dall-e-3' 모델은 더 나은 품질의 이미지를 생성합니다.
        response = client.images.generate(
            model="dall-e-3",  # DALL-E 3 모델 사용
            prompt=prompt,     # 생성된 프롬프트 전달
            n=1,               # 생성할 이미지 개수 (현재 DALL-E 3는 n=1만 지원)
            size="1024x1024"   # 이미지 해상도
            # quality="hd",    # DALL-E 3에서 고품질 이미지 생성을 위해 추가 가능 (비용 증가)
            # style="natural"  # DALL-E 3에서 이미지 스타일 지정 가능
        )

        # 생성된 이미지의 URL 추출
        # DALL-E 3 응답은 data 리스트에 이미지 정보가 담겨 있습니다.
        image_url = response.data[0].url # 첫 번째 (유일한) 이미지 URL

        # 생성된 이미지 URL 반환
        return {"image_url": image_url, "generated_prompt": prompt}

    except openai.APIError as e:
        # OpenAI API 관련 오류 처리
        print(f"OpenAI API 오류 발생: {e}")
        raise HTTPException(
            status_code=e.status_code if hasattr(e, 'status_code') else 500,
            detail=f"OpenAI API 오류: {str(e)}"
        )
    except Exception as e:
        # 기타 예상치 못한 오류 처리
        print(f"내부 서버 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"내부 서버 오류: {str(e)}")



if __name__ == '__main__':
    uvicorn.run("main:app",host="0.0.0.0",port=3002,reload=True)