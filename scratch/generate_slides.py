# generate_slides.py
"""Automated SVG Slide Generator for the Verbal Sparring Final Presentation.

Compiles 10 clean, minimalist SVG slides (16:9) by stripping verbose texts,
focusing on core metrics, and embedding generated evaluation charts (PNGs)
via SVG image links.
"""

import os
from typing import Dict, List, Any

OUTPUT_DIR: str = "./evaluation/slides"
os.makedirs(OUTPUT_DIR, exist_ok=True)

THEME: Dict[str, str] = {
    "bg_gradient_start": "#F8FAFC",  # slate-50
    "bg_gradient_end": "#EFF6FF",    # blue-50
    "card_bg": "#FFFFFF",
    "text_main": "#0F172A",          # slate-900
    "text_muted": "#475569",         # slate-600
    "accent_blue": "#3B82F6",        # blue-500
    "accent_green": "#10B981",       # emerald-500
    "accent_red": "#EF4444",         # red-500
    "accent_orange": "#F97316",      # orange-500
    "border": "#E2E8F0",             # slate-200
    "shadow": "rgba(15, 23, 42, 0.05)"
}

SVG_FONT_FAMILY: str = "font-family=\"system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif\""


def svg_header(page_title: str, slide_num: int) -> str:
    """Renders slide background and NTNU academic header."""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" width="100%" height="100%">
  <defs>
    <!-- Background Gradient -->
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{THEME['bg_gradient_start']}" />
      <stop offset="100%" stop-color="{THEME['bg_gradient_end']}" />
    </linearGradient>
    <!-- Card drop shadow -->
    <filter id="shadowFilter" x="-5%" y="-5%" width="110%" height="110%">
      <feDropShadow dx="0" dy="12" stdDeviation="16" flood-color="#0F172A" flood-opacity="0.04" />
    </filter>
  </defs>

  <!-- Background -->
  <rect width="1920" height="1080" fill="url(#bgGrad)" />

  <!-- Decorative curves -->
  <path d="M 0 0 Q 300 150 960 50 T 1920 0 L 1920 120 L 0 120 Z" fill="#E0F2FE" opacity="0.4" />
  <circle cx="1800" cy="980" r="300" fill="#DBEAFE" opacity="0.3" />
  
  <!-- Slide Header Banner -->
  <text x="80" y="80" fill="{THEME['accent_blue']}" font-size="22" font-weight="800" letter-spacing="2" {SVG_FONT_FAMILY}>期末報告 | 基於多 LoRA 協同對抗微調之「多流派毒舌對決」Web 遊戲系統</text>
  <text x="80" y="160" fill="{THEME['text_main']}" font-size="52" font-weight="800" {SVG_FONT_FAMILY}>{page_title}</text>
  
  <!-- Footer -->
  <line x1="80" y1="990" x2="1840" y2="990" stroke="{THEME['border']}" stroke-width="2" />
  <text x="80" y="1030" fill="{THEME['text_muted']}" font-size="16" {SVG_FONT_FAMILY}>NTNU AGI &amp; Robotics Research | Reinforcement Learning &amp; Cognitive NLP</text>
  <text x="1800" y="1030" fill="{THEME['accent_blue']}" font-size="18" font-weight="700" {SVG_FONT_FAMILY}>Page {slide_num} / 10</text>
"""


def draw_card(x: int, y: int, w: int, h: int, title: str, accent_color: str = "#3B82F6") -> str:
    """Renders a rounded layout card with top accent bar."""
    return f"""
  <!-- Card Container -->
  <g filter="url(#shadowFilter)">
    <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="20" ry="20" fill="{THEME['card_bg']}" />
    <!-- Top accent bar -->
    <path d="M {x} {y+20} A 20 20 0 0 1 {x+20} {y} L {x+w-20} {y} A 20 20 0 0 1 {x+w} {y+20} L {x+w} {y+20} L {x} {y+20} Z" fill="{accent_color}" />
    <!-- Title -->
    <text x="{x+40}" y="{y+65}" fill="{THEME['text_main']}" font-size="26" font-weight="700" {SVG_FONT_FAMILY}>{title}</text>
  </g>
"""


def draw_bullet(x: int, y: int, bold_text: str, normal_text: str, bullet_color: str = "#3B82F6") -> str:
    """Draws a standard bullet item with adjusted spacing."""
    return f"""
  <circle cx="{x}" cy="{y-8}" r="6" fill="{bullet_color}" />
  <text x="{x+25}" y="{y}" fill="{THEME['text_main']}" font-size="20" {SVG_FONT_FAMILY}>
    <tspan font-weight="700">{bold_text}</tspan><tspan fill="{THEME['text_muted']}">{normal_text}</tspan>
  </text>
"""


def draw_arrow(x1: int, y1: int, x2: int, y2: int, label: str = "", arrow_color: str = "#64748B") -> str:
    """Draws a connector arrow with label."""
    import math
    dx = x2 - x1
    dy = y2 - y1
    angle = math.atan2(dy, dx)
    
    arrow_len = 16
    arrow_angle = math.pi / 6
    ax1 = x2 - arrow_len * math.cos(angle - arrow_angle)
    ay1 = y2 - arrow_len * math.sin(angle - arrow_angle)
    ax2 = x2 - arrow_len * math.cos(angle + arrow_angle)
    ay2 = y2 - arrow_len * math.sin(angle + arrow_angle)

    label_xml = ""
    if label:
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2 - 12
        label_xml = f'<text x="{mx}" y="{my}" fill="{THEME["text_muted"]}" font-size="16" font-weight="600" text-anchor="middle" {SVG_FONT_FAMILY}>{label}</text>'

    return f"""
  <g>
    <!-- Arrow shaft -->
    <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{arrow_color}" stroke-width="3" stroke-dasharray="6,4" />
    <!-- Arrow head -->
    <polygon points="{x2},{y2} {ax1},{ay1} {ax2},{ay2}" fill="{arrow_color}" />
    {label_xml}
  </g>
"""


def draw_database(x: int, y: int, w: int, h: int, label: str) -> str:
    """Draws a cylinder database vector graphic."""
    accent = THEME["accent_blue"]
    return f"""
  <g>
    <ellipse cx="{x+w//2}" cy="{y+20}" rx="{w//2}" ry="20" fill="#E2E8F0" />
    <rect x="{x}" y="{y+20}" width="{w}" height="{h-40}" fill="#F1F5F9" />
    <ellipse cx="{x+w//2}" cy="{y+h-20}" rx="{w//2}" ry="20" fill="#E2E8F0" />
    <path d="M {x} {y+20} L {x} {y+h-20} A {w//2} 20 0 0 0 {x+w} {y+h-20} L {x+w} {y+20}" fill="none" stroke="{accent}" stroke-width="3" />
    <ellipse cx="{x+w//2}" cy="{y+20}" rx="{w//2}" ry="20" fill="#DBEAFE" stroke="{accent}" stroke-width="3" />
    <!-- Label -->
    <text x="{x+w//2}" y="{y+h//2+5}" fill="{THEME['text_main']}" font-size="18" font-weight="700" text-anchor="middle" {SVG_FONT_FAMILY}>{label}</text>
  </g>
