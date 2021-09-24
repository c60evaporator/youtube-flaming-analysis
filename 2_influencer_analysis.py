# %% データと各種メソッドの読込
import pandas as pd
import numpy as np
from matplotlib import colors
from datetime import timedelta
import matplotlib.pyplot as plt
from statsmodels.graphics.tsaplots import plot_acf
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import arma_order_select_ic

from read_config import read_config

cfg, _ = read_config()
# 各種定数の指定
NOX_CSV_PATH = f'{cfg["Path"]["NoxInfluencerOutput"]}\\youtube_stats_history.csv'  # NoxInfluencer取得データの格納パス
AFTER_FLAMING = 40  # 炎上後の分析対象日数
BEFORE_FLAMING = 84  # 炎上前の分析対象日数
D_SUBSCRIBER = 2  # 登録者数ARIMAモデルのパラメータd
P_MAX_SUBSCRIBER = 4  # 登録者数ARIMAモデルのパラメータpの最大値
Q_MAX_SUBSCRIBER = 2  # 登録者数ARIMAモデルのパラメータqの最大値
D_VIEW = 1  # 再生回数ARIMAモデルのパラメータd
P_MAX_VIEW = 4  # 再生回数ARIMAモデルのパラメータpの最大値
Q_MAX_VIEW = 4  # 再生回数ARIMAモデルのパラメータpの最大値
ALPHA = 0.05  # 区間予測の有意水準
# データの読込
df_channels = pd.read_csv('./channel_ids.csv', encoding='utf_8_sig', parse_dates=['flaming_date'])
df_noxinfluencer = pd.read_csv(NOX_CSV_PATH, encoding='utf_8_sig', parse_dates=['date', 'acquisition_date'])
# 読み込んだデータを結合
df = pd.merge(df_noxinfluencer, df_channels, how='left', left_on='channel_name', right_on='name').drop(columns=['name'])

color_list = list(colors.TABLEAU_COLORS.values())  # プロット用の色
color_list.extend(list(colors.CSS4_COLORS.values()))

###### メソッドの読込 ######
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

def plot_diff_acf(x, lags, axes_diff, axes_acf, name):
    """差分の自己相関コレログラム描画用メソッド"""
    # 階差1のデータプロット
    axes_diff[0].plot(np.diff(x))
    axes_diff[0].set_title(f'1st_order_correlation_{name}')
    # 階差1の自己相関コレログラム
    plot_acf(np.diff(x),
             lags=lags, ax=axes_acf[0],
             title=f'1st_order_{name}')
    # 階差2のデータプロット
    axes_diff[1].plot(np.diff(np.diff(x)))
    axes_diff[1].set_title(f'2nd_order_correlation_{name}')
    # 階差2の自己相関コレログラム
    plot_acf(np.diff(np.diff(x)),
             lags=lags, ax=axes_acf[1],
             title=f'2nd_order_{name}')
    # 階差3のデータプロット
    axes_diff[2].plot(np.diff(np.diff(np.diff(x))))
    axes_diff[2].set_title(f'3rd_order_correlation_{name}')
    # 階差3の自己相関コレログラム
    plot_acf(np.diff(np.diff(np.diff(x))),
             lags=lags, ax=axes_acf[2],
             title=f'3rd_order_{name}')

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

# %% 分析対象インフルエンサーの可視化
flaming_date = df[df['transferred_name']=='influencer']['flaming_date'][0].to_pydatetime()# 炎上日
df_influencer = df[df['classification']=='influencer_main'].copy()
# 再生回数がマイナスのデータ＆直後の異常データを補正
df_influencer = df_influencer.groupby('transferred_name').apply(
                    lambda group: modify_minus_view(group, 'view_count', 'date'))
# 炎上前週が100となるよう規格化
df_influencer = df_influencer.groupby('transferred_name').apply(
                        lambda group: normalize_last_week(group, flaming_date))
n_channels = df_influencer['transferred_name'].nunique()  # チャンネル数

# プロット用のaxes
fig, axes = plt.subplots(2, 1, figsize=(12, 12))

