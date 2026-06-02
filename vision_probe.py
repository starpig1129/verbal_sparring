# vision_probe.py
"""
獨立診斷 google/gemma-4-E4B-it 的視覺辨識水平，跟遊戲邏輯解耦。
用「答案明確」的程式生成圖 + 中性 prompt（不是毒舌裁判），看模型認得準不準。

用法：
  python vision_probe.py                     # NF4 4-bit（跟遊戲同配置）
  python vision_probe.py --skip-vision-quant # vision tower 不量化、只量化 language model
  python vision_probe.py --fp16              # 全 fp16（最準但最吃 VRAM，可能 CPU offload）

注意：會載入一份模型，請先把遊戲 server 停掉釋放 VRAM。
"""
import sys
import torch
from PIL import Image, ImageDraw, ImageFont
from transformers import AutoProcessor, AutoModelForImageTextToText, BitsAndBytesConfig

MODEL_NAME = "google/gemma-4-E4B-it"
SKIP_VISION_QUANT = "--skip-vision-quant" in sys.argv
FULL_FP16 = "--fp16" in sys.argv


# ---------- 生成答案明確的測試圖 ----------
def solid(color):
    return Image.new("RGB", (224, 224), color)


def red_circle_on_white():
    img = Image.new("RGB", (224, 224), "white")
    ImageDraw.Draw(img).ellipse([45, 45, 179, 179], fill=(220, 20, 20))
    return img


def half_red_blue():
    img = Image.new("RGB", (224, 224), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 112, 224], fill=(220, 20, 20))
    d.rectangle([112, 0, 224, 224], fill=(30, 60, 210))
    return img


def text_abc():
    img = Image.new("RGB", (300, 150), "white")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 90)
    except Exception:
        font = ImageFont.load_default()
    d.text((40, 25), "ABC", fill=(0, 0, 0), font=font)
    return img


TESTS = [
    ("純紅", solid((220, 20, 20)), "紅色"),
    ("純綠", solid((28, 168, 28)), "綠色"),
    ("純藍", solid((30, 60, 210)), "藍色"),
    ("純黃", solid((245, 210, 0)), "黃色"),
    ("白底紅圓", red_circle_on_white(), "白底 + 紅色圓形"),
    ("左紅右藍", half_red_blue(), "左半紅、右半藍"),
    ("英文字 ABC", text_abc(), "白底黑字 ABC"),
]

PROMPT = "用繁體中文簡短回答（一句話）：這張圖的主要顏色是什麼？裡面有什麼形狀、物件或文字？"


# ---------- 載入模型 ----------
def load_model():
    processor = AutoProcessor.from_pretrained(MODEL_NAME)
    if FULL_FP16:
        print("配置：全 fp16（不量化）")
        model = AutoModelForImageTextToText.from_pretrained(
            MODEL_NAME, device_map="auto", torch_dtype=torch.float16
        )
    else:
        bnb = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
        if SKIP_VISION_QUANT:
            print("配置：NF4 4-bit（vision tower 不量化）")
            bnb.llm_int8_skip_modules = ["vision_tower", "multi_modal_projector", "lm_head"]
        else:
            print("配置：NF4 4-bit（全量化，跟遊戲同配置）")
        model = AutoModelForImageTextToText.from_pretrained(
            MODEL_NAME, device_map="auto", quantization_config=bnb
        )
    return processor, model


def main():
    processor, model = load_model()
    print(f"模型已載入。逐張測試（greedy 解碼，結果可重現）：\n{'=' * 60}")

    for name, img, answer in TESTS:
        messages = [{"role": "user", "content": [
            {"type": "image", "image": img},
            {"type": "text", "text": PROMPT},
        ]}]
        inputs = processor.apply_chat_template(
            messages, add_generation_prompt=True,
            tokenize=True, return_dict=True, return_tensors="pt",
        ).to(model.device)
        in_len = inputs["input_ids"].shape[-1]
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=80, do_sample=False)
        resp = processor.tokenizer.decode(out[0][in_len:], skip_special_tokens=True).strip()
        print(f"\n[{name}]  正解：{answer}")
        print(f"  模型：{resp}")

    print(f"\n{'=' * 60}\n測試完成。")


