import queue
import re
import threading
import logging
from typing import Optional

logger = logging.getLogger("EasyBot")

NBT_DATA_TYPE_MAP = {
    0: "playerdata",   # PlayerData
    1: "advancements",  # Advancements
    2: "statistics",    # Statistics
}

DATA_GET_OUTPUT_REGEX = re.compile(
    r"^(\w+) has the following entity data: (.+)$"
)


DATA_COMMAND_MIN_VERSION = (1, 13)


def _parse_version(version_str: str) -> tuple:
    match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", version_str)
    if match:
        major = int(match.group(1))
        minor = int(match.group(2))
        patch = int(match.group(3)) if match.group(3) else 0
        return (major, minor, patch)
    return (0, 0, 0)


class PlayerDataGetter:
    def __init__(self, server):
        self._server = server
        self._work_queue: dict[str, queue.Queue] = {}
        self._lock = threading.Lock()
        self._version_supported = self._check_version()

    def _check_version(self) -> bool:
        try:
            info = self._server.get_server_information()
            version = _parse_version(info.version)
            supported = version >= DATA_COMMAND_MIN_VERSION
            if not supported:
                logger.warning(
                    f"服务器版本 {info.version} 低于 1.13，NBT 数据读取功能不可用"
                )
            return supported
        except Exception:
            logger.warning("无法获取服务器版本，NBT 数据读取功能可能不可用")
            return True

    def on_info(self, text: str):
        match = DATA_GET_OUTPUT_REGEX.match(text)
        if match:
            player_name = match.group(1)
            data = match.group(2)
            with self._lock:
                q = self._work_queue.get(player_name)
            if q is not None:
                q.put(data)

    def get_player_info(self, player: str, path: str = "", timeout: float = 5.0) -> Optional[str]:
        if not self._version_supported:
            return None
        cmd = f"data get entity {player}"
        if path:
            cmd += f" {path}"

        q = queue.Queue()
        with self._lock:
            self._work_queue[player] = q

        try:
            self._server.execute(cmd)
            result = q.get(timeout=timeout)
            return result
        except queue.Empty:
            return None
        finally:
            with self._lock:
                self._work_queue.pop(player, None)

    def read_nbt_data(self, player_uuid: str, data_type: int) -> Optional[dict]:
        if not self._version_supported:
            return None
        type_name = NBT_DATA_TYPE_MAP.get(data_type)
        if type_name is None:
            return None

        if type_name == "playerdata":
            # 尝试通过 RCON 读取在线玩家的背包数据
            # 需要使用在线玩家的名称来读取
            from easybot_mcdr.api.player import online_players, uuid_map

            # 首先通过 UUID 找到玩家名称
            player_name = None
            for name, uuid in uuid_map.items():
                if uuid == player_uuid:
                    player_name = name
                    break

            if player_name and player_name in online_players:
                # 使用 data get entity 命令读取在线玩家数据
                try:
                    result = self._server.rcon_query(
                        f"data get entity {player_name}"
                    )
                    if result and "has the following entity data" in result:
                        # 解析原始数据，提取 Inventory 部分
                        raw_data = result.split("has the following entity data: ", 1)
                        if len(raw_data) > 1:
                            entity_data_str = raw_data[1]
                            # 提取 Inventory 部分
                            import re
                            inventory_match = re.search(
                                r'Inventory: \[(.*?)\]',
                                entity_data_str,
                                re.DOTALL
                            )
                            if inventory_match:
                                inventory_str = inventory_match.group(1)
                                # 解析物品列表
                                inventory = self._parse_inventory_items(inventory_str)
                                return {
                                    "raw": result,
                                    "parsed": {
                                        "Inventory": inventory
                                    },
                                    "inventory": inventory
                                }
                        return {"raw": result}
                except Exception as e:
                    logger.error(f"读取玩家背包数据失败: {e}")
                    pass
            return None

        if type_name == "advancements":
            try:
                result = self._server.rcon_query(
                    f"data get storage minecraft:player_data {player_uuid}.advancements"
                )
                if result:
                    return {"raw": result}
            except Exception:
                pass
            return None

        if type_name == "statistics":
            try:
                result = self._server.rcon_query(
                    f"data get storage minecraft:player_data {player_uuid}.stats"
                )
                if result:
                    return {"raw": result}
            except Exception:
                pass
            return None

        return None

    def _parse_inventory_items(self, inventory_str: str) -> list:
        """解析 Minecraft NBT 格式的物品列表"""
        items = []
        if not inventory_str:
            return items

        # 匹配每个物品: {count: 64, Slot: 0b, id: "minecraft:oak_planks"}
        import re
        item_pattern = re.compile(r'\{([^}]+)\}')
        for match in item_pattern.finditer(inventory_str):
            item_str = match.group(1)
            item = {}

            # 解析 count
            count_match = re.search(r'count:\s*(\d+)', item_str)
            if count_match:
                item['count'] = int(count_match.group(1))

            # 解析 Slot
            slot_match = re.search(r'Slot:\s*(\d+)b?', item_str)
            if slot_match:
                item['slot'] = int(slot_match.group(1))

            # 解析 id
            id_match = re.search(r'id:\s*"([^"]+)"', item_str)
            if id_match:
                item['id'] = id_match.group(1)

            # 解析 tag (如果有)
            tag_match = re.search(r'tag:\s*\{([^}]+)\}', item_str)
            if tag_match:
                item['tag'] = tag_match.group(1)

            if item:
                items.append(item)

        return items

    def get_entity_data(self, player: str, path: str = "", timeout: float = 5.0) -> Optional[dict]:
        raw = self.get_player_info(player, path, timeout)
        if raw is None:
            return None
        try:
            return {"raw": raw, "parsed": parse_minecraft_json(raw)}
        except Exception:
            return {"raw": raw}


def remove_command_result_prefix(text: str) -> str:
    return re.sub(r"^[^ ]* has the following entity data: ", "", text)


def preprocess_minecraft_json(text: str) -> str:
    result = []
    in_string = False
    escape_next = False
    i = 0

    while i < len(text):
        ch = text[i]

        if escape_next:
            result.append(ch)
            escape_next = False
            i += 1
            continue

        if ch == '\\' and in_string:
            result.append(ch)
            escape_next = True
            i += 1
            continue

        if ch == '"' and not in_string:
            in_string = True
            result.append(ch)
            i += 1
            continue

        if ch == '"' and in_string:
            in_string = False
            result.append(ch)
            i += 1
            continue

        if in_string:
            result.append(ch)
            i += 1
            continue

        if ch == '<' and i + 2 < len(text) and text[i+1] == '.' and text[i+2] == '.' and i + 3 < len(text) and text[i+3] == '>':
            i += 4
            continue

        result.append(ch)
        i += 1

    text = ''.join(result)
    text = re.sub(r'([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)([bsLdf])', r'\1', text)
    text = re.sub(r'(?<=\[)[IL];', '', text)
    return text


def parse_minecraft_json(text: str) -> Optional[dict]:
    text = remove_command_result_prefix(text)
    text = preprocess_minecraft_json(text)
    try:
        import hjson
        return hjson.loads(text)
    except ImportError:
        import json
        try:
            return json.loads(text)
        except Exception:
            return None
    except Exception:
        return None
