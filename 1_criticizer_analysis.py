# %% データ読込
import pandas as pd

from read_config import read_config

cfg, _ = read_config()
# 各種定数の指定
NOX_CSV_PATH = f'{cfg["Path"]["NoxInfluencerOutput"]}\\youtube_stats_history.csv'  # NoxInfluencer取得データの格納パス
AFTER_FLAMING = 40  # 炎上後の分析対象日数
BEFORE_FLAMING = 84  # 炎上前の分析対象日数
# データの読込
df_channels = pd.read_csv('./channel_ids.csv', encoding='utf_8_sig', parse_dates=['flaming_date'])
df_noxinfluencer = pd.read_csv(NOX_CSV_PATH, encoding='utf_8_sig', parse_dates=['date', 'acquisition_date'])
# 読み込んだデータを結合
df = pd.merge(df_noxinfluencer, df_channels, how='left', left_on='channel_name', right_on='name').drop(columns=['name'])
# 2動画以上アップロードしたチャンネルに絞る
df_criticizer = df[(df['classification']=='criticizer')
                & (df['critcizing_videos'] >= 2)].copy()
print(df_criticizer.shape)
df_criticizer.head()

# %% 批評者の登録者数と再生回数の炎上前後可視化
import matplotlib.pyplot as plt
from matplotlib import colors
from datetime import timedelta
color_list = list(colors.TABLEAU_COLORS.values())  # プロット用の色

# 炎上日
flaming_date = df[df['transferred_name']=='influencer']['flaming_date'][0].to_pydatetime()

# 炎上前後でデータを分けるメソッド
def devide_before_after(df_src, date_col, flaming_date, before_period, after_period):
    df_before = df_src[
        (df_src[date_col] >= flaming_date - timedelta(days=before_period))
        & (df_src[date_col] < flaming_date)]
    df_after = df_src[
        (df_src[date_col] >= flaming_date)
        & (df_src[date_col] < flaming_date + timedelta(days=after_period))]
    return df_before, df_after

# 炎上前後の登録者数と再生回数をプロットするメソッド
def plot_before_after(ax, date_col, y_col, df_src, flaming_date, before_period, after_period, c, name):
    # 炎上前後でデータを分ける
    df_before, df_after = devide_before_after(df_src, date_col, flaming_date, before_period, after_period)
    # プロット
    ax.plot(df_before[date_col].values, df_before[y_col].values,
             c=c, label=f'{name} before', alpha=0.5)
    ax.plot(df_after[date_col].values, df_after[y_col].values,
            c=c, label=f'{name} after', alpha=1.0)
    ax.axvline(x=flaming_date, color='gray')
    ax.set_title(y_col)
    ax.legend(loc='upper left')
    ax.set_xlabel(f'{date_col}')
    ax.set_ylabel(f'{y_col}')

# 炎上前週を100として登録者数と再生回数を正規化するメソッド
def normalize_last_week(df_src, flaming_date):
    df_last_week = df_src[
        (df_src['date'] >= flaming_date - timedelta(days=7))
        & (df_src['date'] < flaming_date)]
    subscriber_mean = df_last_week['subscriber_count'].mean()  # 前週平均登録者
    view_mean = df_last_week['view_count'].mean()  # 前週平均再生回数
    df_src['subscriber_norm'] = df_src['subscriber_count'] / subscriber_mean * 100  # 登録者数の正規化
    df_src['view_norm'] = df_src['view_count'] / view_mean * 100  # 再生回数の正規化
    return df_src
    
# プロット用のaxes
fig, axes = plt.subplots(2, 1, figsize=(12, 12))

# チャンネルごとにループ
for i, (name, df_ch) in enumerate(df_criticizer.groupby('transferred_name')):
    # 炎上前週を100として登録者数と再生回数を正規化
    df_ch = normalize_last_week(df_ch, flaming_date=flaming_date)
    # 正規化したチャンネル登録者数をプロット
    plot_before_after(ax=axes[0], df_src=df_ch,
                      date_col='date', y_col='subscriber_norm', flaming_date=flaming_date,
                      before_period=BEFORE_FLAMING, after_period=AFTER_FLAMING,
                      c=color_list[i], name=name)
    # 正規化した再生数をプロット
    plot_before_after(ax=axes[1], df_src=df_ch,
                      date_col='date', y_col='view_norm', flaming_date=flaming_date,
                      before_period=BEFORE_FLAMING, after_period=AFTER_FLAMING,
                      c=color_list[i], name=name)
# 図中に炎上日をプロット
axes[0].text(flaming_date, axes[0].get_ylim()[0],
            f'Flaming date = {flaming_date.strftime("%Y/%m/%d")}', verticalalignment='bottom', horizontalalignment='left')
