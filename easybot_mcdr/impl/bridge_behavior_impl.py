from typing import List, Optional

from mcdreforged.api.all import PluginServerInterface
from easybot_mcdr.bridge_behavior import BridgeBehavior
from easybot_mcdr.message import Segment


class DefaultBridgeBehavior(BridgeBehavior):
    def __init__(self, server: PluginServerInterface):
        self.server = server

    def run_command(self, player_name: str, command: str, enable_papi: bool) -> str:
        cmd = command
        try:
            if self.server.is_rcon_running():
                return str(self.server.rcon_query(cmd))
            else:
                self.server.execute(cmd)
                return "executed"
        except Exception as e:
            return f"error: {e}"

    def papi_query(self, player_name: str, query: str) -> str:
        return query

    def get_info(self):
        info = self.server.get_server_information()
        return {
            "name": getattr(info, "server_name", getattr(info, "server_brand", "unknown")),
            "version": getattr(info, "version", "unknown"),
            "max_players": getattr(info, "max_players", getattr(info, "max_player", None)),
            "description": getattr(info, "description", ""),
            "port": getattr(info, "port", None),
        }

    def sync_to_chat(self, message: str):
        self.server.say(message)

    def bind_success_broadcast(self, player_name: str, account_id: str, account_name: str):
        self.server.say(f"[EasyBot] 玩家 {player_name} 绑定账号 {account_name} ({account_id}) 成功")

    def kick_player(self, player: str, kick_message: str):
        try:
            self.server.execute(f"kick {player} {kick_message}")
        except Exception:
            if self.server.is_rcon_running():
                self.server.rcon_query(f"kick {player} {kick_message}")

    def sync_to_chat_extra(self, segments: List[Segment], text: str):
        try:
            if segments:
                from easybot_mcdr.impl.message_sync import render_segments
                render_segments(segments, text)
            else:
                self.server.say(text)
        except Exception:
            self.server.say(text)

    def get_player_list(self):
        return list(self.server.get_online_players())

    def module_is_installed(self, name: str) -> bool:
        return False

    def module_is_enabled(self, name: str) -> bool:
        return False

    def is_authenticated(self, name: str) -> bool:
        return False

    def get_player_skin(self, player_name: str) -> Optional[str]:
        from easybot_mcdr.impl.get_server_info import get_online_mode, get_skins_restorer
        online = get_online_mode()
        has_sr = get_skins_restorer()

        if online or has_sr:
            return f"https://mineskin.eu/download/{player_name}"

        # 离线模式无皮肤站: 查询 Mojang 判断是否正版
        from easybot_mcdr.impl.player_list import _check_premium_sync
        if _check_premium_sync(player_name):
            return f"https://mineskin.eu/download/{player_name}"

        # 非正版: 尝试通过 UUID 获取头像
        try:
            players = self.server.get_online_players()
            for p in players:
                if hasattr(p, 'name') and p.name == player_name:
                    return f"https://mc-heads.net/skin/{p.uuid}"
                if str(p) == player_name:
                    return f"https://mc-heads.net/skin/{p.uuid}"
        except Exception:
            pass
        return None
