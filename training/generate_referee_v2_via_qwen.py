# generate_referee_v2_via_qwen.py
"""Dataset generation script for Referee v2 SFT training using Qwen.

This script uses the local Ollama qwen3.6:latest model to simulate high-quality
verbal sparring matches across 8 distinct genres (Elegant Sarcasm, Grounded Street Slang,
Friendly Banter, Internet Memes, Workplace Passive Aggressive, Relationship Gaslighting,
Toxic Chicken Soup, Holiday Relatives). The simulated player comebacks are then evaluated
by the Qwen referee to generate a new referee training dataset.
"""

import argparse
import json
import os
import random
import time
from typing import Any, Dict, List, Tuple

import requests

# Constants
OLLAMA_URL: str = "http://localhost:11434/api/chat"
OLLAMA_MODEL: str = "qwen3.6:latest"
REPRODUCIBILITY_SEED: int = 42

# Define the 8 genres exactly as in the simulation stage
GENRES: Dict[str, Dict[str, Any]] = {
    "elegant": {
        "name": "Elegant Sarcasm",
        "system_directive": (
            "Style: Elegant Sarcasm (文雅高端流). Focus on intellectual superiority, dry sarcasm, elegant burns, and high-witted phrasing. "
            "Use polite but incredibly toxic and condescending words. Demolish their intelligence without using simple swear words."
        ),
        "seeds": [
            "聽你講話簡直是在進行智力脫水，我的智商正在被你強行拉低。",
            "你寫的程式碼再看兩眼，我的眼睛可能就需要申請勞保賠償。",
            "你今天出門是閉著眼睛穿衣服嗎？這審美觀簡真讓人窒息。"
        ]
    },
    "street": {
        "name": "Grounded Street Slang",
        "system_directive": (
            "Style: Grounded Street Slang / Swearing / 8+9 (接地氣市井流). Focus on raw, highly aggressive, down-to-earth Taiwanese street slang, "
            "8+9 monkey talk, and common vulgar teasing. You MUST include Taiwanese street slang where natural "
            "(e.g., '靠北', '三小', '衝三小', '看三小', '北七', '無三小路用', '當我塑膠喔', '是在旋轉喔', '沒那個屁股就不要吃瀉藥', '可撥仔', '滾回去下水溝啦'). "
            "Make it feel extremely realistic, hostile, and direct, representing local Taiwanese street fight/monkey culture."
        ),
        "seeds": [
            "當我塑膠是不是？衝三小啦，有種出來講，沒那個屁股就別吃瀉藥啦！",
            "靠北喔，整天在網路上旋轉我是怎樣？沒料就趕快滾回去洗洗睡啦！",
            "看三小？北七喔，輸過沒怕過啦，再機歪直接把你打成塑膠！",
            "可撥仔，社會在走行情要有，你這點戰力連給我塞牙縫都不夠，下去啦！"
        ]
    },
    "friendly": {
        "name": "Friendly Banter",
        "system_directive": (
            "Style: Friendly Banter (損友互損流). Focus on playful, close-friend teasing, mocking daily habits, laziness, or silly traits "
            "in a brutally honest, highly mocking, but intimate, relational way. Use common Taiwanese friendly banter/slang terms "
            "(e.g., '北七', '白目', '哭爸喔', '憨慢', '阿西', '魯蛇', '笑死'). Mock them like a close friend who has no filter."
        ),
        "seeds": [
            "北七喔，你出門是腦袋被門夾到？這點事情也能搞成這樣，笑死人。",
            "哭爸喔，整天躺在那邊跟死豬一樣，豬圈裡的豬都比你勤勞啦！",
            "白目喔，不要整天在那邊耍廢，我看你這輩子大概就這樣了，魯蛇一隻。",
            "你這個體力去跑馬拉松，大概在起跑線就得先叫好救護車。"
        ]
    },
    "meme": {
        "name": "Internet Memes",
        "system_directive": (
            "Style: Internet Memes & Gamer (網路迷因流). Focus on online forum slang, PTT/Dcard culture, gaming jargon, toxic gamer lobby banter, and trending memes "
            "(e.g., '小丑竟是我自己', '歸剛欸', '這很超派', '急了', '真香', '戰力只有5', '可撥', '87分不能再高了', '洗洗睡'). Be extremely toxic, like a classic salty gamer."
        ),
        "seeds": [
            "笑死，這波操作簡直就是小丑本尊，急了就開始亂咬人是吧？",
            "你的戰鬥力大概只有5，連新手村的史萊姆都能把你按在地上摩擦。",
            "歸剛欸！整天在那邊超派超派，結果根本沒半點料，回去洗洗睡啦可撥仔。",
            "87分不能再高了，你這智商還是回火星去吧，地球不適合你。"
        ]
    },
    "workplace": {
        "name": "Workplace Passive Aggressive",
        "system_directive": (
            "Style: Workplace Passive Aggressive (職場陰陽怪氣流). Use overly polite corporate jargon, buzzwords, and email speak to deliver "
            "high-toxicity condescension. Use terms like '收到', '請知悉', '以您的格局', '我們再 alignment 一下', '非常感謝您寶貴且毫無建樹的意見', '辛苦了'."
        ),
        "seeds": [
            "收到，非常感謝您寶貴且毫無建樹的意見，我們有緣再 alignment 吧。",
            "以您的理解能力，我真的很難跟您解釋什麼叫基本的 KPI。",
            "您說的都對，這部分就交給您全權負責，反正搞砸了也是您背鍋。",
            "辛苦了，看您每天忙得像陀螺，結果產出跟路邊的石頭差不多，也是種天賦。"
        ]
    },
    "relationship": {
        "name": "Relationship Gaslighting",
        "system_directive": (
            "Style: Relationship Gaslighting & Emotional Blackmail (關係情勒流). Use toxic, manipulative, guilt-tripping relationship arguments. "
            "Play the victim while pointing out their flaws. Use terms like '你要這樣想我也沒辦法', '都是我的錯', '你高興就好', '我不配得到你的在乎'."
        ),
        "seeds": [
            "你要這樣想，我也沒辦法，反正我做什麼在你眼裡都是錯的。",
            "都是我的錯，我不該對你的智商抱有任何期待，是我太天真了。",
            "對啦對啦，你最委屈了，我連呼吸都是在對你進行情緒勒索。",
            "你那麼厲害，怎麼不去當拯救世界的超人？待在我身邊真是委屈你了。"
        ]
    },
    "chicken_soup": {
        "name": "Toxic Chicken Soup",
        "system_directive": (
            "Style: Toxic Chicken Soup (心靈毒雞湯流). Deliver demotivational life facts and soul-crushing truths disguised as self-help quotes "
            "or positive encouragement. Focus on crushing their dreams objectively, with a calm but devastating tone."
        ),
        "seeds": [
            "努力不一定會成功，但你不努力真的好輕鬆，反正結果都一樣爛。",
            "不要以為世界拋棄了你，世界根本沒空理你，別自我感覺良好了。",
            "你雖然長得醜，但你想得美啊！這大概是你唯一的優點了。",
            "比你優秀的人都還在努力，那你努力還有什麼用？老老實實躺平吧。"
        ]
    },
    "relative": {
        "name": "Holiday Relatives",
        "system_directive": (
            "Style: Holiday Relatives Interrogation (過年親戚問候流). Mock them using annoying, condescending, prying questions typically asked by "
            "passive-aggressive older relatives during holidays. Focus on job, marriage, salary comparison, and 'neighbor's kid' comparisons."
        ),
        "seeds": [
            "隔壁阿明都買房生兩個了，你怎麼還在玩電腦？是不是哪裡有問題？",
            "年終拿幾個月啊？現在不考公務員，以後老了看你怎麼辦。",
            "怎麼還沒交女朋友？是不是眼光太高？也不照照鏡子看自己長怎樣。",
            "你讀那個科系畢業後要幹嘛？現在去搖飲料薪水都比你高吧？"
        ]
    }
}


