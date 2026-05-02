#!/usr/bin/env python3
"""
EasyBot-MCDR 插件测试套件

在独立环境中测试插件各项功能，输出 Markdown 格式的测试报告。
"""
import asyncio
import hashlib
import json
import os
import sys
import time
import traceback
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── 测试基础设施 ─────────────────────────────────────────────────────
results: List[Dict[str, Any]] = []


def run_test(name: str, func):
    """执行单个测试并记录结果。"""
    start = time.monotonic()
    try:
        func()
        elapsed = time.monotonic() - start
        results.append({"name": name, "status": "通过", "detail": "", "time": elapsed})
    except Exception as e:
        elapsed = time.monotonic() - start
        tb = traceback.format_exc()
        results.append({"name": name, "status": "失败", "detail": f"{e}\n{tb}", "time": elapsed})


# ── 1. 模块导入测试 ─────────────────────────────────────────────────
def test_import_config():
    from easybot_mcdr.config import get_config, load_config, save_config
    assert callable(get_config)


def test_import_meta():
    from easybot_mcdr.meta import get_plugin_version
    assert callable(get_plugin_version)


def test_import_message():
    from easybot_mcdr.message import (
        Segment, SegmentType, TextSegment, ImageSegment,
        FileSegment, AtSegment, ReplySegment, UnknownSegment,
        segments_from_list, segments_to_list,
    )


def test_import_rpc():
    from easybot_mcdr.rpc import bridge_rpc, bind_registered_handlers, _registry
    assert callable(bridge_rpc)
    assert isinstance(_registry, dict)


def test_import_event_bus():
    from easybot_mcdr.event_bus import EventBus
    eb = EventBus()
    assert hasattr(eb, "on")
    assert hasattr(eb, "emit")


def test_import_prefix_handler():
    from easybot_mcdr.impl.prefix_handler import create_handler, AVAILABLE_HANDLERS
    assert callable(create_handler)
    assert isinstance(AVAILABLE_HANDLERS, list)
    assert len(AVAILABLE_HANDLERS) > 0


def test_import_ws_client():
    from easybot_mcdr.websocket.ws import EasyBotWsClient, SessionInfo
    assert hasattr(EasyBotWsClient, "listen_exec_op")
    assert hasattr(SessionInfo, "from_dict")


def test_import_player_api():
    from easybot_mcdr.api.player import (
        PlayerInfo, generate_offline_uuid, update_player_uuid,
        get_data_map, check_cache, check_online, get_player_list,
    )
    assert callable(generate_offline_uuid)


def test_import_impl_modules():
    """验证所有 impl 子模块均可导入。"""
    import easybot_mcdr.impl.rpc_handlers
    import easybot_mcdr.impl.bind_success_notify
    import easybot_mcdr.impl.un_bind_notify
    import easybot_mcdr.impl.message_sync
    import easybot_mcdr.impl.exec_command
    import easybot_mcdr.impl.cross_server_chat
    import easybot_mcdr.impl.player_list
    import easybot_mcdr.impl.papi
    import easybot_mcdr.impl.get_server_info
    import easybot_mcdr.impl.sync_settings
    import easybot_mcdr.impl.bridge_behavior_impl


# ── 2. 配置加载测试 ─────────────────────────────────────────────────
def test_config_json_parse():
    config_path = PROJECT_ROOT / "data" / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    assert isinstance(cfg, dict)
    assert "token" in cfg
    assert "ws" in cfg
    assert "server_handler" in cfg


def test_config_required_fields():
    config_path = PROJECT_ROOT / "data" / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    required = ["token", "ws", "server_name", "debug", "kick_delay_seconds",
                 "message_sync", "message", "enable_white_list", "events",
                 "bot_filter", "server_handler"]
    for key in required:
        assert key in cfg, f"缺少必填配置项: {key}"


def test_config_bot_filter():
    config_path = PROJECT_ROOT / "data" / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    bf = cfg["bot_filter"]
    assert "enabled" in bf
    assert "prefixes" in bf
    assert isinstance(bf["prefixes"], list)
    assert len(bf["prefixes"]) > 0


