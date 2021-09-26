# youtube-flaming-analysis
Data analysis scripts of YouTube flaming.

![compare_criticizer_influencer_2_eng](https://user-images.githubusercontent.com/59557625/134766794-37825517-432b-481c-bd69-e9cecd72698e.png)

![criticizer_correlation_eng](https://user-images.githubusercontent.com/59557625/134793579-616dce11-d186-4605-a3c9-cda493d5ca90.png)

# Contact
If you have any questions or comments about the scripts,
please feel free to contact me via
Twitter: https://twitter.com/c60evaporator

# 概要
YouTube炎上事例の分析スクリプトです。
詳細は[こちらのQiita記事](https://qiita.com/c60evaporator/items/bf9d5ad2d13876a670cf)を参照ください。

本記事に対する問い合わせは、[私のTwitter](https://twitter.com/c60evaporator)までお願い致します。
（channel_ids.csvやNoxInfluencer取得データが欲しい方も上記Twitterまでご連絡ください）

## モジュール構成

|Module name|内容|Content|
|---|---|---|
|1_criticizer_analysis.py|批評者側の分析|Analysis of criticizer|
|2_influencer_analysis.py|インフルエンサー側の分析|Analysis of flamer|
|get_noxinfluencer_data.py|NoxInfluencerのデータ取得スクリプト|Getting data of NoxInfluencer|
|retrieve_youtube_data.py|YouTube APIによるデータ取得スクリプト|Getting data with YouTube API|
|get_youtube_data.py|YouTube APIでデータ取得するためのメソッド集|Methods of getting data with YouTbe API|
