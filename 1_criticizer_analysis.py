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
# 2動画以上アップロードした批評者チャンネルに絞る
df_criticizer = df[(df['classification']=='criticizer')
                & (df['critcizing_videos'] >= 2)].copy()
print(df_criticizer.shape)
df_criticizer.head()

# %% 批評者の登録者数と再生回数の炎上前後可視化
import matplotlib.pyplot as plt
from matplotlib import colors
from datetime import timedelta
color_list = list(colors.TABLEAU_COLORS.values())  # プロット用の色
color_list.extend(list(colors.CSS4_COLORS.values()))

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

# %% 再生回数がマイナスのデータをゼロにして再プロット
def modify_minus_view(df_ch, y_col, date_col):
    """再生回数がマイナスのデータをゼロに＆30日以内に通常の10倍以上のデータがあれば補正"""
    minus_idx = df_ch[df_ch[y_col] < 0].index  # 再生回数がマイナスのインデックス
    df_ch.loc[minus_idx, y_col] = 0  # 再生回数がマイナスのデータをゼロに補正
    for idx in minus_idx:
        minus_date = df_ch[date_col].at[idx].to_pydatetime()
        # マイナスから30日以内の中央値
        median_minus_month = df_ch[(df_ch[date_col] > minus_date)
                & (df_ch[date_col] <= minus_date + timedelta(days=30))
                ][y_col].median()
        # マイナスから30日以内で再生回数が中央値の10倍を超えたら中央値で補正
        df_ch.loc[(df_ch[date_col] > minus_date)
                & (df_ch[date_col] <= minus_date + timedelta(days=30))
                & (df_ch[y_col] > median_minus_month * 10),
                y_col] = median_minus_month
    return df_ch
# 再生回数がマイナスのデータ＆直後の異常データを補正
df_criticizer = df_criticizer.groupby('transferred_name').apply(
                    lambda group: modify_minus_view(group, 'view_count', 'date'))
# 炎上前週を100として登録者数と再生回数を正規化
df_criticizer = df_criticizer.groupby('transferred_name').apply(
                    lambda group: normalize_last_week(group, flaming_date))

# プロット用のaxes
fig, axes = plt.subplots(2, 1, figsize=(12, 12))
# チャンネルごとにループ
for i, (name, df_ch) in enumerate(df_criticizer.groupby('transferred_name')):
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


# %% 再生回数のスペクトル解析
import numpy as np
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

def plot_increase_scatter(x_before, x_after, y_before, y_after, label, ax):
    """炎上前後の登録者数と再生回数の増加率を散布図プロット"""
    # 炎上日から分析対象日数(AFTER_FLAMING)後までの登録者数の増加率
    x_increase_ratio = (x_after / x_before) * 100 - 100
    # 炎上前と炎上後の再生回数増加率
    y_increase_ratio = (y_after / y_before) * 100 - 100
    # 散布図プロット
    ax.scatter(x_increase_ratio, y_increase_ratio,
               c=color_list[i], label=label)
    ax.legend(loc='upper left')
    ax.set_xlabel('Subscriber increase [%]')
    ax.set_ylabel('View increase [%]')
    return x_increase_ratio, y_increase_ratio

# チャンネルごとにループ
for i, (name, df_ch) in enumerate(df_criticizer.groupby('transferred_name')):
    # 炎上前後40日ずつを抜き出し
    df_before, df_after = devide_before_after(df_ch, 'date', flaming_date,
                            before_period=AFTER_FLAMING, after_period=AFTER_FLAMING)
    # 炎上前後の増加率を散布図プロット
    subscriber_increase_ratio, view_increase_ratio \
        = plot_increase_scatter(x_before=df_before['subscriber_norm'].iloc[-1], x_after=df_after['subscriber_norm'].iloc[-1],
                                y_before=df_before['view_norm'].mean(), y_after=df_after['view_norm'].mean(), label=name, ax=ax)
    subscriber_increase_list.append(subscriber_increase_ratio)
    view_increase_list.append(view_increase_ratio)
