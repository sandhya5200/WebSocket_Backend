from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import User, ChatMessages, Group
from typing import List
from database import engine
from models import Base
import base64

app = FastAPI()

Base.metadata.create_all(bind=engine)

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, WebSocket] = {}           #a simple list which keeps track of all users connected to websocket 

    async def connect(self, websocket: WebSocket, user_id: int):     #to accept the new websocket connection from a client
        await websocket.accept()
        self.active_connections[user_id] = websocket     #adds the new connection to active_connection list

    def disconnect(self, user_id: int):                  #removes the disconnected websocket from the active_connections list
        self.active_connections.pop(user_id, None)

    async def send_personal_message(self, message: str, to_user_id: int):    #For one-to-one message 
        recipient = self.active_connections.get(to_user_id)
        if recipient:
            await recipient.send_text(message)

    async def broadcast(self, message: str, group_users: List[int]):  #to broadcast(sends a message to all connected users)
        for user_id in group_users:
            connection = self.active_connections.get(user_id)
            if connection:
                await connection.send_text(message)

manager = ConnectionManager()

@app.post("/users/")
def create_user(username: str, db: Session = Depends(get_db)):
    new_user = User(username=username)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/groups/")
def create_group(group_name: str, user_ids: List[int], db: Session = Depends(get_db)):
    
    if len(user_ids) != len(set(user_ids)):
        raise HTTPException(status_code=400, detail="Duplicate user IDs are not allowed in the group.")

    existing_users = db.query(User).filter(User.user_id.in_(user_ids)).all()
    existing_user_ids = {user.user_id for user in existing_users}

    missing_users = set(user_ids) - existing_user_ids
    if missing_users:
        raise HTTPException(status_code=400, detail=f"Users not found: {missing_users}")

    group = Group(group_name=group_name, user_ids=user_ids)
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int, db: Session = Depends(get_db)):
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type", "group")
            message_text = data.get("message")
            image_data = data.get("image")
            to_user_id = data.get("to_user_id")
            group_id = data.get("group_id") if message_type == "group" else None

            if message_type == "personal":
                if not to_user_id or not db.query(User).filter_by(user_id=to_user_id).first():
                    await websocket.send_text("error: user does not exist.")
                    continue

            elif message_type == "group":
                group = db.query(Group).filter_by(group_id=group_id).first()
                if not group:
                    await websocket.send_text("error: group does not exist.")
                    continue
                if user_id not in group.user_ids:
                    await websocket.send_text("error: You are not a member of this group.")
                    continue

            # Decode base64 image
            image_binary = None
            if image_data:
                try:
                    image_binary = base64.b64decode(image_data)
                except Exception as e:
                    await websocket.send_text("error: Invalid image data.")
                    continue

            new_message = ChatMessages(
                from_user_id=user_id,
                message=message_text if not image_binary else None,
                image=image_binary if image_binary else None,
                to_user_id=to_user_id if message_type == "personal" else None,
                group_id=group_id,
                type=message_type
            )
            db.add(new_message)
            db.commit()

            # Notify
            if message_type == "personal":
                if message_text:
                    await manager.send_personal_message(
                        f"User #{user_id} (Private): {message_text}", to_user_id
                    )
                elif image_data:
                    await manager.send_personal_message(
                        f"User #{user_id} (Private): {image_data}", to_user_id
                    )

            elif message_type == "group":
                if message_text:
                    await manager.broadcast(
                        f"User #{user_id} says in Group #{group_id}: {message_text}", group.user_ids
                    )
                elif image_data:
                    await manager.broadcast(
                        f"User #{user_id} sent an image in Group #{group_id}", group.user_ids
                    )

    except WebSocketDisconnect:
        manager.disconnect(user_id)
        await manager.broadcast(f"User #{user_id} has left the chat", [])



