from sqlmodel import SQLModel, Session, create_engine
from models import SearchData
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env = load_dotenv(os.path.join(BASE_DIR, ".env"))

db_user = os.environ["DB_USER"]
db_pwd = os.environ["DB_PASSWORD"]
DATABASE_URL = f"mysql+pymysql://{db_user}:{db_pwd}@localhost:3306/test"

# 데이터베이스 엔진 생성
engine = create_engine(DATABASE_URL, echo=True)

# 데이터베이스 초기화 함수
def init_db():
    SQLModel.metadata.create_all(engine)

# 세션 생성기
def get_session():
    with Session(engine) as session:
        yield session