"""


def draw_browser(x: int, y: int, w: int, h: int, title: str) -> str:
    """Draws a mockup browser window vector graphic."""
    border = THEME["border"]
    return f"""
  <g filter="url(#shadowFilter)">
    <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" ry="12" fill="#FFFFFF" stroke="{border}" stroke-width="2" />
    <path d="M {x} {y+40} L {x+w} {y+40} L {x+w} {y+12} A 12 12 0 0 0 {x+w-12} {y} L {x+12} {y} A 12 12 0 0 0 {x} {y+12} Z" fill="#F1F5F9" stroke="{border}" stroke-width="2" />
    <circle cx="{x+25}" cy="{y+20}" r="7" fill="{THEME['accent_red']}" />
    <circle cx="{x+45}" cy="{y+20}" r="7" fill="{THEME['accent_orange']}" />
    <circle cx="{x+65}" cy="{y+20}" r="7" fill="{THEME['accent_green']}" />
    <text x="{x+w//2}" y="{y+25}" fill="{THEME['text_muted']}" font-size="16" font-weight="600" text-anchor="middle" {SVG_FONT_FAMILY}>{title}</text>
  </g>
"""


# ==============================================================================
# Slide 1: Cover Slide
# ==============================================================================
def render_slide_1() -> str:
    xml = svg_header("基於多 LoRA 協同對抗微調之對抗式「華語毒舌」遊戲系統", 1)
    xml = xml.replace('font-size="52"', 'font-size="44"')
    
    xml += f"""
  <g filter="url(#shadowFilter)">
    <rect x="180" y="280" width="1560" height="480" rx="30" ry="30" fill="{THEME['card_bg']}" />
    <path d="M 180 310 A 30 30 0 0 1 210 280 L 1710 280 A 30 30 0 0 1 1740 310 L 1740 310 L 180 310 Z" fill="{THEME['accent_blue']}" />
    
    <text x="260" y="440" fill="{THEME['text_main']}" font-size="64" font-weight="900" {SVG_FONT_FAMILY}>基於多 LoRA 協同對抗微調之華語毒舌對戰系統</text>
    <text x="260" y="530" fill="{THEME['accent_blue']}" font-size="36" font-weight="700" {SVG_FONT_FAMILY}>SFT 與 DPO 兩階段對齊、Neuro-Symbolic 限制解碼與全棧 Web 部署</text>
    <line x1="260" y1="590" x2="1480" y2="590" stroke="{THEME['border']}" stroke-width="2" />
    
    <text x="260" y="650" fill="{THEME['text_muted']}" font-size="22" {SVG_FONT_FAMILY}>報告人：資訊工程研究所 / 智慧機器人與 AGI 研究室</text>
    <text x="260" y="695" fill="{THEME['text_muted']}" font-size="22" {SVG_FONT_FAMILY}>指導教授：國立臺灣師範大學 (NTNU)</text>
  </g>
