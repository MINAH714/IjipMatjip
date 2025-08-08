# 1. 필요한 라이브러리들을 불러옵니다.
import os
from google import genai
from google.genai.types import Image, StyleReferenceImage, StyleReferenceConfig, EditImageConfig
from PIL import Image as PIL_Image
from pymongo import MongoClient # MongoDB 클라이언트 추가

# ----------------------------------------------------------------------
# !!! 1. 기본 설정 (사용자 환경에 맞게 수정) !!!
# ----------------------------------------------------------------------
PROJECT_ID = "virtual-muse-466706-v2"
LOCATION = "us-central1"

# MongoDB 접속 정보
MONGO_URI = "mongodb://13.55.21.100:27017"
MONGO_DB_NAME = "room_measure"
MONGO_COLLECTION_NAME = "room_layouts"

# 스타일의 기준이 될 '대표 이미지' 4개의 GCS 경로
STYLE_REFERENCE_GCS_URIS = [
    "gs://my-room-finetune-bucket/image/7a1b2c3d4e5f6a7b8c9d0e1f.png",
    "gs://my-room-finetune-bucket/image/8b2c3d4e5f6a7b8c9d0e1f2a.png",
    "gs://my-room-finetune-bucket/image/9c3d4e5f6a7b8c9d0e1f2a3b.png"
]

# 결과 이미지를 저장할 폴더 이름
OUTPUT_DIR = "generated_rooms"
# ----------------------------------------------------------------------


# Vertex AI 클라이언트 초기화
print("Vertex AI 클라이언트를 초기화합니다...")
client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
customization_model = "imagen-3.0-capability-001"
print("초기화 완료.")

# 스타일 참조 이미지 객체 미리 준비
style_reference_images = []
for i, gcs_uri in enumerate(STYLE_REFERENCE_GCS_URIS):
    style_image = Image(gcs_uri=gcs_uri)
    style_ref = StyleReferenceImage(
        reference_id=i + 1,
        reference_image=style_image,
        config=StyleReferenceConfig(style_description="a clean, modern Korean-style room with minimalist furniture"),
    )
    style_reference_images.append(style_ref)
print(f"{len(style_reference_images)}개의 스타일 참조 이미지 준비 완료.")


def fetch_data_from_mongodb():
    """
    MongoDB에 연결하여 모든 방 레이아웃 데이터를 가져오는 함수.
    """
    print(f"\n--- MongoDB에서 데이터 조회 중 ({MONGO_URI}) ---")
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client[MONGO_DB_NAME]
        collection = db[MONGO_COLLECTION_NAME]
        layouts = list(collection.find({})) # find 결과를 리스트로 변환
        client.close()
        print(f"성공! {len(layouts)}개의 레이아웃 데이터를 가져왔습니다.")
        return layouts
    except Exception as e:
        print(f"MongoDB 연결 또는 데이터 조회 실패: {e}")
        return []

def layout_to_prompt(layout_data):
    """
    MongoDB에서 가져온 단일 레이아웃 데이터를 분석하여 상세한 영어 프롬프트로 변환하는 함수.
    """
    scene = layout_data['scene']
    room = scene['room']
    furniture_list = scene['furniture']

    # 방 크기 설명 (cm -> m 변환)
    prompt = (f"A wide-angle side view of a room, meticulously arranged, reflecting a modern Korean residential sensibility. "
              f"The room's dimensions are {room['width']/100:.2f}m in width, {room['depth']/100:.2f}m in depth, and {room['height']/100:.2f}m in height. "
              f"The floor has a light-colored wood texture, and the walls are plain white.")

    # 가구 설명
    furniture_prompts = []
    for furniture in furniture_list:
        pos = furniture['position']
        size = furniture['size'] # [가로, 세로, 깊이]
        # cm를 m로 변환하여 프롬프트 생성
        furniture_prompts.append(
            f"A {furniture['type']} ({size[0]/100:.2f}m x {size[2]/100:.2f}m x {size[1]/100:.2f}m) " # size 순서: 가로, 깊이, 세로
            f"is placed at (x={pos['x']/100:.2f}m, z={pos['z']/100:.2f}m from the front wall)."
        )
    
    if furniture_prompts:
        prompt += " The furniture is precisely placed: " + " ".join(furniture_prompts)

    # 마무리 문구
    style_ids = "".join([f"[{i+1}]" for i in range(len(style_reference_images))])
    prompt += (f" The overall aesthetic is clean, uncluttered, and minimalist. "
               f"Render it in the hyper-realistic style of {style_ids}.")
    
    return prompt


def create_image_from_layout(layout_data, output_filename="new_room.png"):
    """
    레이아웃 데이터를 입력받아 최종 이미지를 생성하고 파일로 저장하는 메인 함수.
    """
    # 1단계: 레이아웃 데이터를 프롬프트로 번역
    print("\n--- 1단계: 레이아웃을 프롬프트로 번역 중 ---")
    prompt = layout_to_prompt(layout_data)
    print(f"생성된 프롬프트 (레이아웃 ID: {layout_data.get('_id', 'N/A')}):", prompt[:150] + "...")

    # 2단계: 프롬프트와 스타일 참조로 이미지 생성
    print("\n--- 2단계: 이미지 생성 요청 중 ---")
    try:
        response = client.models.edit_image(
            model=customization_model,
            prompt=prompt,
            reference_images=style_reference_images,
            config=EditImageConfig(
                edit_mode="EDIT_MODE_DEFAULT",
                number_of_images=1,
                seed=1, # 일관된 결과를 위해 시드 고정
                safety_filter_level="BLOCK_MEDIUM_AND_ABOVE",
                person_generation="ALLOW_ADULT",
            ),
        )
        
        # 3단계: 결과 이미지 저장
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        full_path = os.path.join(OUTPUT_DIR, output_filename)
        pil_image = response.generated_images[0].image._pil_image
        pil_image.save(full_path)
        print(f"\n성공! 생성된 이미지를 '{full_path}' 경로에 저장했습니다.")
        return full_path

    except Exception as e:
        print(f"\n오류 발생! 이미지 생성에 실패했습니다 (레이아웃 ID: {layout_data.get('_id', 'N/A')}). 오류: {e}")
        return None


if __name__ == '__main__':
    # 1. MongoDB에서 모든 방 레이아웃 데이터를 가져옵니다.
    all_layouts = fetch_data_from_mongodb()

    if all_layouts:
        # 2. 각 레이아웃에 대해 이미지를 생성합니다.
        for i, layout in enumerate(all_layouts):
            print(f"\n{'='*50}\n[{i+1}/{len(all_layouts)}] 번째 방 이미지 생성을 시작합니다.\n{'='*50}")
            
            # 파일명으로 사용할 고유 ID (ObjectID를 문자열로 변환)
            layout_id = str(layout.get('_id', f"unknown_layout_{i+1}"))
            output_filename = f"room_{layout_id}.png"
            
            # 메인 함수 호출하여 이미지 생성
            create_image_from_layout(layout, output_filename=output_filename)