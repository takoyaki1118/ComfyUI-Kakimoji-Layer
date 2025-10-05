# /ComfyUI-Kakimoji-Layer/__init__.py

from .kakimoji_layer import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

# WEB_DIRECTORYを定義することで、ComfyUIは指定されたフォルダをWebサーバーのルートとして公開します
# これにより、/extensions/ComfyUI-Kakimoji-Layer/kakimoji_editor.js のようにアクセス可能になります
WEB_DIRECTORY = "js"

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']