# チャンネルごとにループ
for i, (name, df_ch) in enumerate(df_influencer.groupby('transferred_name')):
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

# %% 登録者数の予測
pred_subscribers_influencer = {}  # 予測結果保持用
fig, axes = plt.subplots(1, 1, figsize=(8, 3))  # プロット用のaxes
for i, (name, df_ch) in enumerate(df_influencer.groupby('transferred_name')):
    pred_subscribers_influencer[name] = compare_pred_and_flaming(df_src=df_ch, date_col='date', y_col='subscriber_norm', ax=axes,
                                    flaming_date=flaming_date, before_period=BEFORE_FLAMING, after_period=AFTER_FLAMING,
                                    d=D_SUBSCRIBER, p_max=P_MAX_SUBSCRIBER, q_max=Q_MAX_SUBSCRIBER, alpha=ALPHA)
plt.tight_layout()
plt.show()

# %% 再生回数の予測
pred_views_influencer = {}  # 予測結果保持用
fig, axes = plt.subplots(1, 1, figsize=(8, 3))  # プロット用のaxes
for i, (name, df_ch) in enumerate(df_influencer.groupby('transferred_name')):
    pred_views_influencer[name] = compare_pred_and_flaming(df_src=df_ch, date_col='date', y_col='view_norm', ax=axes,
                                flaming_date=flaming_date, before_period=BEFORE_FLAMING, after_period=AFTER_FLAMING,
                                d=D_VIEW, p_max=P_MAX_VIEW, q_max=Q_MAX_VIEW, alpha=ALPHA)
plt.tight_layout()
plt.show()

# %% 登録者数と再生回数の予測値からの増加率
fig, ax = plt.subplots(1, 1, figsize=(6, 6))  # プロット用のaxes
subscriber_increase_list_influencer = []  # 登録者数増加率格納用
view_increase_list_influencer = []  # 再生回数増加率格納用
# チャンネルごとにループ
for i, (name, df_ch) in enumerate(df_influencer.groupby('transferred_name')):
    # 炎上前後39日ずつを抜き出し
    df_before, df_after = devide_before_after(df_ch, 'date', flaming_date,
                            before_period=BEFORE_FLAMING, after_period=AFTER_FLAMING)
    # 炎上後の予測値に対する増加率を散布図プロット 
    subscriber_increase_ratio, view_increase_ratio \
        = plot_increase_scatter(x_before=pred_subscribers_influencer[name].iloc[-1], x_after=df_after['subscriber_norm'].iloc[-1],
                                y_before=pred_views_influencer[name].mean(), y_after=df_after['view_norm'].mean(), label=name, ax=ax)
    subscriber_increase_list_influencer.append(subscriber_increase_ratio)
    view_increase_list_influencer.append(view_increase_ratio)
ax.set_xlim(-50, 50)
ax.set_ylim(-400, 400)
ax.axvline(x=0, color='gray', alpha=0.2)
ax.axhline(y=0, color='gray', alpha=0.2)
print(f'チャンネル登録者数増加率平均={np.mean(subscriber_increase_list_influencer)}%')
print(f'再生回数数増加率平均={np.mean(view_increase_list_influencer)}%')

# %% 批評者との比較
df_criticizer = df[(df['classification']=='criticizer')
                & (df['critcizing_videos'] >= 2)].copy()
# 再生回数がマイナスのデータ＆直後の異常データを補正
df_criticizer = df_criticizer.groupby('transferred_name').apply(
                    lambda group: modify_minus_view(group, 'view_count', 'date'))
# 炎上前週が100となるよう規格化
df_criticizer = df_criticizer.groupby('transferred_name').apply(
                    lambda group: normalize_last_week(group, flaming_date))
n_channels = df_criticizer['transferred_name'].nunique()  # チャンネル数

# 登録者数の予測
pred_subscribers_criticizer = {}  # 予測結果保持用
fig, axes = plt.subplots(n_channels, 1, figsize=(8, n_channels*3))  # プロット用のaxes
for i, (name, df_ch) in enumerate(df_criticizer.groupby('transferred_name')):
    pred_subscribers_criticizer[name] = compare_pred_and_flaming(df_src=df_ch, date_col='date', y_col='subscriber_norm', ax=axes[i],
                                    flaming_date=flaming_date, before_period=BEFORE_FLAMING, after_period=AFTER_FLAMING,
                                    d=D_SUBSCRIBER, p_max=P_MAX_SUBSCRIBER, q_max=Q_MAX_SUBSCRIBER, alpha=ALPHA)