xlim = ax.get_xlim()[1]
ylim = ax.get_ylim()[1]
ax.set_xlim(-xlim, xlim)
ax.set_ylim(-ylim, ylim)
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
    # 炎上前後40日ずつを抜き出し
    df_before, df_after = devide_before_after(df_ch, 'date', flaming_date - timedelta(days=AFTER_FLAMING),
                            before_period=AFTER_FLAMING, after_period=AFTER_FLAMING)
    # 炎上前後の増加率を散布図プロット
    subscriber_increase_ratio, view_increase_ratio \
        = plot_increase_scatter(x_before=df_before['subscriber_norm'].iloc[-1], x_after=df_after['subscriber_norm'].iloc[-1],
                          y_before=df_before['view_norm'].mean(), y_after=df_after['view_norm'].mean(), label=name, ax=ax)
    subscriber_increase_list.append(subscriber_increase_ratio)
    view_increase_list.append(view_increase_ratio)
ax.set_xlim(-xlim, xlim)
ax.set_ylim(-ylim, ylim)
ax.axvline(x=0, color='gray', alpha=0.2)
ax.axhline(y=0, color='gray', alpha=0.2)

print(f'チャンネル登録者数増加率平均={np.mean(subscriber_increase_list)}%')
print(f'再生回数数増加率平均={np.mean(view_increase_list)}%')

# %% 自己相関コレログラム(http://www.mi.u-tokyo.ac.jp/consortium2/pdf/4-4_literacy_level_note.pdf)
from statsmodels.graphics.tsaplots import plot_acf
n_channels = df_criticizer['transferred_name'].nunique()
fig, axes = plt.subplots(n_channels, 2, figsize=(12, n_channels*3))  # プロット用のaxes
# チャンネルごとにループ
for i, (name, df_ch) in enumerate(df_criticizer.groupby('transferred_name')):
    # 炎上前後データを抜き出し
    df_before, df_after = devide_before_after(df_ch, 'date', flaming_date,
                            before_period=BEFORE_FLAMING, after_period=AFTER_FLAMING)
    # 炎上前データの登録者数＆再生回数の自己相関コレログラム表示
    plot_acf(df_before['subscriber_norm'], lags=31, ax=axes[i][0],
             title=f'subscriber_{name}')
    plot_acf(df_before['view_norm'], lags=31, ax=axes[i][1],
             title=f'view_{name}')
plt.tight_layout()

# %% 差分の自己相関コレログラム（登録者数）
from statsmodels.graphics.tsaplots import plot_acf
n_channels = df_criticizer['transferred_name'].nunique()

def plot_diff_acf(x, lags, axes_diff, axes_acf, name):
    """差分の自己相関コレログラム描画用メソッド"""
    # 階差1のデータプロット
    axes_diff[0].plot(np.diff(x))
    axes_diff[0].set_title(f'1st_order_{name}')
    # 階差1の自己相関コレログラム
    plot_acf(np.diff(x),
             lags=lags, ax=axes_acf[0],
             title=f'1st_order_correlation_{name}')
    # 階差2のデータプロット
    axes_diff[1].plot(np.diff(np.diff(x)))
    axes_diff[1].set_title(f'2nd_order_{name}')
    # 階差2の自己相関コレログラム
    plot_acf(np.diff(np.diff(x)),
             lags=lags, ax=axes_acf[1],
             title=f'2nd_order_correlation_{name}')
    # 階差3のデータプロット
    axes_diff[2].plot(np.diff(np.diff(np.diff(x))))
    axes_diff[2].set_title(f'3rd_order_{name}')
    # 階差3の自己相関コレログラム
    plot_acf(np.diff(np.diff(np.diff(x))),
             lags=lags, ax=axes_acf[2],
             title=f'3rd_order_correlation_{name}')

fig, axes = plt.subplots(n_channels * 2, 3, figsize=(18, n_channels*6))  # プロット用のaxes
# チャンネルごとにループ
for i, (name, df_ch) in enumerate(df_criticizer.groupby('transferred_name')):
    # 炎上前後データを抜き出し
    df_before, df_after = devide_before_after(df_ch, 'date', flaming_date,
                            before_period=BEFORE_FLAMING, after_period=AFTER_FLAMING)
    # 差分の自己相関コレログラム描画
    plot_diff_acf(x=df_before['subscriber_norm'].to_numpy(), lags=31,
                  axes_diff=axes[i*2], axes_acf=axes[i*2+1], name=name)

plt.tight_layout()