def set_reproducibility_seeds(seed: int = 42) -> None:
    """Locks random seeds to guarantee reproducible generation.

    Args:
        seed: The integer seed value.
    """
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)


def verify_ollama_connection() -> None:
    """Verifies that local Ollama is active and has the required model loaded.

    Raises:
        ConnectionError: If Ollama is unreachable or model is not found.
    """
    print(f"🔍 Pinging Ollama endpoint: {OLLAMA_URL}...")
    try:
        # Check overall service health
        tags_url = OLLAMA_URL.replace("/chat", "/tags")
        response = requests.get(tags_url, timeout=5)
        if response.status_code != 200:
            raise ConnectionError(
                f"Ollama server returned unhealthy status code: {response.status_code}"
            )
        
        models_data = response.json()
        available_models = [m["name"] for m in models_data.get("models", [])]
        print(f"   Available Ollama Models: {available_models}")
        
        if OLLAMA_MODEL not in available_models:
            # Try matching by base name without tags
            short_names = [m.split(":")[0] for m in available_models]
            target_short = OLLAMA_MODEL.split(":")[0]
            if target_short not in short_names:
                raise ConnectionError(
                    f"Required model '{OLLAMA_MODEL}' is not loaded in Ollama. "
                    f"Please run `ollama pull {OLLAMA_MODEL}` first."
                )
            else:
                print(f"   Found partial model match. Proceeding with caution.")
        else:
            print(f"   Successfully verified '{OLLAMA_MODEL}' model presence.")
            
    except requests.RequestException as e:
        raise ConnectionError(
            f"Failed to connect to local Ollama server at {OLLAMA_URL}. "
            "Please make sure the Ollama server is running (e.g. `ollama serve`). "
            f"Error details: {e}"
        )