axes[1].text(flaming_date, axes[1].get_ylim()[0],
            f'Flaming date = {flaming_date.strftime("%Y/%m/%d")}', verticalalignment='bottom', horizontalalignment='left')

# %% 視聴回数がマイナスのデータをゼロにして再プロット
df_criticizer.loc[df_criticizer['view_count'] < 0, 'view_count'] = 0

# プロット用のaxes
fig, axes = plt.subplots(2, 1, figsize=(12, 12))
# チャンネルごとにループ
for i, (name, df_ch) in enumerate(df_criticizer.groupby('transferred_name')):
    # 炎上前週を100として登録者数と再生回数を正規化
    df_ch = normalize_last_week(df_ch, flaming_date=flaming_date)
    # 正規化したチャンネル登録者数をプロット
    plot_before_after(ax=axes[0], df_src=df_ch,
                      date_col='date', y_col='subscriber_norm', flaming_date=flaming_date,
                      before_period=BEFORE_FLAMING, after_period=AFTER_FLAMING,
                      c=color_list[i], name=name)
    # 正規化した再生数をプロット
    plot_before_after(ax=axes[1], df_src=df_ch,
                      date_col='date', y_col='view_norm', flaming_date=flaming_date,
                      before_period=BEFORE_FLAMING, after_period=AFTER_FLAMING,
                      c=color_list[i], name=name)
# 図中に炎上日をプロット
axes[0].text(flaming_date, axes[0].get_ylim()[0],
            f'Flaming date = {flaming_date.strftime("%Y/%m/%d")}', verticalalignment='bottom', horizontalalignment='left')
axes[1].text(flaming_date, axes[1].get_ylim()[0],
            f'Flaming date = {flaming_date.strftime("%Y/%m/%d")}', verticalalignment='bottom', horizontalalignment='left')


# %% 視聴回数のスペクトル解析
import numpy as np
# 炎上前週を100として登録者数と再生回数を正規化
df_criticizer = df_criticizer.groupby('transferred_name').apply(lambda group: normalize_last_week(group, flaming_date))
# 全チャンネルで日ごとに平均をとる
view_counts_mean = df_criticizer.groupby('date')['view_norm'].mean().values
# ハミング関数で両端を滑らかに
view_counts_hamming = (view_counts_mean - np.mean(view_counts_mean)) * np.hamming(len(view_counts_mean))
# フーリエ変換
dft = np.fft.fft(view_counts_hamming)
freq = np.fft.fftfreq(len(view_counts_mean), d=1.0)
# 変換結果をプロット
fig, axes = plt.subplots(4, 1, figsize=(10, 15))
axes[0].plot(range(len(view_counts_mean)), view_counts_mean)
axes[0].set_title('view_count')
axes[0].set_xlabel('date')
axes[1].plot(range(len(view_counts_mean)), view_counts_hamming)
axes[1].set_title('hamming')
axes[1].set_xlabel('date')
axes[2].plot(1/freq[1:int(len(view_counts_mean) / 2)], abs(dft[1:int(len(view_counts_mean) / 2)]), c='orange')
axes[2].set_title('FFT')
axes[2].set_xscale('log')
axes[2].set_xlabel('date')
axes[3].plot(1/freq[1:int(len(view_counts_mean) / 2)], abs(dft[1:int(len(view_counts_mean) / 2)]), c='darkorange')
axes[3].set_title('FFT 1-10 days')
axes[3].set_xlim(1, 10)
axes[3].set_xlabel('date')
plt.tight_layout()

# %% 登録者数と再生回数を1週間ごとに平均してプロット
import math
# 炎上日からの経過日、経過週を計算
df_criticizer['date_diff'] = (df_criticizer['date'] - flaming_date).dt.total_seconds() / 3600 / 24
df_criticizer['week_diff'] = df_criticizer['date_diff'].map(lambda x: math.floor(x/7))
# 週ごとの平均登録者数と平均再生回数を求める
df_criticizer_grby_week = df_criticizer.groupby(['transferred_name', 'week_diff']).agg({
    'date': 'min',
    'subscriber_norm': 'mean',
    'view_norm': 'mean'
})

# プロット用のaxes
fig, axes = plt.subplots(2, 1, figsize=(12, 12))
# チャンネルごとにループ
for i, (name, df_ch_grby_week) in enumerate(df_criticizer_grby_week.groupby('transferred_name')):
    # 炎上前後の登録者数プロット
    plot_before_after(ax=axes[0], df_src=df_ch_grby_week,
                    date_col='date', y_col='subscriber_norm', flaming_date=flaming_date,
                    before_period=BEFORE_FLAMING, after_period=AFTER_FLAMING,
                    c=color_list[i], name=name)
    # 炎上前後の再生回数プロット
    plot_before_after(ax=axes[1], df_src=df_ch_grby_week,
                    date_col='date', y_col='view_norm', flaming_date=flaming_date,
                    before_period=BEFORE_FLAMING, after_period=AFTER_FLAMING,
                    c=color_list[i], name=name)
