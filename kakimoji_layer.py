import torch
import numpy as np
from PIL import Image
import os
import hashlib
import io
import base64
import server  # ComfyUIのサーバーインスタンスをインポート
from aiohttp import web # Webサーバーの機能をインポート
import folder_paths

# --- アセット読み込み (変更なし) ---
current_dir = os.path.dirname(os.path.realpath(__file__))
assets_dir = os.path.join(current_dir, "assets")
# (find_asset_files_recursively関数とasset_filesの定義は前回のコードと同じなので省略)
def find_asset_files_recursively(base_path):
    if not os.path.exists(base_path): return []
    asset_list = []; supported_extensions = ['.png', '.jpg', '.jpeg', '.webp', '.bmp']
    for root, _, files in os.walk(base_path):
        for file in files:
            if os.path.splitext(file)[1].lower() in supported_extensions:
                relative_path = os.path.relpath(os.path.join(root, file), base_path)
                asset_list.append(relative_path.replace('\\', '/'))
    return sorted(asset_list)
asset_files = find_asset_files_recursively(assets_dir)
if not asset_files: print("[Kakimoji Layer] Warning: 'assets' directory not found or is empty.")


# --- プレビュー用APIエンドポイントの定義 ---
@server.PromptServer.instance.routes.post("/kakimoji/preview")
async def generate_preview(request):
    try:
        json_data = await request.json()
        base_image_name = json_data.get("base_image")
        asset_name = json_data.get("asset_name")
        params = json_data.get("params", {})

        if not base_image_name or not asset_name:
            return web.Response(status=400, text="Missing image or asset name")

        # 画像パスの取得
        base_image_path = folder_paths.get_annotated_filepath(base_image_name)
        asset_path = os.path.join(assets_dir, asset_name)

        if not os.path.exists(base_image_path) or not os.path.exists(asset_path):
            return web.Response(status=404, text="Image file not found")

        # --- 画像サイズへの配慮 ---
        # プレビュー用に画像をリサイズして高速化
        preview_size = (512, 512)
        base_img = Image.open(base_image_path).convert("RGBA")
        base_img.thumbnail(preview_size, Image.LANCZOS)
        
        kakimoji_img = Image.open(asset_path).convert("RGBA")

        # 合成処理
        scale = float(params.get("scale", 1.0))
        rotation = float(params.get("rotation", 0.0))

        # プレビュー画像サイズに対するオフセットを再計算
        original_w, original_h = json_data.get("original_size", (base_img.width, base_img.height))
        scale_x = base_img.width / original_w
        scale_y = base_img.height / original_h

        offset_x = int(params.get("offset_x", 0) * scale_x)
        offset_y = int(params.get("offset_y", 0) * scale_y)
        
        # 書き文字の変形
        new_w = int(kakimoji_img.width * scale * min(scale_x, scale_y))
        new_h = int(kakimoji_img.height * scale * min(scale_x, scale_y))
        if new_w > 0 and new_h > 0:
            scaled_kakimoji = kakimoji_img.resize((new_w, new_h), Image.LANCZOS)
            rotated_kakimoji = scaled_kakimoji.rotate(rotation, expand=True, resample=Image.BICUBIC)
            base_img.paste(rotated_kakimoji, (offset_x, offset_y), rotated_kakimoji)

        # Base64エンコードして返す
        buffered = io.BytesIO()
        base_img.convert("RGB").save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

        return web.json_response({"preview_image": img_str})

    except Exception as e:
        print(f"[Kakimoji Layer] Error in preview API: {e}")
        return web.Response(status=500, text=str(e))


# --- ノード本体のクラス (最終出力用) ---
class KakimojiEditor:
    OUTPUT_NODE = True
    
    @classmethod
    def INPUT_TYPES(s):
        # (INPUT_TYPESの定義は前回のコードと同じなので省略)
        if not asset_files: asset_list = ["No assets found..."]
        else: asset_list = asset_files
        return { "required": { "image": ("IMAGEUPLOAD",), "asset_name": (asset_list,), "offset_x": ("INT", {"default": 0, "min": -8192, "max": 8192, "step": 1}), "offset_y": ("INT", {"default": 0, "min": -8192, "max": 8192, "step": 1}), "scale": ("FLOAT", {"default": 1.0, "min": 0.01, "max": 10.0, "step": 0.01}), "rotation": ("FLOAT", {"default": 0.0, "min": -180.0, "max": 180.0, "step": 0.1}), } }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "load_and_composite"
    CATEGORY = "Image/Layering"

    # Queue Promptが押された時の高画質合成処理 (前回のコードとほぼ同じ)
    def load_and_composite(self, image, asset_name, offset_x, offset_y, scale, rotation):
        image_path = folder_paths.get_annotated_filepath(image)
        base_image_pil = Image.open(image_path).convert("RGBA")

        # (エラーハンドリングなどは前回のコードと同じ)
        if asset_name.startswith("No assets found"):
            output_tensor = torch.from_numpy(np.array(base_image_pil.convert("RGB")).astype(np.float32) / 255.0).unsqueeze(0)
            return ({"result": (output_tensor,), "ui": {"images": [self.pil_to_comfy(base_image_pil)]}},)
        
        asset_path = os.path.join(assets_dir, asset_name)
        if not os.path.exists(asset_path):
            output_tensor = torch.from_numpy(np.array(base_image_pil.convert("RGB")).astype(np.float32) / 255.0).unsqueeze(0)
            return ({"result": (output_tensor,), "ui": {"images": [self.pil_to_comfy(base_image_pil)]}},)
            
        kakimoji_pil = Image.open(asset_path).convert("RGBA")
        
        # 合成処理
        new_width = int(kakimoji_pil.width * scale)
        new_height = int(kakimoji_pil.height * scale)
        if new_width > 0 and new_height > 0:
            scaled_kakimoji = kakimoji_pil.resize((new_width, new_height), Image.LANCZOS)
            rotated_kakimoji = scaled_kakimoji.rotate(rotation, expand=True, resample=Image.BICUBIC)
            base_image_pil.paste(rotated_kakimoji, (offset_x, offset_y), rotated_kakimoji)

        output_tensor = torch.from_numpy(np.array(base_image_pil.convert("RGB")).astype(np.float32) / 255.0).unsqueeze(0)
        
        # 結果をノード上のプレビューに表示するための設定
        return ({"result": (output_tensor,), "ui": {"images": [self.pil_to_comfy(base_image_pil.convert("RGB"))]}},)

    def pil_to_comfy(self, img):
        # 実行結果をノードに表示するためのヘルパー関数
        return {"filename": "kakimoji_result.png", "subfolder": "temp", "type": "temp", "format": "image/png", "bytes": self.pil_to_bytes(img)}

    def pil_to_bytes(self, img):
        with io.BytesIO() as buffered:
            img.save(buffered, format="PNG")
            return buffered.getvalue()

    @classmethod
    def IS_CHANGED(s, image, **kwargs):
        image_path = folder_paths.get_annotated_filepath(image)
        m = hashlib.sha256()
        with open(image_path, 'rb') as f:
            m.update(f.read())
        # パラメータの変更もハッシュに含める
        for key, value in kwargs.items():
            m.update(str(value).encode('utf-8'))
        return m.digest().hex()


NODE_CLASS_MAPPINGS = {"KakimojiEditor": KakimojiEditor}
NODE_DISPLAY_NAME_MAPPINGS = {"KakimojiEditor": "Kakimoji Editor (Live Preview)"}