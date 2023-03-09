import pandas as pd
import sys, os
sys.path.append(os.getcwd()) # 根目录
from config import *

def my_format_data(start_num, end_num):
    """组装数据
        
    Attributes:
        start_num:开始账号
        end_num:结束账号
        is_bitbrowser:是否为比特浏览器数据 True:比特浏览器 False:ads浏览器
    """
    all_wallet = pd.read_csv(eth_wallet_file)

    data = all_wallet.iloc[int(start_num)-1:int(end_num),:].reset_index(drop=True)
    data = data.to_dict('records')
    return data


if __name__ == '__main__':

    my_format_data = my_format_data(1, 2)
    print(my_format_data)