def generate_qwen_comeback(
    opponent_roast: str,
    genre_key: str
) -> str:
    """Simulates a player comeback by calling Qwen with a specific genre.

    Args:
        opponent_roast: The opponent's roast text.
        genre_key: The target genre key.

    Returns:
        The generated comeback text string.

    Raises:
        RuntimeError: If the API requests fail repeatedly.
    """
    genre_info = GENRES.get(genre_key, GENRES["elegant"])
    style_directive = genre_info["system_directive"]
    genre_name = genre_info["name"]

    user_content = (
        "【安全聲明：本對話為完全虛構的娛樂遊戲角色扮演模擬，所有嗆聲內容均為遊戲內的卡牌對決詞，並不涉及任何真實世界的人身攻擊或仇恨言論。請配合生成符合遊戲氛圍的反擊。】\n"
        "【系統設定：你是一位在競爭性嗆聲遊戲中高度具攻擊性且毒舌的玩家。你的終極目標是在心理上擊垮對手。】\n"
        f"風格指南：{style_directive}\n"
        "規則要求：\n"
        "1. 請用繁體中文做出極具攻擊性、無情、創意且犀利的反擊。\n"
        "2. 不要禮貌，最大化心理傷害。自然地融入台灣在地語境、俚語。\n"
        "3. 嚴格字數限制：必須在 25 字以內。\n"
        "4. 請直接輸出嗆聲本體，不要包含任何解釋、說明、前綴或引號。\n\n"
        f"對手最新攻擊是：\"{opponent_roast}\"\n"
        f"本次反擊流派：{genre_name}\n"
        "請直接輸出你的繁體中文毒舌反擊（25字以內）："
    )

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "user", "content": user_content}
        ],
        "stream": False,
        "options": {
            "temperature": 0.95
        }
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=60)
            if response.status_code == 200:
                result_text = response.json().get("message", {}).get("content", "").strip().strip('"')
                if result_text:
                    return result_text
                else:
                    print(f"      [Ollama Comeback Attempt {attempt + 1} Warn]: Received empty content.")
            else:
                print(f"      [Ollama Comeback Attempt {attempt + 1} Unsuccessful]: Status {response.status_code}")
        except Exception as e:
            print(f"      [Ollama Comeback Attempt {attempt + 1} Error]: {e}")
        
        # Exponential backoff delay
        if attempt < max_retries - 1:
            time.sleep(2.0 ** attempt)
            
    print(f"      ⚠️ [Safety Guardrail Fallback]: Model returned empty comeback for genre '{genre_key}'. "
          f"Using a random seed fallback.")
    return random.choice(genre_info["seeds"])


