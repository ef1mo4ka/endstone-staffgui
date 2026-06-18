import json
import time
import random
from pathlib import Path
from datetime import datetime

from endstone.plugin import Plugin
from endstone.command import Command, CommandSender
from endstone import Player
from endstone.event import event_handler, PlayerJoinEvent, PlayerQuitEvent, PlayerDropItemEvent, PlayerInteractEvent, \
    BlockBreakEvent, PlayerChatEvent
from endstone.form import ActionForm, ModalForm, TextInput
from endstone.inventory import ItemStack
from endstone.nbt import CompoundTag, StringTag
from endstone._python.level import Location


class StaffGUIPlugin(Plugin):
    api_version = "0.5"

    commands = {
        "menu": {"description": "Открыть меню", "usages": ["/menu"], "permissions": ["groupchat.chat"]},
        "setrank": {"description": "Установить ранг", "usages": ["/setrank <player: target> <rank: string>"],
                    "permissions": ["groupchat.stuff"]},
        "delrank": {"description": "Сбросить ранг", "usages": ["/delrank <player: target>"],
                    "permissions": ["groupchat.stuff"]},
        "color": {"description": "Установить цвет ника", "usages": ["/color <color: message>"],
                  "permissions": ["groupchat.modern"]},
        "prefix": {"description": "Установить префикс", "usages": ["/prefix <prefix: message>"],
                   "permissions": ["groupchat.helper"]},
        "spawn": {"description": "Телепорт на спавн", "usages": ["/spawn", "/spawn <player: target>"],
                  "permissions": ["staff.spawn"]},
        "setspawn": {"description": "Установить спавн", "usages": ["/setspawn"], "permissions": ["staff.admin"]},
        "tpto": {"description": "Телепорт к игроку", "usages": ["/tpto <player: target>"],
                 "permissions": ["staff.teleport"]},
        "tphere": {"description": "Телепортировать к себе", "usages": ["/tphere <player: target>"],
                   "permissions": ["staff.teleport"]},
        "rtp": {"description": "Рандомный телепорт", "usages": ["/rtp"], "permissions": ["groupchat.chat"]},
        "vanish": {"description": "Режим невидимки", "usages": ["/vanish"], "permissions": ["staff.vanish"]},
        "kickplayer": {"description": "Кикнуть игрока", "usages": ["/kickplayer <player: target> <reason: message>"],
                       "permissions": ["staff.kick"]},
        "mute": {"description": "Замутить", "usages": ["/mute <player: target>"], "permissions": ["staff.mute"]},
        "unmute": {"description": "Размутить", "usages": ["/unmute <player: target>"], "permissions": ["staff.mute"]},
        "banplayer": {"description": "Забанить", "usages": ["/banplayer <player: target> <reason: message>"],
                      "permissions": ["staff.ban"]},
        "unbanplayer": {"description": "Разбанить", "usages": ["/unbanplayer <player: target>"],
                        "permissions": ["staff.ban"]},
    }

    permissions = {
        "staff.admin": {"description": "Админ", "default": "op"},
        "staff.teleport": {"description": "ТП", "default": "op"},
        "staff.spawn": {"description": "Спавн", "default": True},
        "staff.kick": {"description": "Кик", "default": "op"},
        "staff.mute": {"description": "Мут", "default": "op"},
        "staff.ban": {"description": "Бан", "default": "op"},
        "staff.vanish": {"description": "Ваниш", "default": "op"},
    }

    RANK_HIERARCHY = ["stuff", "admin", "helper", "builder", "moder", "player"]

    WORLDEDIT_PERMS = [
        "worldedit.wand", "worldedit.set", "worldedit.undo",
        "worldedit.show", "worldedit.copy", "worldedit.cut", "worldedit.paste"
    ]

    RANK_PERMISSIONS = {
        "stuff": ["staff.admin", "staff.teleport", "staff.spawn", "staff.kick", "staff.mute", "staff.ban",
                  "staff.vanish"] + WORLDEDIT_PERMS,
        "admin": ["staff.admin", "staff.teleport", "staff.spawn", "staff.kick", "staff.mute",
                  "staff.ban"] + WORLDEDIT_PERMS,
        "helper": ["staff.teleport", "staff.kick", "staff.mute", "staff.vanish"],
        "builder": ["staff.teleport", "staff.spawn", "staff.kick"] + WORLDEDIT_PERMS,
        "moder": ["staff.mute"],
        "player": ["staff.spawn"],
    }

    MENU_PERMISSIONS = {
        "stuff": ["players", "ranks", "setrank", "delrank", "color", "prefix", "invsee", "clear_prefix", "trash",
                  "settings"],
        "admin": ["players", "ranks", "color", "prefix", "invsee", "clear_prefix", "trash", "settings"],
        "helper": ["players", "ranks", "color", "prefix", "clear_prefix", "trash", "settings"],
        "builder": ["players", "ranks", "color", "prefix", "clear_prefix", "trash", "settings"],
        "moder": ["players", "ranks", "trash", "settings"],
        "player": ["players", "ranks", "trash", "settings"],
    }

    COLOR_NAMES_RU = {
        "red": "Красный", "green": "Зелёный", "blue": "Синий",
        "gold": "Золотой", "yellow": "Жёлтый", "aqua": "Бирюзовый",
        "pink": "Розовый", "white": "Белый", "gray": "Серый",
        "dark_red": "Тёмно-красный", "dark_green": "Тёмно-зелёный",
        "dark_blue": "Тёмно-синий", "black": "Чёрный"
    }

    CONTAINER_ITEMS = {
        "minecraft:shulker_box", "minecraft:bundle",
        "minecraft:white_shulker_box", "minecraft:orange_shulker_box",
        "minecraft:magenta_shulker_box", "minecraft:light_blue_shulker_box",
        "minecraft:yellow_shulker_box", "minecraft:lime_shulker_box",
        "minecraft:pink_shulker_box", "minecraft:gray_shulker_box",
        "minecraft:light_gray_shulker_box", "minecraft:cyan_shulker_box",
        "minecraft:purple_shulker_box", "minecraft:blue_shulker_box",
        "minecraft:brown_shulker_box", "minecraft:green_shulker_box",
        "minecraft:red_shulker_box", "minecraft:black_shulker_box",
    }

    RU_NAMES = {
        "minecraft:shulker_box": "Шалкер", "minecraft:bundle": "Мешок",
        "minecraft:diamond": "Алмаз", "minecraft:stick": "Палка",
        "minecraft:stone": "Камень", "minecraft:dirt": "Земля",
        "minecraft:apple": "Яблоко", "minecraft:torch": "Факел",
    }

    def on_enable(self):
        self.logger.info("StaffGUI enabled!")
        self._last_drop_warning = {}
        self.muted_players = {}
        self.banned_players = {}
        self.menu_settings = {}
        self.vanished_players = set()

        self.gc_path = Path(self.data_folder).parent / "groupchat"
        self.gc_path.mkdir(exist_ok=True)

        self.settings_file = self.gc_path / "settings.json"
        if self.settings_file.exists():
            self.menu_settings = json.loads(self.settings_file.read_text("utf-8"))

        self.spawn_file = self.gc_path / "spawn.json"
        self.spawn_config = {"x": -500, "y": 78, "z": -133, "pitch": 0, "yaw": 0}
        if self.spawn_file.exists():
            self.spawn_config = json.loads(self.spawn_file.read_text("utf-8"))

        self.mute_file = self.gc_path / "mutes.json"
        if self.mute_file.exists():
            self.muted_players = json.loads(self.mute_file.read_text("utf-8"))

        self.ban_file = self.gc_path / "bans.json"
        if self.ban_file.exists():
            self.banned_players = json.loads(self.ban_file.read_text("utf-8"))

        self.register_events(self)

        # Скрываем ванильные команды
        for cmd_name in ["tp", "kick", "ban", "unban"]:
            try:
                cmd = self.server.get_plugin_command(cmd_name)
                if cmd:
                    cmd.permission = "staff.admin"
            except:
                pass

    def _save(self):
        self.settings_file.write_text(json.dumps(self.menu_settings, ensure_ascii=False, indent=2), "utf-8")
        self.spawn_file.write_text(json.dumps(self.spawn_config, ensure_ascii=False, indent=2), "utf-8")
        self.mute_file.write_text(json.dumps(self.muted_players, ensure_ascii=False, indent=2), "utf-8")
        self.ban_file.write_text(json.dumps(self.banned_players, ensure_ascii=False, indent=2), "utf-8")

    @property
    def groupchat(self):
        for plugin in self.server.plugin_manager.plugins:
            if plugin.name == "GroupChat":
                return plugin
        return None

    def _get_rank(self, player_name):
        gc = self.groupchat
        return gc.get_rank(player_name) if gc else "player"

    def _get_rank_index(self, player_name):
        rank = self._get_rank(player_name)
        return self.RANK_HIERARCHY.index(rank) if rank in self.RANK_HIERARCHY else 99

    def _can_target(self, player, target_name):
        if target_name.lower() == "ef1mo4ka": return False
        player_idx = self._get_rank_index(player.name)
        target_idx = self._get_rank_index(target_name)
        return player_idx < target_idx

    def _give_permissions(self, player, rank):
        if rank in ("stuff", "admin", "builder"):
            for perm in self.WORLDEDIT_PERMS:
                try:
                    player.add_permission(perm)
                except:
                    pass
        if rank in ("stuff", "admin"):
            try:
                player.add_permission("staff.admin")
            except:
                pass

    def _has_menu_book(self, player):
        for slot in range(36):
            item = player.inventory.get_item(slot)
            if item and item.nbt and "groupchat_menu" in item.nbt: return True
        return False

    def _give_menu_book(self, player):
        if self._has_menu_book(player): return
        book = ItemStack("minecraft:enchanted_book", 1)
        nbt = CompoundTag()
        nbt["groupchat_menu"] = StringTag("true")
        book.nbt = nbt
        meta = book.item_meta
        if meta:
            meta.display_name = "§6§l/menu"
            meta.lore = ["§7Меню сервера", "§oby ef1mo4ka"]
            book.set_item_meta(meta)
        player.inventory.add_item(book)

    def _remove_menu_book(self, player):
        for slot in range(36):
            item = player.inventory.get_item(slot)
            if item and item.nbt and "groupchat_menu" in item.nbt:
                player.inventory.remove_item(item)

    def _get_container_items(self, item):
        items = []
        try:
            nbt = item.nbt
            if nbt and "Items" in nbt:
                items_list = nbt["Items"]
                for i in range(len(items_list)):
                    item_tag = items_list[i]
                    item_id = "?"
                    if "id" in item_tag:
                        item_id = str(item_tag["id"])
                    elif "Name" in item_tag:
                        item_id = str(item_tag["Name"])
                    else:
                        d = item_tag.to_dict() if hasattr(item_tag, 'to_dict') else {}
                        item_id = str(d.get("id", d.get("Name", "?")))
                    item_count = int(item_tag["Count"]) if "Count" in item_tag else 1
                    item_name = self._translate_item(item_id)
                    items.append((item_name, item_count))
        except:
            pass
        return items

    def _translate_item(self, item_id):
        if item_id in self.RU_NAMES: return self.RU_NAMES[item_id]
        return item_id.replace("minecraft:", "").replace("_", " ").title()

    def _get_item_name(self, item):
        return self._translate_item(str(item.type))

    def _has_staff_perm(self, player, perm):
        if player.is_op: return True
        rank = self._get_rank(player.name)
        return perm in self.RANK_PERMISSIONS.get(rank, [])

    def _get_menu_perms(self, player_name):
        rank = self._get_rank(player_name)
        return self.MENU_PERMISSIONS.get(rank, [])

    def on_command(self, sender: CommandSender, command: Command, args: list[str]):
        if not isinstance(sender, Player):
            sender.send_message("§c§lТолько игрок!")
            return

        cmd = command.name.lower()

        if cmd == "rtp":
            x = sender.location.x + random.randint(-5000, 5000)
            z = sender.location.z + random.randint(-5000, 5000)
            y = 120
            sender.teleport(Location(sender.dimension, x, y, z))
            sender.send_message(f"§a§lРандомный телепорт: §e{x:.0f} {y:.0f} {z:.0f}")
            return

        if cmd == "vanish":
            if not self._has_staff_perm(sender, "staff.vanish"):
                sender.send_message("§c§lНет прав!");
                return
            if sender.name in self.vanished_players:
                self.vanished_players.discard(sender.name)
                sender.send_message("§a§lТы снова видим!")
                for p in self.server.online_players: p.show_player(sender)
            else:
                self.vanished_players.add(sender.name)
                sender.send_message("§a§lТы невидим!")
                for p in self.server.online_players:
                    if p.name != sender.name: p.hide_player(sender)
            return

        if cmd == "menu":
            if self.menu_settings.get(sender.name, True):
                self._give_menu_book(sender)
            self._open_menu(sender)
            return

        if cmd in ("setrank", "delrank", "color", "prefix"):
            gc = self.groupchat
            if not gc: sender.send_message("§c§lGroupChat не загружен!"); return
            if cmd == "setrank":
                if not gc.has_perm(sender, "groupchat.stuff"):
                    sender.send_message("§c§lНет прав!");
                    return
                if len(args) < 2:
                    sender.send_message("§c§lsetrank <player> <stuff/admin/helper/builder/moder/player>");
                    return
                target, rank = args[0], args[1].lower()
                aliases = {"stuff": "stuff", "admin": "admin", "helper": "helper", "builder": "builder",
                           "moder": "moder", "player": "player"}
                rank = aliases.get(rank, rank)
                if rank not in gc.ranks:
                    sender.send_message("§c§lРанги: stuff, admin, helper, builder, moder, player");
                    return
                if rank == "stuff" and sender.name.lower() != "ef1mo4ka":
                    sender.send_message("§c§lТолько владелец может выдавать STUFF!");
                    return
                gc.set_rank(target, rank)
                if rank == "stuff":
                    self.server.dispatch_command(self.server.command_sender, f"op {target}")
                elif gc.get_rank(target) == "stuff":
                    self.server.dispatch_command(self.server.command_sender, f"deop {target}")
                tp = self.server.get_player(target)
                if tp: self._give_permissions(tp, rank)
                sender.send_message(f"§a§l{target} теперь {gc.get_rank_data(rank)['display']}")
                if tp: tp.send_message(f"§a§lТвой ранг: {gc.get_rank_data(rank)['display']}")
            elif cmd == "delrank":
                if not gc.has_perm(sender, "groupchat.stuff"):
                    sender.send_message("§c§lНет прав!");
                    return
                if len(args) < 1: sender.send_message("§c§ldelrank <player>"); return
                target = args[0]
                if not self._can_target(sender, target):
                    sender.send_message("§c§lНедостаточно прав!");
                    return
                gc.set_rank(target, "player")
                sender.send_message(f"§a§lРанг {target} сброшен")
            elif cmd == "color":
                if not gc.has_perm(sender, "groupchat.modern"):
                    sender.send_message("§c§lНет прав!");
                    return
                if not args: sender.send_message(f"§c§lcolor <цвет>"); return
                c = args[0].lower().replace("&", "§")
                for name, code in gc.COLORS.items():
                    if c == code or c == name:
                        gc.set_player_color(sender.name, code)
                        sender.send_message(f"§a§lЦвет: {code}Пример");
                        return
                sender.send_message("§c§lЦвет не найден!")
            elif cmd == "prefix":
                if not gc.has_perm(sender, "groupchat.helper"):
                    sender.send_message("§c§lНет прав!");
                    return
                if not args: sender.send_message("§c§lprefix <текст> или prefix clear"); return
                if args[0].lower() == "clear":
                    gc.set_player_prefix(sender.name, "")
                    sender.send_message("§a§lПрефикс очищен!");
                    return
                gc.set_player_prefix(sender.name, " ".join(args).replace("&", "§"))
                sender.send_message("§a§lПрефикс установлен!")
            return

        perm_map = {
            "spawn": "staff.spawn", "setspawn": "staff.admin",
            "tpto": "staff.teleport", "tphere": "staff.teleport",
            "kickplayer": "staff.kick", "mute": "staff.mute",
            "unmute": "staff.mute", "banplayer": "staff.ban", "unbanplayer": "staff.ban",
        }
        required = perm_map.get(cmd)
        if required and not self._has_staff_perm(sender, required):
            sender.send_message("§c§lНет прав!");
            return

        if cmd == "spawn":
            x, y, z = self.spawn_config["x"], self.spawn_config["y"], self.spawn_config["z"]
            pitch, yaw = self.spawn_config.get("pitch", 0), self.spawn_config.get("yaw", 0)
            if args:
                if not self._has_staff_perm(sender, "staff.admin"):
                    sender.send_message("§c§lНет прав!");
                    return
                if not self._can_target(sender, args[0]):
                    sender.send_message("§c§lНедостаточно прав!");
                    return
                target = self.server.get_player(args[0])
                if not target: sender.send_message("§c§lНе найден!"); return
                target.teleport(Location(target.dimension, x, y, z, pitch, yaw))
                target.send_message("§a§lТы на спавне!")
                sender.send_message(f"§a§l{target.name} на спавне!")
            else:
                sender.teleport(Location(sender.dimension, x, y, z, pitch, yaw))
                sender.send_message("§a§lТы на спавне!")

        elif cmd == "setspawn":
            loc = sender.location
            self.spawn_config.update({"x": loc.x, "y": loc.y, "z": loc.z, "pitch": loc.pitch, "yaw": loc.yaw})
            self._save()
            sender.send_message(f"§a§lСпавн: {loc.x:.0f} {loc.y:.0f} {loc.z:.0f}")

        elif cmd == "tpto":
            if not args: sender.send_message("§c§l/tpto <player>"); return
            if not self._can_target(sender, args[0]):
                sender.send_message("§c§lНедостаточно прав!");
                return
            target = self.server.get_player(args[0])
            if not target: sender.send_message("§c§lНе найден!"); return
            sender.teleport(target.location)
            sender.send_message(f"§a§lТы у {target.name}!")

        elif cmd == "tphere":
            if not args: sender.send_message("§c§l/tphere <player>"); return
            if not self._can_target(sender, args[0]):
                sender.send_message("§c§lНедостаточно прав!");
                return
            target = self.server.get_player(args[0])
            if not target: sender.send_message("§c§lНе найден!"); return
            target.teleport(sender.location)
            target.send_message(f"§a§lТы у {sender.name}!")
            sender.send_message(f"§a§l{target.name} у тебя!")

        elif cmd == "kickplayer":
            if not args: sender.send_message("§c§l/kickplayer <player>"); return
            if not self._can_target(sender, args[0]):
                sender.send_message("§c§lНедостаточно прав!");
                return
            target = self.server.get_player(args[0])
            if not target: sender.send_message("§c§lНе найден!"); return
            reason = " ".join(args[1:]) if len(args) > 1 else "Kicked"
            target.kick(f"§c{reason}")
            sender.send_message(f"§a§l{target.name} кикнут!")

        elif cmd == "mute":
            if not args: sender.send_message("§c§l/mute <player>"); return
            if not self._can_target(sender, args[0]):
                sender.send_message("§c§lНедостаточно прав!");
                return
            self.muted_players[args[0]] = True;
            self._save()
            sender.send_message(f"§a§l{args[0]} в муте!")

        elif cmd == "unmute":
            if not args: sender.send_message("§c§l/unmute <player>"); return
            if not self._can_target(sender, args[0]):
                sender.send_message("§c§lНедостаточно прав!");
                return
            self.muted_players.pop(args[0], None);
            self._save()
            sender.send_message(f"§a§l{args[0]} размучен!")

        elif cmd == "banplayer":
            if not args: sender.send_message("§c§l/banplayer <player>"); return
            if not self._can_target(sender, args[0]):
                sender.send_message("§c§lНедостаточно прав!");
                return
            target = args[0]
            reason = " ".join(args[1:]) if len(args) > 1 else "Banned"
            self.banned_players[target] = reason;
            self._save()
            tp = self.server.get_player(target)
            if tp: tp.kick(f"§cBanned: {reason}")
            sender.send_message(f"§a§l{target} забанен!")

        elif cmd == "unbanplayer":
            if not args: sender.send_message("§c§l/unbanplayer <player>"); return
            self.banned_players.pop(args[0], None);
            self._save()
            sender.send_message(f"§a§l{args[0]} разбанен!")

    # ========== МЕНЮ (ВСТАВЬ МЕТОДЫ ГУИ) ==========
    # _open_menu, _show_players_list, _show_ranks_gui, _confirm, _trash_menu,
    # _container_trash_menu, _remove_from_container, _invsee_menu, _show_inventory,
    # _container_inv_menu, _settings_menu, _color_menu, _color_pick, _prefix_menu,
    # _prefix_modal, _clear_prefix_menu, _clear_prefix_target, _setrank_menu,
    # _setrank_select, _delrank_menu, _delrank_target, _player_select_form,
    # _player_input_modal, _show_done_menu

    @event_handler
    def on_interact(self, event: PlayerInteractEvent):
        item = event.item
        if item and item.nbt and "groupchat_menu" in item.nbt:
            event.cancelled = True
            action = str(event.action).lower()
            if "block" in action: return
            self._open_menu(event.player)

    @event_handler
    def on_block_break(self, event: BlockBreakEvent):
        item = event.player.inventory.item_in_main_hand
        if item and item.nbt and "groupchat_menu" in item.nbt:
            event.cancelled = True
            self._open_menu(event.player)

    @event_handler
    def on_drop(self, event: PlayerDropItemEvent):
        item = event.item
        if item and item.nbt and "groupchat_menu" in item.nbt:
            event.cancelled = True
            now = time.time()
            last = self._last_drop_warning.get(event.player.name, 0)
            if now - last > 5:
                self._last_drop_warning[event.player.name] = now
                event.player.send_message(
                    "§c§l⚠ Внимание! §fДля §cудаления §fданного предмета, требуется выключить выдачу §e/menu §fво вкладке §6настройки!")

    @event_handler
    def on_chat(self, event: PlayerChatEvent):
        player = event.player

        if self.muted_players.get(player.name):
            player.send_message("§c§lТы в муте!")
            event.is_cancelled = True
            return
        if self.banned_players.get(player.name):
            player.kick(f"§cBanned: {self.banned_players[player.name]}")
            return

        msg = event.message.strip()
        parts = msg.split(" ")
        first = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        cmd_map = {
            "tp": "tpto", "tpto": "tpto", "tphere": "tphere",
            "kick": "kickplayer", "kickplayer": "kickplayer",
            "ban": "banplayer", "banplayer": "banplayer",
            "unban": "unbanplayer", "unbanplayer": "unbanplayer",
            "mute": "mute", "unmute": "unmute",
            "spawn": "spawn", "rtp": "rtp", "vanish": "vanish",
            "menu": "menu", "setrank": "setrank", "delrank": "delrank",
            "color": "color", "prefix": "prefix",
        }

        if first in cmd_map:
            event.is_cancelled = True
            cmd_name = cmd_map[first]
            cmd = self.get_command(cmd_name)
            if cmd:
                self.on_command(player, cmd, args)
            return

    @event_handler
    def on_join(self, event: PlayerJoinEvent):
        p = event.player
        if self.banned_players.get(p.name):
            p.kick(f"§cBanned: {self.banned_players[p.name]}")
            return
        for v in self.vanished_players:
            vp = self.server.get_player(v)
            if vp: p.hide_player(vp)
        rank = self._get_rank(p.name)
        self._give_permissions(p, rank)