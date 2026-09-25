from fastapi import FastAPI, Depends,Query,HTTPException
from sqlalchemy.orm import Session
import models
from pydantic import BaseModel,Field
from typing import Annotated,Optional,Literal
from models import Room,RentPayment,Reservation,Review, Roommate_Requests
from database import engine,Sessionlocal
from fastapi.responses import JSONResponse
from router import admin,auth
from router.auth import get_current_user
from sqlalchemy import asc, desc
from fastapi.middleware.cors import CORSMiddleware

app=FastAPI()

origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
class RoommateRequestCreate(BaseModel):
    preferred_location: str
    budget_min: Optional[float] = Field(default=None, ge=0)
    budget_max: Optional[float] = Field(default=None, ge=0)
    preferred_category: str
    description: str


class RoommateRequestUpdate(BaseModel):
    preferred_location: Optional[str] = None
    budget_min: Optional[float] = Field(default=None, ge=0)
    budget_max: Optional[float] = Field(default=None, ge=0)
    preferred_category: Optional[str] = None
    description: Optional[str] = None

class ReviewCreate(BaseModel):
    rating: int = Field(default=None, ge=1, le=5)
    comment:str


class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    comment: Optional[str] =Field(default=None)
    
class RentPaymentCreate(BaseModel):
    room_id: int
    amount: float = Field(default=None, gt=0)

    payment_method: Literal[
        "cash",
        "bkash",
        "nagad",
        "bank"
    ]

    transaction_id: Optional[str] = Field( default=None )

class RentPaymentUpdate(BaseModel):
    amount: Optional[float] = Field( default=None,gt=0 )
    payment_method: Optional[
        Literal[
            "cash",
            "bkash",
            "nagad",
            "bank"
        ]
    ] =Field( default=None )

    status: Optional[ Literal["paid","pending","failed"]] = Field( default=None )

    transaction_id: Optional[str] =Field( default=None )
    
models.Base.metadata.create_all(bind=engine)
app.include_router(auth.router)
app.include_router(admin.router)


def get_db():
    db=Sessionlocal()
    try:
        yield db
    finally:
        db.close()
db_dapandancy=Annotated[Session,Depends(get_db)]
user_dapandancy=Annotated[dict,Depends(get_current_user)]

@app.get("/rooms/all")
def get_all_rooms( db: db_dapandancy):
    rooms = db.query(Room).all()
    return rooms


@app.get("/room/{room_id}")
def get_specific_room(user: user_dapandancy,db: db_dapandancy,room_id: int):
    if user is None:
        raise HTTPException( status_code=401,detail="Failed authentication")
    room = db.query(Room).filter(Room.id == room_id).first()
    if room is None:
        raise HTTPException(status_code=404,detail="Room Not Found!")
    return room
@app.post("/reserved/{room_id}")
def reserve_room( user: user_dapandancy, db: db_dapandancy, room_id: int):
    if user is None:
        raise HTTPException(status_code=401,  detail="Failed authentication" )

    room = db.query(Room).filter( Room.id == room_id).first()
    if room is None:
        raise HTTPException( status_code=404, detail="Room Not Found!")

    existing_reservation = db.query(Reservation).filter(
        Reservation.room_id == room_id,
        Reservation.user_id == user.get("user_id"),
        Reservation.status == "pending" ).first()

    if existing_reservation:
        raise HTTPException(status_code=400,detail="You already have a pending reservation for this room" )

    if room.available_seats <= 0:
        raise HTTPException(status_code=400,detail="No available seats")

    reservation_model = Reservation(
        room_id=room_id,
        user_id=user.get("user_id"),
        status="pending"
    )

    db.add(reservation_model)
    db.commit()
    return JSONResponse(status_code=201, content={"message": "Room reserved successfully"})

@app.delete("/reservation/cancelled/{reservation_id}")
def cancelled_reservation(user: user_dapandancy,db: db_dapandancy, reservation_id: int):
    if user is None:
        raise HTTPException(status_code=401,detail="Failed authentication")

    reservation = db.query(Reservation).filter(
        Reservation.id == reservation_id,
        Reservation.user_id == user.get("user_id")
    ).first()

    if reservation is None:
        raise HTTPException(status_code=404,detail="Reservation Not Found!")
    reservation.status = "cancelled"
    db.commit()

    return JSONResponse(status_code=200,content={"message": "Reservation cancelled successfully"})


@app.get("/reservation/my")
def my_reservations(user: user_dapandancy,db: db_dapandancy):
    if user is None:
        raise HTTPException(status_code=401, detail="Failed authentication")

    reservations = db.query(Reservation).filter(Reservation.user_id == user.get("user_id")).all()
    return reservations

