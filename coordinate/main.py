import os
import json
from dotenv import load_dotenv
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel, Image

# .env 파일 로드
load_dotenv()

# Vertex AI 프로젝트 설정
PROJECT_ID = "virtual-muse-466706-v2"
LOCATION = "us-central1"
vertexai.init(project=PROJECT_ID, location=LOCATION)


# ----------------- 여기가 수정된 프롬프트 생성 함수입니다 -----------------

def create_revised_prompt_from_json(json_data):
    """
    JSON 데이터를 기반으로 AI가 이해하기 쉬운 서술형 프롬프트를 생성합니다.
    """
    scene = json_data["scene"]
    room = scene["room"]
    objects = scene["objects"]

    # 기본 스타일과 분위기 설정 (가장 중요)
    prompt_parts = [
        "A photorealistic 3D render of a bright, clean, and modern Korean-style bedroom.",
        "The room has simple white wallpaper and light-colored wood linoleum flooring.",
        "The overall aesthetic is minimalist, calm, and uncluttered, with a focus on natural textures and soft lighting."
    ]

    # 객체 정보를 자연스러운 문장으로 변환
    object_descriptions = []
    for obj in objects:
        obj_type = obj["type"]
        obj_name = obj["name"]
        material = obj.get("material", "a generic material")

        # 좌표 대신 상대적 위치를 묘사합니다.
        if obj_name == "bed":
            object_descriptions.append(f"A low-profile bed with an {material} is placed in the bottom-left area of the room.")
        elif obj_name == "desk":
            object_descriptions.append(f"A simple desk with a {material} is set against the bottom wall on the right side.")
        elif obj_name == "wardrobe":
            object_descriptions.append(f"A tall, {material} wardrobe stands in the top-right corner, against the right wall.")
        elif obj_name == "main_door":
            object_descriptions.append(f"A {material} door is on the right wall.")
        elif obj_name == "main_window":
            # 창문은 '뒤쪽 벽 중앙'과 같이 핵심적인 위치만 강조합니다.
            object_descriptions.append("A large window is centered on the back wall, letting in soft, natural light.")

    prompt_parts.extend(object_descriptions)

    # 최종적인 구도와 퀄리티 요구사항 추가
    prompt_parts.extend([
        "The view is a wide-angle shot, showing the entire room including the floor, ceiling, and all walls.",
        "No furniture or objects are cut off by the frame.",
        "The scene is rendered with realistic shadows and a natural, gentle light source from the window.",
        "Avoid any excessive decorations, clutter, or overly luxurious materials like marble."
    ])
    
    return " ".join(prompt_parts)

# ----------------- 여기까지 함수가 변경됩니다 -----------------


def generate_image_with_imagen(prompt: str, output_filename: str = "generated_image.png"):
    """
    Vertex AI Imagen 모델을 사용하여 이미지를 생성하고 파일로 저장합니다.
    (이 함수는 기존 코드를 그대로 사용합니다.)
    """
    print("✅ Imagen 모델을 사용하여 이미지 생성을 시작합니다...")
    model = ImageGenerationModel.from_pretrained("imagegeneration@006")
    images = model.generate_images(
        prompt=prompt,
        number_of_images=1
    )
    if images:
        images[0].save(location=output_filename, include_generation_parameters=True)
        print(f"🎉 이미지가 '{output_filename}' 파일로 성공적으로 저장되었습니다.")
        return output_filename
    else:
        print("❌ 이미지 생성에 실패했습니다.")
        return None

# 제공된 JSON 데이터 (기존과 동일)
json_input_data = {
    "scene": {
        "description": "...",
        "walls": { "...": {} },
        "room": { "width": 4000, "depth": 3000, "height": 2700 },
        "objects": [
            { "type": "door", "name": "main_door", "wall": 2, "dimensions": { "width": 900, "height": 2100 }, "position": { "x": 4000, "y": 500 }, "material": "white painted wood" },
            { "type": "window", "name": "main_window", "wall": 3, "dimensions": { "width": 1200, "height": 1200 }, "position": { "x": 1400, "y": 3000 }, "details": "..." },
            { "type": "furniture", "name": "bed", "dimensions": { "width": 2000, "depth": 1500 }, "position": { "x": 600, "y": 600 }, "material": "oak frame with white bedding" },
            { "type": "furniture", "name": "desk", "dimensions": { "width": 1200, "depth": 600 }, "position": { "x": 2400, "y": 400 }, "material": "maple top, metal legs" },
            { "type": "furniture", "name": "wardrobe", "dimensions": { "width": 800, "depth": 600 }, "position": { "x": 3500, "y": 2200 }, "material": "white matte finish" }
        ]
    }
}

# **수정된 함수를 사용하여 프롬프트 생성**
generated_prompt = create_revised_prompt_from_json(json_input_data)
print("--- [수정된] 생성된 이미지 프롬프트 ---")
print(generated_prompt)
print("\n--- 이미지 생성 시도 ---")

# 수정된 이미지 생성 함수 호출
generate_image_with_imagen(generated_prompt, output_filename="room_layout_revised.png")