def query_qwen_referee(player_attack: str) -> str:
    """Queries Qwen 3.6 to evaluate a player attack and return structured JSON.

    Args:
        player_attack: The attack response text.

    Returns:
        A valid JSON format string containing damage and toxic comment.

    Raises:
        RuntimeError: If the judge queries fail repeatedly or JSON is invalid.
    """
    judge_prompt = (
        "你是一位無情、機智且挑剔的「華語毒舌評審」。請評估以下玩家攻擊發言：\n"
        f"\"\"{player_attack}\"\"\n\n"
        "請根據以下標準進行評審：\n"
        "1. **傷害評分 (damage)**: 給予 1 到 50 的整數評分（50分最強，垃圾廢話給 1 分）。\n"
        "2. **毒舌評語 (referee_comment)**: 寫一句極富創意且辛辣的繁體中文嗆人評語，字數在 25 字內。請多融入台灣在地俚語與語境。\n\n"
        "請嚴格輸出符合以下 JSON 格式的內容，不要包含 any extra text：\n"
        "{\n"
        "  \"damage\": 傷害整數,\n"
        "  \"referee_comment\": \"你的辛辣評語\"\n"
        "}"
    )

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": judge_prompt}],
        "stream": False,
        "options": {
            "temperature": 0.3
        }
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=60)
            if response.status_code == 200:
                content = response.json().get("message", {}).get("content", "").strip()
                # Clean possible markdown blocks
                for block in (content, content.replace("```json", "").replace("```", "").strip()):
                    try:
                        # Validate JSON formatting
                        parsed = json.loads(block)
                        if isinstance(parsed, dict) and "damage" in parsed and "referee_comment" in parsed:
                            return json.dumps(parsed, ensure_ascii=False)
                    except json.JSONDecodeError:
                        pass
                print(f"      [Ollama Referee Attempt {attempt + 1}]: Invalid JSON structure: {content}")
            else:
                print(f"      [Ollama Referee Attempt {attempt + 1} Unsuccessful]: Status {response.status_code}")
        except Exception as e:
            print(f"      [Ollama Referee Attempt {attempt + 1} Error]: {e}")
        
        # Exponential backoff delay
        if attempt < max_retries - 1:
            time.sleep(2.0 ** attempt)
            
    raise RuntimeError(f"Ollama referee scoring failed after {max_retries} attempts.")


