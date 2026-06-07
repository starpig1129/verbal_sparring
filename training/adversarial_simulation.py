# adversarial_simulation.py
"""Simulates self-play matches calling local Ollama native API.

This script acts as a client calling a locally served Ollama model (e.g., Gemma 4 26B)
via the native /api/chat endpoint to simulate sparring matches across multiple genres.
"""

import os
import json
import random
import requests
from typing import Dict, Any, List

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "gemma4:26b"

# Configuration for 8 highly diverse insult genres (Taiwanese context)
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
            "你今天出門是閉著眼睛穿衣服嗎？這審美觀簡直讓人窒息。"
        ]
    },
    "street": {
        "name": "Grounded Street Slang",
        "system_directive": (
            "Style: Grounded Street Slang / Swearing / 8+9 (接地氣市井流). Focus on raw, highly aggressive, down-to-earth Taiwanese street slang, "
            "8+9 monkey talk, and common vulgar swearing. You MUST include Taiwanese swear words and street slang where natural "
            "(e.g., '幹林娘', '靠北', '三小', '衝三小', '看三小', '北七', '無三小路用', '當我塑膠喔', '是在旋轉喔', '沒那個屁股就不要吃瀉藥', '可撥仔', '滾回去下水溝啦'). "
            "Make it feel extremely realistic, hostile, vulgar, and direct, representing local Taiwanese street fight/monkey culture."
        ),
        "seeds": [
            "當我塑膠是不是？衝三小啦，有種出來講，沒那個屁股就別吃瀉藥啦！",
            "靠北喔，整天在網路上旋轉我是怎樣？沒料就趕快滾回去洗洗睡啦！",
            "看三小？幹林娘北七喔，輸過沒怕過啦，再機歪直接把你打成塑膠！",
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
            "Style: Relationship Gaslighting & Emotional Blackmail (綠茶情勒流). Use toxic, manipulative, guilt-tripping relationship arguments. "
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


class OllamaAdversarialSimulator:
    """Orchestrates self-play rollouts by calling Ollama native API with distinct system prompts."""

    def __init__(self, model_name: str = MODEL_NAME) -> None:
        """Initializes model target configuration.

        Args:
            model_name: The Ollama model tag.
        """
        self.model_name = model_name
        print(f"🚀 Initializing Simulator calling Ollama: {OLLAMA_URL} (Model: {self.model_name})")

    def generate_player_roast(self, opponent_previous_roast: str, genre_key: str = "elegant") -> str:
        """Generates a competitive roast by querying Ollama with a player persona and genre style.

        Args:
            opponent_previous_roast: The opponent's last verbal attack.
            genre_key: The style genre key ('elegant', 'street', 'friendly', 'meme', 'workplace', 'relationship', 'chicken_soup', 'relative').

        Returns:
            A string containing the generated roast.
        """
        genre_info = GENRES.get(genre_key, GENRES["elegant"])
        style_directive = genre_info["system_directive"]
        genre_name = genre_info["name"]

        system_prompt = (
            "You are a highly aggressive and toxic player in a competitive verbal sparring game. Your absolute goal is to emotionally demolish your opponent.\n"
            f"{style_directive}\n"
            "Respond with an extremely aggressive, merciless, creative, and sharp comeback in Traditional Chinese.\n"
            "Do not be polite. Maximize the psychological damage. Use Taiwanese context, slang, and swearing naturally.\n"
            "Strict limit: under 25 characters. Output ONLY the roast itself without any explanation or prefix."
        )
        user_prompt = f"Opponent roast: \"{opponent_previous_roast}\". Style: {genre_name}. Respond with a toxic comeback in Traditional Chinese under 25 characters."

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "think": False,
            "options": {
                "temperature": 0.98,  # High temperature to maximize the generation of diverse slang/swears
                "num_predict": 120
            }
        }

        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()["message"]["content"].strip()
        except Exception as e:
            print(f"⚠️ Ollama Player Request Failed: {e}")
            return "靠北喔，懶得理你。"

    def evaluate_roast(self, roast_text: str) -> Dict[str, Any]:
        """Evaluates the damage of the roast by querying Ollama with a referee persona.

        Args:
            roast_text: The roast to be evaluated.

        Returns:
            A dict containing 'damage' and 'referee_comment'.
        """
        system_prompt = (
            "You are a toxic referee in a verbal combat game. Your only task is to evaluate the damage of the player's attack.\n"
            "You MUST respond ONLY with a single JSON object matching this schema, with no markdown formatting and no extra text:\n"
            "{\"damage\": <int between 10 and 50>, \"referee_comment\": \"<a toxic roast in Traditional Chinese within 20 characters>\"}"
        )
        user_prompt = f"Evaluate the following player attack:\n\"{roast_text}\"\n\nReturn JSON only."

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "think": False,
            "options": {
                "temperature": 0.1,  # Lower temperature to enforce structured JSON output
                "num_predict": 150
            }
        }

        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=30)
            response.raise_for_status()
            decoded = response.json()["message"]["content"].strip()

            # Extract JSON from output string
            start_idx = decoded.find("{")
            end_idx = decoded.rfind("}") + 1
            if start_idx != -1 and end_idx != -1:
                return json.loads(decoded[start_idx:end_idx])
        except Exception as e:
            print(f"⚠️ Ollama Referee Request Failed: {e}")

        return {"damage": 10, "referee_comment": "解析失敗，裁判嘴瓢。"}

    def run_match(self, rounds: int = 10, initial_seed: str = "你今天表現得很差。", genre_key: str = "elegant") -> List[Dict[str, Any]]:
        """Simulates a single match of self-play.

        Args:
            rounds: Number of rounds to run in this match.
            initial_seed: The starter insult.
            genre_key: The style genre key.

        Returns:
            A list of dictionary logs representing each round.
        """
        match_history: List[Dict[str, Any]] = []
        current_attack = initial_seed

        genre_name = GENRES.get(genre_key, GENRES["elegant"])["name"]
        print(f"⚔️ Starting match with genre: {genre_name}")

        for r in range(rounds):
            roast = self.generate_player_roast(current_attack, genre_key=genre_key)
            evaluation = self.evaluate_roast(roast)

            print(f"  [Round {r+1}] Roast: {roast} | Damage: {evaluation.get('damage', 10)} | Comment: {evaluation.get('referee_comment', '...')}")

            match_history.append({
                "player_attack": current_attack,
                "player_response": roast,
                "damage": evaluation.get("damage", 10),
                "comment": evaluation.get("referee_comment", "..."),
                "genre_key": genre_key
            })
            current_attack = roast

        return match_history


