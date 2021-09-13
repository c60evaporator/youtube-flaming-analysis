import configparser
import pandas as pd

def read_config():
    cfg = configparser.ConfigParser()
    cfg.read('./config.ini', encoding='utf-8')

    channel_ids = pd.read_csv('./channel_ids.csv', encoding='utf-8', index_col=0)

    return cfg, channel_ids