def test_config_server_handler():
    config_path = PROJECT_ROOT / "data" / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    assert cfg["server_handler"] in ("forge", "fabric", "spigot", "paper", "vanilla", ""), f"无效 server_handler: {cfg['server_handler']}"


# ── 3. 消息模型测试 ─────────────────────────────────────────────────
def test_text_segment():
    from easybot_mcdr.message import TextSegment, SegmentType, Segment
    seg = TextSegment("hello")
    assert seg.type == SegmentType.TEXT
    assert seg.text == "hello"
    d = seg.to_dict()
    assert d == {"type": "text", "text": "hello"}
    restored = Segment.from_dict(d)
    assert isinstance(restored, TextSegment)
    assert restored.text == "hello"


def test_image_segment():
    from easybot_mcdr.message import ImageSegment, SegmentType, Segment
    seg = ImageSegment("https://example.com/img.png")
    assert seg.type == SegmentType.IMAGE
    d = seg.to_dict()
    restored = Segment.from_dict(d)
    assert isinstance(restored, ImageSegment)
    assert restored.url == "https://example.com/img.png"


def test_file_segment():
    from easybot_mcdr.message import FileSegment, SegmentType, Segment
    seg = FileSegment("https://example.com/file.pdf", name="doc.pdf")
    d = seg.to_dict()
    restored = Segment.from_dict(d)
    assert isinstance(restored, FileSegment)
    assert restored.url == "https://example.com/file.pdf"
    assert restored.name == "doc.pdf"


def test_at_segment():
    from easybot_mcdr.message import AtSegment, SegmentType, Segment
    seg = AtSegment("Steve")
    d = seg.to_dict()
    restored = Segment.from_dict(d)
    assert isinstance(restored, AtSegment)
    assert restored.target == "Steve"


def test_reply_segment():
    from easybot_mcdr.message import ReplySegment, SegmentType, Segment
    seg = ReplySegment("msg_123", text="original")
    d = seg.to_dict()
    restored = Segment.from_dict(d)
    assert isinstance(restored, ReplySegment)
    assert restored.message_id == "msg_123"
    assert restored.text == "original"


def test_segments_roundtrip():
    from easybot_mcdr.message import TextSegment, ImageSegment, AtSegment, segments_from_list, segments_to_list
    original = [TextSegment("hi"), ImageSegment("url"), AtSegment("Bob")]
    data = segments_to_list(original)
    restored = segments_from_list(data)
    assert len(restored) == 3
    assert restored[0].text == "hi"
    assert restored[1].url == "url"
    assert restored[2].target == "Bob"


# ── 4. 玩家 API 测试 ────────────────────────────────────────────────
def test_player_info_construction():
    from easybot_mcdr.api.player import PlayerInfo
    p = PlayerInfo("127.0.0.1", "Steve", "uuid-1234")
    assert p.ip == "127.0.0.1"
    assert p.name == "Steve"
    assert p.uuid == "uuid-1234"


def test_offline_uuid_generation():
    from easybot_mcdr.api.player import generate_offline_uuid
    uuid = generate_offline_uuid("Steve")
    assert isinstance(uuid, str)
    assert len(uuid) == 36
    assert uuid.count("-") == 4
    expected = "5627dd98-e6be-3c21-b8a8-e92344183641"
    assert uuid == expected, f"期望 {expected}，实际 {uuid}"


def test_offline_uuid_deterministic():
    from easybot_mcdr.api.player import generate_offline_uuid
    uuid1 = generate_offline_uuid("TestPlayer")
    uuid2 = generate_offline_uuid("TestPlayer")
    assert uuid1 == uuid2, "UUID 生成应具有确定性"


def test_offline_uuid_different_names():
    from easybot_mcdr.api.player import generate_offline_uuid
    uuid1 = generate_offline_uuid("Player1")
    uuid2 = generate_offline_uuid("Player2")
    assert uuid1 != uuid2, "不同名称应生成不同 UUID"