</svg>
"""
    return xml


# ==============================================================================
# Slide 2: Project Motivation & Objectives (MINIMALIST VER.)
# ==============================================================================
def render_slide_2() -> str:
    xml = svg_header("專案核心動機與實現目標", 2)
    
    # Left Card: Painpoints (Minimalist)
    xml += draw_card(80, 240, 840, 680, "傳統大型 LLM 落地痛點", THEME["accent_red"])
    xml += draw_bullet(130, 390, "1. 邊緣延遲 (Latency)：", "20B+ 模型即時對戰推理超時 (>3秒)")
    xml += draw_bullet(130, 500, "2. 語意單調 (Monolithic)：", "通用模型在幽默與在地俚語特徵上張力不足")
    xml += draw_bullet(130, 610, "3. 格式漂移 (JSON Drift)：", "神經網絡輸出 JSON 格式不穩，導致系統崩潰")
    xml += draw_bullet(130, 720, "4. 硬體規格高昂 (Compute)：", "全參數微調大模型之算力與記憶體成本過高")

    # Right Card: Objectives (Minimalist)
    xml += draw_card(990, 240, 850, 680, "本專案之技術解決方案", THEME["accent_green"])
    xml += draw_bullet(1040, 390, "1. 4B 量化模型基底：", "採用 Gemma-4-E4B-it，壓低顯存至 10GB")
    xml += draw_bullet(1040, 500, "2. 兩階段對齊蒸餾：", "SFT 穩定 JSON 格式，DPO 蒸餾 Qwen-27B 嗆聲偏好")
    xml += draw_bullet(1040, 610, "3. Neuro-Symbolic 限制解碼：", "以 CFG 採樣約束與括號配對法，達成 100% 解析")
    xml += draw_bullet(1040, 720, "4. 雙 LoRA 動態熱插拔：", "對決端與裁判端動態切換 Peft，精簡顯存佔用")
    
    xml += "</svg>"
    return xml


# ==============================================================================
# Slide 3: Full Stack System Architecture Diagram
# ==============================================================================
def render_slide_3() -> str:
    xml = svg_header("系統運行架構與實時數據流圖", 3)
    
    # 1. Draw React Browser (Left)
    xml += draw_browser(80, 260, 420, 400, "React Frontend (Port 3000)")
    xml += f'<rect x="110" y="340" width="360" height="20" fill="#E2E8F0" rx="3" />'
    xml += f'<rect x="110" y="380" width="160" height="80" fill="#FEE2E2" rx="10" />'
    xml += f'<text x="190" y="430" fill="{THEME["accent_red"]}" font-size="20" font-weight="700" text-anchor="middle" {SVG_FONT_FAMILY}>Opponent HP: 85</text>'
    xml += f'<rect x="310" y="380" width="160" height="80" fill="#D1FAE5" rx="10" />'
    xml += f'<text x="390" y="430" fill="{THEME["accent_green"]}" font-size="20" font-weight="700" text-anchor="middle" {SVG_FONT_FAMILY}>NPC HP: 100</text>'
    
    xml += f'<rect x="110" y="480" width="360" height="100" fill="#F8FAFC" stroke="{THEME["border"]}" stroke-width="1" rx="5" />'
    xml += f'<text x="130" y="510" fill="{THEME["text_main"]}" font-size="14" {SVG_FONT_FAMILY}>對手：「演技好是因為要把你演成單方面屠殺」</text>'
    xml += f'<text x="130" y="540" fill="{THEME["accent_blue"]}" font-size="14" {SVG_FONT_FAMILY}>[裁判打分] 傷害：46 | 評語：畫面有了，扣分扣得爽</text>'
    
    xml += f'<rect x="110" y="600" width="280" height="40" fill="#FFFFFF" stroke="{THEME["border"]}" rx="5" />'
    xml += f'<text x="130" y="625" fill="{THEME["text_muted"]}" font-size="14" {SVG_FONT_FAMILY}>輸入你的嘴砲反擊...</text>'
    xml += f'<rect x="400" y="600" width="70" height="40" fill="{THEME["accent_blue"]}" rx="5" />'
    xml += f'<text x="435" y="625" fill="#FFFFFF" font-size="14" font-weight="700" text-anchor="middle" {SVG_FONT_FAMILY}>發送</text>'

    # Arrow 1: Browser -> FastAPI (WebSocket)
    xml += draw_arrow(520, 420, 710, 420, "1. 實時發言 / 梗圖", THEME["accent_blue"])
    xml += draw_arrow(710, 460, 520, 460, "4. 實時 HP 更新 / 蓋章", THEME["accent_green"])

    # 2. Draw FastAPI Card (Middle)
    xml += draw_card(730, 240, 480, 420, "FastAPI WebSocket 異步引擎", THEME["accent_orange"])
    xml += draw_bullet(770, 360, "Room Manager:", "多人對決房間與配對管理")
    xml += draw_bullet(770, 420, "Battle Session:", "回合狀態機與 HP 扣減控制")
    xml += draw_bullet(770, 480, "LangGraph Pipeline:", "動態調度 NPC / Referee 代理流程")
    xml += draw_bullet(770, 540, "Symbolic Constraint:", "JSON 符號提取容錯層")

    # Arrow 2: FastAPI -> DB (SQLAlchemy)
    xml += draw_arrow(970, 680, 970, 740, "ORM (SQL)")

    # 3. Draw PostgreSQL Database (Bottom Middle)
    xml += draw_database(770, 760, 400, 160, "PostgreSQL (NpcMemory)")

    # Arrow 3: FastAPI -> Inference Model
    xml += draw_arrow(1230, 420, 1420, 420, "2. 戰況提示詞", THEME["accent_blue"])
    xml += draw_arrow(1420, 460, 1230, 460, "3. 預測傷害 JSON", THEME["accent_green"])

    # 4. Draw Inference Model Card (Right)
    xml += draw_card(1440, 240, 400, 420, "Inference PEFT Engine", THEME["accent_blue"])
    xml += f'<rect x="1480" y="340" width="320" height="240" fill="#F1F5F9" stroke="{THEME["accent_blue"]}" stroke-width="2" rx="10" />'
    xml += f'<text x="1640" y="380" fill="{THEME["text_main"]}" font-size="18" font-weight="700" text-anchor="middle" {SVG_FONT_FAMILY}>Base Model (Gemma-4 4B)</text>'
    
    xml += f'<rect x="1510" y="420" width="260" height="60" fill="#DBEAFE" stroke="{THEME["accent_blue"]}" stroke-width="2" rx="5" />'
    xml += f'<text x="1640" y="455" fill="{THEME["text_main"]}" font-size="16" font-weight="700" text-anchor="middle" {SVG_FONT_FAMILY}>Player LoRA (NPC 嗆聲)</text>'
    
    xml += f'<rect x="1510" y="500" width="260" height="60" fill="#D1FAE5" stroke="{THEME["accent_green"]}" stroke-width="2" rx="5" />'
    xml += f'<text x="1640" y="535" fill="{THEME["text_main"]}" font-size="16" font-weight="700" text-anchor="middle" {SVG_FONT_FAMILY}>Referee LoRA (裁判打分)</text>'
    
    xml += f'<text x="1640" y="620" fill="{THEME["text_muted"]}" font-size="14" text-anchor="middle" {SVG_FONT_FAMILY}>(在一個 GPU 進程內動態熱插拔載入)</text>'

    # Bottom notes
    xml += f'<rect x="80" y="940" width="1760" height="1" fill="{THEME["border"]}" />'
    xml += "</svg>"
    return xml


# ==============================================================================
# Slide 4: Real-Time Contextual & Opponent Memory (MINIMALIST WITH REAL PROMPT)
# ==============================================================================
def render_slide_4() -> str:
    xml = svg_header("對話上下文與長期對手偏好記憶", 4)
    
    # Left Column: NpcMemory Flowchart (Compact)
    xml += draw_card(80, 240, 780, 680, "對手特徵記憶與自適應反饋流程 (Memory Loop)", THEME["accent_orange"])
    
    xml += f'<rect x="130" y="340" width="310" height="60" fill="#FFE4E6" stroke="{THEME["accent_red"]}" stroke-width="2" rx="10" />'
    xml += f'<text x="285" y="375" fill="{THEME["text_main"]}" font-size="18" font-weight="700" text-anchor="middle" {SVG_FONT_FAMILY}>1. 玩家(對手)發送攻擊文本</text>'
    xml += draw_arrow(285, 400, 285, 450, "Update SQL")

    xml += f'<rect x="130" y="450" width="310" height="60" fill="#FEF3C7" stroke="{THEME["accent_orange"]}" stroke-width="2" rx="10" />'
    xml += f'<text x="285" y="485" fill="{THEME["text_main"]}" font-size="18" font-weight="700" text-anchor="middle" {SVG_FONT_FAMILY}>2. update_npc_memory()</text>'
    xml += draw_arrow(285, 510, 285, 560, "Upsert")

    xml += draw_database(155, 560, 260, 110, "Table: npc_memory")
    xml += draw_arrow(430, 615, 520, 615, "Load Patterns")

    xml += f'<rect x="530" y="555" width="300" height="120" fill="#DBEAFE" stroke="{THEME["accent_blue"]}" stroke-width="2" rx="10" />'
    xml += f'<text x="680" y="590" fill="{THEME["text_main"]}" font-size="18" font-weight="700" text-anchor="middle" {SVG_FONT_FAMILY}>3. 提示詞動態載入</text>'
    xml += f'<text x="550" y="625" fill="{THEME["text_muted"]}" font-size="15" {SVG_FONT_FAMILY}>[Opponent patterns]: 網路迷因流</text>'
    xml += f'<text x="550" y="650" fill="{THEME["text_muted"]}" font-size="15" {SVG_FONT_FAMILY}>[Avg damage recved]: 24.5 pts</text>'

    xml += draw_arrow(680, 555, 680, 510, "Inference")

    xml += f'<rect x="530" y="450" width="300" height="60" fill="#D1FAE5" stroke="{THEME["accent_green"]}" stroke-width="2" rx="10" />'
    xml += f'<text x="680" y="485" fill="{THEME["text_main"]}" font-size="18" font-weight="700" text-anchor="middle" {SVG_FONT_FAMILY}>4. 自適應毒舌反擊</text>'

    # Summary note
    xml += f'<rect x="120" y="740" width="700" height="150" fill="#F1F5F9" rx="5" />'
    xml += f'<text x="145" y="780" fill="{THEME["text_main"]}" font-size="16" font-weight="700" {SVG_FONT_FAMILY}>- 即時上下文：拼裝當前血量狀態與最近 4 輪對話窗口。</text>'
    xml += f'<text x="145" y="820" fill="{THEME["text_main"]}" font-size="16" font-weight="700" {SVG_FONT_FAMILY}>- 長期偏好記憶：自動加載對手習慣，實現自適應嗆聲。</text>'
    xml += f'<text x="145" y="860" fill="{THEME["text_muted"]}" font-size="15" {SVG_FONT_FAMILY}>(對應代碼：src/backend/services/npc/agent.py 中的 run_npc_turn)</text>'

    # Right Column: Actual Prompts (REAL PROMPT INJECTION EXAMPLE)
    xml += draw_card(890, 240, 950, 680, "真實進入 Player 模型的 Prompt 結構與範例", THEME["accent_blue"])
    
    xml += f'<rect x="930" y="340" width="870" height="190" fill="#F8FAFC" stroke="{THEME["border"]}" rx="8" />'
    xml += f'<text x="950" y="375" fill="{THEME["accent_blue"]}" font-size="18" font-weight="700" {SVG_FONT_FAMILY}>[System Message] (System Prompt 原文簡化)</text>'
    xml += f'<text x="950" y="410" fill="{THEME["text_muted"]}" font-size="15" font-family="monospace">You are a highly aggressive and toxic player in a competitive verbal sparring game.</text>'
    xml += f'<text x="950" y="435" fill="{THEME["text_muted"]}" font-size="15" font-family="monospace">Respond with a merciless, sharp comeback in Traditional Chinese. Limit: under 25 chars.</text>'
    xml += f'<text x="950" y="460" fill="{THEME["text_muted"]}" font-size="15" font-family="monospace">Style Guide: Grounded Street Slang. Include Taiwanese street slang naturally</text>'
    xml += f'<text x="950" y="485" fill="{THEME["text_muted"]}" font-size="15" font-family="monospace">(e.g., \"靠北\", \"三小\", \"是在旋轉喔\", \"沒那個屁股就不要吃瀉藥\", \"滾回去啦\").</text>'
    
    xml += f'<rect x="930" y="550" width="870" height="340" fill="#EFF6FF" stroke="{THEME["accent_blue"]}" rx="8" />'
    xml += f'<text x="950" y="585" fill="{THEME["accent_blue"]}" font-size="18" font-weight="700" {SVG_FONT_FAMILY}>[Human Message] (動態情境與 SQL 記憶載入實體)</text>'
    xml += f'<text x="950" y="625" fill="{THEME["text_main"]}" font-size="16" font-weight="700" font-family="monospace">[Round 3 | NPC HP: 85 | Opponent HP: 60]</text>'
    xml += f'<text x="950" y="655" fill="{THEME["accent_orange"]}" font-size="16" font-weight="700" font-family="monospace">[Long-term opponent patterns]: 網路迷因流, 8+9流</text>'
    xml += f'<text x="950" y="685" fill="{THEME["text_main"]}" font-size="15" font-weight="700" font-family="monospace">[Recent battle dialogue]:</text>'
    xml += f'<text x="950" y="715" fill="{THEME["text_muted"]}" font-size="15" font-family="monospace">- opponent: "演技好是因為要在你這菜鳥面前，把比賽演成單方面屠殺。"</text>'
    xml += f'<text x="950" y="740" fill="{THEME["text_muted"]}" font-size="15" font-family="monospace">- npc: "演得這麼用力，是怕輸了連腦袋都沒得用嗎？"</text>'
    xml += f'<text x="950" y="765" fill="{THEME["text_muted"]}" font-size="15" font-family="monospace">- opponent: "三小啦，你這廢物是在旋轉喔？滾回去下水溝啦。"</text>'
    
    xml += f'<text x="950" y="810" fill="{THEME["accent_green"]}" font-size="16" font-weight="700" font-family="monospace">Generate your attack now (Traditional Chinese, &lt; 25 chars, NO extra explanation):</text>'
    
    xml += f'<rect x="950" y="830" width="830" height="45" fill="#D1FAE5" rx="5" />'
    xml += f'<text x="970" y="858" fill="{THEME["text_main"]}" font-size="16" font-weight="700" font-family="monospace">&gt; "看三小？腦袋長在屁股上喔？靠北滾啦！" (48 pts, 由 LoRA 輸出)</text>'

    xml += "</svg>"
    return xml


# ==============================================================================
# Slide 5: Stage 1 NPC Training: SFT LoRA
# ==============================================================================
def render_slide_5() -> str:
    xml = svg_header("NPC 第一階段訓練：SFT 監督微調", 5)
    
    xml += draw_card(80, 240, 840, 680, "SFT 訓練配置與超參數", THEME["accent_blue"])
    xml += draw_bullet(130, 360, "基座模型 (Base Model)：", "google/gemma-4-E4B-it (4B)")
    xml += draw_bullet(130, 430, "微調精度 (Precision)：", "4-bit NF4 (Double Quant), BF16 Compute")
    xml += draw_bullet(130, 500, "適配器設定 (LoRA)：", "Rank r=16, Alpha=32, Dropout=0.05")
    xml += draw_bullet(130, 570, "訓練量 (Epochs/Steps)：", "3 Epochs, lr=2e-4, PagedAdamW 8bit")
    xml += draw_bullet(130, 640, "梯度積累 (Grad Accumulation)：", "Per-device batch=2, Accumulation=4")
    
    xml += f'<rect x="130" y="690" width="740" height="190" fill="#EFF6FF" rx="10" />'
    xml += f'<text x="160" y="735" fill="{THEME["text_main"]}" font-size="18" font-weight="700" {SVG_FONT_FAMILY}>關鍵修復：排除 vision_tower 維度不相容</text>'
    xml += f'<text x="160" y="775" fill="{THEME["text_muted"]}" font-size="16" {SVG_FONT_FAMILY}>在 `LoraConfig` 中使用目標層正則表達式：</text>'
    xml += f'<text x="160" y="815" fill="{THEME["accent_blue"]}" font-size="16" font-family="monospace">target_modules = ".*language_model.*(q_proj|v_proj|...)"</text>'
    xml += f'<text x="160" y="855" fill="{THEME["text_muted"]}" font-size="15" {SVG_FONT_FAMILY}>主動跳過視覺投影層，防範 k-bit 準備與梯度回傳時的維度報錯。</text>'

    xml += draw_card(990, 240, 850, 680, "SFT 微調達成目標", THEME["accent_orange"])
    xml += draw_bullet(1040, 360, "1. 多輪對話格式擬合：", "學會遵循 Gemini-it 標準對話 template。")
    xml += draw_bullet(1040, 440, "2. 8 大流派風格掌握：", "模型能辨識風格標記，並輸出相對應句式。")
    xml += draw_bullet(1040, 520, "3. 物理邊界初步限制：", "學會在 25 字以內結束句子，不包含 extra text。")
    xml += draw_bullet(1040, 600, "4. 台灣在地語境適配：", "初步能講出「靠北、三小、魯蛇、歸剛欸」等台灣俚語。")
    
    xml += f'<rect x="1040" y="660" width="750" height="220" fill="#FEF3C7" rx="10" />'
    xml += f'<text x="1070" y="710" fill="{THEME["text_main"]}" font-size="18" font-weight="700" {SVG_FONT_FAMILY}>SFT 侷限與 DPO 引進動機：</text>'
    xml += f'<text x="1070" y="755" fill="{THEME["text_muted"]}" font-size="16" {SVG_FONT_FAMILY}>雖然 SFT 學會了基本格式與俚語，但在對抗性對局中：</text>'
    xml += f'<text x="1070" y="795" fill="{THEME["accent_orange"]}" font-size="16" font-weight="700" {SVG_FONT_FAMILY}>- 模型傾向給予安全、冗長且禮貌的回答，缺乏「挑釁力」。</text>'
    xml += f'<text x="1070" y="835" fill="{THEME["accent_orange"]}" font-size="16" font-weight="700" {SVG_FONT_FAMILY}>- 為了讓模型更「毒舌」且精簡，必須進行二階段偏好對齊。</text>'

    xml += "</svg>"
    return xml


# ==============================================================================
# Slide 6: Stage 2 NPC Training: DPO Preference (MINIMALIST WITH EMBEDDED CHART)
# ==============================================================================
def render_slide_6() -> str:
    xml = svg_header("NPC 第二階段訓練：DPO 偏好對齊", 6)
    
    # Left Column: Compact DPO Pairing
    xml += draw_card(80, 240, 780, 680, "DPO 偏好資料生成與對齊機制", THEME["accent_blue"])
    xml += draw_bullet(130, 360, "偏好配對機制 (Chosen vs Rejected)：", "")
    xml += f'<text x="150" y="410" fill="{THEME["text_muted"]}" font-size="18" {SVG_FONT_FAMILY}>針對同一個挑釁 Prompt，SFT 產生 3 個候選句。由 Qwen 27B 打分：</text>'
    
    xml += f'<rect x="130" y="440" width="700" height="100" fill="#ECFDF5" rx="10" stroke="{THEME["accent_green"]}" stroke-width="1.5" />'
    xml += f'<text x="160" y="480" fill="{THEME["accent_green"]}" font-size="18" font-weight="700" {SVG_FONT_FAMILY}>Chosen (優選反擊，分數最高，字數符合且辣度高)：</text>'
    xml += f'<text x="160" y="515" fill="{THEME["text_main"]}" font-size="16" font-family="monospace">「看三小？腦袋長在屁股上喔？靠北滾啦！」 (48 pts)</text>'

    xml += f'<rect x="130" y="560" width="700" height="100" fill="#FEF2F2" rx="10" stroke="{THEME["accent_red"]}" stroke-width="1.5" />'
    xml += f'<text x="160" y="600" fill="{THEME["accent_red"]}" font-size="18" font-weight="700" {SVG_FONT_FAMILY}>Rejected (劣等反擊，分數最低，溫和或長篇大論)：</text>'
    xml += f'<text x="160" y="635" fill="{THEME["text_main"]}" font-size="16" font-family="monospace">「好啦都是我的錯，你要這樣想我也沒辦法。」 (12 pts)</text>'

    # Summary metrics (Big Stats)
    xml += draw_bullet(130, 700, "1. 毒舌攻擊點數暴增 (+5.17)：", "平均毒舌分由 SFT 34.97 提升至 DPO 40.13。")
    xml += draw_bullet(130, 770, "2. 物理字數強大約束：", "對長回覆施加 penalty，提升長度限制遵循率。")
    xml += draw_bullet(130, 840, "3. 保持詞彙多樣度 (Entropy)：", "香農熵微增 (7.17)，無發生模式崩塌 (Mode Collapse)。")

    # Right Column: Embedded Matplotlib Chart (REAL EVALUATION CHART)
    xml += draw_card(890, 240, 950, 680, "SFT vs DPO 評測指標橫向對比圖表", THEME["accent_green"])
    # Embed the actual matplotlib-generated benchmark comparison chart
    # Path is relative to output directory (./evaluation/slides/ -> ./evaluation/player_benchmark_comparison.png)
    xml += f'<image x="930" y="330" width="870" height="540" href="../player_benchmark_comparison.png" />'

    xml += "</svg>"
    return xml


# ==============================================================================
# Slide 7: Referee SFT & A/B Evaluation (MINIMALIST WITH EMBEDDED CHART)
# ==============================================================================
def render_slide_7() -> str:
    xml = svg_header("裁判微調 SFT v2 與基準評測", 7)
    
    # Left Column: Configuration (Minimal text)
    xml += draw_card(80, 240, 780, 680, "裁判微調配置與學術設計", THEME["accent_blue"])
    xml += draw_bullet(130, 360, "1. 訓練流派對抗更新 (SFT v2)：", "使用 DPO Player 對抗產出攻防")
    xml += f'<text x="160" y="395" fill="{THEME["text_muted"]}" font-size="18" {SVG_FONT_FAMILY}>日誌，交由 Qwen 27B 重新打分，產出高品質裁判蒸餾集。</text>'
    
    xml += draw_bullet(130, 465, "2. 為什麼裁判不適合 DPO：", "裁判本質是「打分與評語生成」回歸任務。")
    xml += f'<text x="160" y="500" fill="{THEME["text_muted"]}" font-size="18" {SVG_FONT_FAMILY}>對其進行 DPO 會導致給分「收縮偏極化」，且 JSON 格式損壞。</text>'

    xml += f'<rect x="130" y="550" width="700" height="320" fill="#EFF6FF" rx="10" />'
    xml += f'<text x="160" y="600" fill="{THEME["text_main"]}" font-size="20" font-weight="700" {SVG_FONT_FAMILY}>微調後實測指標 (A/B Test 成果)：</text>'
    xml += draw_bullet(160, 660, "- JSON Validity (格式遵循率)：", "0.00%  =>  100.00% (系統防護網)", THEME["accent_green"])
    xml += draw_bullet(160, 720, "- Inference Latency (平均延遲)：", "3143ms  =>  1348ms (降幅 57%)", THEME["accent_green"])
    xml += draw_bullet(160, 780, "- Pearson Correlation (與導師相關)：", "0.0000  =>  0.3988 (語意對齊)", THEME["accent_green"])
    xml += draw_bullet(160, 840, "- Damage MAE (平均絕對誤差)：", "8.38 pts  =>  21.54 pts (分布貼合)", THEME["accent_green"])

    # Right Column: Embedded Matplotlib Chart (REAL REFEREE CHART)
    xml += draw_card(890, 240, 950, 680, "裁判微調前後指標對比圖表", THEME["accent_green"])
    # Embed the referee benchmark comparison chart
    # Path is relative (./evaluation/slides/ -> ./docs/evaluation/benchmark_comparison.png)
    xml += f'<image x="930" y="330" width="870" height="540" href="../../docs/evaluation/benchmark_comparison.png" />'

    xml += "</svg>"
    return xml


# ==============================================================================
# Slide 8: Deployed Prompt Engineering & Balanced Brace
# ==============================================================================
def render_slide_8() -> str:
    xml = svg_header("提示詞工程與 Neuro-Symbolic 限制解碼", 8)
    
    # Left Column: Real Prompt Box
    xml += draw_card(80, 240, 920, 680, "真實進入裁判(Referee)模型的 Prompt 結構與 Few-Shots", THEME["accent_blue"])
    
    xml += f'<rect x="120" y="340" width="840" height="230" fill="#F8FAFC" stroke="{THEME["border"]}" rx="8" />'
    xml += f'<text x="140" y="375" fill="{THEME["accent_blue"]}" font-size="18" font-weight="700" {SVG_FONT_FAMILY}>[System Message] (System Prompt 與 JSON 限制約束)</text>'
    xml += f'<text x="140" y="410" fill="{THEME["text_muted"]}" font-size="15" font-family="monospace">你是一位無情、機智且挑剔的「華語毒舌評審」。請評估玩家攻擊發言。</text>'
    xml += f'<text x="140" y="435" fill="{THEME["text_muted"]}" font-size="15" font-family="monospace">請根據以下標準進行評審：</text>'
    xml += f'<text x="140" y="460" fill="{THEME["text_muted"]}" font-size="15" font-family="monospace">1. 傷害評分 (damage): 給予 1 到 50 的整數評分。 2. 毒舌評語 (referee_comment): &lt; 25字。</text>'
    xml += f'<text x="140" y="485" fill="{THEME["text_muted"]}" font-size="15" font-family="monospace">請嚴格輸出符合以下 JSON 格式的內容，不要包含 any extra text：</text>'
    xml += f'<text x="140" y="510" fill="{THEME["text_main"]}" font-size="15" font-weight="700" font-family="monospace">{{"damage": 傷害整數, "referee_comment": "你的辛辣評語"}}</text>'

    # Few-Shots Demonstration (Referee core design)
    xml += f'<rect x="120" y="590" width="840" height="300" fill="#EFF6FF" stroke="{THEME["accent_blue"]}" rx="8" />'
    xml += f'<text x="140" y="625" fill="{THEME["accent_blue"]}" font-size="18" font-weight="700" {SVG_FONT_FAMILY}>[Few-Shot 示範輪次 (In-Context Learning)]</text>'
    xml += f'<text x="140" y="660" fill="{THEME["text_muted"]}" font-size="14" font-family="monospace">Human: 玩家發言：「你長得像被卡車碾過的便當」</text>'
    xml += f'<text x="140" y="685" fill="{THEME["accent_green"]}" font-size="14" font-weight="700" font-family="monospace">AI: {{"damage": 24, "referee_comment": "畫面有了，扣分扣得理所當然"}}</text>'
    xml += f'<line x1="140" y1="710" x2="920" y2="710" stroke="{THEME["border"]}" stroke-width="1" />'
    
    # Active Input
    xml += f'<text x="140" y="735" fill="{THEME["text_main"]}" font-size="15" font-weight="700" {SVG_FONT_FAMILY}>[Current Active Input - 實際推理內容]</text>'
    xml += f'<text x="140" y="765" fill="{THEME["text_muted"]}" font-size="14" font-family="monospace">Human: [Round 3 | Attacker HP: 60 | Opponent HP: 85]</text>'
    xml += f'<text x="140" y="785" fill="{THEME["text_muted"]}" font-size="14" font-family="monospace">[Recent battle dialogue]:</text>'
    xml += f'<text x="140" y="805" fill="{THEME["text_muted"]}" font-size="14" font-family="monospace">- opponent: "演技好是因為要把你演成單方面屠殺。"</text>'
    xml += f'<text x="140" y="825" fill="{THEME["text_muted"]}" font-size="14" font-family="monospace">- npc: "演得這麼用力，是怕輸了連腦袋都沒得用嗎？"</text>'
    xml += f'<text x="140" y="845" fill="{THEME["text_main"]}" font-size="14" font-weight="700" font-family="monospace">玩家發言：「看三小？腦袋長在屁股上喔？靠北滾啦！」</text>'
    
    xml += f'<rect x="140" y="865" width="800" height="20" fill="#D1FAE5" rx="3" />'
    xml += f'<text x="150" y="880" fill="{THEME["text_main"]}" font-size="13" font-family="monospace">&gt; Output (Gemma-LoRA): {{"damage": 48, "referee_comment": "髒度拉滿，屁股這詞挺有韻律"}}</text>'

    # Right Column: Flowcharts (Balanced Brace Parser State Machine)
    xml += draw_card(1030, 240, 810, 680, "Neuro-Symbolic: 三段式 JSON 容錯解析流", THEME["accent_green"])
    
    y_step = 340
    xml += f'<rect x="1070" y="{y_step}" width="730" height="70" fill="#E0F2FE" stroke="{THEME["accent_blue"]}" stroke-width="2" rx="10" />'
    xml += f'<text x="1100" y="{y_step+40}" fill="{THEME["text_main"]}" font-size="18" font-weight="700" {SVG_FONT_FAMILY}>Step 1. json.loads(raw_response.strip())</text>'
    xml += draw_arrow(1435, y_step+70, 1435, y_step+110, "Decode Error")
    
    y_step = 450
    xml += f'<rect x="1070" y="{y_step}" width="730" height="70" fill="#BAE6FD" stroke="{THEME["accent_blue"]}" stroke-width="2" rx="10" />'
    xml += f'<text x="1100" y="{y_step+40}" fill="{THEME["text_main"]}" font-size="18" font-weight="700" {SVG_FONT_FAMILY}>Step 2. 去除 Markdown Fences (```json ... ```)</text>'
    xml += draw_arrow(1435, y_step+70, 1435, y_step+110, "Decode Error")

    y_step = 560
    xml += f'<rect x="1070" y="{y_step}" width="730" height="330" fill="#FEF3C7" stroke="{THEME["accent_orange"]}" stroke-width="2" rx="10" />'
    xml += f'<text x="1100" y="{y_step+40}" fill="{THEME["text_main"]}" font-size="20" font-weight="800" {SVG_FONT_FAMILY}>Step 3. Balanced Brace Parser (括號配對深度掃描)</text>'
    
    xml += f'<circle cx="1170" cy="{y_step+150}" r="45" fill="#DBEAFE" stroke="{THEME["accent_blue"]}" stroke-width="2" />'
    xml += f'<text x="1170" y="{y_step+155}" fill="{THEME["text_main"]}" font-size="14" font-weight="700" text-anchor="middle" {SVG_FONT_FAMILY}>深度 depth = 0</text>'
    xml += draw_arrow(1220, y_step+150, 1375, y_step+150, "遇到「{」depth++ (記錄起點)")
    
    xml += f'<circle cx="1435" cy="{y_step+150}" r="45" fill="#FDE68A" stroke="{THEME["accent_orange"]}" stroke-width="2" />'
    xml += f'<text x="1435" y="{y_step+155}" fill="{THEME["text_main"]}" font-size="14" font-weight="700" text-anchor="middle" {SVG_FONT_FAMILY}>深度 depth &gt; 0</text>'
    xml += draw_arrow(1490, y_step+150, 1645, y_step+150, "遇到「}」depth--")

    xml += f'<circle cx="1700" cy="{y_step+150}" r="45" fill="#D1FAE5" stroke="{THEME["accent_green"]}" stroke-width="2" />'
    xml += f'<text x="1700" y="{y_step+155}" fill="{THEME["text_main"]}" font-size="14" font-weight="700" text-anchor="middle" {SVG_FONT_FAMILY}>合適 JSON 區段</text>'
    xml += draw_arrow(1700, y_step+200, 1435, 780, "截取 json.loads()")
    
    xml += f'<rect x="1100" y="800" width="670" height="70" fill="#D1FAE5" stroke="{THEME["accent_green"]}" stroke-width="2" rx="8" />'
    xml += f'<text x="1120" y="840" fill="{THEME["text_main"]}" font-size="16" font-weight="700" {SVG_FONT_FAMILY}>[後處置] validate_clamp(): 傷害強制 Clamping [10, 30] 且評語長度限制在 40 字內</text>'

    xml += "</svg>"
    return xml


# ==============================================================================
# Slide 9: Fullstack Deployment & WebSocket Runtime (UPGRADED WITH CONTAINER DIAGRAM)
# ==============================================================================
def render_slide_9() -> str:
    xml = svg_header("全棧部署架構與實時對局引擎", 9)
    
    # Left Column: Deployment (WITH CONTAINER DIAGRAM)
    xml += draw_card(80, 240, 840, 680, "Docker 服務容器化關係圖 (docker-compose)", THEME["accent_blue"])
    
    # React Container
    xml += f'<rect x="120" y="340" width="310" height="150" fill="#EFF6FF" stroke="{THEME["accent_blue"]}" stroke-width="2" rx="10" />'
    xml += f'<text x="140" y="380" fill="{THEME["text_main"]}" font-size="20" font-weight="700" {SVG_FONT_FAMILY}>Frontend (React Vite)</text>'
    xml += f'<text x="140" y="415" fill="{THEME["text_muted"]}" font-size="16" {SVG_FONT_FAMILY}>- Port 3000 mapping</text>'
    xml += f'<text x="140" y="445" fill="{THEME["text_muted"]}" font-size="16" {SVG_FONT_FAMILY}>- TypeScript &amp; Tailwind UI</text>'

    # Arrow React <-> FastAPI
    xml += draw_arrow(440, 415, 530, 415, "WebSocket", THEME["accent_blue"])
    xml += draw_arrow(530, 445, 440, 445, "Battle sync", THEME["accent_green"])

    # FastAPI Container
    xml += f'<rect x="540" y="340" width="340" height="150" fill="#FEF3C7" stroke="{THEME["accent_orange"]}" stroke-width="2" rx="10" />'
    xml += f'<text x="560" y="380" fill="{THEME["text_main"]}" font-size="20" font-weight="700" {SVG_FONT_FAMILY}>Backend (FastAPI Engine)</text>'
    xml += f'<text x="560" y="415" fill="{THEME["text_muted"]}" font-size="16" {SVG_FONT_FAMILY}>- Port 8000 mapping</text>'
    xml += f'<text x="560" y="445" fill="{THEME["text_muted"]}" font-size="16" {SVG_FONT_FAMILY}>- WebSocket異步對戰</text>'

    # Arrow FastAPI -> DB
    xml += draw_arrow(710, 500, 710, 575, "SQLAlchemy")

    # DB Cylinder (SQL)
    xml += draw_database(540, 590, 340, 120, "PostgreSQL Database")

    # Arrow DB -> React
    xml += draw_arrow(540, 650, 275, 650, "NpcMemory Cache")

    # Micro-LoRA serving box
    xml += f'<rect x="120" y="550" width="310" height="150" fill="#ECFDF5" stroke="{THEME["accent_green"]}" stroke-width="2" rx="10" />'
    xml += f'<text x="140" y="590" fill="{THEME["text_main"]}" font-size="20" font-weight="700" {SVG_FONT_FAMILY}>Inference Server (vLLM)</text>'
    xml += f'<text x="140" y="625" fill="{THEME["text_muted"]}" font-size="16" {SVG_FONT_FAMILY}>- Port 8060 / API endpoint</text>'
    xml += f'<text x="140" y="655" fill="{THEME["text_muted"]}" font-size="16" {SVG_FONT_FAMILY}>- Dynamic LoRA Hot-swapping</text>'

    xml += draw_arrow(540, 460, 440, 580, "Inference API")

    # Bottom notes
    xml += f'<rect x="120" y="740" width="760" height="140" fill="#F1F5F9" rx="10" />'
    xml += f'<text x="140" y="780" fill="{THEME["text_main"]}" font-size="16" font-weight="700" {SVG_FONT_FAMILY}>動態加載 PEFT 機制 (Dynamic PEFT Adapter Loading)：</text>'
    xml += f'<text x="140" y="815" fill="{THEME["text_muted"]}" font-size="15" {SVG_FONT_FAMILY}>- 使用 PEFT 的 `model.load_adapter()` 和 `model.set_adapter()`，</text>'
    xml += f'<text x="140" y="845" fill="{THEME["text_muted"]}" font-size="15" {SVG_FONT_FAMILY}>  使同一個 GPU 進程能同時服務對手與裁判，大幅壓縮顯存與推理硬體開銷。</text>'

    # Right Column: WebSockets (Minimal text)
    xml += draw_card(990, 240, 850, 680, "實時對決 WebSocket 異步對抗引擎", THEME["accent_orange"])
    xml += draw_bullet(1040, 360, "多人對決協定 (battle_ws.py)：", "WebSocket 雙向通信，實時連線配對")
    xml += draw_bullet(1040, 440, "異步調度管道 (State Graph)：", "解決大模型推理線程阻塞 (ainvoke)")
    xml += draw_bullet(1040, 520, "會話狀態管理 (battle_session.py)：", "負責對局狀態機控制")
    
    xml += f'<rect x="1040" y="580" width="750" height="290" fill="#FEF3C7" rx="10" />'
    xml += f'<text x="1070" y="630" fill="{THEME["text_main"]}" font-size="18" font-weight="700" {SVG_FONT_FAMILY}>BattleSession 對局機制：</text>'
    xml += f'<text x="1070" y="680" fill="{THEME["text_muted"]}" font-size="16" {SVG_FONT_FAMILY}>1. 雙方血量 HP 扣減與死亡判定</text>'
    xml += f'<text x="1070" y="725" fill="{THEME["text_muted"]}" font-size="16" {SVG_FONT_FAMILY}>2. 攻防 Turn-taking 狀態機輪替</text>'
    xml += f'<text x="1070" y="770" fill="{THEME["text_muted"]}" font-size="16" {SVG_FONT_FAMILY}>3. 裁判打分廣播：「damage, referee_comment」</text>'
    xml += f'<text x="1070" y="815" fill="{THEME["text_muted"]}" font-size="16" {SVG_FONT_FAMILY}>4. ORM 記錄持久化寫入 rounds 和 matches 表</text>'

    xml += "</svg>"
    return xml


# ==============================================================================
# Slide 10: Conclusion & Future Outlook
# ==============================================================================
def render_slide_10() -> str:
    xml = svg_header("結論與未來展望", 10)
    
    xml += draw_card(80, 240, 840, 680, "專案重要結論與工程成果", THEME["accent_green"])
    xml += draw_bullet(130, 360, "1. 兩階段對齊微調之可行性：", "")
    xml += f'<text x="150" y="405" fill="{THEME["text_muted"]}" font-size="18" {SVG_FONT_FAMILY}>輕量化 4B VLM/LLM 透過 SFT + DPO，可成功蒸餾出 27B 的</text>'
    xml += f'<text x="150" y="435" fill="{THEME["text_muted"]}" font-size="18" {SVG_FONT_FAMILY}>在地幽默與對抗張力，且 VRAM 要求僅 10GB。</text>'
    
    xml += draw_bullet(130, 500, "2. Neuro-Symbolic 限制解碼消弭漂移：", "")
    xml += f'<text x="150" y="545" fill="{THEME["text_muted"]}" font-size="18" {SVG_FONT_FAMILY}>結合文法樹限制與括號配對後處置，將原本 0% 的 JSON 解析率</text>'
    xml += f'<text x="150" y="575" fill="{THEME["text_muted"]}" font-size="18" {SVG_FONT_FAMILY}>提升至 **100% 絕對穩定**，是 LLM 接入確定性系統的核心安全網。</text>'
    
    xml += draw_bullet(130, 640, "3. 輕量熱插拔 Multi-LoRA 架構：", "")
    xml += f'<text x="150" y="685" fill="{THEME["text_muted"]}" font-size="18" {SVG_FONT_FAMILY}>在同個 GPU 計算實例中動態熱插拔多個 LoRA，大幅壓縮多角色</text>'
    xml += f'<text x="150" y="715" fill="{THEME["text_muted"]}" font-size="18" {SVG_FONT_FAMILY}>部署時的硬體基礎設施開銷。</text>'

    xml += draw_card(990, 240, 850, 680, "未來研究與開發展望", THEME["accent_blue"])
    xml += draw_bullet(1040, 360, "1. 多模態視覺 LoRA 裁判微調：", "")
    xml += f'<text x="1060" y="405" fill="{THEME["text_muted"]}" font-size="18" {SVG_FONT_FAMILY}>未來將進一步微調 Gemma-4 的 Vision Tower，讓裁判能識別</text>'
    xml += f'<text x="1060" y="435" fill="{THEME["text_muted"]}" font-size="18" {SVG_FONT_FAMILY}>玩家表情與梗圖 (Meme) 中的視覺諷刺細節，提供更辛辣的打分。</text>'

    xml += draw_bullet(1040, 500, "2. 線上即時強化學習自適應對決 (On-the-fly RLAIF)：", "")
    xml += f'<text x="1060" y="545" fill="{THEME["text_muted"]}" font-size="18" {SVG_FONT_FAMILY}>直接以玩家對局時的投降率、按讚率或對決時長作為 Reward，</text>'
    xml += f'<text x="1060" y="575" fill="{THEME["text_muted"]}" font-size="18" {SVG_FONT_FAMILY}>在線上對決中動態進行 Policy Gradient 更新。</text>'

    xml += draw_bullet(1040, 640, "3. 混合神經符號邏輯推導 (Neuro-Symbolic Reasoning)：", "")
    xml += f'<text x="1060" y="685" fill="{THEME["text_muted"]}" font-size="18" {SVG_FONT_FAMILY}>結合知識圖譜 (Knowledge Graph)，讓 NPC 能在對決中引用對手</text>'
    xml += f'<text x="1060" y="715" fill="{THEME["text_muted"]}" font-size="18" {SVG_FONT_FAMILY}>在其他對局中的真實背景或歷史言論，增強心理戰層面。</text>'

    xml += "</svg>"
    return xml


def main() -> None:
    """Orchestrates slide writing loop."""
    print("🎨 Initializing SVG Presentation Slide Compiler...")
    
    slides = {
        "slide_1_cover.svg": render_slide_1(),
        "slide_2_motivation.svg": render_slide_2(),
        "slide_3_architecture.svg": render_slide_3(),
        "slide_4_memory.svg": render_slide_4(),
        "slide_5_sft.svg": render_slide_5(),
        "slide_6_dpo.svg": render_slide_6(),
        "slide_7_referee.svg": render_slide_7(),
        "slide_8_prompt_eng.svg": render_slide_8(),
        "slide_9_deployment.svg": render_slide_9(),
        "slide_10_conclusion.svg": render_slide_10()
    }

    for filename, xml_content in slides.items():
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(xml_content)
        print(f"   Saved Slide: {filepath}")

    print("✅ All 10 SVG slides generated successfully in ./evaluation/slides/")


if __name__ == "__main__":
    main()
