import requests
import json
import pandas as pd
import csv
import os
from datetime import datetime

from get_youtube_data import get_channel_detail
from read_config import read_config

cfg, _ = read_config()
API_KEY = cfg['APIKeys']['YoutubeAPIKey']  # APIキー
CSV_PATH = f'{cfg["Path"]["NoxInfluencerOutput"]}\\youtube_stats_history.csv'  # CSV出力先
URL_SUBSCRIBERS = ''
URL_VIEWCOUNT = ''

# 登録者数の履歴を取得
def get_subscribers_history(url_subscribers):
    response = requests.get(url_subscribers)
    response_dict = json.loads(response.text)
    df_response = pd.DataFrame(response_dict['retData']['history'])
    df_response['date'] = pd.to_datetime(df_response['date'])  # date列をdatetime型に変換
    df_response = df_response.rename(columns={'value': 'subscriber_count'})  # 列名変更
    return df_response

# 視聴者数の履歴を取得
def get_viewcount_history(url_viewcount):
    response = requests.get(url_viewcount)
    response_dict = json.loads(response.text)
    df_response = pd.DataFrame(response_dict['retData']['history'])
    df_response['date'] = pd.to_datetime(df_response['date'])  # date列をdatetime型に変換
    df_response = df_response.rename(columns={'value': 'total_view_count'})  # 列名変更
    return df_response


df_subscribers = get_subscribers_history(URL_SUBSCRIBERS)
df_viewcount = get_viewcount_history(URL_VIEWCOUNT)
df_history = pd.merge(df_subscribers, df_viewcount[['date', 'total_view_count']], how='left', on='date')
# チャンネルIDからチャンネル
channel_id = URL_SUBSCRIBERS.split('trend/')[1].split('?')
df_history['channel_name'] = get_channel_detail(channel_id, API_KEY)['snippet']['title']
df_history['acquisition_date'] = datetime.today()

# CSV出力（追記するため）
#出力ファイル存在しないとき、新たに作成
if not os.path.exists(CSV_PATH):
    df_history.to_csv(CSV_PATH, encoding='utf_8_sig', index=False)
#出力ファイル存在するとき、1行ずつ追加
else:
    with open(CSV_PATH, 'a', encoding='utf_8_sig', newline='') as f:
        for _, row in df_history.iterrows():
            writer = csv.DictWriter(f, row.to_dict().keys())
            writer.writerow(row.to_dict())