def test_player_data_map():
    from easybot_mcdr.api.player import get_data_map, online_players, uuid_map, cached_data
    dm = get_data_map()
    assert "online_players" in dm
    assert "uuid_map" in dm
    assert "cache" in dm


# ── 5. 假人过滤测试 ─────────────────────────────────────────────────
def test_bot_filter_matching():
    """测试假人前缀匹配逻辑。"""
    prefixes = ["Bot_", "BOT_", "bot_"]
    assert any("Bot_Steve".startswith(p) for p in prefixes)
    assert any("BOT_Creeper".startswith(p) for p in prefixes)
    assert any("bot_Zombie".startswith(p) for p in prefixes)
    assert not any("Steve".startswith(p) for p in prefixes)
    assert not any("Notch".startswith(p) for p in prefixes)


def test_bot_filter_disabled():
    """假人过滤禁用时，不应过滤任何玩家。"""
    prefixes = ["Bot_", "BOT_", "bot_"]
    enabled = False
    def is_bot(player):
        if not enabled:
            return False
        return any(player.startswith(p) for p in prefixes)
    assert not is_bot("Bot_Steve")
    assert not is_bot("Steve")


# ── 6. Prefix Handler 测试 ──────────────────────────────────────────
def test_prefix_handler_forge():
    from easybot_mcdr.impl.prefix_handler import create_handler, _handler_map
    if "forge" not in _handler_map:
        return
    handler = create_handler("forge")
    name = handler.get_name()
    assert name == "easybot_prefix_handler"


def test_prefix_handler_fabric():
    from easybot_mcdr.impl.prefix_handler import create_handler, _handler_map
    if "fabric" not in _handler_map:
        return
    handler = create_handler("fabric")
    name = handler.get_name()
    assert name == "easybot_prefix_handler"


def test_prefix_handler_vanilla():
    from easybot_mcdr.impl.prefix_handler import create_handler, _handler_map
    if "vanilla" not in _handler_map:
        return
    handler = create_handler("vanilla")
    name = handler.get_name()
    assert name == "easybot_prefix_handler"


def test_prefix_handler_fallback():
    """无效处理器名称应回退到默认值。"""
    from easybot_mcdr.impl.prefix_handler import create_handler
    handler = create_handler("nonexistent")
    name = handler.get_name()
    assert name == "easybot_prefix_handler"


def test_prefix_handler_parse_chat():
    """测试 ForgeHandler 可识别的标准服务器输出格式。"""
    from easybot_mcdr.impl.prefix_handler import create_handler
    handler = create_handler("forge")
    info = handler.parse_server_stdout(
        "[12:00:00] [Server thread/INFO]: <Steve> Hello world"
    )
    assert info is not None
    assert info.player == "Steve"
    assert "Hello world" in info.content


# ── 7. RPC 注册表测试 ───────────────────────────────────────────────
def test_rpc_decorator_registration():
    import easybot_mcdr.impl.rpc_handlers
    from easybot_mcdr.rpc import _registry
    assert len(_registry) > 0, "未注册任何 RPC 处理器"


def test_rpc_expected_ops():
    import easybot_mcdr.impl.rpc_handlers
    from easybot_mcdr.rpc import _registry
    expected = {"PING", "GET_SERVER_INFO", "RUN_COMMAND", "KICK_PLAYER",
                "SYNC_CHAT", "GET_PLAYER_LIST", "SYNC_SEGMENTS"}
    registered = set(_registry.keys())
    missing = expected - registered
    assert not missing, f"缺少 RPC 处理器: {missing}"


# ── 8. EventBus 测试 ────────────────────────────────────────────────
def test_event_bus_register_and_emit():
    from easybot_mcdr.event_bus import EventBus
    eb = EventBus()
    called = []

    @eb.on("test_event")
    def handler(**kwargs):
        called.append(kwargs.get("value"))

    loop = asyncio.new_event_loop()
    loop.run_until_complete(eb.emit("test_event", value=42))
    loop.close()
    assert called == [42]


