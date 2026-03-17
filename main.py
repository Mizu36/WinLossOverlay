import copy
import json
import base64
from datetime import datetime, timezone
from pathlib import Path

try:
    import keyboard as keyboard_library
except ImportError:
    keyboard_library = None

overwatch_ranks = ["Bronze5", "Bronze4", "Bronze3", "Bronze2", "Bronze1", "Silver5", "Silver4", "Silver3", "Silver2", "Silver1", "Gold5", "Gold4", "Gold3", "Gold2", "Gold1", "Platinum5", "Platinum4", "Platinum3", "Platinum2", "Platinum1", "Diamond5", "Diamond4", "Diamond3", "Diamond2", "Diamond1", "Master5", "Master4", "Master3", "Master2", "Master1", "Grandmaster5", "Grandmaster4", "Grandmaster3", "Grandmaster2", "Grandmaster1", "Top500"]
valorant_ranks = ["Iron1", "Iron2", "Iron3", "Bronze1", "Bronze2", "Bronze3", "Silver1", "Silver2", "Silver3", "Gold1", "Gold2", "Gold3", "Platinum1", "Platinum2", "Platinum3", "Diamond1", "Diamond2", "Diamond3", "Ascendant1", "Ascendant2", "Ascendant3", "Immortal1", "Immortal2", "Immortal3", "Radiant"]

game_rank_lists = {
    "Overwatch": overwatch_ranks,
    "Valorant": valorant_ranks,
}

games_with_multiple_rank_categories = ["Overwatch"]

settings = {}
saved_data = {}
current_session_data = {}
current_game = "Overwatch"
registered_hotkey_handlers = {}
image_data_uri_cache = {}


def get_app_root():
    return Path(__file__).resolve().parent


def get_settings_path():
    return get_app_root() / "data" / "settings.json"


def get_saved_data_path():
    return get_app_root() / "data" / "saved_data.json"


def get_overlay_state_path():
    return get_app_root() / "data" / "overlay_state.json"


def get_default_settings():
    return {
        "Active Game": "Overwatch",
        "Opacity": 100,
        "Stats Overlay Opacity": 100,
        "Rank Overlay Opacity": 100,
        "Hotkeys": {
            "Record Win": "",
            "Record Loss": "",
            "Record Draw": "",
            "Reset Current Stats": "",
            "Increase Rank": "",
            "Decrease Rank": "",
        },
    }


def get_default_saved_data():
    return {
        "Overwatch": {
            "Wins": 0,
            "Losses": 0,
            "Draws": 0,
            "Total Matches": 0,
            "Win/Loss Ratio": 0.0,
            "Rank": {
                "Open Queue": "Unranked",
                "Support": "Unranked",
                "Tank": "Unranked",
                "Damage": "Unranked",
                "Stadium": "Unranked",
            },
        },
        "Valorant": {
            "Wins": 0,
            "Losses": 0,
            "Draws": 0,
            "Total Matches": 0,
            "Win/Loss Ratio": 0.0,
            "Rank": "Unranked",
        },
    }


