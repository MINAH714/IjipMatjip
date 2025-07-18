# .env 파일 예시:
# OPENAI_API_KEY=sk-xxxxxxx
# AWS_ACCESS_KEY_ID=AKIAxxxxxx
# AWS_SECRET_ACCESS_KEY=xxxxxxxx
# S3_BUCKET=your-bucket-name

import os
import uuid
import json
import requests
import boto3
import pymysql
from dotenv import load_dotenv
from openai import OpenAI

# 1. 환경변수(.env) 불러오기
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
S3_BUCKET = os.getenv('S3_BUCKET')

# 2. MySQL 접속 정보
MYSQL_CONF = {
    "host": "13.236.16.220",  # 예시 IP. 실제 환경에 맞게 수정
    "port": 3306,
    "user": "root",
    "password": "1234",
    "database": "furniture_db"   # 반드시 생성된 DB명
}

# 3. OpenAI로 이미지 생성 (신버전 openai 패키지 호환)
def generate_furniture_image(prompt):
    client = OpenAI()
    response = client.images.generate(
        prompt=prompt,
        n=1,
        size="1024x1024"
    )
    image_url = response.data[0].url
    return image_url

# 4. S3 업로드 함수
def upload_image_to_s3(image_url, category, obj_id):
    s3_client = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )
    img_data = requests.get(image_url).content
    s3_key = f'furniture/{category}/{obj_id}/main.jpg'
    s3_client.put_object(Bucket=S3_BUCKET, Key=s3_key, Body=img_data, ContentType='image/jpeg')
    s3_url = f'https://{S3_BUCKET}.s3.amazonaws.com/{s3_key}'
    return s3_url

# 5. MySQL 저장 함수 (컬럼명/타입 사전 테이블 생성돼야 함)
def save_furniture_metadata(metadata_dict):
    connection = pymysql.connect(
        host=MYSQL_CONF["host"], port=MYSQL_CONF["port"],
        user=MYSQL_CONF["user"], password=MYSQL_CONF["password"],
        db=MYSQL_CONF["database"], charset='utf8mb4'
    )
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO furniture 
            (id, name, category, width, depth, height, form, image_url, restriction, tags, notes) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                metadata_dict['id'],
                metadata_dict.get('name', ''),
                metadata_dict.get('category', ''),
                metadata_dict.get('width', 0),
                metadata_dict.get('depth', 0),
                metadata_dict.get('height', 0),
                metadata_dict.get('form', ''),
                metadata_dict.get('image_url', ''),
                json.dumps(metadata_dict.get('restriction', [])),
                json.dumps(metadata_dict.get('tags', [])),
                metadata_dict.get('notes', '')
            ))
            connection.commit()
    finally:
        connection.close()

# 6. 전체 자동화 실행 함수
def create_and_save_furniture(prompt, category, metadata):
    obj_id = str(uuid.uuid4())
    # 1) OpenAI 이미지 생성
    image_url = generate_furniture_image(prompt)
    # 2) 이미지 S3 업로드
    s3_url = upload_image_to_s3(image_url, category, obj_id)
    # 3) 메타데이터 준비 및 DB 저장
    metadata = metadata.copy()
    metadata['id'] = obj_id
    metadata['image_url'] = s3_url
    metadata['category'] = category
    save_furniture_metadata(metadata)
    return obj_id, s3_url

# 7. 실행 예시
if __name__ == "__main__":
    # 예시 프롬프트 & 메타데이터
    prompt = "Modern wood single bed with storage, front view, white background"
    category = "bed"
    sample_metadata = {
        "name": "원목 수납형 침대",
        "width": 2060,
        "depth": 1100,
        "height": 900,
        "form": "rectangle",
        "restriction": ["no_window_front"],
        "tags": ["모던", "수납", "원목"],
        "notes": "창문 앞 설치 금지"
    }
    obj_id, img_url = create_and_save_furniture(prompt, category, sample_metadata)
    print(f"등록 완료: {obj_id}\nS3 이미지: {img_url}")