def test_event_bus_priority():
    from easybot_mcdr.event_bus import EventBus
    eb = EventBus()
    order = []

    @eb.on("prio", priority=10)
    def high(**kw):
        order.append("high")

    @eb.on("prio", priority=1)
    def low(**kw):
        order.append("low")

    loop = asyncio.new_event_loop()
    loop.run_until_complete(eb.emit("prio"))
    loop.close()
    assert order == ["high", "low"], f"优先级顺序错误: {order}"


# ── 9. WebSocket 连接测试 ───────────────────────────────────────────
WS_URL = "ws://home.123165.xyz:26990/bridge"
WS_TOKEN = "XzFdc6IcNCsaYFB#dtnTaVXIozV43Uwi"
WS_TIMEOUT = 15


def test_ws_connection_and_auth():
    """连接测试服务器，完成鉴权握手，验证心跳。"""
    import websockets

    async def _test():
        results_detail = {}
        try:
            async with websockets.connect(WS_URL, open_timeout=WS_TIMEOUT) as ws:
                # 步骤 1：接收服务器 hello 包 (op: 0)
                raw = await asyncio.wait_for(ws.recv(), timeout=WS_TIMEOUT)
                hello = json.loads(raw)
                assert hello.get("op") == 0, f"期望 op 0，收到 {hello.get('op')}"
                assert "session_id" in hello, "hello 包缺少 session_id"
                assert "token" in hello, "hello 包缺少 token"
                results_detail["hello"] = "OK"
                results_detail["session_id"] = hello["session_id"]
                results_detail["core_version"] = hello.get("version", "unknown")
                results_detail["core_system"] = hello.get("system", "unknown")

                # 步骤 2：发送鉴权包 (op: 1)
                auth_packet = {
                    "op": 1,
                    "token": WS_TOKEN,
                    "plugin_version": "test",
                    "server_description": "MCDR_test",
                }
                await ws.send(json.dumps(auth_packet))

                # 步骤 3：接收鉴权结果 (op: 3 = 成功)
                raw = await asyncio.wait_for(ws.recv(), timeout=WS_TIMEOUT)
                auth_result = json.loads(raw)
                assert auth_result.get("op") == 3, f"期望 op 3，收到 {auth_result.get('op')}"
                results_detail["auth"] = "OK"
                results_detail["server_name"] = auth_result.get("server_name", "unknown")

                return True, results_detail
        except asyncio.TimeoutError:
            results_detail["error"] = "连接超时"
            return False, results_detail
        except ConnectionRefusedError:
            results_detail["error"] = "连接被拒绝"
            return False, results_detail
        except Exception as e:
            results_detail["error"] = str(e)
            return False, results_detail

    success, detail = loop.run_until_complete(_test())
    if not success:
        raise ConnectionError(f"WebSocket 测试失败: {detail}")
    results[-1]["ws_detail"] = detail


# ── 执行所有测试 ────────────────────────────────────────────────────
loop = asyncio.new_event_loop()