# %% 差分の自己相関コレログラム（再生回数）
from statsmodels.graphics.tsaplots import plot_acf
n_channels = df_criticizer['transferred_name'].nunique()
fig, axes = plt.subplots(n_channels * 2, 3, figsize=(18, n_channels*6))  # プロット用のaxes
# チャンネルごとにループ
for i, (name, df_ch) in enumerate(df_criticizer.groupby('transferred_name')):
    # 炎上前後データを抜き出し
    df_before, df_after = devide_before_after(df_ch, 'date', flaming_date,
                            before_period=BEFORE_FLAMING, after_period=AFTER_FLAMING)
    # 差分の自己相関コレログラム描画
    plot_diff_acf(x=df_before['view_norm'].to_numpy(), lags=31,
                  axes_diff=axes[i*2], axes_acf=axes[i*2+1], name=name)
plt.tight_layout()

# %% ARIMAモデルのp, qを推定し、モデル予測結果をプロット（登録者数）
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import arma_order_select_ic
D_SUBSCRIBER = 2  # ARIMAモデルのパラメータd（階差の数）
P_MAX_SUBSCRIBER = 4  # ARIMAモデルのパラメータpの最大値
Q_MAX_SUBSCRIBER = 2  # ARIMAモデルのパラメータqの最大値
ALPHA = 0.05  # 区間予測の有意水準

def optimize_arima_pq(x, d, p_max, q_max):
    """ARIMAモデルのpとqを推定するメソッド"""
    diff = x.copy()
    for i in range(d):  # d回差分をとる
        diff = diff.diff()
    diff = diff.dropna()  # nanを削除
    # diffが全て0なら、p=0, q=0を返す
    if diff.nunique() == 1 and diff.iat[0] == 0:
        return 0, 0
    # ARMAのパラメータ推定
    res = arma_order_select_ic(diff, ic='aic', trend='nc',
                               max_ar=p_max, max_ma=q_max)
    print(res['aic'])
    print(f'best p={res["aic_min_order"][0]}, q={res["aic_min_order"][1]}')
    return res['aic_min_order']

def plot_arima_predict(x, order, predict_start, predict_end, ax, alpha=None):
    """推定したパラメータでARIMAモデル作成し、予測結果をプロット"""
    # ARIMAモデル作成
    model = ARIMA(x, order=order)
    res = model.fit()  # 学習
    print(res.summary())
    # モデルで将来予測
    pred = res.get_prediction(start=predict_start,
                                 end=predict_end,
                                 dynamic=False)
    pred_mean = pred.predicted_mean
    pred_ci = pred.conf_int(alpha=alpha)
    ax.plot(x, label='observed')
    ax.plot(pred_mean, label='predict', c='green')
    if alpha is not None:
        ax.fill_between(pred_ci.index,
                        pred_ci.iloc[:, 0],
                        pred_ci.iloc[:, 1],
                        color='green', alpha=0.2)
    return pred_mean

def compare_pred_and_flaming(df_src, date_col, y_col, ax,
                             flaming_date, before_period, after_period,
                             d, p_max, q_max, alpha):
    """ARIMAモデルで予測して炎上後の実データと比較プロットするメソッド"""
    # 炎上前後データを抜き出し
    df_before, df_after = devide_before_after(df_src, date_col, flaming_date,
                            before_period=before_period, after_period=after_period)
    # 時間がindexのSeriesを作成
    x_series = df_before[[y_col, date_col]]
    x_series = x_series.set_index(date_col)[y_col]
    # パラメータpとqの推定
    best_p, best_q= optimize_arima_pq(x=x_series,
                                      d=d,
                                      p_max=p_max,
                                      q_max=q_max)
    # 推定したパラメータでARIMAモデル作成し、予測結果をプロット
    pred_mean = plot_arima_predict(x=x_series, order=(best_p, d, best_q),
                                   predict_start=flaming_date, 
                                   predict_end=flaming_date + timedelta(days=after_period-1),
                                   ax=ax, alpha=alpha)
    # 実際の炎上後の推移をプロット
    ax.plot(df_after[date_col].values, df_after[y_col].values,
                 label='after flaming', c='red')
    ax.legend(loc='upper left')
    ax.set_title(f'{y_col}_{name}')
    ax.text(x_series.index.min(), ax.get_ylim()[0],
            f'p={best_p}\nq={best_q}', verticalalignment='bottom', horizontalalignment='left')
    return pred_mean