axes[0].set_ylim(0,)
axes[1].set_ylim(0,)

# %% 登録者数と再生回数の増加率
fig, ax = plt.subplots(1, 1, figsize=(6, 6))  # プロット用のaxes
subscriber_increase_list = []  # 登録者数増加率格納用
view_increase_list = []  # 再生回数増加率格納用
# チャンネルごとにループ
for i, (name, df_ch) in enumerate(df_criticizer.groupby('transferred_name')):
    # 炎上前後39日ずつを抜き出し
    df_before, df_after = devide_before_after(df_ch, 'date', flaming_date,
                            before_period=AFTER_FLAMING, after_period=AFTER_FLAMING)
    # 炎上日から分析対象日数(AFTER_FLAMING)後までの登録者数の増加率
    subscribers_flaming_day = df_before['subscriber_count'].iloc[-1]
    subscribers_after_flaming = df_after['subscriber_count'].iloc[-1]
    subscriber_increase_ratio = (subscribers_after_flaming / subscribers_flaming_day) * 100 - 100
    subscriber_increase_list.append(subscriber_increase_ratio)
    # 炎上前と炎上後の再生回数増加率
    views_before_flaming = df_before['view_count'].mean()
    views_after_flaming = df_after['view_count'].mean()
    view_increase_ratio = (views_after_flaming / views_before_flaming) * 100 - 100
    view_increase_list.append(view_increase_ratio)
    # 散布図プロット
    ax.scatter(subscriber_increase_ratio, view_increase_ratio,
               c=color_list[i], label=name)
    ax.legend(loc='upper left')
xlim = ax.get_xlim()[1]
ylim = ax.get_ylim()[1]
ax.set_xlim(-xlim, xlim)
ax.set_ylim(-ylim, ylim)
ax.set_xlabel('Subscriber increase [%]')
ax.set_ylabel('View increase [%]')
ax.axvline(x=0, color='gray', alpha=0.2)
ax.axhline(y=0, color='gray', alpha=0.2)

print(f'チャンネル登録者数増加率平均={np.mean(subscriber_increase_list)}%')
print(f'再生回数数増加率平均={np.mean(view_increase_list)}%')

# %% 登録者数と再生回数の増加率（炎上が発生していない期間）
fig, ax = plt.subplots(1, 1, figsize=(6, 6))  # プロット用のaxes
subscriber_increase_list = []  # 登録者数増加率格納用
view_increase_list = []  # 再生回数増加率格納用
# チャンネルごとにループ
for i, (name, df_ch) in enumerate(df_criticizer.groupby('transferred_name')):
    # 炎上前後39日ずつを抜き出し
    df_before, df_after = devide_before_after(df_ch, 'date', flaming_date - timedelta(days=AFTER_FLAMING),
                            before_period=AFTER_FLAMING, after_period=AFTER_FLAMING)
    # 炎上日から分析対象日数(AFTER_FLAMING)後までの登録者数の増加率
    subscribers_flaming_day = df_before['subscriber_count'].iloc[-1]
    subscribers_after_flaming = df_after['subscriber_count'].iloc[-1]
    subscriber_increase_ratio = (subscribers_after_flaming / subscribers_flaming_day) * 100 - 100
    subscriber_increase_list.append(subscriber_increase_ratio)
    # 炎上前と炎上後の再生回数増加率
    views_before_flaming = df_before['view_count'].mean()
    views_after_flaming = df_after['view_count'].mean()
    view_increase_ratio = (views_after_flaming / views_before_flaming) * 100 - 100
    view_increase_list.append(view_increase_ratio)
    # 散布図プロット
    ax.scatter(subscriber_increase_ratio, view_increase_ratio,
               c=color_list[i], label=name)
    ax.legend(loc='upper left')
ax.set_xlim(-xlim, xlim)
ax.set_ylim(-ylim, ylim)
ax.set_xlabel('Subscriber increase [%]')
ax.set_ylabel('View increase [%]')
ax.axvline(x=0, color='gray', alpha=0.2)
ax.axhline(y=0, color='gray', alpha=0.2)

print(f'チャンネル登録者数増加率平均={np.mean(subscriber_increase_list)}%')
print(f'再生回数数増加率平均={np.mean(view_increase_list)}%')