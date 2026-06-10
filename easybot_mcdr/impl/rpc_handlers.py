import asyncio

from mcdreforged.api.all import ServerInterface
from easybot_mcdr.rpc import bridge_rpc
from easybot_mcdr.impl.bridge_behavior_impl import DefaultBridgeBehavior
from easybot_mcdr.message import segments_from_list


def _behavior():
    server = ServerInterface.get_instance()
    return DefaultBridgeBehavior(server)


@bridge_rpc("PING", description="Health check")
async def ping(ctx, data, session_info):
    await ctx.callback({"success": True, "text": "pong"})


@bridge_rpc("GET_EXTENSIONS", description="Get installed extensions")
async def get_extensions(ctx, data, session_info):
    await ctx.callback({"success": True, "extensions": {}})


@bridge_rpc("SYNC_SEGMENTS", description="Sync structured message to chat")
async def sync_segments(ctx, data, session_info):
    segments = segments_from_list(data.get("segments", []) or [])
    text = data.get("text", "")
    _behavior().sync_to_chat_extra(segments, text)
    await ctx.callback({"success": True})


@bridge_rpc("RUN_COMMAND", description="Run command (PAPI disabled)")
async def run_command(ctx, data, session_info):
    player = data.get("player_name") or ""
    command = data.get("command") or ""
    enable_papi = False
    try:
        result = _behavior().run_command(player, command, enable_papi)
        await ctx.callback({"success": True, "text": result})
    except Exception as e:
        await ctx.callback({"success": False, "text": str(e)})


@bridge_rpc("PAPI_QUERY", description="PAPI disabled")
async def papi_query(ctx, data, session_info):
    query = data.get("query") or ""
    await ctx.callback({"success": False, "text": f"PAPI disabled: {query}"})


@bridge_rpc("KICK_PLAYER", description="Kick player with message")
async def kick_player(ctx, data, session_info):
    player = data.get("player_name") or ""
    msg = data.get("message") or ""
    try:
        _behavior().kick_player(player, msg)
        await ctx.callback({"success": True})
    except Exception as e:
        await ctx.callback({"success": False, "text": str(e)})


@bridge_rpc("BIND_SUCCESS_BROADCAST", description="Broadcast bind success message")
async def bind_success_broadcast(ctx, data, session_info):
    player = data.get("player_name") or ""
    account_id = data.get("account_id") or ""
    account_name = data.get("account_name") or ""
    try:
        _behavior().bind_success_broadcast(player, account_id, account_name)
        await ctx.callback({"success": True})
    except Exception as e:
        await ctx.callback({"success": False, "text": str(e)})


@bridge_rpc("SYNC_CHAT", description="Sync plain chat message")
async def sync_chat(ctx, data, session_info):
    msg = data.get("message") or ""
    try:
        _behavior().sync_to_chat(msg)
        await ctx.callback({"success": True})
    except Exception as e:
        await ctx.callback({"success": False, "text": str(e)})


@bridge_rpc("GET_PLAYER_LIST", description="Get online player list")
async def get_player_list(ctx, data, session_info):
    try:
        players = _behavior().get_player_list()
        await ctx.callback({"success": True, "players": players})
    except Exception as e:
        await ctx.callback({"success": False, "text": str(e)})


@bridge_rpc("MODULE_INSTALLED", description="Check if a module/plugin is installed")
async def module_installed(ctx, data, session_info):
    name = data.get("name") or ""
    await ctx.callback({"success": True, "result": _behavior().module_is_installed(name)})


@bridge_rpc("MODULE_ENABLED", description="Check if a module/plugin is enabled")
async def module_enabled(ctx, data, session_info):
    name = data.get("name") or ""
    await ctx.callback({"success": True, "result": _behavior().module_is_enabled(name)})


@bridge_rpc("IS_AUTHENTICATED", description="Check if a player is authenticated/bound")
async def is_authenticated(ctx, data, session_info):
    player_name = data.get("player_name") or ""
    await ctx.callback({"success": True, "result": _behavior().is_authenticated(player_name)})


@bridge_rpc("GET_PLAYER_SKIN", description="Get player skin URL")
async def get_player_skin(ctx, data, session_info):
    player_name = data.get("player_name") or ""
    skin_url = _behavior().get_player_skin(player_name)
    await ctx.callback({"success": True, "skin_url": skin_url or ""})
