# /ComfyUI-Kakimoji-Layer/__init__.py

# このファイルからノードのマッピング情報をインポートして公開します
from .kakimoji_layer import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

# ComfyUIがこの変数を探します
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']