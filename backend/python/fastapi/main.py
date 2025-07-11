# import os
# import requests
# from dotenv import load_dotenv
# from fastapi import FastAPI, Query, HTTPException, Response
# from io import BytesIO
# from PIL import Image

# # Load environment variables from .env file
# load_dotenv()

# # Get Stability AI API key from environment variables
# STABILITY_KEY = os.getenv("STABILITY_KEY")

# # Check if the API key is set
# if not STABILITY_KEY:
#     raise ValueError("STABILITY_KEY not found in .env file. Please set it.")

# app = FastAPI(
#     title="Furniture Image Generator with Stability AI",
#     description="API to generate furniture images using Stability AI's Stable Image Core model.",
#     version="1.0.0"
# )

# def send_generation_request(
#     host: str,
#     params: dict
# ) -> bytes:
#     """
#     Sends a generation request to the Stability AI API and returns the image bytes.

#     Args:
#         host (str): The API endpoint URL.
#         params (dict): Dictionary of parameters for the image generation.

#     Returns:
#         bytes: The generated image content as bytes.

#     Raises:
#         HTTPException: If the API request fails or the content is filtered.
#     """
#     headers = {
#         "Accept": "image/*",
#         "Authorization": f"Bearer {STABILITY_KEY}"
#     }

#     # Files are not used in this specific implementation as we are not sending images/masks
#     # but rather just parameters for text-to-image generation.
#     files = {"none": ''} # Required by the original send_generation_request logic

#     print(f"Sending REST request to {host} with params: {params}")
#     try:
#         response = requests.post(
#             host,
#             headers=headers,
#             files=files,
#             data=params
#         )
#         response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
#     except requests.exceptions.RequestException as e:
#         raise HTTPException(status_code=500, detail=f"Failed to connect to Stability AI API: {e}")

#     # Decode response
#     output_image = response.content
#     finish_reason = response.headers.get("finish-reason")
#     seed = response.headers.get("seed")

#     # Check for NSFW classification
#     if finish_reason == 'CONTENT_FILTERED':
#         raise HTTPException(status_code=400, detail="Generation failed due to content filter.")

#     print(f"Image generated with seed: {seed}")
#     return output_image

# @app.post("/generate-furniture", summary="Generate a furniture image", response_description="The generated image")
# async def generate_furniture(
#     prompt: str = Query(..., description="The prompt for generating the furniture image."),
#     negative_prompt: str = Query("", description="Optional: Negative prompt to guide the generation away from certain things."),
#     aspect_ratio: str = Query("1:1", description="Aspect ratio of the generated image.",
#                                enum=["21:9", "16:9", "3:2", "5:4", "1:1", "4:5", "2:3", "9:16", "9:21"]),
#     style_preset: str = Query("None", description="Optional: Style preset to apply to the generation.",
#                                enum=["None", "3d-model", "analog-film", "anime", "cinematic", "comic-book", "digital-art", "enhance", "fantasy-art", "isometric", "line-art", "low-poly", "modeling-compound", "neon-punk", "origami", "photographic", "pixel-art", "tile-texture"]),
#     seed: int = Query(0, description="Optional: Seed for reproducible generations. Use 0 for random."),
#     output_format: str = Query("jpeg", description="Output format of the image.",
#                                 enum=["webp", "jpeg", "png"])
# ):
#     """
#     Generates a furniture image based on the provided parameters using Stability AI's Stable Image Core model.

#     **Parameters:**
#     - `prompt`: A detailed description of the furniture you want to generate (e.g., "modern minimalist sofa in a living room").
#     - `negative_prompt`: (Optional) Things you want to avoid in the image (e.g., "blurry, distorted, old").
#     - `aspect_ratio`: (Optional) The desired aspect ratio of the image.
#     - `style_preset`: (Optional) A stylistic preset to apply to the image.
#     - `seed`: (Optional) A seed value for reproducible results. Set to 0 for random.
#     - `output_format`: (Optional) The desired output image format.

#     **Returns:**
#     - The generated image in the specified format.
#     """
#     host = "https://api.stability.ai/v2beta/stable-image/generate/core"