def read_json_file(path: Path, fallback_dictionary):
    if not path.exists():
        return copy.deepcopy(fallback_dictionary)
    with path.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def write_json_file(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_handle:
        json.dump(value, file_handle, indent=4)


def ensure_settings_shape(loaded_settings):
    merged_settings = copy.deepcopy(get_default_settings())
    loaded_settings_dictionary = loaded_settings if isinstance(loaded_settings, dict) else {}
    if isinstance(loaded_settings, dict):
        merged_settings.update(loaded_settings)
        merged_settings["Hotkeys"].update(loaded_settings.get("Hotkeys", {}))

    legacy_opacity_value = int(merged_settings.get("Opacity", 100))
    if "Stats Overlay Opacity" not in loaded_settings_dictionary:
        merged_settings["Stats Overlay Opacity"] = legacy_opacity_value
    if "Rank Overlay Opacity" not in loaded_settings_dictionary:
        merged_settings["Rank Overlay Opacity"] = legacy_opacity_value

    merged_settings["Stats Overlay Opacity"] = max(0, min(100, int(merged_settings.get("Stats Overlay Opacity", legacy_opacity_value))))
    merged_settings["Rank Overlay Opacity"] = max(0, min(100, int(merged_settings.get("Rank Overlay Opacity", legacy_opacity_value))))
    merged_settings["Opacity"] = merged_settings["Stats Overlay Opacity"]

    if "Record Victory" in merged_settings["Hotkeys"] and not merged_settings["Hotkeys"].get("Record Win"):
        merged_settings["Hotkeys"]["Record Win"] = merged_settings["Hotkeys"]["Record Victory"]
    if "Record Defeat" in merged_settings["Hotkeys"] and not merged_settings["Hotkeys"].get("Record Loss"):
        merged_settings["Hotkeys"]["Record Loss"] = merged_settings["Hotkeys"]["Record Defeat"]
    if "Reset Current Game Stats" in merged_settings["Hotkeys"] and not merged_settings["Hotkeys"].get("Reset Current Stats"):
        merged_settings["Hotkeys"]["Reset Current Stats"] = merged_settings["Hotkeys"]["Reset Current Game Stats"]
    return merged_settings


def ensure_saved_data_shape(loaded_saved_data):
    merged_saved_data = copy.deepcopy(get_default_saved_data())
    if isinstance(loaded_saved_data, dict):
        for game_name, game_data in loaded_saved_data.items():
            if game_name not in merged_saved_data:
                merged_saved_data[game_name] = game_data
                continue
            if isinstance(game_data, dict):
                merged_saved_data[game_name].update(game_data)

    overwatch_rank_data = merged_saved_data["Overwatch"].get("Rank", {})
    if not isinstance(overwatch_rank_data, dict):
        overwatch_rank_data = copy.deepcopy(get_default_saved_data()["Overwatch"]["Rank"])
    for queue_name in get_default_saved_data()["Overwatch"]["Rank"]:
        overwatch_rank_data.setdefault(queue_name, "Unranked")
    merged_saved_data["Overwatch"]["Rank"] = overwatch_rank_data

    if not isinstance(merged_saved_data["Valorant"].get("Rank"), str):
        merged_saved_data["Valorant"]["Rank"] = "Unranked"

    for game_name, game_data in merged_saved_data.items():
        if not isinstance(game_data, dict):
            continue
        wins = int(game_data.get("Wins", 0))
        losses = int(game_data.get("Losses", 0))
        draws = int(game_data.get("Draws", 0))
        game_data["Wins"] = wins
        game_data["Losses"] = losses
        game_data["Draws"] = draws
        game_data["Total Matches"] = wins + losses + draws
        game_data["Win/Loss Ratio"] = calculate_win_loss_ratio(wins=wins, losses=losses, draws=draws)

    return merged_saved_data


def load_settings():
    global settings
    settings = ensure_settings_shape(read_json_file(get_settings_path(), get_default_settings()))
    save_settings(settings)
    return settings


def save_settings(settings_dictionary):
    write_json_file(get_settings_path(), settings_dictionary)


def load_saved_data():
    global saved_data
    saved_data = ensure_saved_data_shape(read_json_file(get_saved_data_path(), get_default_saved_data()))
    save_saved_data(saved_data)
    return saved_data


def save_saved_data(saved_data_dictionary):
    write_json_file(get_saved_data_path(), saved_data_dictionary)


def get_rank_categories_for_game(game_name):
    game_rank_data = saved_data.get(game_name, {}).get("Rank", "Unranked")
    if isinstance(game_rank_data, dict):
        return list(game_rank_data.keys())
    return []


def get_active_game_total_data():
    return saved_data.get(current_game, {})


def get_active_game_current_session_data():
    return current_session_data.get(current_game, {})


def calculate_win_loss_ratio(wins=0, losses=0, draws=0, total_matches=None):
    total_match_count = total_matches if total_matches is not None else wins + losses + draws
    if total_match_count == 0:
        return 0.0
    return (wins + (0.5 * draws)) / total_match_count


def get_image_mime_type(file_extension):
    mime_type_by_extension = {
        ".png": "image/png",
        ".webp": "image/webp",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }
    return mime_type_by_extension.get(file_extension.lower(), "application/octet-stream")


def get_image_data_uri(image_file_path: Path):
    if not image_file_path.exists():
        return None

    cache_key = f"{image_file_path.resolve()}::{image_file_path.stat().st_mtime_ns}"
    cached_data_uri = image_data_uri_cache.get(cache_key)
    if cached_data_uri:
        return cached_data_uri

    encoded_bytes = base64.b64encode(image_file_path.read_bytes())
    encoded_text = encoded_bytes.decode("utf-8")
    mime_type = get_image_mime_type(image_file_path.suffix)
    data_uri = f"data:{mime_type};base64,{encoded_text}"
    image_data_uri_cache[cache_key] = data_uri
    return data_uri


def get_image_asset_for_name(base_directory: Path, relative_directory_parts, asset_name):
    file_extensions_to_try = [".webp", ".png", ".jpg", ".jpeg"]

    for file_extension in file_extensions_to_try:
        candidate_file = base_directory / f"{asset_name}{file_extension}"
        if candidate_file.exists():
            relative_path = "../" + "/".join([*relative_directory_parts, f"{asset_name}{file_extension}"])
            return {
                "relativePath": relative_path,
                "absolutePath": candidate_file,
            }

    fallback_relative_path = "../" + "/".join([*relative_directory_parts, f"{asset_name}.png"])
    fallback_absolute_path = base_directory / f"{asset_name}.png"
    return {
        "relativePath": fallback_relative_path,
        "absolutePath": fallback_absolute_path,
    }


def get_logo_image_asset(game_name):
    logos_directory = get_app_root() / "overlay" / "assets" / "Logos"
    return get_image_asset_for_name(
        base_directory=logos_directory,
        relative_directory_parts=["assets", "Logos"],
        asset_name=game_name,
    )


def get_rank_image_relative_path(game_name, rank_name):
    ranks_directory = get_app_root() / "overlay" / "assets" / "Ranks" / game_name
    image_asset = get_image_asset_for_name(
        base_directory=ranks_directory,
        relative_directory_parts=["assets", "Ranks", game_name],
        asset_name=rank_name,
    )
    return image_asset["relativePath"]


def get_rank_image_asset(game_name, rank_name):
    ranks_directory = get_app_root() / "overlay" / "assets" / "Ranks" / game_name
    return get_image_asset_for_name(
        base_directory=ranks_directory,
        relative_directory_parts=["assets", "Ranks", game_name],
        asset_name=rank_name,
    )


def get_rank_display_entries_for_game(game_name):
    rank_data = saved_data.get(game_name, {}).get("Rank", "Unranked")
    rank_entries = []

    if isinstance(rank_data, dict):
        for category_name, category_rank in rank_data.items():
            if category_rank and category_rank != "Unranked":
                image_asset = get_rank_image_asset(game_name, category_rank)
                rank_entries.append({
                    "category": category_name,
                    "rank": category_rank,
                    "image": image_asset["relativePath"],
                    "imageDataUri": get_image_data_uri(image_asset["absolutePath"]),
                })
    elif isinstance(rank_data, str) and rank_data != "Unranked":
        image_asset = get_rank_image_asset(game_name, rank_data)
        rank_entries.append({
            "category": "",
            "rank": rank_data,
            "image": image_asset["relativePath"],
            "imageDataUri": get_image_data_uri(image_asset["absolutePath"]),
        })

    return rank_entries


def build_overlay_state_dictionary():
    active_game_total_data = get_active_game_total_data()
    active_game_session_data = get_active_game_current_session_data()

    session_wins = int(active_game_session_data.get("Wins", 0))
    session_losses = int(active_game_session_data.get("Losses", 0))
    session_draws = int(active_game_session_data.get("Draws", 0))
    session_total_matches = session_wins + session_losses + session_draws

    total_wins = int(active_game_total_data.get("Wins", 0))
    total_losses = int(active_game_total_data.get("Losses", 0))
    total_draws = int(active_game_total_data.get("Draws", 0))
    total_matches = total_wins + total_losses + total_draws

    stats_opacity_percent = settings.get("Stats Overlay Opacity", settings.get("Opacity", 100))
    rank_opacity_percent = settings.get("Rank Overlay Opacity", settings.get("Opacity", 100))
    stats_opacity_fraction = max(0.0, min(1.0, float(stats_opacity_percent) / 100.0))
    rank_opacity_fraction = max(0.0, min(1.0, float(rank_opacity_percent) / 100.0))
    logo_asset = get_logo_image_asset(current_game)

    overlay_state = {
        "version": 1,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "activeGame": current_game,
        "opacity": stats_opacity_fraction,
        "opacities": {
            "stats": stats_opacity_fraction,
            "rank": rank_opacity_fraction,
        },
        "assets": {
            "logo": logo_asset["relativePath"],
            "logoDataUri": get_image_data_uri(logo_asset["absolutePath"]),
        },
        "stats": {
            "currentSession": {
                "wins": session_wins,
                "losses": session_losses,
                "draws": session_draws,
                "totalMatches": session_total_matches,
                "ratio": calculate_win_loss_ratio(wins=session_wins, losses=session_losses, draws=session_draws),
            },
            "total": {
                "wins": total_wins,
                "losses": total_losses,
                "draws": total_draws,
                "totalMatches": total_matches,
                "ratio": calculate_win_loss_ratio(wins=total_wins, losses=total_losses, draws=total_draws),
            },
        },
        "rank": {
            "entries": get_rank_display_entries_for_game(current_game),
        },
    }
    return overlay_state


def update_displayed_stats(**kwargs):
    session_data = get_active_game_current_session_data()

    if "wins" in kwargs and kwargs["wins"] is not None:
        session_data["Wins"] = int(kwargs["wins"])
    if "losses" in kwargs and kwargs["losses"] is not None:
        session_data["Losses"] = int(kwargs["losses"])
    if "draws" in kwargs and kwargs["draws"] is not None:
        session_data["Draws"] = int(kwargs["draws"])

    current_session_data[current_game] = session_data
    overlay_state = build_overlay_state_dictionary()
    write_json_file(get_overlay_state_path(), overlay_state)


def initialize_current_session_data():
    global current_session_data
    current_session_data = {}
    for game_name in saved_data:
        current_session_data[game_name] = {
            "Wins": 0,
            "Losses": 0,
            "Draws": 0,
        }


def set_active_game(game_name):
    global current_game
    if game_name not in saved_data:
        return
    current_game = game_name
    settings["Active Game"] = game_name
    save_settings(settings)
    update_displayed_stats()


def set_overlay_opacity(opacity_percent):
    clamped_value = max(0, min(100, int(opacity_percent)))
    settings["Opacity"] = clamped_value
    settings["Stats Overlay Opacity"] = clamped_value
    settings["Rank Overlay Opacity"] = clamped_value
    save_settings(settings)
    update_displayed_stats()


def set_stats_overlay_opacity(opacity_percent):
    clamped_value = max(0, min(100, int(opacity_percent)))
    settings["Stats Overlay Opacity"] = clamped_value
    settings["Opacity"] = clamped_value
    save_settings(settings)
    update_displayed_stats()


def set_rank_overlay_opacity(opacity_percent):
    clamped_value = max(0, min(100, int(opacity_percent)))
    settings["Rank Overlay Opacity"] = clamped_value
    save_settings(settings)
    update_displayed_stats()


def record_victory():
    session_data = get_active_game_current_session_data()
    total_data = get_active_game_total_data()

    session_data["Wins"] = int(session_data.get("Wins", 0)) + 1
    total_data["Wins"] = int(total_data.get("Wins", 0)) + 1
    total_data["Total Matches"] = int(total_data.get("Total Matches", 0)) + 1
    total_data["Win/Loss Ratio"] = calculate_win_loss_ratio(
        wins=total_data["Wins"],
        losses=total_data.get("Losses", 0),
        draws=total_data.get("Draws", 0),
    )
    save_saved_data(saved_data)
    update_displayed_stats()


def record_defeat():
    session_data = get_active_game_current_session_data()
    total_data = get_active_game_total_data()

    session_data["Losses"] = int(session_data.get("Losses", 0)) + 1
    total_data["Losses"] = int(total_data.get("Losses", 0)) + 1
    total_data["Total Matches"] = int(total_data.get("Total Matches", 0)) + 1
    total_data["Win/Loss Ratio"] = calculate_win_loss_ratio(
        wins=total_data.get("Wins", 0),
        losses=total_data["Losses"],
        draws=total_data.get("Draws", 0),
    )
    save_saved_data(saved_data)
    update_displayed_stats()


def record_draw():
    session_data = get_active_game_current_session_data()
    total_data = get_active_game_total_data()

    session_data["Draws"] = int(session_data.get("Draws", 0)) + 1
    total_data["Draws"] = int(total_data.get("Draws", 0)) + 1
    total_data["Total Matches"] = int(total_data.get("Total Matches", 0)) + 1
    total_data["Win/Loss Ratio"] = calculate_win_loss_ratio(
        wins=total_data.get("Wins", 0),
        losses=total_data.get("Losses", 0),
        draws=total_data["Draws"],
    )
    save_saved_data(saved_data)
    update_displayed_stats()


def get_rank_for_category(game_name, rank_category=None):
    game_rank_data = saved_data.get(game_name, {}).get("Rank", "Unranked")
    if isinstance(game_rank_data, dict):
        if rank_category is None:
            rank_category = next(iter(game_rank_data), None)
        return game_rank_data.get(rank_category, "Unranked")
    return game_rank_data


def set_rank(new_rank, rank_category=None):
    total_data = get_active_game_total_data()
    game_rank_data = total_data.get("Rank", "Unranked")

    if isinstance(game_rank_data, dict):
        if rank_category is None:
            rank_category = next(iter(game_rank_data), None)
        if rank_category in game_rank_data:
            game_rank_data[rank_category] = new_rank
    else:
        total_data["Rank"] = new_rank

    save_saved_data(saved_data)
    update_displayed_stats()


def increase_rank(rank_category=None):
    rank_list = game_rank_lists.get(current_game, [])
    if not rank_list:
        return

    if current_game in games_with_multiple_rank_categories:
        if rank_category is None:
            return
        
    current_rank = get_rank_for_category(current_game, rank_category)
    if current_rank == "Unranked":
        set_rank(rank_list[0], rank_category=rank_category)
        return

    if current_rank not in rank_list:
        return

    current_index = rank_list.index(current_rank)
    if current_index < len(rank_list) - 1:
        set_rank(rank_list[current_index + 1], rank_category=rank_category)


def decrease_rank(rank_category=None):
    rank_list = game_rank_lists.get(current_game, [])
    if not rank_list:
        return
    
    if current_game in games_with_multiple_rank_categories:
        if rank_category is None:
            return

    current_rank = get_rank_for_category(current_game, rank_category)
    if current_rank not in rank_list:
        return

    current_index = rank_list.index(current_rank)
    if current_index > 0:
        set_rank(rank_list[current_index - 1], rank_category=rank_category)
    else:
        set_rank("Unranked", rank_category=rank_category)


def set_current_session_stats(wins, losses, draws):
    session_data = get_active_game_current_session_data()
    session_data["Wins"] = max(0, int(wins))
    session_data["Losses"] = max(0, int(losses))
    session_data["Draws"] = max(0, int(draws))
    update_displayed_stats()


def reset_current_stats():
    set_current_session_stats(wins=0, losses=0, draws=0)


def reset_total_stats():
    total_data = get_active_game_total_data()
    total_data["Wins"] = 0
    total_data["Losses"] = 0
    total_data["Draws"] = 0
    total_data["Total Matches"] = 0
    total_data["Win/Loss Ratio"] = 0.0

    rank_data = total_data.get("Rank")
    if isinstance(rank_data, dict):
        for category_name in rank_data:
            rank_data[category_name] = "Unranked"
    else:
        total_data["Rank"] = "Unranked"

    save_saved_data(saved_data)
    update_displayed_stats()


def full_reset():
    reset_current_stats()
    reset_total_stats()


def unregister_hotkeys():
    if keyboard_library is None:
        return

    for hotkey_name, hotkey_handler in registered_hotkey_handlers.items():
        try:
            keyboard_library.remove_hotkey(hotkey_handler)
        except Exception:
            continue
    registered_hotkey_handlers.clear()


def register_hotkeys(on_hotkey_action_callback=None):
    unregister_hotkeys()

    if keyboard_library is None:
        return {
            "enabled": False,
            "registeredCount": 0,
            "message": "Hotkey package not installed. Install 'keyboard' to enable listeners.",
        }

    hotkeys = settings.get("Hotkeys", {})
    hotkey_to_action_map = {
        "Record Win": record_victory,
        "Record Loss": record_defeat,
        "Record Draw": record_draw,
        "Reset Current Stats": reset_current_stats,
        "Increase Rank": increase_rank,
        "Decrease Rank": decrease_rank,
    }

    registered_count = 0
    for hotkey_setting_name, hotkey_action in hotkey_to_action_map.items():
        hotkey_value = str(hotkeys.get(hotkey_setting_name, "")).strip()
        if not hotkey_value:
            continue

        def create_hotkey_handler(action_name, action_function):
            def hotkey_handler():
                action_function()
                if on_hotkey_action_callback is not None:
                    on_hotkey_action_callback(action_name)

            return hotkey_handler

        try:
            hotkey_handler = keyboard_library.add_hotkey(
                hotkey_value,
                create_hotkey_handler(hotkey_setting_name, hotkey_action),
                suppress=False,
                trigger_on_release=False,
            )
            registered_hotkey_handlers[hotkey_setting_name] = hotkey_handler
            registered_count += 1
        except Exception:
            continue

    return {
        "enabled": True,
        "registeredCount": registered_count,
        "message": f"Registered {registered_count} hotkey listeners.",
    }


def main():
    global current_game
    load_settings()
    load_saved_data()
    initialize_current_session_data()

    selected_game = settings.get("Active Game", "Overwatch")
    if selected_game not in saved_data:
        selected_game = "Overwatch"
    current_game = selected_game

    update_displayed_stats()


if __name__ == "__main__":
    main()