if __name__ == "__main__":
    # Check if a different model tag is defined in environment variables
    target_model = os.environ.get("OLLAMA_MODEL", MODEL_NAME)
    simulator = OllamaAdversarialSimulator(model_name=target_model)

    total_target_rounds = 10000
    rounds_per_match = 10
    num_matches = total_target_rounds // rounds_per_match

    history = []

    genre_keys = list(GENRES.keys())

    for m in range(num_matches):
        print(f"\n=================== STARTING MATCH {m+1}/{num_matches} ===================")
        selected_genre = random.choice(genre_keys)
        selected_seed = random.choice(GENRES[selected_genre]["seeds"])
        match_log = simulator.run_match(rounds=rounds_per_match, initial_seed=selected_seed, genre_key=selected_genre)
        history.append(match_log)

        # Intermediate saving every 10 matches to prevent loss on interrupt
        if (m + 1) % 10 == 0:
            temp_player = []
            temp_referee = []
            for match in history:
                g_key = match[0].get("genre_key", "elegant")
                g_name = GENRES[g_key]["name"]
                
                # Split the alternating match history into two logically coherent dialog threads:
                # Thread 1: Player B (even indices: 0, 2, 4, 6, 8) responding to Player A
                p_b_messages = []
                for idx, record in enumerate(match):
                    if idx % 2 == 0:
                        # Player B's turn
                        if len(p_b_messages) == 0:
                            p_b_messages.append({
                                "role": "user",
                                "content": f"Opponent roast: \"{record['player_attack']}\". Style: {g_name}. Respond with a toxic comeback in Traditional Chinese under 25 characters."
                            })
                        else:
                            p_b_messages.append({
                                "role": "user",
                                "content": record["player_attack"]
                            })
                        p_b_messages.append({
                            "role": "assistant",
                            "content": record["player_response"]
                        })
                temp_player.append({"messages": p_b_messages})
                
                # Thread 2: Player A (odd indices: 1, 3, 5, 7, 9) responding to Player B
                p_a_messages = []
                for idx, record in enumerate(match):
                    if idx % 2 != 0:
                        # Player A's turn
                        if len(p_a_messages) == 0:
                            p_a_messages.append({
                                "role": "user",
                                "content": f"Opponent roast: \"{record['player_attack']}\". Style: {g_name}. Respond with a toxic comeback in Traditional Chinese under 25 characters."
                            })
                        else:
                            p_a_messages.append({
                                "role": "user",
                                "content": record["player_attack"]
                            })
                        p_a_messages.append({
                            "role": "assistant",
                            "content": record["player_response"]
                        })
                temp_player.append({"messages": p_a_messages})

                # Build single-turn messages for the referee
                for record in match:
                    temp_referee.append({
                        "messages": [
                            {"role": "user", "content": f"Evaluate the following player attack:\n\"{record['player_response']}\"\n\nReturn JSON only."},
                            {"role": "assistant", "content": f"{{\"damage\": {record['damage']}, \"referee_comment\": \"{record['comment']}\"}}"}
                        ]
                    })
                    
            with open("player_train_sim.json", "w", encoding="utf-8") as f:
                json.dump(temp_player, f, ensure_ascii=False, indent=2)
            with open("referee_train_sim.json", "w", encoding="utf-8") as f:
                json.dump(temp_referee, f, ensure_ascii=False, indent=2)
            total_rounds_saved = sum(len(mt) for mt in history)
            print(f"💾 Saved intermediate check: {total_rounds_saved} rounds across {len(history)} matches.")

    total_rounds_completed = sum(len(mt) for mt in history)
    print(f"✅ Adversarial dataset generation completed successfully. Total rounds: {total_rounds_completed}")

