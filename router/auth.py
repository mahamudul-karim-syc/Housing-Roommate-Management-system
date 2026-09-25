from fastapi import FastAPI,APIRouter,Depends,HTTPException
from database import Sessionlocal
from typing import Annotated,Optional
from sqlalchemy.orm import Session 
from models import User
from pydantic import BaseModel,Field
from fastapi.responses import JSONResponse
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm,OAuth2PasswordBearer
from jose import jwt
from datetime import timedelta,datetime,timezone

router=APIRouter()

class Create_User(BaseModel):
    email:str
    username:str
    firstname:str
    lastname:str
    password:str
    phone:str
    role:str

 
class Update_user(BaseModel):
    
    email:Optional[str]=Field(default=None)
    username:Optional[str]=Field(default=None)
    firstname:Optional[str]=Field(default=None)
    lastname:Optional[str]=Field(default=None)
    phone:Optional[str]=Field(default=None)
    
class Update_password(BaseModel):
    current_password:str
    new_password:str
    
bcrypt_context=CryptContext(schemes=['bcrypt'],deprecated='auto')
oAuth_bearer=OAuth2PasswordBearer(tokenUrl='login')

SECRET_KEY='31be39e9f0d724e37e6b7e65403753c9574949e0d0e7d1d93de50a44632b2ccf'
ALGORITHM='HS256'

def authenticate_user(username,password,db):
    user=db.query(User).filter(User.username==username).first()
    if user is None:
        return False
    if bcrypt_context.verify(password,user.hashpassword):
        return user
    return False


def token_user(username:str,user_id:int,role:str,expert=timedelta):
    encode={'sub':username,'id':user_id,'role':role}
    exp=datetime.now(timezone.utc)+expert
    encode.update({'exp':exp})
    return jwt.encode(encode,SECRET_KEY,algorithm=ALGORITHM)


def get_current_user(token:Annotated[str,Depends(oAuth_bearer)]):
    try:
        payload=jwt.decode(token,SECRET_KEY,algorithms=[ALGORITHM])
        username:str=payload.get('sub')
        user_id:int=payload.get('id')
        role:str=payload.get('role')
        if username is None or user_id is None:
            raise HTTPException(status_code=404,detail='user not found')
            
        return {'username':username,'user_id':user_id,'role':role}
    except:
        
         raise HTTPException(status_code=404,detail='user not found')

def get_db():
    db=Sessionlocal()
    try:
        yield db
    finally:
        db.close()
db_dapandancy=Annotated[Session,Depends(get_db)]
user_dapandancy=Annotated[dict,Depends(get_current_user)]

@router.post('/create_user')
def create_user(db:db_dapandancy,new_user:Create_User):
    user_modal=User (
       email=new_user.email,
       username=new_user.username,
       firstname=new_user.firstname,
       lastname=new_user.lastname,
       phone=new_user.phone,
       hashpassword=bcrypt_context.hash(new_user.password),
       role=new_user.role    
   )
    db.add(user_modal)
    db.commit()
    return JSONResponse(status_code=201,content={'message':'Create User Successfully'})

@router.post('/login')
def login_user(db:db_dapandancy,from_data:Annotated[OAuth2PasswordRequestForm,Depends()]):
    user=authenticate_user(from_data.username,from_data.password,db)
    if not user :
        raise HTTPException(status_code=401,detail='Filed Autheraizration')
    token=token_user(user.username,user.id,user.role, timedelta(minutes=30))
    return {'access_token':token,'token_type':'bearer'}
@router.get('/user')
def get_user(
    user: user_dapandancy,
    db: db_dapandancy
):
    if user is None:
        raise HTTPException(
            status_code=401,
            detail='Failed Authentication'
        )

    current_user = db.query(User).filter(
        User.id == user.get("user_id")
    ).first()

    if current_user is None:
        raise HTTPException(
            status_code=404,
            detail='User not found'
        )

    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "firstname": current_user.firstname,
        "lastname": current_user.lastname,
        "phone": current_user.phone,
        "role": current_user.role
    }



@router.put('/Edituser')
def update_user(user:user_dapandancy,db:db_dapandancy,Update_user:Update_user):
    
    if user is None:
        raise HTTPException(status_code=401,detail='Filed Autheraizration')
    
    user=  db.query(User).filter(User.id==user.get("user_id")).first()
    updata_data=Update_user.model_dump(exclude_unset=True)
    
    for key,values in updata_data.items():
        setattr(user,key,values)
        
    db.commit()
    return JSONResponse(status_code=201,content={"massage":"User Update Successfully"})


@router.put('/passwordchange')
def update_password(user:user_dapandancy,db:db_dapandancy,updatepassword:Update_password):
    if user is None:
        raise HTTPException(status_code=401,detail='Filed Autheraizration')
    
    user=  db.query(User).filter(User.id==user.get('user_id')).first()
    
    if not bcrypt_context.verify(updatepassword.current_password,user.hashpassword):
        raise HTTPException(status_code=401,detail='wrong password')
    
    user.hashpassword=bcrypt_context.hash(updatepassword.new_password)
    
    db.add(user)
    db.commit()
    return JSONResponse(status_code=201,content={"message":"Password Update Successfully"})

