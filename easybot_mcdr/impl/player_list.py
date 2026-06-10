import asyncio
import time
import requests
from easybot_mcdr.impl.get_server_info import get_online_mode, get_skins_restorer
from easybot_mcdr.websocket.context import ExecContext
from easybot_mcdr.websocket.ws import EasyBotWsClient
from mcdreforged.api.all import *

# Mojang 正版检测缓存: {name: (is_premium, timestamp)}
_premium_cache = {}
_PREMIUM_CACHE_TTL = 3600  # 1小时


def _check_premium_sync(name: str) -> bool:
    """同步查询 Mojang API 判断是否为正版账户"""
    try:
        resp = requests.get(
            f"https://api.mojang.com/users/profiles/minecraft/{name}",
            timeout=5
        )
        return resp.status_code == 200
    except Exception:
        return False


async def check_premium(name: str) -> bool:
    """异步查询 Mojang API，带缓存"""
    now = time.time()
    if name in _premium_cache:
        is_premium, ts = _premium_cache[name]
        if now - ts < _PREMIUM_CACHE_TTL:
            return is_premium
    loop = asyncio.get_event_loop()
    is_premium = await loop.run_in_executor(None, _check_premium_sync, name)
    _premium_cache[name] = (is_premium, now)
    return is_premium


async def try_get_skin(name, uuid=""):
    online = get_online_mode()
    has_sr = get_skins_restorer()

    if online:
        return f"https://mineskin.eu/download/{name}"

    if has_sr:
        return f"https://mineskin.eu/download/{name}"

    # 离线模式无皮肤站: 查询 Mojang 判断是否正版
    is_premium = await check_premium(name)
    if is_premium:
        # 正版账户: mineskin 能获取到正确皮肤
        return f"https://mineskin.eu/download/{name}"

    # 非正版: 使用 mc-heads.net 头像
    if uuid:
        return f"https://mc-heads.net/skin/{uuid}"
    return ""

@EasyBotWsClient.listen_exec_op("PLAYER_LIST")
async def on_get_player_list(ctx: ExecContext, data:dict, _):
    logger = ServerInterface.get_instance().logger
    from easybot_mcdr.api.player import get_player_list
    online_list = get_player_list()
    list = []
    for player in online_list:
        skin_url = await try_get_skin(player, online_list[player].uuid)
        list.append({
            "player_name": player,
            "player_uuid": online_list[player].uuid,
            "ip": online_list[player].ip,
            "bedrock": False,
            "skin_url": skin_url
        })
    await ctx.callback({
        "list": list
    })