plt.tight_layout()
plt.show()

# 再生回数の予測
pred_views_criticizer = {}  # 予測結果保持用
fig, axes = plt.subplots(n_channels, 1, figsize=(8, n_channels*3))  # プロット用のaxes
for i, (name, df_ch) in enumerate(df_criticizer.groupby('transferred_name')):
    pred_views_criticizer[name] = compare_pred_and_flaming(df_src=df_ch, date_col='date', y_col='view_norm', ax=axes[i],
                                flaming_date=flaming_date, before_period=BEFORE_FLAMING, after_period=AFTER_FLAMING,
                                d=D_VIEW, p_max=P_MAX_VIEW, q_max=Q_MAX_VIEW, alpha=ALPHA)
plt.tight_layout()
plt.show()

# 登録者数と再生回数の予測値からの増加率
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
        = plot_increase_scatter(x_before=pred_subscribers_criticizer[name].iloc[-1], x_after=df_after['subscriber_norm'].iloc[-1],
                                y_before=pred_views_criticizer[name].mean(), y_after=df_after['view_norm'].mean(), label=name, ax=ax)
    subscriber_increase_list.append(subscriber_increase_ratio)
    view_increase_list.append(view_increase_ratio)
ax.set_xlim(-50, 50)
ax.set_ylim(-400, 400)
ax.axvline(x=0, color='gray', alpha=0.2)
ax.axhline(y=0, color='gray', alpha=0.2)
plt.show()

# インフルエンサーとの比較プロット
fig, ax = plt.subplots(1, 1, figsize=(6, 6))  # プロット用のaxes
ax.scatter(subscriber_increase_list, view_increase_list, 
           c='tab:red', label='criticizer')
ax.scatter(subscriber_increase_list_influencer, view_increase_list_influencer, 
           c='tab:blue', label='influencer_main')
ax.legend(loc='upper left')
ax.set_xlim(-50, 50)
ax.set_ylim(-400, 400)
ax.axvline(x=0, color='gray', alpha=0.2)
ax.axhline(y=0, color='gray', alpha=0.2)
ax.set_xlabel('Subscriber increase [%]')
ax.set_ylabel('View increase [%]')
plt.show()

# %% その他の炎上したビジネス系インフルエンサー
df_other = df[df['classification']=='influencer_other'].copy()
# 再生回数がマイナスのデータ＆直後の異常データを補正
df_other = df_other.groupby('transferred_name').apply(
                    lambda group: modify_minus_view(group, 'view_count', 'date'))
# 炎上前週が100となるよう規格化
df_other = df_other.groupby('transferred_name').apply(
                    lambda group: normalize_last_week(group, group['flaming_date'].iat[0].to_pydatetime()))
n_channels = df_other['transferred_name'].nunique()  # チャンネル数

# 登録者数の予測
pred_subscribers_other = {}  # 予測結果保持用
fig, axes = plt.subplots(n_channels, 1, figsize=(8, n_channels*3))  # プロット用のaxes
for i, (name, df_ch) in enumerate(df_other.groupby('transferred_name')):
    flaming_date = df_ch['flaming_date'].iat[0].to_pydatetime()  # 炎上日
    pred_subscribers_other[name] = compare_pred_and_flaming(df_src=df_ch, date_col='date', y_col='subscriber_norm', ax=axes[i],
                                    flaming_date=flaming_date, before_period=BEFORE_FLAMING, after_period=AFTER_FLAMING,
                                    d=D_SUBSCRIBER, p_max=P_MAX_SUBSCRIBER, q_max=Q_MAX_SUBSCRIBER, alpha=ALPHA)
plt.tight_layout()
plt.show()

