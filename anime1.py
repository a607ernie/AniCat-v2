#!/usr/bin/python
# -*- coding: UTF-8 -*-
from bs4 import BeautifulSoup
from alive_progress import alive_bar
import requests, os, re, time, json, sys
from urllib.parse import urlparse
import math
import concurrent.futures
import tempfile
# import  concurrent.futures

download_path = "{}/Anime1_Download".format(os.getcwd())

# 設定 Header 
headers = {
    "Accept": "*/*",
    "Accept-Language": 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    "DNT": "1",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "cookie": "__cfduid=d8db8ce8747b090ff3601ac6d9d22fb951579718376; _ga=GA1.2.1940993661.1579718377; _gid=GA1.2.1806075473.1579718377; _ga=GA1.3.1940993661.1579718377; _gid=GA1.3.1806075473.1579718377",
    "Content-Type":"application/x-www-form-urlencoded",
    "user-agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3573.0 Safari/537.36",
}

def Anime_Season(url):
    urls = []
    # https://anime1.me/category/.../...
    r = requests.post(url, headers = headers)
    soup = BeautifulSoup(r.text, 'lxml') 
    h2 = soup.find_all('h2', class_="entry-title")
    for i in h2:
        url = i.find("a", attrs={"rel": "bookmark"}).get('href')
        urls.append(url)

    # NextPage
    if(soup.find('div', class_ = 'nav-previous')):
        ele_div = soup.find('div', class_ = 'nav-previous')
        NextUrl = ele_div.find('a').get('href')
        urls.extend(Anime_Season(NextUrl))
    
    return urls

def Anime_Episode(url):
    # 使用同一個 Session 先抓取頁面，保持 cookies（例如 __cfduid、_ga）
    session = requests.Session()
    session.headers.update(headers)
    # 移除靜態的 Cookie header，否則 requests 會使用此 header 而不帶 session.cookies
    session.headers.pop('cookie', None)
    # 保存原始頁面 URL
    page_url = url
    r = session.post(url)
    soup = BeautifulSoup(r.text, 'lxml') 
    data = soup.find('video', class_ = 'video-js')['data-apireq']
    title = soup.find('h2', class_="entry-title").text

    # #2 https://v.anime1.me/watch?v=...
    # r = requests.post(url,headers = headers)
    # soup = BeautifulSoup(r.text, 'lxml') 
    # script_text = soup.find_all("script")[1].string
    # xsend = 'd={}'.format(re.search(r"'d=(.*?)'", script_text, re.M|re.I).group(1))
    xsend = 'd={}'.format(data)

    #3 APIv2 - 使用同一個 session 呼叫 API，並補足瀏覽器常見 header（API 會檢查 Origin/Referer）
    session.headers.update({
        'origin': 'https://anime1.me',
        'referer': page_url,
        'sec-ch-ua': '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-site': 'same-site',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty'
    })
    # retry API post once on transient errors
    try:
        r = session.post('https://v.anime1.me/api', data = xsend)
    except Exception as e:
        print('API POST failed first attempt:', e)
        time.sleep(0.5)
        try:
            r = session.post('https://v.anime1.me/api', data = xsend)
        except Exception as e:
            print('API POST failed again:', e)
            return
    api_json = json.loads(r.text)
    # debug: show api response snippet
    try:
        print('--- API response snippet ---')
        print(r.text[:1000])
    except:
        pass
    # API may return multiple candidate sources;嘗試每個直到成功
    src_list = api_json.get('s', [])
    if not src_list:
        print('API returned no sources')
        return
    
    # 優先使用 response.cookies（安全，不會被 Expires 的逗號干擾）
    cookie_e = r.cookies.get('e') or ''
    cookie_p = r.cookies.get('p') or ''
    cookie_h = r.cookies.get('h') or ''

    # fallback：若 response.cookies 沒拿到，則從 raw set-cookie header 用 regex 全域搜尋
    if not (cookie_e and cookie_p and cookie_h):
        set_cookie_header = r.headers.get('set-cookie', '')
        if set_cookie_header:
            if not cookie_e:
                m = re.search(r"e=(.*?);", set_cookie_header)
                if m:
                    cookie_e = m.group(1)
            if not cookie_p:
                m = re.search(r"p=(.*?);", set_cookie_header)
                if m:
                    cookie_p = m.group(1)
            if not cookie_h:
                m = re.search(r"h=(.*?);", set_cookie_header)
                if m:
                    cookie_h = m.group(1)
    cookies = f"e={cookie_e};p={cookie_p};h={cookie_h};"
    # 把取得的 cookies 加到 session（fallback，通常 session 已有）
    if cookie_e:
        session.cookies.set('e', cookie_e, domain='v.anime1.me')
    if cookie_p:
        session.cookies.set('p', cookie_p, domain='v.anime1.me')
    if cookie_h:
        session.cookies.set('h', cookie_h, domain='v.anime1.me')

    # 以 session 下載，讓 requests 自動處理 Cookie header
    # 依序嘗試所有來源
    for src_item in src_list:
        raw_src = src_item.get('src')
        if not raw_src:
            continue
        # normalize URL
        if raw_src.startswith('//'):
            url_try = 'https:' + raw_src
        elif raw_src.startswith('/'):
            url_try = 'https://v.anime1.me' + raw_src
        elif raw_src.startswith('http'):
            url_try = raw_src
        else:
            url_try = 'https://' + raw_src

        if url_try.startswith('https:///'):
            url_try = url_try.replace('https:///', 'https://')

        print('Trying Download URL:', url_try)
        success = MP4_DL(session, url_try, title, page_url, xsend)
        if success:
            break
        else:
            print('Source failed, trying next if available')

