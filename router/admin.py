from fastapi import APIRouter, Depends,HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel,Field
from typing import Annotated,Optional
from models import Room,Reservation,RentPayment
from database import Sessionlocal
from fastapi.responses import JSONResponse
from router.auth import get_current_user

router=APIRouter()

class RoomCreate(BaseModel):
    title: str
    category: str
    description: str
    rent: float = Field(default=0.0, ge=0)
    address: str
    room_size: str | None = None
    total_seats: int = Field(default=1, ge=1)
    available_seats: int = Field(default=1, ge=0)
    cover_image: str | None = None

class UpdateRoom(BaseModel):

    title: Optional[str] =Field(default=None) 
    category: Optional[str] =Field(default=None)
    description: Optional[str] =Field(default=None)
    rent: Optional[float] = Field(default=None, ge=0)
    address: Optional[str] = Field(default=None)
    room_size: Optional[str] =Field(default=None)
    total_seats: Optional[int] = Field(default=None, ge=1)
    available_seats: Optional[int] = Field(default=None, ge=0)
    cover_image: Optional[str] =Field(default=None)
  
def get_db():
    db=Sessionlocal()
    try:
        yield db
    finally:
        db.close()
db_dapandancy=Annotated[Session,Depends(get_db)]
user_dapandancy=Annotated[dict,Depends(get_current_user)]

@router.post("/admin/create_room")
def create_room(
    user: user_dapandancy,
    db: db_dapandancy,
    new_room: RoomCreate
):
    if user is None or user.get("role") != "admin":
        raise HTTPException(
            status_code=401,
            detail="Failed authentication"
        )

    room_model = Room(
        **new_room.model_dump(),
        admin_id=user.get("id")
    )

    db.add(room_model)
    db.commit()
    db.refresh(room_model)

    return JSONResponse(
        status_code=201,
        content={
            "message": "Room added successfully"
        }
    )


@router.put("/admin/update_room/{room_id}")
def update_room(
    user: user_dapandancy,
    db: db_dapandancy,
    update_room_data: UpdateRoom,
    room_id: int
):
    if user is None or user.get("role") != "admin":
        raise HTTPException(
            status_code=401,
            detail="Failed authentication"
        )

    room = db.query(Room).filter(
        Room.id == room_id
    ).first()

    if room is None:
        raise HTTPException(
            status_code=404,
            detail="Room not found"
        )

    update_data = update_room_data.model_dump(
        exclude_unset=True
    )

    for key, value in update_data.items():
        setattr(room, key, value)

    db.commit()
    db.refresh(room)

    return {
        "message": "Room updated successfully"
    }
    
@router.delete("/admin/delete_room/{room_id}")
def delete_room(
    user: user_dapandancy,
    db: db_dapandancy,
    room_id: int
):
    if user is None or user.get("role") != "admin":
        raise HTTPException(
            status_code=401,
            detail="Failed authentication"
        )

    room = db.query(Room).filter(
        Room.id == room_id
    ).first()

    if room is None:
        raise HTTPException(
            status_code=404,
            detail="Room not found"
        )

    db.delete(room)
    db.commit()

    return JSONResponse(
        status_code=200,
        content={
            "message": "Room deleted successfully"
        }
    )
    
    
@router.put("/admin/approve_reservation/{reservation_id}")
def approve_reservation(
    user: user_dapandancy,
    db: db_dapandancy,
    reservation_id: int
):
    if user is None or user.get("role") != "admin":
        raise HTTPException(
            status_code=401,
            detail="Failed authentication"
        )

    reservation = db.query(Reservation).filter(
        Reservation.id == reservation_id
    ).first()

    if reservation is None:
        raise HTTPException(
            status_code=404,
            detail="Reservation not found"
        )

    if reservation.status != "pending":
        raise HTTPException(
            status_code=400,
            detail="Reservation is not pending"
        )

    room = db.query(Room).filter(
        Room.id == reservation.room_id
    ).first()

    if room is None:
        raise HTTPException(
            status_code=404,
            detail="Room not found"
        )

    if room.available_seats <= 0:
        raise HTTPException(
            status_code=400,
            detail="No available seats"
        )

    reservation.status = "approved"
    room.available_seats -= 1

    db.commit()

    return {
        "message": "Reservation approved successfully"
    }
    
@router.put("/admin/payment/{payment_id}/approve")
def approve_payment(
    payment_id: int,
    user: user_dapandancy,
    db: db_dapandancy
):
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Failed authentication"
        )

    # Admin check
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admin can approve payment"
        )

    payment = db.query(RentPayment).filter(
        RentPayment.id == payment_id
    ).first()

    if payment is None:
        raise HTTPException(
            status_code=404,
            detail="Payment not found"
        )

    if payment.status != "pending":
        raise HTTPException(
            status_code=400,
            detail="Only pending payment can be approved"
        )

    payment.status = "paid"

    db.commit()
    db.refresh(payment)

    return {
        "message": "Payment approved successfully",
        "payment_id": payment.id,
        "status": payment.status
    }