@app.post("/roommate/request")
def create_roommate_request(user: user_dapandancy,db: db_dapandancy,request_data: RoommateRequestCreate):
    if user is None:
        raise HTTPException(status_code=401,detail="Failed authentication")
    if (
        request_data.budget_min is not None
        and request_data.budget_max is not None
        and request_data.budget_max < request_data.budget_min):
        raise HTTPException(
            status_code=400, detail="Maximum budget cannot be less than minimum budget")

    roommate_request = Roommate_Requests(
        user_id=user.get("user_id"),
        preferred_location=request_data.preferred_location,
        budget_min=request_data.budget_min,
        budget_max=request_data.budget_max,
        preferred_category=request_data.preferred_category,
        description=request_data.description,
        status="active"
    )

    db.add(roommate_request)
    db.commit()
    return JSONResponse(status_code=201, content={"message": "Roommate request created successfully" })
    
@app.get("/roommate/my")
def my_roommate_requests(user: user_dapandancy,db: db_dapandancy):
    if user is None:
        raise HTTPException(status_code=401,detail="Failed authentication")

    requests = db.query(Roommate_Requests).filter( Roommate_Requests.user_id == user.get("user_id")).all()
    return requests

@app.put("/roommate/{request_id}")
def update_roommate_request(user: user_dapandancy,db: db_dapandancy,request_id: int, request_data: RoommateRequestUpdate):
    if user is None:
        raise HTTPException(status_code=401,detail="Failed authentication")
    roommate_request = db.query(Roommate_Requests).filter(
        Roommate_Requests.id == request_id,
        Roommate_Requests.user_id == user.get("user_id")).first()
    if roommate_request is None:
        raise HTTPException( status_code=404,detail="Roommate request not found")

    update_data = request_data.model_dump( exclude_unset=True)

    new_min = update_data.get( "budget_min",roommate_request.budget_min)

    new_max = update_data.get( "budget_max", roommate_request.budget_max)

    if (new_min is not None and new_max is not None and new_max < new_min):
        raise HTTPException(
            status_code=400,detail="Maximum budget cannot be less than minimum budget")
    for key, value in update_data.items():
        setattr(roommate_request, key, value)
    db.commit()
    return JSONResponse(status_code=201, content={"message": "Roommate request updated successfully"})
@app.get("/roommate/requests/active")
def active_roommate_requests(user: user_dapandancy,db: db_dapandancy):
    if user is None:
        raise HTTPException(status_code=401,detail="Failed authentication")
    requests = db.query(Roommate_Requests).filter(
        Roommate_Requests.status == "active",
        Roommate_Requests.user_id != user.get("user_id")).all()
    return requests

@app.post("/review/{room_id}")
def create_review(room_id: int,review_data: ReviewCreate,user: user_dapandancy, db: db_dapandancy):
    if user is None:raise HTTPException(status_code=401,detail="Failed authentication")
    room = db.query(Room).filter(Room.id == room_id ).first()
    if room is None:
        raise HTTPException(status_code=404,detail="Room not found")
    existing_review = db.query(Review).filter(
        Review.room_id == room_id,
        Review.user_id == user.get("user_id")
    ).first()

    if existing_review:
        raise HTTPException( status_code=400,detail="You have already reviewed this room")

    review = Review(
        room_id=room_id,
        user_id=user.get("user_id"),
        rating=review_data.rating,
        comment=review_data.comment
    )

    db.add(review)
    db.commit()
    return JSONResponse( status_code=201, content={"message": "Review created successfully","review_id": review.id})
    
# @app.get("/review/room/{room_id}")
# def get_room_reviews(room_id: int,user: user_dapandancy,db: db_dapandancy):
#     if user is None:
#         raise HTTPException(status_code=401,detail="Failed authentication" )

#     room = db.query(Room).filter(Room.id == room_id).first()

#     if room is None:
#         raise HTTPException(status_code=404,detail="Room not found")

#     reviews = db.query(Review).filter(Review.room_id == room_id).all()
#     return reviews
@app.get("/review/my")
def get_my_reviews(user: user_dapandancy,db: db_dapandancy):
    if user is None:
        raise HTTPException(status_code=401,detail="Failed authentication")

    reviews = db.query(Review).filter(Review.user_id == user.get("user_id")).all()
    return reviews


@app.post("/payment")
def create_payment(payment_data: RentPaymentCreate,user: user_dapandancy,db: db_dapandancy):
    if user is None:
        raise HTTPException( status_code=401, detail="Failed authentication")
    room = db.query(Room).filter(Room.id == payment_data.room_id).first()
    if room is None:
        raise HTTPException(status_code=404,detail="Room not found")
    payment = RentPayment(
        room_id=payment_data.room_id,
        user_id=user.get("user_id"),
        amount=payment_data.amount,
        payment_method=payment_data.payment_method,
        transaction_id=payment_data.transaction_id,
        status="pending"
    )
    db.add(payment)
    db.commit()
    return JSONResponse( status_code=201, content={"message": "Rent payment created successfully",    "payment_id": payment.id})

