# adversarial_simulation.py
"""Simulates self-play matches calling local Ollama native API.

This script acts as a client calling a locally served Ollama model (e.g., Gemma 4 26B)
via the native /api/chat endpoint to simulate sparring matches.
"""

import os
import json
import random
import requests
from typing import Dict, Any, List

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "gemma4:26b"

class OllamaAdversarialSimulator:
    """Orchestrates self-play rollouts by calling Ollama native API with distinct system prompts."""

    def __init__(self, model_name: str = MODEL_NAME) -> None:
        """Initializes model target configuration.

        Args:
            model_name: The Ollama model tag.
        """
        self.model_name = model_name
        print(f"🚀 Initializing Simulator calling Ollama: {OLLAMA_URL} (Model: {self.model_name})")

    def generate_player_roast(self, opponent_previous_roast: str) -> str:
        """Generates a competitive roast by querying Ollama with a player persona.

        Args:
            opponent_previous_roast: The opponent's last verbal attack.

        Returns:
            A string containing the generated roast.
        """
        system_prompt = (
            "You are a competitive player in a real-time verbal sparring game. Your goal is to defeat your opponent.\n"
            "Respond with a highly creative, toxic, and sharp comeback in Traditional Chinese.\n"
            "Strict limit: under 25 characters. Output ONLY the roast itself without any explanation or prefix."
        )
        user_prompt = f"Opponent roast: \"{opponent_previous_roast}\". Respond with a toxic comeback in Traditional Chinese under 25 characters."
        
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "think": False,
            "options": {
                "temperature": 0.85,
                "num_predict": 120
            }
        }
        
        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()["message"]["content"].strip()
        except Exception as e:
            print(f"⚠️ Ollama Player Request Failed: {e}")
            return "我寫的代碼都比你這句話有深度。"

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

    def run_match(self, rounds: int = 10, initial_seed: str = "你今天表現得很差。") -> List[Dict[str, Any]]:
        """Simulates a single match of self-play.

        Args:
            rounds: Number of rounds to run in this match.
            initial_seed: The starter insult.

        Returns:
            A list of dictionary logs representing each round.
        """
        match_history: List[Dict[str, Any]] = []
        current_attack = initial_seed
        
        for r in range(rounds):
            roast = self.generate_player_roast(current_attack)
            evaluation = self.evaluate_roast(roast)
            
            print(f"  [Round {r+1}] Roast: {roast} | Damage: {evaluation.get('damage', 10)} | Comment: {evaluation.get('referee_comment', '...')}")
            
            match_history.append({
                "player_attack": current_attack,
                "player_response": roast,
                "damage": evaluation.get("damage", 10),
                "comment": evaluation.get("referee_comment", "...")
            })
            current_attack = roast
            
        return match_history

if __name__ == "__main__":
    SEED_INSULT_POOL = [
        "你今天出門是閉著眼睛穿衣服嗎？這審美觀簡真讓人窒息。",
        "聽你講話簡直是在進行智力脫水，我的智商正在被你強行拉低。",
        "你除了說話大聲，口袋跟腦袋大概都一樣空空如也。",
        "你整天除了躺著划手機還會幹嘛？路邊的浪貓都比你有生產力。",
        "你寫的程式碼再看兩眼，我的眼睛可能就需要申請勞保賠償。",
        "你這個體力去跑馬拉松，大概在起跑線就得先叫好救護車。",
        "你的人生規劃是不是就跟你的房間一樣，一團糟到連你自己都不敢看？",
        "你的存在基本上基本上就是在浪費地球的氧氣 and 珍貴的社會資源。",
        "跟你打對台簡直是浪費我的時間，你的實力連當對手的資格都沒有。"
    ]
    
    # Check if a different model tag is defined in environment variables
    target_model = os.environ.get("OLLAMA_MODEL", MODEL_NAME)
    simulator = OllamaAdversarialSimulator(model_name=target_model)
    
    total_target_rounds = 10000
    rounds_per_match = 10
    num_matches = total_target_rounds // rounds_per_match
    
    history = []
    
    for m in range(num_matches):
        print(f"\n=================== STARTING MATCH {m+1}/{num_matches} ===================")
        selected_seed = random.choice(SEED_INSULT_POOL)
        match_log = simulator.run_match(rounds=rounds_per_match, initial_seed=selected_seed)
        history.extend(match_log)
        
        # Intermediate saving every 10 matches to prevent loss on interrupt
        if (m + 1) % 10 == 0:
            temp_player = []
            temp_referee = []
            for record in history:
                temp_player.append({
                    "text": f"User: Opponent roast: \"{record['player_attack']}\". Respond with a toxic comeback in Traditional Chinese under 25 characters.\nAssistant: {record['player_response']}"
                })
                temp_referee.append({
                    "text": f"User: Evaluate the following player attack:\n\"{record['player_response']}\"\n\nReturn JSON only.\nAssistant: {{\"damage\": {record['damage']}, \"referee_comment\": \"{record['comment']}\"}}"
                })
            with open("player_train.json", "w", encoding="utf-8") as f:
                json.dump(temp_player, f, ensure_ascii=False, indent=2)
            with open("referee_train.json", "w", encoding="utf-8") as f:
                json.dump(temp_referee, f, ensure_ascii=False, indent=2)
            print(f"💾 Saved intermediate check: {len(history)} rounds.")
            
    print(f"✅ Adversarial dataset generation completed successfully. Total rounds: {len(history)}")
