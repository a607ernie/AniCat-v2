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


3. 執行 `anime1.py`
    ```
    python3 anime1.py 
    ```
執行後，`sn_list.json`的`isDownload`會被修改為`'Y'`，若需要重新下載`曾經下載過的動畫`，則修改此值為`NaN`

```json
"鬼滅之刃 遊郭篇": {
        "Downloads": "Ｙ", 若要下載，設定為Ｙ，否則預設為Ｎ
        "ID": 976,
        "episode": "1-11",
        "isDownloads": "Ｙ", 執行後程式會修改為Ｙ，若要重複下載同一個動畫，則手動改回ＮaN
        "season": "冬",
        "subtitle group": "豌豆&風之聖殿",
        "title": "鬼滅之刃 遊郭篇",
        "year": "2022"
    },
```