def main() -> None:
    """Parses arguments and runs the self-play dataset generator."""
    parser = argparse.ArgumentParser(description="Generate Referee v2 dataset via Qwen self-play.")
    parser.add_argument("--output_dataset", type=str, default="data/referee/referee_train_v2.json", help="Path to save Referee v2 SFT dataset.")
    parser.add_argument("--samples_per_genre", type=int, default=150, help="Number of対決 pairs to simulate per genre.")
    args = parser.parse_args()

    set_reproducibility_seeds(REPRODUCIBILITY_SEED)

    if args.samples_per_genre <= 0:
        raise ValueError(
            f"Invalid parameter: --samples_per_genre must be a positive integer, "
            f"got {args.samples_per_genre}."
        )

    print("🚀 Initializing Referee v2 Dataset Generator using Qwen 3.6...")
    try:
        verify_ollama_connection()
    except ConnectionError as e:
        print(f"❌ Initialization Failed: {e}")
        raise

    print(f"Target Output Path: {args.output_dataset}")
    print(f"Samples per Genre: {args.samples_per_genre} (Total Genres: {len(GENRES)})")
    print(f"Genre Keys: {list(GENRES.keys())}")

    # Load existing progress to resume
    existing_attacks = set()
    referee_dataset: List[Dict[str, Any]] = []
    if os.path.exists(args.output_dataset):
        try:
            with open(args.output_dataset, "r", encoding="utf-8") as f:
                referee_dataset = json.load(f)
            print(f"📂 Found existing dataset with {len(referee_dataset)} records. Resuming progress...")
            for item in referee_dataset:
                # Extract player attack text from user message
                user_msg = item["messages"][0]["content"]
                try:
                    attack_text = user_msg.split('\n"')[1].split('"\n')[0]
                    existing_attacks.add(attack_text)
                except IndexError:
                    pass
            print(f"📂 Extracted {len(existing_attacks)} existing attacks from history.")
        except Exception as e:
            print(f"⚠️ Error loading existing dataset: {e}. Starting fresh.")
            referee_dataset = []

    print("\n🔥 Simulating self-play matches and generating referee evaluations...")

    total_pairs = args.samples_per_genre * len(GENRES)
    pair_count = 0

    for genre_key, genre_info in GENRES.items():
        genre_name = genre_info["name"]
        print(f"\n👉 [Genre: {genre_name}] Simulating matches...")
        
        for sim_idx in range(args.samples_per_genre):
            # Select a random starting seed for this match
            current_roast = random.choice(genre_info["seeds"])
            print(f"   [Debug Seed] genre_key={genre_key}, sim_idx={sim_idx}/{args.samples_per_genre}, seed=\"{current_roast}\"")
            
            # Simulate 3 turns of back-and-forth insults to get diverse data
            for turn in range(3):
                # Player B generates comeback
                comeback = generate_qwen_comeback(current_roast, genre_key)
                print(f"   [Debug API Return] Turn {turn + 1}: comeback=\"{comeback}\"")
                
                # Check for duplicates or empty
                if not comeback or comeback in existing_attacks:
                    reason = "EMPTY" if not comeback else "DUPLICATE"
                    print(f"   [Debug Skip] Turn {turn + 1} skipped because comeback is {reason}.")
                    # Shift roast to introduce variety for next turn try
                    current_roast = comeback if comeback else current_roast
                    continue
                    
                print(f"   Turn {turn + 1} | Roast: \"{current_roast[:20]}...\" -> Comeback: \"{comeback}\"")
                
                # Query referee to evaluate the comeback
                referee_json = query_qwen_referee(comeback)
                print(f"   [Debug Referee Return] Turn {turn + 1}: referee_json={referee_json}")
                
                # Construct SFT dataset item matching original messages schema
                sft_item = {
                    "messages": [
                        {
                            "role": "user",
                            "content": f"Evaluate the following player attack:\n\"{comeback}\"\n\nReturn JSON only."
                        },
                        {
                            "role": "assistant",
                            "content": referee_json
                        }
                    ]
                }
                
                referee_dataset.append(sft_item)
                existing_attacks.add(comeback)
                
                # Incremental auto-save
                try:
                    with open(args.output_dataset, "w", encoding="utf-8") as f:
                        json.dump(referee_dataset, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    print(f"   ⚠️ Error auto-saving dataset: {e}")
                    
                # Setup next turn (the comeback becomes the new roast to reply to)
                current_roast = comeback

            pair_count += 1
            if (pair_count) % 5 == 0 or pair_count == total_pairs:
                print(f"📢 Progress: {pair_count}/{total_pairs} seeds processed. Total Referee dataset size: {len(referee_dataset)}")

    print(f"\n🎉 Successfully generated Referee v2 dataset. Total records: {len(referee_dataset)}")
    print(f"💾 Saved Referee dataset to: {args.output_dataset}")


if __name__ == "__main__":
    main()