def MP4_DL(session, Download_URL, Video_Name, referer_url, xsend=None):
    # 每次下載的資料大小（改大以提升效能）
    chunk_size = 1024 * 256  # 256 KB
    # 每多少個 chunk flush 一次（減少 I/O 開銷）
    flush_every = 8  # 8 * 256KB = 2MB
    # 每多少個 chunk 更新 progress bar（減少 UI 更新次數）
    update_every = 1

    headers_cookies = {
        "accept": "*/*",
        "accept-encoding": "identity",
        "accept-language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        # 不手動設定 cookie，交由 session 管理
        "dnt": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
    "referer": referer_url,
        "origin": "https://anime1.me"
    }
    # 移除手動 Host/Range，改由 requests 自行處理；設定 referer/origin 指向 v.anime1.me
    # 使用傳入的實際 referer（頁面 URL），而非固定 v.anime1.me
    headers_cookies['referer'] = referer_url
    headers_cookies['origin'] = 'https://v.anime1.me'
    # 加入 sec-ch / sec-fetch 類似瀏覽器的欄位
    headers_cookies.update({
        'sec-ch-ua': '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-site': 'same-site',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty'
    })
    
    # 明確把 session.cookies 組成 Cookie header，確保 e/p/h 被送出
    cookie_str = '; '.join([f"{k}={v}" for k, v in session.cookies.get_dict().items()])
    headers_cookies['cookie'] = cookie_str
    # 在下載前嘗試重新呼叫 API 以刷新 e/p/h tokens（若提供 xsend）
    parsed = urlparse(Download_URL)
    cdn_host = parsed.netloc
    if xsend:
        try:
            ra = session.post('https://v.anime1.me/api', data=xsend, timeout=10)
            # 優先使用 response.cookies，並把重要 cookie 同步到 CDN domain
            for ck in ('e', 'p', 'h'):
                val = ra.cookies.get(ck)
                if val:
                    session.cookies.set(ck, val, domain='v.anime1.me')
                    try:
                        session.cookies.set(ck, val, domain=cdn_host)
                    except:
                        pass
            # 若 response.cookies 沒包含，嘗試從 header 萃取
            sc = ra.headers.get('set-cookie', '')
            if sc:
                for ck in ('e', 'p', 'h'):
                    if not session.cookies.get(ck):
                        m = re.search(rf"{ck}=(.*?);", sc)
                        if m:
                            session.cookies.set(ck, m.group(1), domain='v.anime1.me')
                            try:
                                session.cookies.set(ck, m.group(1), domain=cdn_host)
                            except:
                                pass
        except Exception:
            # 忽略刷新失敗，之後的 HEAD/GET 會收集診斷資訊
            pass

    # do a HEAD first to verify resource exists and see response code
    head = session.head(Download_URL, headers=headers_cookies, allow_redirects=True, timeout=15)
    if head.status_code not in (200, 206):
        print(f'HEAD check failed: {head.status_code}')
        try:
            print('--- HEAD response headers ---')
            for k, v in head.headers.items():
                print(f"{k}: {v}")
        except:
            pass
        # proceed to GET anyway to collect diagnostic info
    # 如果伺服器支援 Range（206 或 Accept-Ranges header），嘗試平行分段下載
    accepts_ranges = head.headers.get('accept-ranges', '')
    content_length = int(head.headers.get('content-length', 0))
    supports_range = (head.status_code == 206) or ('bytes' in accepts_ranges.lower()) or (content_length > 0)

    def download_range_part(url, start, end, idx, headers, session_local):
        h = headers.copy()
        h['range'] = f'bytes={start}-{end}'
        attempts = 3
        backoff = 0.5
        for attempt in range(1, attempts + 1):
            try:
                resp = session_local.get(url, headers=h, stream=True, timeout=30)
                if resp.status_code in (200, 206):
                    # write to temp file
                    tmp = tempfile.NamedTemporaryFile(delete=False)
                    for chunk in resp.iter_content(chunk_size=chunk_size):
                        if chunk:
                            tmp.write(chunk)
                    tmp.flush()
                    tmp.close()
                    return tmp.name
                else:
                    raise RuntimeError(f'part {idx} failed: {resp.status_code}')
            except Exception as ex:
                if attempt == attempts:
                    raise
                time.sleep(backoff)
                backoff *= 2

    if supports_range and content_length > 0:
        # parallel download
        max_workers = min(16, (content_length // (1024*1024)) + 1)
        part_size = max(2048*1024, content_length // max_workers)
        ranges = []
        start = 0
        idx = 0
        while start < content_length:
            end = min(start + part_size - 1, content_length - 1)
            ranges.append((start, end, idx))
            start = end + 1
            idx += 1

        print(f'Attempting parallel download: {len(ranges)} parts, {max_workers} workers')
        tmp_files = [None] * len(ranges)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {}
            for (s, e, i) in ranges:
                futures[ex.submit(download_range_part, Download_URL, s, e, i, headers_cookies, session)] = i
            # show progress bar for completed parts
            with alive_bar(len(ranges), spinner='ball_scrolling', bar='blocks') as bar:
                for fut in concurrent.futures.as_completed(futures):
                    i = futures[fut]
                    try:
                        tmp_files[i] = fut.result()
                        bar()
                    except Exception as exc:
                        print('Part download failed:', exc)
                        # fallback to single stream
                        tmp_files = None
                        break

        if tmp_files:
            # merge
            with open(os.path.join(download_path,  '{}.mp4'.format(Video_Name)), 'wb') as fout:
                for tf in tmp_files:
                    with open(tf, 'rb') as fin:
                        while True:
                            b = fin.read(1024*1024)
                            if not b:
                                break
                            fout.write(b)
            # remove temp files
            for tf in tmp_files:
                try:
                    os.remove(tf)
                except:
                    pass
            print('Parallel download complete')
            return True
        else:
            print('Parallel download failed, falling back to single stream')

    r = session.get(Download_URL, headers = headers_cookies, stream=True)
    # 影片大小
    content_length = int(r.headers.get('content-length', 0))

    # if name have other symbol, replace it.
    # like '超異域公主連結 Re:Dive'
    if ':' in Video_Name:
        Video_Name = Video_Name.replace(':','_')

    if(r.status_code == 200):
        print('+ \033[1;34m{}\033[0m [{size:.2f} MB]'.format(Video_Name, size = content_length / 1024 / 1024))
        # 計算總步數（以 chunk 為單位），避免 round 導致 0 的情況
        if content_length and content_length > 0:
            total_steps = math.ceil(content_length / chunk_size)
        else:
            total_steps = None

        # Progress Bar：有 content-length 時顯示完整進度，否則顯示 spinner
        if total_steps:
            with alive_bar(total_steps, spinner = 'ball_scrolling', bar = 'blocks' ) as bar:
                with open(os.path.join(download_path,  '{}.mp4'.format(Video_Name)), 'wb') as f:
                    cnt = 0
                    for data in r.iter_content(chunk_size = chunk_size):
                        if not data:
                            continue
                        f.write(data)
                        cnt += 1
                        if cnt % flush_every == 0:
                            f.flush()
                        if cnt % update_every == 0:
                            bar()
                    f.flush()
                    # 完整補足進度條
                    while cnt < total_steps:
                        bar()
                        cnt += 1
        else:
            with alive_bar(spinner = 'ball_scrolling', bar = 'blocks') as bar:
                with open(os.path.join(download_path,  '{}.mp4'.format(Video_Name)), 'wb') as f:
                    cnt = 0
                    for data in r.iter_content(chunk_size = chunk_size):
                        if not data:
                            continue
                        f.write(data)
                        cnt += 1
                        if cnt % flush_every == 0:
                            f.flush()
                        bar()
                    f.flush()
        # single-stream completed
        return True
    else:
        print("- \033[1;31mFailure\033[0m：{}".format(r.status_code))
        try:
            print('--- Request headers ---')
            for k, v in r.request.headers.items():
                print(f"{k}: {v}")
            print('--- Response headers ---')
            for k, v in r.headers.items():
                print(f"{k}: {v}")
            print('--- Session cookies ---')
            print(session.cookies.get_dict())
            print('--- Response text (first 500 chars) ---')
            txt = r.text
            print(txt[:500])

            # 更廣泛的診斷：嘗試多種 referer / host / cookie 組合，找出能成功的組合
            parsed = urlparse(Download_URL)
            hosts_to_try = [parsed.netloc, 'v.anime1.me', 'toko.v.anime1.me']
            referers_to_try = [referer_url, 'https://anime1.me/', 'https://v.anime1.me/']
            cookie_options = [True, False]
            for host_try in hosts_to_try:
                for ref_try in referers_to_try:
                    for use_cookie in cookie_options:
                        try:
                            test_headers = headers_cookies.copy()
                            test_headers['host'] = host_try
                            test_headers['referer'] = ref_try
                            if use_cookie:
                                test_headers['cookie'] = '; '.join([f"{k}={v}" for k, v in session.cookies.get_dict().items()])
                            else:
                                test_headers.pop('cookie', None)
                            print(f"Trying host={host_try} referer={ref_try} cookie={use_cookie} ...")
                            h = requests.head(Download_URL, headers=test_headers, allow_redirects=True, timeout=5)
                            print(' HEAD ->', h.status_code)
                            g = requests.get(Download_URL, headers=test_headers, timeout=5)
                            print(' GET ->', g.status_code)
                            if g.status_code == 200:
                                print('Found working combination; saving file not attempted in diagnostic mode.')
                                return
                        except Exception as ee:
                            print(' trial failed:', ee)
            print('Diagnostic combinations exhausted.')
        except Exception as e:
            print('Debug print failed:', e)
        # diagnostic failed
        return False
        


def read_json():
    text_str = {}
    anime_urls = []
    titles = []
    try:
        with open('sn_list.json', "r", encoding='utf8') as f:
            text_str = json.loads(f.read())
            for i in text_str.keys():
                if (text_str[i]['Downloads'] == 'Y' and text_str[i]['isDownloads'] == 'NaN') :
                    # check ID = #num
                    try:
                        if int(text_str[i]['ID']) >= 0:
                            url = 'https://anime1.me/?cat='+str(text_str[i]['ID'])
                            res = requests.get(url)
                            anime_urls.append(res.url)
                    # add anime info in sn_list, e.g. ID="http://xxxx......"
                    except:
                        anime_urls.append(str(text_str[i]['ID']))
                    titles.append(text_str[i]['title'])
                    

    except:
        print("sn_list is empty. Create a new file now.\n")

    return text_str,anime_urls,titles

if __name__ == '__main__':     
    url_list = []
    if not os.path.exists(download_path):
        os.mkdir(download_path)

    # read sn_list to get the anime url and title.
    text_str , anime_urls , titles= read_json()

    if anime_urls != []:
        for url in anime_urls:
            
            #anime_urls = input("? Anime1 URL：").split(',')
            anime_urls = url.split(',')

            for anime_url in anime_urls:
                # 區分連結類型
                if re.search(r"anime1.me/category/(.*?)", anime_url, re.M|re.I):
                    url_list.extend(Anime_Season(anime_url))
                elif re.search(r"anime1.me/[0-9]", anime_url, re.M|re.I):
                    url_list.append(anime_url)
                else:
                    print("- \033[1;31mUnable to support this link. QAQ ({})\033[0m".format(anime_url))
                    sys.exit(0)
            
            start_time = time.time()

        for url in url_list:
            Anime_Episode(url)
            time.sleep(0.5)
        
        end_time = time.time()
        print(f"+ 共耗時 {end_time - start_time} 秒（{len(url_list)} 個已下載）")

        ###############
        # download anime finish , rewrite the sn_list , update the isDownload = Y
        ################
        try:
            for i in titles:
                text_str[i]['isDownloads'] = 'Y'
            with open('sn_list.json', 'w', encoding = 'utf8') as f:
                f.write(json.dumps(text_str, ensure_ascii = False, sort_keys=True,indent = 4))
        except:
            print("There is a wrong with rewrite the sn_list.json. Please check the sn_list.json")
    # if sn_list not find "Download" = "Y"
    else:
        print("Not find new anime should download.")