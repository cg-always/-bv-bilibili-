import requests
import re
import time
import random
import json
from tqdm import tqdm
import sys

# 要改
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'https://www.bilibili.com/',
    'Origin': 'https://www.bilibili.com',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Connection': 'keep-alive',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache'
}

#要改
# 如果需要登录才能访问的弹幕，添加你的 Cookie
COOKIE = "buvid4=83BCF525-C70C-8E50-F115-3E13AC3E962965873-024022410-pQf0mh3Ltj8z%2FyDRNGE9YQ%3D%3D; enable_web_push=DISABLE; header_theme_version=CLOSE; buvid_fp_plain=undefined; CURRENT_BLACKGAP=0; FEED_LIVE_VERSION=V_WATCHLATER_PIP_WINDOW3; hit-dyn-v2=1; fingerprint=77359313eb2f7eda225579542c5e4cb2; DedeUserID=487760599; DedeUserID__ckMd5=b3c08241a1013a63; buvid_fp=77359313eb2f7eda225579542c5e4cb2; _uuid=744E7561-3F5F-44D8-51061-66FDEC4BE36395389infoc; enable_feed_channel=ENABLE; SESSDATA=ff2132c0%2C1758556641%2Cd7174%2A32CjCWAzrs_jSqVlXTC12buru6cP6s5bUE7L_Eo6HoJiEXNDindFiVcIBOaYwvtz8yCJ8SVkN0V1UwaEsybjM3bzdSVXFjakIxRW8yNWpNVnNqWFprMXkzN1FDZ2VIUXhxZVlhWFFPNkVJal95RFRtakdjdTFKZ3h3dWE2ejZyY1A4Q1pKenNLbl9nIIEC; bili_jct=cd6b998b216c5f38f1bd8b1ca566cc33; buvid3=208A6806-C341-46B7-8AD5-9368554986FD78260infoc; b_nut=1743332773; rpdid=0z9ZwfQfjx|eZ0BaYIE|1nP|3w1TYQTt; CURRENT_QUALITY=112; bili_ticket=eyJhbGciOiJIUzI1NiIsImtpZCI6InMwMyIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NDQ4MTI1MTMsImlhdCI6MTc0NDU1MzI1MywicGx0IjotMX0.0kL2LFtCT3dyO8NlgevHq3yis3uWU_jeog2mI9DaZdw; bili_ticket_expires=1744812453; bsource=search_bing; bmg_af_switch=1; bmg_src_def_domain=i0.hdslb.com; sid=8s8exskf; CURRENT_FNVAL=2000; bp_t_offset_487760599=1056012018613485568; PVID=2; b_lsid=1FDF28A2_19639272AD3; home_feed_column=4; browser_resolution=888-941"

def get_cid(bvid):
    """获取视频CID"""
    url = f'https://api.bilibili.com/x/player/pagelist?bvid={bvid}&jsonp=jsonp'
    try:
        # 添加 Cookie 到请求头
        req_headers = headers.copy()
        if COOKIE:
            req_headers['Cookie'] = COOKIE

        response = requests.get(url, headers=req_headers, timeout=10)

        # 检查 412 错误
        if response.status_code == 412:
            print(f"触发412错误，等待10秒后重试...")
            time.sleep(10)
            return get_cid(bvid)  # 递归重试

        response.raise_for_status()
        data = response.json()
        if data['code'] == 0 and data['data']:
            return data['data'][0]['cid']
        print(f"获取CID失败(BV号:{bvid}): 无有效数据")
        return None
    except Exception as e:
        print(f"获取CID失败(BV号:{bvid}): {str(e)}")
        return None


def get_danmaku(cid, bvid):
    """获取弹幕数据"""
    url = f'https://api.bilibili.com/x/v1/dm/list.so?oid={cid}'
    try:
        # 动态设置 Referer
        req_headers = headers.copy()
        req_headers['Referer'] = f'https://www.bilibili.com/video/{bvid}'
        if COOKIE:
            req_headers['Cookie'] = COOKIE

        response = requests.get(url, headers=req_headers, timeout=10)

        # 检查 412 错误
        if response.status_code == 412:
            print(f"触发412错误，等待15秒后重试...")
            time.sleep(15)
            return get_danmaku(cid, bvid)  # 递归重试

        response.raise_for_status()
        data = response.content

        # 解析XML弹幕
        danmaku_list = []
        pattern = re.compile(r'<d p="(.*?)">(.*?)</d>')
        matches = pattern.findall(data.decode('utf-8', errors='ignore'))

        for match in matches:
            attrs = match[0].split(',')
            danmaku_list.append({
                'time': float(attrs[0]),
                'mode': int(attrs[1]),
                'size': int(attrs[2]),
                'color': int(attrs[3]),
                'timestamp': int(attrs[4]),
                'pool': int(attrs[5]),
                'sender': attrs[6],
                'content': match[1]
            })

        return danmaku_list

    except Exception as e:
        print(f"获取弹幕失败(CID:{cid}): {str(e)}")
        return None


def main():
    print("B站弹幕批量爬虫 v1.2")
    print("=" * 40)

    # 自动读取当前目录下的bvids.txt
    input_file = "bvids.txt"
    output_file = "damn.json"

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            bvids = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"错误: 找不到文件 {input_file}")
        print("请确保当前目录下存在bvids.txt文件，每行一个BV号")
        sys.exit(1)
    except Exception as e:
        print(f"读取文件失败: {str(e)}")
        sys.exit(1)

    if not bvids:
        print("错误: bvids.txt中没有有效的BV号")
        sys.exit(1)

    all_danmaku = {}
    processed = 0

    try:
        for bvid in tqdm(bvids, desc="正在处理视频"):
            if not bvid.startswith('BV'):
                print(f"跳过无效BV号: {bvid}")
                continue

            time.sleep(random.uniform(5, 10))

            cid = get_cid(bvid)
            if not cid:
                continue

            danmaku = get_danmaku(cid, bvid)
            if danmaku:
                all_danmaku[bvid] = {
                    'cid': cid,
                    'count': len(danmaku),
                    'danmaku': danmaku
                }
                processed += 1
                print(f"成功获取 {bvid} 的 {len(danmaku)} 条弹幕")
            else:
                print(f"未获取到 {bvid} 的弹幕")

    except KeyboardInterrupt:
        print("\n用户中断操作，正在保存已获取数据...")
    except Exception as e:
        print(f"程序运行出错: {str(e)}")
    finally:
        # 保存结果
        if all_danmaku:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(all_danmaku, f, ensure_ascii=False, indent=2)
                print(f"\n成功保存 {processed}/{len(bvids)} 个视频的弹幕到 {output_file}")
            except Exception as e:
                print(f"保存文件失败: {str(e)}")
        else:
            print("没有获取到任何弹幕数据")


if __name__ == '__main__':
    main()