@app.get("/rooms/sort")
def sort_rooms(
    db: db_dapandancy,
    sorted_by: str = Query(
        description="sort on the basis of rent, title, created_at or available_seats"),
    order: str = Query("desc", description="choose order asc or desc")):
    valid_fields = [
        "rent",
        "title",
        "created_at",
        "available_seats"
    ]

    if sorted_by not in valid_fields:
        raise HTTPException(status_code=400,detail=f"Invalid field. Select from {valid_fields}")

    if order not in ["asc", "desc"]:
        raise HTTPException(status_code=400,detail="Choose between asc or desc")

    if order == "asc":
        data = db.query(Room).order_by(asc(getattr(Room, sorted_by))).all()
    else:
        data = db.query(Room).order_by(desc(getattr(Room, sorted_by))).all()

    return data

# @app.get("/payment/my")
# def get_my_payments(user: user_dapandancy,db: db_dapandancy):
#     if user is None:
#         raise HTTPException(status_code=401,detail="Failed authentication")
#     payments = db.query(RentPayment).filter(RentPayment.user_id == user.get("user_id")).all()
#     return payments
# @app.get("/payment/room/{room_id}")
# def get_room_payments(room_id: int,user: user_dapandancy,db: db_dapandancy):
#     if user is None:
#         raise HTTPException(status_code=401, detail="Failed authentication")
#     room = db.query(Room).filter(Room.id == room_id ).first()
#     if room is None:
#         raise HTTPException( status_code=404, detail="Room not found")

#     payments = db.query(RentPayment).filter(RentPayment.room_id == room_id).all()
#     return payments

# @app.get("/payment/{payment_id}")
# def get_payment( payment_id: int, user: user_dapandancy, db: db_dapandancy):
#     if user is None:
#         raise HTTPException( status_code=401, detail="Failed authentication" )
#     payment = db.query(RentPayment).filter( RentPayment.id == payment_id,  RentPayment.user_id == user.get("user_id")).first()
#     if payment is None:
#         raise HTTPException( status_code=404,detail="Payment not found")
#     return payment

# @app.put("/payment/{payment_id}")
# def update_payment(payment_id: int,payment_data: RentPaymentUpdate, user: user_dapandancy,db: db_dapandancy):
#     if user is None:
#         raise HTTPException( status_code=401, detail="Failed authentication")
#     payment = db.query(RentPayment).filter(RentPayment.id == payment_id,RentPayment.user_id == user.get("user_id")).first()
#     if payment is None:
#         raise HTTPException(status_code=404,detail="Payment not found")
#     update_data = payment_data.model_dump( exclude_unset=True)
#     for key, value in update_data.items():
#         setattr(payment, key, value)
#     db.commit()
#     return JSONResponse( status_code=201, content= {"message": "Payment updated successfully"})
# @app.delete("/payment/{payment_id}")
# def delete_payment(payment_id: int,user: user_dapandancy,db: db_dapandancy):
#     if user is None:
#         raise HTTPException(status_code=401,detail="Failed authentication")
#     payment = db.query(RentPayment).filter(RentPayment.id == payment_id,RentPayment.user_id == user.get("user_id")).first()
#     if payment is None:
#         raise HTTPException(status_code=404,detail="Payment not found")
#     db.delete(payment)
#     db.commit()
#     return JSONResponse( status_code=201, content= {"message": "Payment deleted successfully"})
# @app.put("/review/{review_id}")
# def update_review(review_id: int,review_data: ReviewUpdate, user: user_dapandancy,db: db_dapandancy):
#     if user is None:
#         raise HTTPException(status_code=401,detail="Failed authentication")

#     review = db.query(Review).filter(Review.id == review_id,Review.user_id == user.get("user_id")).first()

#     if review is None:
#         raise HTTPException(status_code=404,detail="Review not found")
#     update_data = review_data.model_dump(exclude_unset=True)
#     for key, value in update_data.items():
#         setattr(review, key, value)
#     db.commit()
#     return JSONResponse( status_code=201, content={"message": "Review updated successfully"})
# @app.delete("/review/{review_id}")
# def delete_review(review_id: int, user: user_dapandancy,db: db_dapandancy):
#     if user is None:
#         raise HTTPException(status_code=401,detail="Failed authentication")
#     review = db.query(Review).filter(Review.id == review_id,Review.user_id == user.get("user_id") ).first()
#     if review is None:
#         raise HTTPException( status_code=404,detail="Review not found")
#     db.delete(review)
#     db.commit()
#     return JSONResponse( status_code=201, content={"message": "Review deleted successfully"})