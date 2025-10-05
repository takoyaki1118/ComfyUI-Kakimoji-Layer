import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

// スライダー操作を間引いて、APIリクエストの頻発を防ぐための関数
function debounce(func, delay) {
    let timeout;
    return function(...args) {
        const context = this;
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(context, args), delay);
    };
}

app.registerExtension({
    name: "Kakimoji.Editor",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "KakimojiEditor") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                onNodeCreated?.apply(this, arguments);

                // プレビュー表示用の画像ウィジェットを作成
                const previewWidget = this.addDOMWidget("preview", "img", document.createElement("img"), {
                    // ここでスタイルを直接設定
                    styles: (img) => {
                        img.style.width = "100%";
                        img.style.objectFit = "contain";
                        img.style.display = "none"; // 最初は非表示
                    }
                });
                
                let originalSize = [0, 0];
                const imageWidget = this.widgets.find(w => w.name === "image");
                
                // 元画像のサイズを取得する処理
                const originalOnRemoved = this.onRemoved;
                this.onRemoved = () => {
                    previewWidget.value.src = "";
                    return originalOnRemoved?.apply(this, arguments);
                }
                const originalCallback = imageWidget.callback;
                imageWidget.callback = (value) => {
                    if (value) {
                         // 画像がアップロードされたら、そのサイズを取得
                        const img = new Image();
                        img.onload = () => {
                            originalSize = [img.width, img.height];
                            updatePreview(); // サイズ取得後にプレビューを更新
                        };
                        const url = `/view?filename=${encodeURIComponent(value)}&type=input&subfolder=`;
                        img.src = url;
                    }
                    return originalCallback?.apply(this, arguments);
                };


                // プレビューを更新するメイン関数
                const updatePreview = async () => {
                    const baseImage = this.widgets.find(w => w.name === "image").value;
                    if (!baseImage) {
                        previewWidget.value.style.display = "none";
                        return;
                    }

                    // 現在の全パラメータを取得
                    const params = {};
                    this.widgets.forEach(w => {
                        if (w.name !== "image" && w.name !== "preview") {
                            params[w.name] = w.value;
                        }
                    });

                    // APIにリクエストを送信
                    try {
                        const response = await api.fetchApi("/kakimoji/preview", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({
                                base_image: baseImage,
                                asset_name: params.asset_name,
                                params: params,
                                original_size: originalSize
                            }),
                        });
                        const data = await response.json();
                        
                        // 返ってきたBase64画像をプレビューウィジェットに設定
                        previewWidget.value.src = "data:image/jpeg;base64," + data.preview_image;
                        previewWidget.value.style.display = "block";

                    } catch (error) {
                        console.error("Kakimoji Preview Error:", error);
                    }
                };

                const debouncedUpdate = debounce(updatePreview, 200); // 200msの間隔をあける

                // 各ウィジェットの変更を監視して、プレビュー更新関数を呼び出す
                this.widgets.forEach(w => {
                    if (w.name !== "image" && w.name !== "preview") {
                        const originalCallback = w.callback;
                        w.callback = (value) => {
                            originalCallback?.apply(this, [value]);
                            debouncedUpdate();
                        };
                    }
                });
                 
                // 初期ロード時に一度だけ実行
                if (imageWidget.value) {
                    imageWidget.callback(imageWidget.value);
                }
            };
        }
    },
});