# 再生回数の予測
pred_views_other = {}  # 予測結果保持用
fig, axes = plt.subplots(n_channels, 1, figsize=(8, n_channels*3))  # プロット用のaxes
for i, (name, df_ch) in enumerate(df_other.groupby('transferred_name')):
    flaming_date = df_ch['flaming_date'].iat[0].to_pydatetime()  # 炎上日
    pred_views_other[name] = compare_pred_and_flaming(df_src=df_ch, date_col='date', y_col='view_norm', ax=axes[i],
                                flaming_date=flaming_date, before_period=BEFORE_FLAMING, after_period=AFTER_FLAMING,
                                d=D_VIEW, p_max=P_MAX_VIEW, q_max=Q_MAX_VIEW, alpha=ALPHA)
plt.tight_layout()
plt.show()

# 登録者数と再生回数の予測値からの増加率
fig, ax = plt.subplots(1, 1, figsize=(6, 6))  # プロット用のaxes
subscriber_increase_list_other = []  # 登録者数増加率格納用
view_increase_list_other = []  # 再生回数増加率格納用
# チャンネルごとにループ
for i, (name, df_ch) in enumerate(df_other.groupby('transferred_name')):
    flaming_date = df_ch['flaming_date'].iat[0].to_pydatetime()  # 炎上日
    # 炎上前後40日ずつを抜き出し
    df_before, df_after = devide_before_after(df_ch, 'date', flaming_date,
                            before_period=BEFORE_FLAMING, after_period=AFTER_FLAMING)
    # 炎上後の予測値に対する増加率を散布図プロット 
    subscriber_increase_ratio, view_increase_ratio \
        = plot_increase_scatter(x_before=pred_subscribers_other[name].iloc[-1], x_after=df_after['subscriber_norm'].iloc[-1],
                                y_before=pred_views_other[name].mean(), y_after=df_after['view_norm'].mean(), label=name, ax=ax)
    subscriber_increase_list_other.append(subscriber_increase_ratio)
    view_increase_list_other.append(view_increase_ratio)
ax.set_xlim(-50, 50)
ax.set_ylim(-400, 400)
ax.axvline(x=0, color='gray', alpha=0.2)
ax.axhline(y=0, color='gray', alpha=0.2)
print(f'チャンネル登録者数増加率平均={np.mean(subscriber_increase_list_other)}%')
print(f'再生回数数増加率平均={np.mean(view_increase_list_other)}%')

# %% 泥酔事件インフルエンサー
df_drunk = df[df['classification']=='influencer_drunk'].copy()
# 再生回数がマイナスのデータ＆直後の異常データを補正
df_drunk = df_drunk.groupby('transferred_name').apply(
                    lambda group: modify_minus_view(group, 'view_count', 'date'))
# 炎上前週が100となるよう規格化
df_drunk = df_drunk.groupby('transferred_name').apply(
                    lambda group: normalize_last_week(group, group['flaming_date'].iat[0].to_pydatetime()))
n_channels = df_drunk['transferred_name'].nunique()  # チャンネル数

# 登録者数の予測
pred_subscribers_drunk = {}  # 予測結果保持用
fig, axes = plt.subplots(n_channels, 1, figsize=(8, n_channels*3))  # プロット用のaxes
for i, (name, df_ch) in enumerate(df_drunk.groupby('transferred_name')):
    flaming_date = df_ch['flaming_date'].iat[0].to_pydatetime()  # 炎上日
    pred_subscribers_drunk[name] = compare_pred_and_flaming(df_src=df_ch, date_col='date', y_col='subscriber_norm', ax=axes[i],
                                    flaming_date=flaming_date, before_period=BEFORE_FLAMING, after_period=AFTER_FLAMING,
                                    d=D_SUBSCRIBER, p_max=P_MAX_SUBSCRIBER, q_max=Q_MAX_SUBSCRIBER, alpha=ALPHA)
plt.tight_layout()
plt.show()

