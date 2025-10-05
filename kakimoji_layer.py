# /ComfyUI-Kakimoji-Layer/kakimoji_layer.py

import torch
import numpy as np
from PIL import Image
import os

# --- アセットの読み込み ---
# このスクリプトファイルが存在するディレクトリを取得
current_dir = os.path.dirname(os.path.realpath(__file__))
# アセットフォルダのパスを構築
assets_dir = os.path.join(current_dir, "assets")

# アセットフォルダが存在する場合、中の画像ファイル名をリストアップ
if os.path.exists(assets_dir):
    # サポートする画像拡張子
    supported_extensions = ['.png', '.jpg', '.jpeg', '.webp', '.bmp']
    asset_files = sorted([f for f in os.listdir(assets_dir) if os.path.splitext(f)[1].lower() in supported_extensions])
else:
    print("[Kakimoji Layer] Warning: 'assets' directory not found. Please create it and add image files.")
    asset_files = []


class LayerKakimojiWithAssets:
    """
    A custom node to layer a built-in "kakimoji" asset
    onto a base image with controls for position, scale, and rotation.
    """
    @classmethod
    def INPUT_TYPES(s):
        # アセットリストが空の場合、エラーメッセージを表示する選択肢を追加
        if not asset_files:
            asset_list = ["No assets found in assets folder!"]
        else:
            asset_list = asset_files
            
        return {
            "required": {
                "base_image": ("IMAGE",),
                "asset_name": (asset_list,), # ドロップダウンリストとしてアセットファイル一覧を表示
                "offset_x": ("INT", {"default": 0, "min": -8192, "max": 8192, "step": 1}),
                "offset_y": ("INT", {"default": 0, "min": -8192, "max": 8192, "step": 1}),
                "scale": ("FLOAT", {"default": 1.0, "min": 0.01, "max": 10.0, "step": 0.01}),
                "rotation": ("FLOAT", {"default": 0.0, "min": -180.0, "max": 180.0, "step": 0.1}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "composite_with_asset"
    CATEGORY = "Image/Layering"

    def composite_with_asset(self, base_image, asset_name, offset_x, offset_y, scale, rotation):
        # アセットが一つもない場合は、何もせずベース画像を返す
        if not asset_files:
            return (base_image,)

        # アセット画像のフルパスを構築
        asset_path = os.path.join(assets_dir, asset_name)
        
        # ファイルが存在しない場合のエラーハンドリング
        if not os.path.exists(asset_path):
            print(f"[Kakimoji Layer] Error: Asset file not found at {asset_path}")
            return (base_image,)

        # PILでアセット画像をRGBAとして読み込む
        kakimoji_pil = Image.open(asset_path).convert("RGBA")
        
        # ベース画像をPILに変換 (バッチの最初の画像のみ処理)
        base_image_pil = Image.fromarray((base_image[0].cpu().numpy() * 255.).astype(np.uint8)).convert("RGBA")

        # --- Transformations ---
        # 1. Scale
        original_width, original_height = kakimoji_pil.size
        new_width = int(original_width * scale)
        new_height = int(original_height * scale)
        if new_width < 1 or new_height < 1: return (base_image,)
        scaled_kakimoji = kakimoji_pil.resize((new_width, new_height), Image.LANCZOS)

        # 2. Rotate
        rotated_kakimoji = scaled_kakimoji.rotate(rotation, expand=True, resample=Image.BICUBIC)

        # --- Composition ---
        output_image = base_image_pil.copy()
        output_image.paste(rotated_kakimoji, (offset_x, offset_y), rotated_kakimoji)

        # ComfyUIのテンソル形式 (B, H, W, C) に戻す
        output_tensor = torch.from_numpy(np.array(output_image.convert("RGB")).astype(np.float32) / 255.0).unsqueeze(0)

        return (output_tensor,)

# ComfyUIにノードを登録するためのマッピング
NODE_CLASS_MAPPINGS = {
    "LayerKakimojiWithAssets": LayerKakimojiWithAssets
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "LayerKakimojiWithAssets": "Layer Kakimoji (Assets)"
}