#     params = {
#         "prompt": prompt,
#         "negative_prompt": negative_prompt,
#         "aspect_ratio": aspect_ratio,
#         "seed": seed,
#         "output_format": output_format,
#         "mode": "text-to-image" # Explicitly set mode for clarity
#     }

#     if style_preset != "None":
#         params["style_preset"] = style_preset

#     try:
#         image_bytes = send_generation_request(host, params)
#         # Determine the media type based on the output_format
#         media_type = f"image/{output_format}"
#         if output_format == "jpeg":
#             media_type = "image/jpeg"
#         elif output_format == "png":
#             media_type = "image/png"
#         elif output_format == "webp":
#             media_type = "image/webp"

#         return Response(content=image_bytes, media_type=media_type)
#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")




import os
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Query, HTTPException, Response
from io import BytesIO
from PIL import Image
import boto3
import uuid # 고유한 파일명 생성을 위한 uuid 라이브러리 가져오기

# .env 파일에서 환경 변수 로드
load_dotenv()

# 환경 변수에서 Stability AI API 키 가져오기
STABILITY_KEY = os.getenv("STABILITY_KEY")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET_NAME = "kibwa-12"
# API 키 및 AWS 자격 증명 설정 확인
if not STABILITY_KEY:
    raise ValueError(".env 파일에 STABILITY_KEY가 없습니다. 설정해주세요.")
if not AWS_ACCESS_KEY_ID:
    raise ValueError(".env 파일에 AWS_ACCESS_KEY_ID가 없습니다. 설정해주세요.")
if not AWS_SECRET_ACCESS_KEY:
    raise ValueError(".env 파일에 AWS_SECRET_ACCESS_KEY가 없습니다. 설정해주세요.")
if not S3_BUCKET_NAME:
    raise ValueError(".env 파일에 S3_BUCKET_NAME이 없습니다. 설정해주세요.")

# S3 클라이언트 초기화
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

app = FastAPI(
    title="Stability AI를 활용한 가구 이미지 생성기",
    description="Stability AI의 Stable Image Core 모델을 사용하여 가구 이미지를 생성하고 S3에 저장하는 API입니다.",
    version="1.0.0"
)

