from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,declarative_base

Base = declarative_base()

db_user = 'postgres'
db_password = "thrymr%40123"
db_host = 'localhost'
db_port = '5432'
db_name = 'socket'

DATABASE_URL = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

print("Tables created successfully!")