pred_subscribers = {}  # 予測結果保持用
fig, axes = plt.subplots(n_channels, 1, figsize=(8, n_channels*3))  # プロット用のaxes
# チャンネルごとにループ
for i, (name, df_ch) in enumerate(df_criticizer.groupby('transferred_name')):
    # ARIMAモデルで予測して炎上後の実データと比較プロット
    pred_subscribers[name] = compare_pred_and_flaming(df_src=df_ch, date_col='date', y_col='subscriber_norm', ax=axes[i],
                                    flaming_date=flaming_date, before_period=BEFORE_FLAMING, after_period=AFTER_FLAMING,
                                    d=D_SUBSCRIBER, p_max=P_MAX_SUBSCRIBER, q_max=Q_MAX_SUBSCRIBER, alpha=ALPHA)
plt.tight_layout()

# %% ARIMAモデルのp, qを推定し、モデル予測結果をプロット（再生回数）
D_VIEW = 1  # ARIMAモデルのパラメータd（階差の数）
P_MAX_VIEW = 4  # ARIMAモデルのパラメータpの最大値
Q_MAX_VIEW = 4  # ARIMAモデルのパラメータpの最大値
pred_views = {}  # 予測結果保持用
fig, axes = plt.subplots(n_channels, 1, figsize=(8, n_channels*3))  # プロット用のaxes
# チャンネルごとにループ
for i, (name, df_ch) in enumerate(df_criticizer.groupby('transferred_name')):
    pred_views[name] = compare_pred_and_flaming(df_src=df_ch, date_col='date', y_col='view_norm', ax=axes[i],
                                flaming_date=flaming_date, before_period=BEFORE_FLAMING, after_period=AFTER_FLAMING,
                                d=D_VIEW, p_max=P_MAX_VIEW, q_max=Q_MAX_VIEW, alpha=ALPHA)
plt.tight_layout()

# %% 登録者数と再生回数の予測値からの増加率
fig, ax = plt.subplots(1, 1, figsize=(6, 6))  # プロット用のaxes
subscriber_increase_list = []  # 登録者数増加率格納用
view_increase_list = []  # 再生回数増加率格納用
# チャンネルごとにループ
for i, (name, df_ch) in enumerate(df_criticizer.groupby('transferred_name')):
    # 炎上前後40日ずつを抜き出し
    df_before, df_after = devide_before_after(df_ch, 'date', flaming_date,
                            before_period=BEFORE_FLAMING, after_period=AFTER_FLAMING)
    # 炎上後の予測値に対する増加率を散布図プロット 
    subscriber_increase_ratio, view_increase_ratio \
        = plot_increase_scatter(x_before=pred_subscribers[name].iloc[-1], x_after=df_after['subscriber_norm'].iloc[-1],
                                y_before=pred_views[name].mean(), y_after=df_after['view_norm'].mean(), label=name, ax=ax)
    subscriber_increase_list.append(subscriber_increase_ratio)
    view_increase_list.append(view_increase_ratio)
ax.set_xlim(-xlim, xlim)
ax.set_ylim(-ylim, ylim)
ax.axvline(x=0, color='gray', alpha=0.2)
ax.axhline(y=0, color='gray', alpha=0.2)

print(f'チャンネル登録者数増加率平均={np.mean(subscriber_increase_list)}%')
print(f'再生回数数増加率平均={np.mean(view_increase_list)}%')

# %% 登録者数・再生回数増加率と批評動画アップロード数の比較
from seaborn_analyzer import regplot
video_nums = df_criticizer.groupby('transferred_name')['critcizing_videos'].mean().to_numpy()
regplot.linear_plot(video_nums, np.array(subscriber_increase_list), 
                    x_colname='critcizing_videos', plot_scores=False)
plt.ylabel('subscriber_increase_ratio')
plt.show()
regplot.linear_plot(video_nums, np.array(view_increase_list), 
                    x_colname='critcizing_videos', plot_scores=False)
plt.ylabel('view_increase_ratio')
plt.show()

# %% 1回のみ炎上関連動画をアップロードしたユーザー
df_one_criticizer = df[(df['classification']=='criticizer')
                     & (df['critcizing_videos'] == 1)].copy()
# 再生回数がマイナスのデータ＆直後の異常データを補正
df_one_criticizer = df_one_criticizer.groupby('transferred_name').apply(
                    lambda group: modify_minus_view(group, 'view_count', 'date'))
