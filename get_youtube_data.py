from googleapiclient.discovery import build
import pandas as pd
from datetime import datetime

API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

def _get_playlist_from_user(channel_id, api_key):
    """ユーザIDからプレイリストIDを取得"""
    youtube = build(API_SERVICE_NAME, API_VERSION, developerKey=api_key)
    search_response = youtube.channels().list(
        part= 'snippet,contentDetails',
        id=channel_id,
        ).execute()
    return search_response['items'][0]

def _get_channel_detail(channel_id, api_key):
    youtube = build(API_SERVICE_NAME, API_VERSION, developerKey=api_key)
    search_response = youtube.channels().list(
        part='snippet,statistics',
        id=channel_id,
    ).execute()
    print(f'Channel_name={search_response["items"][0]["snippet"]["title"]}')
    return search_response['items'][0]

def _get_videos_from_playlist(playlist_id, apy_key):
    """プレイリストIDから含まれる動画情報のリストを取得"""
    responses = []
    nextPageToken = 'start'
    counts = 0
    # 50件ずつ動画を取得
    while(nextPageToken is not None):
        youtube = build(API_SERVICE_NAME, API_VERSION, developerKey=apy_key)
        # 最初の50件
        if(nextPageToken == 'start'):
            search_response = youtube.playlistItems().list(
            part= 'snippet',
            playlistId=playlist_id,
            maxResults = 50,
            ).execute()
            nextPageToken = search_response['nextPageToken'] if 'nextPageToken' in search_response.keys() else None
        # 最初の50件以外
        else:
            search_response = youtube.playlistItems().list(
            part= 'snippet',
            playlistId=playlist_id,
            maxResults = 50,
            pageToken = nextPageToken
            ).execute()
            nextPageToken = search_response['nextPageToken'] if 'nextPageToken' in search_response.keys() else None
        # 取得した動画情報のリストをresponsesに追加
        responses.extend(search_response['items'])
        counts += len(search_response['items'])

    print('Load '+str(counts)+' videos...')
    return responses

def _get_video_detail(video_id, api_key):
    """動画IDから動画情報詳細を取得"""
    youtube = build(API_SERVICE_NAME, API_VERSION, developerKey=api_key)
    search_response = youtube.videos().list(
        part= 'statistics,contentDetails',
        id=video_id,
        ).execute()
    video_detail = search_response['items'][0]
    return video_detail

def _get_date(str_date):
    """日時文字列をdatetimeに変換(フォーマットが動画により変わるので注意)"""
    date_list = str_date.replace('Z','').split('T')
    year, month, date = date_list[0].split('-')
    hour, minute, sec = date_list[1].split(':')
    sec = sec.split('.')[0]
    return datetime(int(year),int(month),int(date),int(hour),int(minute),int(sec))

def get_subscriber_viewer_count(channel_id, api_key, save_detail=False, save_detail_dir=None):
    """チャンネルIDから動画の総再生数とチャンネル登録者数を取得"""
    
    # 取得した情報の保持用dict
    subscriber_viewer_dict = {}
    subscriber_viewer_dict['api_date'] = datetime.today()
    subscriber_viewer_dict['channel_id'] = channel_id
    
    # チャンネルIDからチャンネル情報を取得
    channel_detail = _get_channel_detail(channel_id, api_key)
    subscriber_viewer_dict['channel_name'] = channel_detail['snippet']['title']  # チャンネル名
    subscriber_viewer_dict['channel_publish_date'] = _get_date(channel_detail['snippet']['publishedAt'])  # チャンネル作成日
    subscriber_viewer_dict['subscriber_count'] = int(channel_detail['statistics']['subscriberCount'])  # 登録者数
    subscriber_viewer_dict['total_view_count'] = int(channel_detail['statistics']['viewCount'])  # 動画総再生数
    subscriber_viewer_dict['video_count'] = int(channel_detail['statistics']['videoCount'])  # 動画数

    # チャンネルIDからプレイリストID取得
    playlist_info = _get_playlist_from_user(channel_id, api_key)
    playlist_id = playlist_info['contentDetails']['relatedPlaylists']['uploads']

    # プレイリストIDから動画ID取得
    videos_info = _get_videos_from_playlist(playlist_id, api_key)

    # 動画IDから動画詳細を取得
    if save_detail:
        detail_list = []
        for i, video_info in enumerate(videos_info):
            video_id = video_info['snippet']['resourceId']['videoId']
            # 動画詳細情報を取得してdictに格納
            detail_dict = {}
            video_detail = _get_video_detail(video_id, api_key)
            detail_dict['video_id'] = video_id  # 動画作成日
            detail_dict['video_name'] = video_info['snippet']['title']  # 動画名
            detail_dict['video_publish_date'] = _get_date(video_info['snippet']['publishedAt'])  # 動画作成日
            detail_dict['view_count'] = int(video_detail['statistics']['viewCount'])  # 再生数
            detail_dict['comment_count'] = int(video_detail['statistics']['commentCount'])  # コメント数
            # 取得した詳細情報をlistに追加
            detail_list.append(detail_dict)
            print(f'channel name = {subscriber_viewer_dict["channel_name"]}, {i}/{len(videos_info)}')
        df_video_detail = pd.DataFrame(detail_list)
        df_count_sum = df_video_detail[['view_count', 'comment_count']].sum()
        subscriber_viewer_dict['view_count_sum'] = df_count_sum['view_count']
        subscriber_viewer_dict['comment_count_sum'] = df_count_sum['comment_count']

        filename = f'{subscriber_viewer_dict["channel_name"]}_{subscriber_viewer_dict["api_date"].strftime("%Y%m%d%H%M")}.csv'
        df_video_detail.to_csv(f'{save_detail_dir}\\{filename}', encoding='utf_8_sig', index=False)
    
    return subscriber_viewer_dict