def inspect_preprocess():
    """只載 processor（不載 model、不吃 GPU），檢查圖是否被正確前處理成 pixel_values。"""
    processor = AutoProcessor.from_pretrained(MODEL_NAME)
    img_token_id = getattr(processor.tokenizer, "image_token_id", None)
    samples = [("純紅", solid((220, 20, 20))), ("純藍", solid((30, 60, 210)))]
    pvs = {}
    for name, img in samples:
        messages = [{"role": "user", "content": [
            {"type": "image", "image": img},
            {"type": "text", "text": "描述這張圖"},
        ]}]
        inputs = processor.apply_chat_template(
            messages, add_generation_prompt=True,
            tokenize=True, return_dict=True, return_tensors="pt",
        )
        print(f"\n[{name}] inputs keys: {list(inputs.keys())}")
        pv = inputs.get("pixel_values")
        if pv is None:
            print("  ⚠️ 沒有 pixel_values！圖根本沒進到模型輸入。")
            continue
        pvs[name] = pv
        print(f"  pixel_values shape={tuple(pv.shape)} dtype={pv.dtype}")
        print(f"  min={float(pv.min()):.4f} max={float(pv.max()):.4f} mean={float(pv.mean()):.4f} std={float(pv.std()):.4f}")
        ids = inputs["input_ids"][0].tolist()
        if img_token_id is not None:
            print(f"  image_token({img_token_id}) 在 input_ids 出現 {ids.count(img_token_id)} 次")
        print(f"  input_ids 長度={len(ids)}")
    # 純紅 vs 純藍 的 pixel_values 差異 —— 若幾乎相同代表圖內容沒被編碼
    if "純紅" in pvs and "純藍" in pvs and pvs["純紅"].shape == pvs["純藍"].shape:
        diff = (pvs["純紅"].float() - pvs["純藍"].float()).abs().mean().item()
        print(f"\n>>> 純紅 vs 純藍 pixel_values 平均絕對差異 = {diff:.5f}")
        print(">>> 若接近 0：圖內容沒被正確讀入（前處理問題）；若明顯 >0：前處理正常，問題在量化/模型。")


def inspect_features():
    """載 4-bit model，直接比較 vision tower 對不同圖輸出的 image features 是否有區分。"""
    import itertools
    processor = AutoProcessor.from_pretrained(MODEL_NAME)
    bnb = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForImageTextToText.from_pretrained(
        MODEL_NAME, device_map="auto", quantization_config=bnb)
    samples = [
        ("純紅", solid((220, 20, 20))),
        ("純藍", solid((30, 60, 210))),
        ("純綠", solid((28, 168, 28))),
        ("紅圓", red_circle_on_white()),
    ]
    feats = {}
    for name, img in samples:
        messages = [{"role": "user", "content": [
            {"type": "image", "image": img}, {"type": "text", "text": "x"}]}]
        inputs = processor.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=True,
            return_dict=True, return_tensors="pt").to(model.device)
        with torch.no_grad():
            out = model.get_image_features(inputs["pixel_values"], inputs.get("image_position_ids"))
        f = getattr(out, "pooler_output", None)
        if f is None:
            f = getattr(out, "last_hidden_state", out)
        if isinstance(f, (tuple, list)):
            f = f[0]
        f = f.float().cpu()
        feats[name] = f
        print(f"{name}: shape={tuple(f.shape)} norm={f.norm():.3f} mean={f.mean():.4f} std={f.std():.4f}")
    print("\n=== vision features pairwise 平均絕對差異 ===")
    for a, b in itertools.combinations(feats, 2):
        if feats[a].shape == feats[b].shape:
            print(f"  {a} vs {b}: {(feats[a]-feats[b]).abs().mean().item():.5f}")
    print(">>> 若各組差異都接近 0：vision tower 對不同圖輸出相同 features（vision 在輸出層級就失效）")
    print(">>> 若明顯 >0：vision tower 有區分，問題在 features 注入語言模型之後")


def test_real_image():
    """用真實照片（vision tower 訓練分布內）測試，排除純色/合成圖 OOD 的干擾。"""
    import urllib.request
    url = "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/pipeline-cat-chonk.jpeg"
    path = "/tmp/probe_real.jpg"
    urllib.request.urlretrieve(url, path)
    img = Image.open(path).convert("RGB")
    print(f"真實照片（官方範例貓圖）尺寸: {img.size}")
    processor = AutoProcessor.from_pretrained(MODEL_NAME)
    bnb = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForImageTextToText.from_pretrained(
        MODEL_NAME, device_map="auto", quantization_config=bnb,
        attn_implementation="sdpa")
    messages = [{"role": "user", "content": [
        {"type": "image", "image": img},
        {"type": "text", "text": "用繁體中文簡短描述這張圖：有什麼動物或物件？什麼顏色？"},
    ]}]
    inputs = processor.apply_chat_template(
        messages, add_generation_prompt=True, tokenize=True,
        return_dict=True, return_tensors="pt").to(model.device)
    in_len = inputs["input_ids"].shape[-1]
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=100, do_sample=False)
    resp = processor.tokenizer.decode(out[0][in_len:], skip_special_tokens=True).strip()
    print(f"\n正解：一隻貓\n模型：{resp}")


if __name__ == "__main__":
    if "--inspect" in sys.argv:
        inspect_preprocess()
    elif "--features" in sys.argv:
        inspect_features()
    elif "--real" in sys.argv:
        test_real_image()
    else:
        main()
