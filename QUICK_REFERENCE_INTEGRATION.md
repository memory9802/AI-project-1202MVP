# 🚀 快速參考 - 前後端串接

## 訪問網址

- 🏠 **首頁**: http://localhost:5001/
- 👔 **衣櫃**: http://localhost:5001/wardrobe
- 💡 **推薦**: http://localhost:5001/recommendation
- 🤝 **分享**: http://localhost:5001/share
- 🔐 **登入**: http://localhost:5001/login

## Docker 指令

```bash
# 啟動
docker compose up -d

# 重新建置
docker compose up --build -d

# 停止
docker compose down

# 查看日誌
docker compose logs -f flask

# 重啟 Flask
docker compose restart flask
```

## 路由對應

| URL | 函數 | 模板 | 說明 |
|-----|------|------|------|
| `/` | `home()` | `home.html` | 首頁 |
| `/home` | `home()` | `home.html` | 首頁別名 |
| `/wardrobe` | `wardrobe()` | `wardrobe.html` | 衣櫃 |
| `/recommendation` | `recommendation()` | `recommendation.html` | 推薦 |
| `/share` | `share()` | `share.html` | 分享 |
| `/login` | `login()` | `login.html` | 登入 |
| `/recommend_page` | `recommend_page()` | `index.html` | AI iframe |

## 修改的檔案

- ✅ `app/app.py` - 新增 5 個路由
- ✅ `app/templates/login.html` - 修正連結
- ✅ `.dockerignore` - 新建
- ✅ `app/static/` - 移動舊 HTML 到 backup

## 測試狀態

✅ 所有頁面正常顯示中文內容  
✅ 導航連結正常運作  
✅ AI 對話框可正常開關  
✅ Docker 環境正常運行  

**串接完成!** 🎉
