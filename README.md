# AniCat-v2

AniCat-v2 為一個 [Anime1.me](https://anime1.me/) 的下載器。

## 功能
- 支援多連結輸入(已修改為透過讀取`sn_list.json`來輸入連結)。[a607ernie](https://github.com/a607ernie)新增
- 支援下載進度條

## 使用方法

- 建立環境
    
    ```
    pip3 install -r requirements.txt 
    ```
以下由[a607ernie](https://github.com/a607ernie)新增。

- 先執行[Anime-Crawl](https://github.com/a607ernie/Anime-Crawl)得到`sn_list.json`
- 修改`sn_list.json`，詳細步驟請參考[Anime-Crawl](https://github.com/a607ernie/Anime-Crawl)


- 執行 `anime1.py`
    ```
    python3 anime1.py 
    ```
執行後，`sn_list.json`的`isDownload`會被修改為`'Y'`，若需要重新下載`曾經下載過的動畫`，則修改此值為`NaN`

```json
"鬼滅之刃 遊郭篇": {
        "Downloads": "Ｙ", 若要下載，設定為Ｙ，否則預設為Ｎ
        "ID": 976,
        "episode": "1-11",
        "isDownloads": "Ｙ", 執行後程式會修改為Ｙ，若需要重複下載同一個動畫，則手動改回ＮaN
        "season": "冬",
        "subtitle group": "豌豆&風之聖殿",
        "title": "鬼滅之刃 遊郭篇",
        "year": "2022"
    },
```

# sn_list手動增加項目

因為`ID`為程式抓取，若需要手動增加，請自行複製以下範例

- 把`ID`改為`該項目網址`
- 若要下載，設定`"Downloads": "Y"`
- 確定isDownloads是否為ＮaN `"isDownloads": "NaN"`
- `title` 需設定為跟`key`一樣 
    - 例如 ：`"刀劍神域 (Sword Art Online)"`需要設定在開頭的地方和`title`的地方
- 其他資訊可自行更改，不影響程式執行

```
"刀劍神域 (Sword Art Online)": {
        "Downloads": "Y",
        "ID": "https://xxxx/category/xxxx",
        "episode": "1-12",
        "isDownloads": "NaN",
        "season": "秋",
        "subtitle group": "",
        "title": "刀劍神域 (Sword Art Online)",
        "year": "2022"
    },
```

# 免責聲明
此repo為對 python 進行學習時的test project，註解有簡易的說明。資料屬於原網站，切勿用作非法用途。