# 炎上前週が100となるよう規格化
df_one_criticizer = df_one_criticizer.groupby('transferred_name').apply(
                        lambda group: normalize_last_week(group, flaming_date))
n_channels = df_one_criticizer['transferred_name'].nunique()  # チャンネル数

# 登録者数の予測
pred_subscribers_one = {}  # 予測結果保持用
fig, axes = plt.subplots(n_channels, 1, figsize=(8, n_channels*3))  # プロット用のaxes
for i, (name, df_ch) in enumerate(df_one_criticizer.groupby('transferred_name')):
    pred_subscribers_one[name] = compare_pred_and_flaming(df_src=df_ch, date_col='date', y_col='subscriber_norm', ax=axes[i],
                                    flaming_date=flaming_date, before_period=BEFORE_FLAMING, after_period=AFTER_FLAMING,
                                    d=D_SUBSCRIBER, p_max=P_MAX_SUBSCRIBER, q_max=Q_MAX_SUBSCRIBER, alpha=ALPHA)
plt.tight_layout()
plt.show()

# 再生回数の予測
pred_views_one = {}  # 予測結果保持用
fig, axes = plt.subplots(n_channels, 1, figsize=(8, n_channels*3))  # プロット用のaxes
for i, (name, df_ch) in enumerate(df_one_criticizer.groupby('transferred_name')):
    pred_views_one[name] = compare_pred_and_flaming(df_src=df_ch, date_col='date', y_col='view_norm', ax=axes[i],
                                flaming_date=flaming_date, before_period=BEFORE_FLAMING, after_period=AFTER_FLAMING,
                                d=D_VIEW, p_max=P_MAX_VIEW, q_max=Q_MAX_VIEW, alpha=ALPHA)
plt.tight_layout()
plt.show()

# 登録者数と再生回数の予測値からの増加率
fig, ax = plt.subplots(1, 1, figsize=(6, 6))  # プロット用のaxes
subscriber_increase_list_one = []  # 登録者数増加率格納用
view_increase_list_one = []  # 再生回数増加率格納用
# チャンネルごとにループ
for i, (name, df_ch) in enumerate(df_one_criticizer.groupby('transferred_name')):
    # 炎上前後40日ずつを抜き出し
    df_before, df_after = devide_before_after(df_ch, 'date', flaming_date,
                            before_period=BEFORE_FLAMING, after_period=AFTER_FLAMING)
    # 炎上後の予測値に対する増加率を散布図プロット 
    subscriber_increase_ratio, view_increase_ratio \
        = plot_increase_scatter(x_before=pred_subscribers_one[name].iloc[-1], x_after=df_after['subscriber_norm'].iloc[-1],
                                y_before=pred_views_one[name].mean(), y_after=df_after['view_norm'].mean(), label=name, ax=ax)
    subscriber_increase_list_one.append(subscriber_increase_ratio)
    view_increase_list_one.append(view_increase_ratio)
ax.set_xlim(-xlim, xlim)
ax.set_ylim(-ylim, ylim)
ax.axvline(x=0, color='gray', alpha=0.2)
ax.axhline(y=0, color='gray', alpha=0.2)
print(f'チャンネル登録者数増加率平均={np.mean(subscriber_increase_list_one)}%')
print(f'再生回数数増加率平均={np.mean(view_increase_list_one)}%')

# %% 炎上とは無関係なビジネス系YouTuber
df_business = df[df['classification']=='business'].copy()
# 再生回数がマイナスのデータ＆直後の異常データを補正
df_business = df_business.groupby('transferred_name').apply(
                    lambda group: modify_minus_view(group, 'view_count', 'date'))
# 炎上前週が100となるよう規格化
df_business = df_business.groupby('transferred_name').apply(
                        lambda group: normalize_last_week(group, flaming_date))
n_channels = df_business['transferred_name'].nunique()  # チャンネル数

# 登録者数の予測
pred_subscribers_business = {}  # 予測結果保持用
fig, axes = plt.subplots(n_channels, 1, figsize=(8, n_channels*3))  # プロット用のaxes
for i, (name, df_ch) in enumerate(df_business.groupby('transferred_name')):
    pred_subscribers_business[name] = compare_pred_and_flaming(df_src=df_ch, date_col='date', y_col='subscriber_norm', ax=axes[i],
                                    flaming_date=flaming_date, before_period=BEFORE_FLAMING, after_period=AFTER_FLAMING,
                                    d=D_SUBSCRIBER, p_max=P_MAX_SUBSCRIBER, q_max=Q_MAX_SUBSCRIBER, alpha=ALPHA)
