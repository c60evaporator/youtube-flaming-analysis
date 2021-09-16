# YouTube情報の蓄積
import pandas as pd
import os
import csv

from read_config import read_config
from get_youtube_data import *

cfg, channel_ids = read_config()
API_KEY = cfg['APIKeys']['YoutubeAPIKey']  # APIキー
CHANNEL_IDS = channel_ids['channel_id'].values.tolist()  # インフルエンサーのチャンネルID
CSV_PATH = f'{cfg["Path"]["CSVOutput"]}\\youtube_stats_summary.csv'
SAVE_DETAIL_DIR = f'{cfg["Path"]["DetailCSVOutput"]}'

# チャンネル登録者数・再生数を取得
start_date = datetime.today()
channel_info_list = []
for i, channel_id in enumerate(CHANNEL_IDS):
    # チャンネルIDからチャンネル情報
    print(f'Channnel No.{i} start')
    if i <= 4:
        subscriber_and_viewer_dict = get_subscriber_viewcount_detail(channel_id, API_KEY, save_detail=True, save_detail_dir=SAVE_DETAIL_DIR)
    else:
        subscriber_and_viewer_dict = get_subscriber_viewcount(channel_id, API_KEY)
    channel_info_list.append(subscriber_and_viewer_dict)
df_channel_info = pd.DataFrame(channel_info_list)
df_channel_info['start_date'] = start_date
df_channel_info['end_date'] = datetime.today()

# CSV出力（追記するため）
#出力ファイル存在しないとき、新たに作成
if not os.path.exists(CSV_PATH):
    df_channel_info.to_csv(CSV_PATH, encoding='utf_8_sig', index=False)
#出力ファイル存在するとき、1行ずつ追加
else:
    with open(CSV_PATH, 'a', encoding='utf_8_sig', newline='') as f:
        for _, row in df_channel_info.iterrows():
            writer = csv.DictWriter(f, row.to_dict().keys())
            writer.writerow(row.to_dict())