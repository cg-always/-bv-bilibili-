import requests
import re
import time
import random
import json
from tqdm import tqdm
import sys

# 要改
headers = {
    'User-Agent': '',
    'Referer': 'https://www.bilibili.com/',
    'Origin': 'https://www.bilibili.com',
    'Accept': '',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Connection': 'keep-alive',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache'
}

#要改
# 如果需要登录才能访问的弹幕，添加你的 Cookie
COOKIE = ""

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