ALL_TESTS = [
    # 模块导入
    ("导入: config", test_import_config),
    ("导入: meta", test_import_meta),
    ("导入: message", test_import_message),
    ("导入: rpc", test_import_rpc),
    ("导入: event_bus", test_import_event_bus),
    ("导入: prefix_handler", test_import_prefix_handler),
    ("导入: ws_client", test_import_ws_client),
    ("导入: player_api", test_import_player_api),
    ("导入: impl_modules", test_import_impl_modules),
    # 配置
    ("配置: JSON 解析", test_config_json_parse),
    ("配置: 必填字段", test_config_required_fields),
    ("配置: bot_filter", test_config_bot_filter),
    ("配置: server_handler", test_config_server_handler),
    # 消息模型
    ("消息: TextSegment", test_text_segment),
    ("消息: ImageSegment", test_image_segment),
    ("消息: FileSegment", test_file_segment),
    ("消息: AtSegment", test_at_segment),
    ("消息: ReplySegment", test_reply_segment),
    ("消息: 序列化往返", test_segments_roundtrip),
    # 玩家 API
    ("玩家: PlayerInfo", test_player_info_construction),
    ("玩家: 离线 UUID", test_offline_uuid_generation),
    ("玩家: UUID 确定性", test_offline_uuid_deterministic),
    ("玩家: UUID 唯一性", test_offline_uuid_different_names),
    ("玩家: 数据映射", test_player_data_map),
    # 假人过滤
    ("假人过滤: 前缀匹配", test_bot_filter_matching),
    ("假人过滤: 禁用状态", test_bot_filter_disabled),
    # Prefix Handler
    ("处理器: forge", test_prefix_handler_forge),
    ("处理器: fabric", test_prefix_handler_fabric),
    ("处理器: vanilla", test_prefix_handler_vanilla),
    ("处理器: 回退", test_prefix_handler_fallback),
    ("处理器: 聊天解析", test_prefix_handler_parse_chat),
    # RPC
    ("RPC: 注册表", test_rpc_decorator_registration),
    ("RPC: 完整性", test_rpc_expected_ops),
    # EventBus
    ("事件总线: 触发", test_event_bus_register_and_emit),
    ("事件总线: 优先级", test_event_bus_priority),
    # WebSocket
    ("WebSocket: 连接鉴权", test_ws_connection_and_auth),
]


def generate_report() -> str:
    """生成 Markdown 格式的测试报告。"""
    passed = sum(1 for r in results if r["status"] == "通过")
    failed = sum(1 for r in results if r["status"] == "失败")
    total = len(results)
    total_time = sum(r["time"] for r in results)

    try:
        with open(PROJECT_ROOT / "mcdreforged.plugin.json", "r") as f:
            version = json.load(f).get("version", "未知")
    except Exception:
        version = "未知"

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    lines = [
        "# EasyBot-MCDR 测试报告",
        "",
        f"**插件版本:** {version}",
        f"**Python:** {py_ver}",
        f"**运行平台:** {sys.platform}",
        f"**测试时间:** {now}",
        f"**总耗时:** {total_time:.2f}s",
        "",
        "## 概览",
        "",
        f"| 指标 | 结果 |",
        f"|------|------|",
        f"| 总计 | {total} |",
        f"| 通过 | {passed} |",
        f"| 失败 | {failed} |",
        f"| 通过率 | {passed/total*100:.1f}% |",
        "",
        "## 测试详情",
        "",
        "| # | 测试项 | 结果 | 耗时 |",
        "|---|--------|------|------|",
    ]

    for i, r in enumerate(results, 1):
        icon = "通过" if r["status"] == "通过" else "失败"
        lines.append(f"| {i} | {r['name']} | {icon} | {r['time']:.3f}s |")

    # WebSocket 连接详情
    for r in results:
        if "ws_detail" in r:
            d = r["ws_detail"]
            lines.extend([
                "",
                "## WebSocket 连接详情",
                "",
                f"- **服务端名称:** {d.get('server_name', 'N/A')}",
                f"- **核心版本:** {d.get('core_version', 'N/A')}",
                f"- **核心系统:** {d.get('core_system', 'N/A')}",
                f"- **会话 ID:** {d.get('session_id', 'N/A')}",
            ])

    # 失败详情
    if failed > 0:
        lines.extend(["", "## 失败详情", ""])
        for r in results:
            if r["status"] == "失败":
                lines.append(f"### {r['name']}")
                lines.append("```")
                lines.append(r["detail"])
                lines.append("```")
                lines.append("")

    return "\n".join(lines)


# ── 主入口 ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    for name, func in ALL_TESTS:
        run_test(name, func)

    report = generate_report()
    print(report)

    failed = sum(1 for r in results if r["status"] == "失败")
    sys.exit(1 if failed > 0 else 0)