# 再生回数の予測
pred_views_drunk = {}  # 予測結果保持用
fig, axes = plt.subplots(n_channels, 1, figsize=(8, n_channels*3))  # プロット用のaxes
for i, (name, df_ch) in enumerate(df_drunk.groupby('transferred_name')):
    flaming_date = df_ch['flaming_date'].iat[0].to_pydatetime()  # 炎上日
    pred_views_drunk[name] = compare_pred_and_flaming(df_src=df_ch, date_col='date', y_col='view_norm', ax=axes[i],
                                flaming_date=flaming_date, before_period=BEFORE_FLAMING, after_period=AFTER_FLAMING,
                                d=D_VIEW, p_max=P_MAX_VIEW, q_max=Q_MAX_VIEW, alpha=ALPHA)
plt.tight_layout()
plt.show()

# 登録者数と再生回数の予測値からの増加率
fig, ax = plt.subplots(1, 1, figsize=(6, 6))  # プロット用のaxes
subscriber_increase_list_drunk = []  # 登録者数増加率格納用
view_increase_list_drunk = []  # 再生回数増加率格納用
# チャンネルごとにループ
for i, (name, df_ch) in enumerate(df_drunk.groupby('transferred_name')):
    flaming_date = df_ch['flaming_date'].iat[0].to_pydatetime()  # 炎上日
    # 炎上前後40日ずつを抜き出し
    df_before, df_after = devide_before_after(df_ch, 'date', flaming_date,
                            before_period=BEFORE_FLAMING, after_period=AFTER_FLAMING)
    # 炎上後の予測値に対する増加率を散布図プロット 
    subscriber_increase_ratio, view_increase_ratio \
        = plot_increase_scatter(x_before=pred_subscribers_drunk[name].iloc[-1], x_after=df_after['subscriber_norm'].iloc[-1],
                                y_before=pred_views_drunk[name].mean(), y_after=df_after['view_norm'].mean(), label=name, ax=ax)
    subscriber_increase_list_drunk.append(subscriber_increase_ratio)
    view_increase_list_drunk.append(view_increase_ratio)
ax.set_xlim(-50, 50)
ax.set_ylim(-400, 400)
ax.axvline(x=0, color='gray', alpha=0.2)
ax.axhline(y=0, color='gray', alpha=0.2)
print(f'チャンネル登録者数増加率平均={np.mean(subscriber_increase_list_drunk)}%')
print(f'再生回数数増加率平均={np.mean(view_increase_list_drunk)}%')

# %% 再生回数増加率上位2チャンネルを除いた再生回数増加率
view_increase_list_drunk_new = [v for i, v in enumerate(view_increase_list_drunk) if i not in [0, 12]]
print(f'再生回数数増加率平均={np.mean(view_increase_list_drunk_new)}%')

# %% 全炎上インフルエンサーの比較プロット
fig, ax = plt.subplots(1, 1, figsize=(6, 6))  # プロット用のaxes
ax.scatter(subscriber_increase_list_drunk, view_increase_list_drunk, 
           c='tab:purple', label='influencer_drunk')
ax.scatter(subscriber_increase_list_other, view_increase_list_other,
           c='tab:green', label='influencer_other')
ax.scatter(subscriber_increase_list_influencer, view_increase_list_influencer, 
           c='tab:blue', label='influencer_main')
ax.legend(loc='upper left')
ax.set_xlim(-50, 50)
ax.set_ylim(-400, 400)
ax.axvline(x=0, color='gray', alpha=0.2)
ax.axhline(y=0, color='gray', alpha=0.2)
ax.set_xlabel('Subscriber increase [%]')
ax.set_ylabel('View increase [%]')
plt.show()
subscriber_increase_list_all = subscriber_increase_list_influencer + subscriber_increase_list_other + subscriber_increase_list_drunk
view_increase_list_all = view_increase_list_influencer + view_increase_list_other + view_increase_list_drunk
print(f'チャンネル登録者数増加率平均={np.mean(subscriber_increase_list_all)}%')
print(f'再生回数数増加率平均={np.mean(view_increase_list_all)}%')
print(f'登録者減少チャンネル数={len([v for v in subscriber_increase_list_all if v <= 0])}/{len(subscriber_increase_list_all)}')
print(f'再生回数減少チャンネル数={len([v for v in view_increase_list_all if v <= 0])}/{len(view_increase_list_all)}')

# %%
