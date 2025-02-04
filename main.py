from fastapi import FastAPI,Depends,status,HTTPException,Query,Request
from sqlmodel import SQLModel,create_engine,Session,select
from models import User
from fastapi.responses import JSONResponse
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer,OAuth2PasswordRequestForm
from jose import jwt
import datetime
import secrets
import os
import aiohttp
from pydantic import BaseModel
app=FastAPI()

KINOPOISK_API_URL="https://kinopoiskapiunofficial.tech"
API_KEY="" #Enter your free Kinopoisk API - API_KEY 

class Token (BaseModel):
    access_token:str
    token_type:str

engine=create_engine("sqlite:///./database.db",connect_args={"check_same_thread": False})

def get_session():
    with Session(engine) as session:
        yield session

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)
def get_secret_key_from_file(filename=".env"):
  try:
    with open(filename, "r") as f:
      for line in f:
        key, value = line.strip().split("=")
        if key == "SECRET_KEY":
          return value
  except FileNotFoundError:
    print(f"Файл {filename} не найден.")
    return None

SECRET_KEY = get_secret_key_from_file()
ACCESS_TOKEN_EXPIRE_MINUTES=30
oauth2_scheme=OAuth2PasswordBearer(tokenUrl="/login")

def create_access_token(data:dict):
    expire = datetime.datetime.utcnow()+datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode={"exp":expire,"jti":secrets.token_urlsafe(32),"sub":data.get("sub"),"id":data.get("id")}
    encoded_jwt=jwt.encode(to_encode,SECRET_KEY)
    return encoded_jwt

async def get_current_user(token:str=Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token,SECRET_KEY)
        username:str = payload.get("sub")
        usernameId:int = payload.get("id")
        if(username is None):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="fake token")
        return {"id":usernameId,"login":username}
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


pwd_context=CryptContext(schemes=["bcrypt"],deprecated="auto")
def hash_password(password):
    return pwd_context.hash(password)

def verify_password(plain_password,hashed_password):
    return pwd_context.verify(plain_password,hashed_password)

@app.post("/register")    
async def registration(user_data:dict,session:Session=Depends(get_session)):
    isCreated=next(session.exec(select(User).where(User.login==user_data['login'])),None)
    if(isCreated):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Username already exists!")
    else:
        new_user = User(login=user_data['login'],password=hash_password(user_data['password']))
        session.add(new_user)
        session.commit()
    return JSONResponse(status_code=status.HTTP_201_CREATED,content={'message':"User registrated successfully"})

@app.post("/login")
async def login(user_data:OAuth2PasswordRequestForm=Depends(),session:Session=Depends(get_session)):
    user_data_in_BD=next(session.exec(select(User).where(User.login==user_data.username)),None)
    if(not user_data_in_BD):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Incorrect username or password")
    if(not verify_password(user_data.password,user_data_in_BD.password)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Incorrect username or password")
    else:
        access_token = create_access_token(data={"sub":user_data_in_BD.login,"id":user_data_in_BD.id})
    return Token(access_token=access_token,token_type="bearer")

@app.get("/profile")
async def get_profile(someUser:dict = Depends(get_current_user),session:Session = Depends(get_session)):
    userData=session.exec(select(User).where(User.login==someUser["login"])).all()  

    return userData[0]

async def get_movies_by_keyword(keyword:str):
    headers = {
       "X-API-KEY": API_KEY,
        "Accept": "application/json", 
    }
    async with aiohttp.ClientSession() as session:
        url = f"{KINOPOISK_API_URL}/api/v2.1/films/search-by-keyword"
        response = await session.get(url,headers=headers,params={"keyword":keyword})
        data = await response.json()
        return data

async def get_movies_by_id(kinopoisk_id:int):
    headers = {
       "X-API-KEY": API_KEY,
        "Accept": "application/json", 
    }
    async with aiohttp.ClientSession() as session:
        url = f"{KINOPOISK_API_URL}/api/v2.2/films/{kinopoisk_id}"
        response = await session.get(url,headers=headers)
        data = await response.json()
        return data



@app.get("/movies/search")
async def search_movies(someUser:dict = Depends(get_current_user),query:str=Query(required = True)):
    try:
        movies = await get_movies_by_keyword(query)
    except aiohttp.ClientError as e:
        raise HTTPException(status_code=500,detail=str(e))

    try:
        data=[]
        for movie in movies["films"]:
            data.append({"film_kinopoisk_id":movie["filmId"],"nameEn":movie["nameEn"],"nameRu":movie["nameRu"],"year":movie["year"]})
    except:HTTPException(status_code=status.HTTP_409_CONFLICT,detail="Incorrect API data")
    return data

@app.get("/movies/{kinopoisk_id:int}")
async def search_movies_by_id(kinopoisk_id:int,someUser:dict = Depends(get_current_user)):
    try:
        movie=await get_movies_by_id(kinopoisk_id)
    except aiohttp.ClientError as e:
        raise HTTPException(status_code=500,detail=str(e))

    return movie  

@app.post("/movies/favorites")
async def add_movies_to_favorites(kinopoisk_id:int,someUser:dict=Depends(get_current_user),session:Session=Depends(get_session)):
    try:
        movie = await get_movies_by_id(kinopoisk_id)
        user_data_in_bd=session.get(User,someUser["id"])
        if not kinopoisk_id in user_data_in_bd.favourite_movies:
            
            new_favorite_list:list[int]=user_data_in_bd.favourite_movies.copy()
            new_favorite_list.append(kinopoisk_id)
    
            user_data_in_bd.favourite_movies=new_favorite_list
            session.commit()
            session.refresh(user_data_in_bd)
        return JSONResponse(status_code=status.HTTP_200_OK,content="Successfully adding a movie to your favorites list")            
    except aiohttp.ClientError as e:
        raise HTTPException(status_code=500,detail = str(e))
    


@app.delete("/movies/favorites/{kinopoisk_id}")
async def del_movies_into_favorites(kinopoisk_id:int,someUser:dict=Depends(get_current_user),session:Session=Depends(get_session)):
    try:
        movie = await get_movies_by_id(kinopoisk_id)
        user_data_in_bd=session.get(User,someUser["id"])
        if kinopoisk_id in user_data_in_bd.favourite_movies:

            new_favorite_list:list[int]=user_data_in_bd.favourite_movies.copy()
            new_favorite_list.remove(kinopoisk_id)
    
            user_data_in_bd.favourite_movies=new_favorite_list
            session.commit()
            session.refresh(user_data_in_bd)
        return JSONResponse(status_code=status.HTTP_200_OK,content="Successfully deleting a movie from the favorites list")        
    except aiohttp.ClientError as e:
        raise HTTPException(status_code=500,detail = str(e))

@app.get("/movies/favorites")
async def get_favorite_movies(someUser:dict=Depends(get_current_user),session:Session = Depends(get_session)):
    data_user_in_bd = session.get(User,someUser["id"])
    try:
        movies_list=[]
        for movies_id in data_user_in_bd.favourite_movies:
            movie=await get_movies_by_id(int(movies_id))
            movies_list.append(movie)

        return movies_list
    except aiohttp.ClientError as e:
        raise HTTPException(status_code=500,detail=str(e))
            
