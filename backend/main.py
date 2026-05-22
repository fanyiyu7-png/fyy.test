import asyncio
import json
import psutil
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from commands import (
    execute_remote, get_remote_stats, SERVERS, COMMON_COMMANDS,
    add_server, remove_server
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ControlRequest(BaseModel):
    server_id: str
    command: str

class AddServerRequest(BaseModel):
    ip: str
    password: str
    username: str = "root"
    port: int = 22
    name: str = None

class RemoveServerRequest(BaseModel):
    server_id: str

connected_clients = []

def get_local_stats():
    return {
        "cpu": round(psutil.cpu_percent(interval=1), 1),
        "memory": round(psutil.virtual_memory().percent, 1),
        "disk": round(psutil.disk_usage('/').percent, 1),
        "network_sent": psutil.net_io_counters().bytes_sent,
        "network_recv": psutil.net_io_counters().bytes_recv,
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            local = get_local_stats()
            
            servers_stats = {}
            for server_id in list(SERVERS.keys()):
                stats = await asyncio.get_event_loop().run_in_executor(
                    None, get_remote_stats, server_id
                )
                servers_stats[server_id] = stats
            
            payload = {
                "local": local,
                "servers": servers_stats,
            }
            
            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
    except Exception:
        if websocket in connected_clients:
            connected_clients.remove(websocket)

@app.get("/servers")
def list_servers():
    result = {}
    for k, v in SERVERS.items():
        result[k] = {
            "host": v["host"],
            "name": v["name"],
            "port": v["port"],
            "username": v["username"]
        }
    return result

@app.get("/commands")
def list_commands():
    return COMMON_COMMANDS

@app.post("/servers/add")
def api_add_server(req: AddServerRequest):
    try:
        server_id = add_server(
            ip=req.ip,
            password=req.password,
            username=req.username,
            port=req.port,
            name=req.name
        )
        return {"success": True, "server_id": server_id, "message": "添加成功: " + req.ip}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/servers/remove")
def api_remove_server(req: RemoveServerRequest):
    success = remove_server(req.server_id)
    if success:
        return {"success": True, "message": "已移除: " + req.server_id}
    return {"success": False, "error": "服务器不存在"}

@app.post("/control")
def remote_control(req: ControlRequest):
    result = execute_remote(req.server_id, req.command)
    return result
