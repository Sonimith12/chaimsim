"""FastAPI app: REST endpoints to load scenarios, plus a WebSocket that drives the simulation."""

from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import TypeAdapter, ValidationError

from schemas import (
    CustomScenarioRequest,
    EventActionCommand,
    ErrorMessage,
    LoadScenarioRequest,
    PolicyChangeCommand,
    ResetCommand,
    StateMessage,
    StepCommand,
)
import campaign
from network_spec import NetworkSpec
from sim_bridge import NetworkSpecError, SimBridge

app = FastAPI(title="ChainSim 3D backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single-player local game: one simulation shared by REST and the WebSocket.
bridge = SimBridge()

_Command = TypeAdapter(StepCommand | ResetCommand | PolicyChangeCommand | EventActionCommand)


@app.get("/api/scenarios")
def list_scenarios() -> list[dict]:
    return bridge.list_scenarios()


@app.post("/api/scenario/load")
def load_scenario(body: LoadScenarioRequest) -> dict:
    try:
        return bridge.load_scenario(body.name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0])) from exc


@app.post("/api/scenario/custom")
def load_custom(body: CustomScenarioRequest) -> dict:
    try:
        return bridge.load_custom(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/scenario/{name}/spec")
def scenario_spec(name: str) -> dict:
    try:
        return bridge.preset_spec(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0])) from exc


@app.post("/api/network/validate")
def validate_network(spec: NetworkSpec) -> dict:
    errors = bridge.validate_network(spec)
    return {"valid": not errors, "errors": errors}


@app.post("/api/scenario/from_spec")
def load_from_spec(spec: NetworkSpec) -> dict:
    try:
        return bridge.load_spec(spec)
    except NetworkSpecError as exc:
        raise HTTPException(
            status_code=422, detail={"message": str(exc), "errors": exc.errors}
        ) from exc


@app.get("/api/campaign")
def campaign_levels() -> list[dict]:
    return [level.meta() for level in campaign.LEVELS]


@app.post("/api/campaign/{level_id}/start")
def campaign_start(level_id: int) -> dict:
    try:
        return bridge.start_level(level_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0])) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/campaign/{level_id}/spec")
def campaign_spec(level_id: int) -> dict:
    try:
        return bridge.level_spec(level_id).model_dump()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0])) from exc


@app.get("/api/state")
def get_state() -> dict:
    if not bridge.loaded:
        raise HTTPException(status_code=409, detail="no scenario loaded")
    return bridge.get_state()


@app.websocket("/ws/sim")
async def sim_socket(ws: WebSocket) -> None:
    await ws.accept()
    if bridge.loaded:
        await ws.send_json(StateMessage(state=bridge.get_state()).model_dump())
    try:
        while True:
            raw = await ws.receive_text()
            try:
                command = _Command.validate_python(json.loads(raw))
                if not bridge.loaded:
                    raise RuntimeError("no scenario loaded")
                if isinstance(command, StepCommand):
                    reply = StateMessage(state=bridge.step())
                elif isinstance(command, ResetCommand):
                    reply = StateMessage(state=bridge.reset())
                elif isinstance(command, EventActionCommand):
                    state, outcome = bridge.resolve_event(
                        command.event_id, command.choice_id, command.auto
                    )
                    reply = StateMessage(state=state, event="event_resolved", outcome=outcome)
                else:
                    state = bridge.change_policy(
                        command.node_id, command.policy_type, command.params
                    )
                    reply = StateMessage(
                        state=state, event="policy_changed", node_id=command.node_id
                    )
            except (ValidationError, json.JSONDecodeError) as exc:
                reply = ErrorMessage(message=f"invalid command: {exc}")
            except (KeyError, ValueError, RuntimeError) as exc:
                reply = ErrorMessage(message=str(exc.args[0]) if exc.args else str(exc))
            await ws.send_json(reply.model_dump())
    except WebSocketDisconnect:
        return