def send_generation_request(
    host: str,
    params: dict
) -> bytes:
    """
    Stability AI API에 생성 요청을 보내고 이미지 바이트를 반환합니다.

    Args:
        host (str): API 엔드포인트 URL.
        params (dict): 이미지 생성을 위한 매개변수 딕셔너리.

    Returns:
        bytes: 생성된 이미지 콘텐츠(바이트).

    Raises:
        HTTPException: API 요청이 실패하거나 콘텐츠가 필터링된 경우.
    """
    headers = {
        "Accept": "image/*",
        "Authorization": f"Bearer {STABILITY_KEY}"
    }

    files = {"none": ''}

    print(f"매개변수: {params}로 {host}에 REST 요청을 보냅니다.")
    try:
        response = requests.post(
            host,
            headers=headers,
            files=files,
            data=params
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Stability AI API 연결에 실패했습니다: {e}")

    output_image = response.content
    finish_reason = response.headers.get("finish-reason")
    seed = response.headers.get("seed")

    if finish_reason == 'CONTENT_FILTERED':
        raise HTTPException(status_code=400, detail="콘텐츠 필터로 인해 생성에 실패했습니다.")

    print(f"시드: {seed}로 이미지가 생성되었습니다.")
    return output_image

async def upload_image_to_s3(image_bytes: bytes, file_name: str, content_type: str):
    """
    이미지 바이트를 S3 버킷에 업로드합니다.

    Args:
        image_bytes (bytes): 이미지 콘텐츠(바이트).
        file_name (str): S3에 저장할 이미지의 원하는 파일명.
        content_type (str): 이미지의 콘텐츠 유형 (예: "image/jpeg").

    Raises:
        HTTPException: S3 업로드에 실패한 경우.
    """
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=file_name,
            Body=image_bytes,
            ContentType=content_type
        )
        print(f"S3://{S3_BUCKET_NAME}/{file_name}에 이미지가 성공적으로 업로드되었습니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"S3에 이미지 업로드에 실패했습니다: {e}")



## S3 업로드 및 다운로드 기능이 포함된 FastAPI 엔드포인트

@app.post("/generate-furniture", summary="가구 이미지를 생성하고 S3에 저장 및 다운로드 제공", response_description="생성된 이미지 및 S3 URL")
async def generate_furniture(
    prompt: str = Query(..., description="가구 이미지 생성을 위한 프롬프트입니다."),
    negative_prompt: str = Query("", description="선택 사항: 특정 요소로부터 생성을 멀리하게 하는 부정적인 프롬프트입니다."),
    aspect_ratio: str = Query("1:1", description="생성된 이미지의 종횡비입니다.",
                               enum=["21:9", "16:9", "3:2", "5:4", "1:1", "4:5", "2:3", "9:16", "9:21"]),
    style_preset: str = Query("None", description="선택 사항: 생성에 적용할 스타일 프리셋입니다.",
                               enum=["None", "3d-model", "analog-film", "anime", "cinematic", "comic-book", "digital-art", "enhance", "fantasy-art", "isometric", "line-art", "low-poly", "modeling-compound", "neon-punk", "origami", "photographic", "pixel-art", "tile-texture"]),
    seed: int = Query(0, description="선택 사항: 재현 가능한 생성을 위한 시드입니다. 무작위를 원하면 0을 사용하세요."),
    output_format: str = Query("jpeg", description="이미지의 출력 형식입니다.",
                                enum=["webp", "jpeg", "png"])
):
    """
    Stability AI의 Stable Image Core 모델을 사용하여 제공된 매개변수를 기반으로 가구 이미지를 생성하고,
    생성된 이미지를 S3 버킷에 저장하며, 클라이언트가 이미지를 다운로드할 수 있도록 합니다.

    **매개변수:**
    - `prompt`: 생성하려는 가구에 대한 자세한 설명 (예: "거실에 있는 현대적인 미니멀리스트 소파").
    - `negative_prompt`: (선택 사항) 이미지에서 피하고 싶은 것 (예: "흐릿한, 왜곡된, 오래된").
    - `aspect_ratio`: (선택 사항) 이미지의 원하는 종횡비.
    - `style_preset`: (선택 사항) 이미지에 적용할 스타일 프리셋.
    - `seed`: (선택 사항) 재현 가능한 결과를 위한 시드 값. 무작위를 원하면 0으로 설정하세요.
    - `output_format`: (선택 사항) 원하는 출력 이미지 형식.

    **반환:**
    - 지정된 형식의 생성된 이미지, S3 URL, 그리고 다운로드를 위한 'Content-Disposition' 헤더.
    """
    host = "https://api.stability.ai/v2beta/stable-image/generate/core"

    params = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "aspect_ratio": aspect_ratio,
        "seed": seed,
        "output_format": output_format,
        "mode": "text-to-image"
    }

    if style_preset != "None":
        params["style_preset"] = style_preset

    try:
        image_bytes = send_generation_request(host, params)
        
        media_type = f"image/{output_format}"
        if output_format == "jpeg":
            media_type = "image/jpeg"
        elif output_format == "png":
            media_type = "image/png"
        elif output_format == "webp":
            media_type = "image/webp"

        folder_name = "furniture" # 또는 원하는 폴더명
        file_name = f"{folder_name}/furniture_image_{uuid.uuid4()}.{output_format}"
        
        await upload_image_to_s3(image_bytes, file_name, media_type)

        s3_url = f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{file_name}"
        
        headers = {
            "X-S3-URL": s3_url,
            # Content-Disposition 헤더를 추가하여 다운로드를 제안합니다.
            "Content-Disposition": f"attachment; filename=\"{file_name}\""
        }
        
        return Response(content=image_bytes, media_type=media_type, headers=headers)

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"예상치 못한 오류가 발생했습니다: {e}")

# 이 애플리케이션을 실행하려면 Python 파일(예: main.py)로 저장한 다음,
# 터미널에서 다음 명령을 실행하세요:
# uvicorn main:app --reload