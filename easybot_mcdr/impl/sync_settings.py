from easybot_mcdr.websocket.context import ExecContext
from easybot_mcdr.websocket.ws import EasyBotWsClient
from mcdreforged.api.all import ServerInterface
from easybot_mcdr.config import get_config, save_config

@EasyBotWsClient.listen_exec_op("SYNC_SETTINGS_UPDATED")
async def on_sync_settings_updated(ctx: ExecContext, data: dict, _):
    server = ServerInterface.get_instance()
    
    sync_money = data.get("sync_money", 0)
    sync_mode = data.get("sync_mode", 0)
    
    server.logger.info(f"[EasyBot] 收到同步配置更新: Mode={sync_mode}, Money={sync_money}")
    
    # 更新运行时配置
    config = get_config()
    if "runtime" not in config:
        config["runtime"] = {}
    
    config["runtime"]["sync_mode"] = sync_mode
    config["runtime"]["sync_money"] = sync_money
    
    # 可选：如果希望重启后保留，取消下面注释
    # save_config(server)