plt.tight_layout()
plt.show()

# 再生回数の予測
pred_views_business = {}  # 予測結果保持用
fig, axes = plt.subplots(n_channels, 1, figsize=(8, n_channels*3))  # プロット用のaxes
for i, (name, df_ch) in enumerate(df_business.groupby('transferred_name')):
    pred_views_business[name] = compare_pred_and_flaming(df_src=df_ch, date_col='date', y_col='view_norm', ax=axes[i],
                                flaming_date=flaming_date, before_period=BEFORE_FLAMING, after_period=AFTER_FLAMING,
                                d=D_VIEW, p_max=P_MAX_VIEW, q_max=Q_MAX_VIEW, alpha=ALPHA)
plt.tight_layout()
plt.show()

# 登録者数と再生回数の予測値からの増加率
fig, ax = plt.subplots(1, 1, figsize=(6, 6))  # プロット用のaxes
subscriber_increase_list_business = []  # 登録者数増加率格納用
view_increase_list_business = []  # 再生回数増加率格納用
# チャンネルごとにループ
for i, (name, df_ch) in enumerate(df_business.groupby('transferred_name')):
    # 炎上前後40日ずつを抜き出し
    df_before, df_after = devide_before_after(df_ch, 'date', flaming_date,
                            before_period=BEFORE_FLAMING, after_period=AFTER_FLAMING)
    # 炎上後の予測値に対する増加率を散布図プロット 
    subscriber_increase_ratio, view_increase_ratio \
        = plot_increase_scatter(x_before=pred_subscribers_business[name].iloc[-1], x_after=df_after['subscriber_norm'].iloc[-1],
                                y_before=pred_views_business[name].mean(), y_after=df_after['view_norm'].mean(), label=name, ax=ax)
    subscriber_increase_list_business.append(subscriber_increase_ratio)
    view_increase_list_business.append(view_increase_ratio)
ax.set_xlim(-xlim, xlim)
ax.set_ylim(-ylim, ylim)
ax.axvline(x=0, color='gray', alpha=0.2)
ax.axhline(y=0, color='gray', alpha=0.2)
print(f'チャンネル登録者数増加率平均={np.mean(subscriber_increase_list_business)}%')
print(f'再生回数数増加率平均={np.mean(view_increase_list_business)}%')

# %% 批評者、1回のみ炎上関係動画アップ、炎上と無関係なビジネス系YouTuberを比較
fig, ax = plt.subplots(1, 1, figsize=(6, 6))  # プロット用のaxes
ax.scatter(subscriber_increase_list_business, view_increase_list_business, 
           c='dodgerblue', label='business')
ax.scatter(subscriber_increase_list_one, view_increase_list_one, 
           c='orange', label='one_criticizer')
ax.scatter(subscriber_increase_list, view_increase_list, 
           c='tab:red', label='criticizer')
ax.legend(loc='upper left')
ax.set_xlim(-xlim, xlim)
ax.set_ylim(-ylim, ylim)
ax.axvline(x=0, color='gray', alpha=0.2)
ax.axhline(y=0, color='gray', alpha=0.2)
ax.set_xlabel('Subscriber increase [%]')
ax.set_ylabel('View increase [%]')

# %% マハラノビス距離算出
from scipy.spatial import distance
X_criticizer = np.array([subscriber_increase_list, view_increase_list]).T  # 批評者データ
X_normal = np.array([subscriber_increase_list_business, view_increase_list_business]).T  # ビジネス系YouTuberを正常データとして利用
mean = np.mean(X_normal, axis=0)  # 平均
cov = np.cov(X_normal.T)  # 分散共分散行列
cov_i = np.linalg.pinv(cov)  # 分散共分散逆行列
# マハラノビス距離
mahalanobis_dist = np.apply_along_axis(lambda x:
        distance.mahalanobis(x, mean, cov_i), 1, X_criticizer)
mahalanobis_dist = pd.Series(mahalanobis_dist, 
        index=list(df_criticizer.groupby('transferred_name').groups.keys()))
print(mahalanobis_dist)

# %%
