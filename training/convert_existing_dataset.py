# convert_existing_dataset.py
"""Converts Chinese prompt templates SFT datasets to English formats.

This script parses existing player_train.json and referee_train.json files
from data/ and rewrites them, saving them to *_legacy.json in the current directory.
It also provides a utility to merge simulation data and legacy data into the final SFT dataset.
"""

import os
import json
import re
import random
from typing import List, Dict, Any, Tuple

def find_file_path(filename: str) -> str:
    """Finds the correct path of a file across workspace directories.

    Args:
        filename: Name of the file.

    Returns:
        The resolved absolute or relative path, or empty string if not found.
    """
    candidates = [
        filename,
        os.path.join("training", filename),
        os.path.join("..", filename),
        os.path.join("data", "player", filename),
        os.path.join("data", "referee", filename),
        os.path.join("..", "data", "player", filename),
        os.path.join("..", "data", "referee", filename)
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return ""

def convert_player_dataset(file_name: str = "player_train.json") -> None:
    """Parses player dataset and chains sequential single-turn prompts into legacy multi-turn messages.

    Args:
        file_name: The file name of the player dataset.
    """
    file_path = find_file_path(file_name)
    if not file_path:
        print(f"❌ Could not find {file_name} in current directory or data/player/")
        return

    print(f"📖 Reading player dataset from: {file_path}")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Failed to read {file_path}: {e}")
        return

    # Regular expressions to extract opponent roast and assistant response
    zh_pattern = re.compile(
        r"User: 對手前一輪嗆你：「(.*?)」。請寫一句極富創意且辛辣的話嗆回去，不超過25字，不要有多餘說明。\nAssistant: (.*)",
        re.DOTALL
    )
    en_pattern = re.compile(
        r"User: Opponent roast: \"(.*?)\"\. Respond with a toxic comeback in Traditional Chinese under 25 characters\.\nAssistant: (.*)",
        re.DOTALL
    )
    style_pattern = re.compile(
        r"User: Opponent roast: \"(.*?)\"\. Style: (.*?)\. Respond with a toxic comeback in Traditional Chinese under 25 characters\.\nAssistant: (.*)",
        re.DOTALL
    )
    
    extracted_pairs: List[Tuple[str, str, str]] = []
    
    # 1. Parse all items into raw (opponent_roast, style, response) tuples
    for item in data:
        if "messages" in item:
            msgs = item["messages"]
            for i in range(0, len(msgs) - 1, 2):
                if msgs[i]["role"] == "user" and msgs[i+1]["role"] == "assistant":
                    user_content = msgs[i]["content"]
                    player_response = msgs[i+1]["content"]
                    
                    style_match = style_pattern.search(f"User: {user_content}\nAssistant: {player_response}")
                    if style_match:
                        extracted_pairs.append((style_match.group(1), style_match.group(2), player_response))
                    else:
                        roast_match = re.search(r'Opponent roast: "(.*?)"', user_content)
                        opp_roast = roast_match.group(1) if roast_match else user_content
                        extracted_pairs.append((opp_roast, "Elegant Sarcasm", player_response))
        else:
            text = item.get("text", "")
            zh_match = zh_pattern.search(text)
            en_match = en_pattern.search(text)
            style_match = style_pattern.search(text)
            
            if zh_match:
                extracted_pairs.append((zh_match.group(1), "Elegant Sarcasm", zh_match.group(2)))
            elif en_match:
                extracted_pairs.append((en_match.group(1), "Elegant Sarcasm", en_match.group(2)))
            elif style_match:
                extracted_pairs.append((style_match.group(1), style_match.group(2), style_match.group(3)))
            elif "text" in item:
                text_content = item["text"]
                if "User: " in text_content and "\nAssistant: " in text_content:
                    parts = text_content.split("\nAssistant: ")
                    user_part = parts[0].replace("User: ", "").strip()
                    assistant_part = parts[1].strip()
                    roast_match = re.search(r'Opponent roast: "(.*?)"', user_part)
                    opp_roast = roast_match.group(1) if roast_match else user_part
                    style_match = re.search(r'Style: (.*?)\.', user_part)
                    style_name = style_match.group(1) if style_match else "Elegant Sarcasm"
                    extracted_pairs.append((opp_roast, style_name, assistant_part))

    # 2. Chain sequential single-turns where opponent_roast matches the previous player_response
    chains: List[List[Tuple[str, str, str]]] = []
    current_chain: List[Tuple[str, str, str]] = []
    
    for opponent_roast, style_name, player_response in extracted_pairs:
        if not current_chain:
            current_chain.append((opponent_roast, style_name, player_response))
        else:
            last_pair = current_chain[-1]
            last_response = last_pair[2]
            
            if opponent_roast.strip() == last_response.strip():
                current_chain.append((opponent_roast, style_name, player_response))
                if len(current_chain) >= 10:
                    chains.append(current_chain)
                    current_chain = []
            else:
                chains.append(current_chain)
                current_chain = [(opponent_roast, style_name, player_response)]
                
    if current_chain:
        chains.append(current_chain)

    # 3. Format chains into SFT messages structures (two alternating perspectives)
    converted_data: List[Dict[str, Any]] = []
    for chain in chains:
        g_name = chain[0][1]
        
        # Thread 1: Player B (even indices: 0, 2, 4...)
        p_b_messages = []
        for idx, (opponent_roast, style_name, player_response) in enumerate(chain):
            if idx % 2 == 0:
                if len(p_b_messages) == 0:
                    p_b_messages.append({
                        "role": "user",
                        "content": f"Opponent roast: \"{opponent_roast}\". Style: {g_name}. Respond with a toxic comeback in Traditional Chinese under 25 characters."
                    })
                else:
                    p_b_messages.append({
                        "role": "user",
                        "content": opponent_roast
                    })
                p_b_messages.append({
                    "role": "assistant",
                    "content": player_response
                })
        if p_b_messages:
            converted_data.append({"messages": p_b_messages})

        # Thread 2: Player A (odd indices: 1, 3, 5...)
        p_a_messages = []
        for idx, (opponent_roast, style_name, player_response) in enumerate(chain):
            if idx % 2 != 0:
                if len(p_a_messages) == 0:
                    p_a_messages.append({
                        "role": "user",
                        "content": f"Opponent roast: \"{opponent_roast}\". Style: {g_name}. Respond with a toxic comeback in Traditional Chinese under 25 characters."
                    })
                else:
                    p_a_messages.append({
                        "role": "user",
                        "content": opponent_roast
                    })
                p_a_messages.append({
                    "role": "assistant",
                    "content": player_response
                })
        if p_a_messages:
            converted_data.append({"messages": p_a_messages})

    # Save to current dir and training/ subfolder to cover all execution bases
    for out_path in ["player_train_legacy.json", os.path.join("training", "player_train_legacy.json")]:
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(converted_data, f, ensure_ascii=False, indent=2)
            print(f"🚀 Saved {len(converted_data)} chained multi-turn legacy player records to {out_path}")
        except Exception:
            pass

def convert_referee_dataset(file_name: str = "referee_train.json") -> None:
    """Parses referee dataset and rewrites user prompts into English.

    Args:
        file_name: The file name of the referee dataset.
    """
    file_path = find_file_path(file_name)
    if not file_path:
        print(f"❌ Could not find {file_name} in current directory or data/referee/")
        return

    print(f"📖 Reading referee dataset from: {file_path}")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Failed to read {file_path}: {e}")
        return

    converted_data: List[Dict[str, Any]] = []
    
    zh_pattern = re.compile(
        r"User: 你是一個毒舌裁判。請評估以下攻擊，並以 JSON 格式輸出評估結果，格式為：\n"
        r"\{\"damage\": 10到50之間的整數, \"referee_comment\": \"20字內的毒舌短評\"\}\n\n"
        r"玩家攻擊：「(.*?)」\nAssistant: (.*)",
        re.DOTALL
    )
    en_pattern = re.compile(
        r"User: Evaluate the following player attack:\n\"(.*?)\"\n\nReturn JSON only\.\nAssistant: (.*)",
        re.DOTALL
    )
    
    for item in data:
        text = item.get("text", "")
        zh_match = zh_pattern.search(text)
        en_match = en_pattern.search(text)
        
        if zh_match:
            player_response = zh_match.group(1)
            referee_response = zh_match.group(2)
            converted_data.append({
                "messages": [
                    {"role": "user", "content": f"Evaluate the following player attack:\n\"{player_response}\"\n\nReturn JSON only."},
                    {"role": "assistant", "content": referee_response}
                ]
            })
        elif en_match:
            player_response = en_match.group(1)
            referee_response = en_match.group(2)
            converted_data.append({
                "messages": [
                    {"role": "user", "content": f"Evaluate the following player attack:\n\"{player_response}\"\n\nReturn JSON only."},
                    {"role": "assistant", "content": referee_response}
                ]
            })
        elif "messages" in item:
            converted_data.append(item)
        elif "text" in item:
            text_content = item["text"]
            if "User: " in text_content and "\nAssistant: " in text_content:
                parts = text_content.split("\nAssistant: ")
                user_part = parts[0].replace("User: ", "").strip()
                assistant_part = parts[1].strip()
                converted_data.append({
                    "messages": [
                        {"role": "user", "content": user_part},
                        {"role": "assistant", "content": assistant_part}
                    ]
                })
            else:
                converted_data.append(item)
        else:
            converted_data.append(item)
            
    # Save to both locations
    for out_path in ["referee_train_legacy.json", os.path.join("training", "referee_train_legacy.json")]:
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(converted_data, f, ensure_ascii=False, indent=2)
            print(f"🚀 Saved converted legacy referee records to {out_path}")
        except Exception:
            pass

def merge_datasets() -> None:
    """Safely merges and shuffles legacy data and simulation data to construct the final SFT datasets."""
    print("🔄 Starting Dataset Merging Utility...")
    random.seed(42)
    
    # 1. Merge Player Datasets
    merged_player = []
    
    # Find player_train_sim.json
    sim_player_path = find_file_path("player_train_sim.json")
    if sim_player_path:
        with open(sim_player_path, "r", encoding="utf-8") as f:
            sim_data = json.load(f)
            merged_player.extend(sim_data)
        print(f"  Loaded simulation player SFT data from {sim_player_path}: {len(sim_data)} items.")
    
    # Find player_train_legacy.json
    legacy_player_path = find_file_path("player_train_legacy.json")
    if legacy_player_path:
        with open(legacy_player_path, "r", encoding="utf-8") as f:
            legacy_data = json.load(f)
            merged_player.extend(legacy_data)
        print(f"  Loaded legacy player SFT data from {legacy_player_path}: {len(legacy_data)} items.")
        
    if merged_player:
        random.shuffle(merged_player)
        for out_path in ["player_train.json", os.path.join("training", "player_train.json")]:
            try:
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(merged_player, f, ensure_ascii=False, indent=2)
                print(f"✅ Final merged Player dataset saved to {out_path} ({len(merged_player)} items).")
            except Exception:
                pass
    else:
        print("⚠️ No Player datasets found to merge.")

    # 2. Merge Referee Datasets
    merged_referee = []
    
    # Find referee_train_sim.json
    sim_ref_path = find_file_path("referee_train_sim.json")
    if sim_ref_path:
        with open(sim_ref_path, "r", encoding="utf-8") as f:
            sim_ref_data = json.load(f)
            merged_referee.extend(sim_ref_data)
        print(f"  Loaded simulation referee SFT data from {sim_ref_path}: {len(sim_ref_data)} items.")
        
    # Find referee_train_legacy.json
    legacy_ref_path = find_file_path("referee_train_legacy.json")
    if legacy_ref_path:
        with open(legacy_ref_path, "r", encoding="utf-8") as f:
            legacy_ref_data = json.load(f)
            merged_referee.extend(legacy_ref_data)
        print(f"  Loaded legacy referee SFT data from {legacy_ref_path}: {len(legacy_ref_data)} items.")
        
    if merged_referee:
        random.shuffle(merged_referee)
        for out_path in ["referee_train.json", os.path.join("training", "referee_train.json")]:
            try:
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(merged_referee, f, ensure_ascii=False, indent=2)
                print(f"✅ Final merged Referee dataset saved to {out_path} ({len(merged_referee)} items).")
            except Exception:
                pass
    else:
        print("⚠️ No Referee datasets found to merge.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--merge-only":
        merge_datasets()
    else:
        convert_player_dataset()
        convert_referee_dataset()
        # Merge if simulation files are already present
        merge_datasets()
