import sys, os, requests, json, random
from decimal import Decimal
import ccxt
sys.path.append(os.getcwd()) # 根目录
from config import *
from utils.utils import *
from formatdata import *
from onepassword import parse_file

class OKXUtil():

    @try_except_code
    def __init__(self, account, chain):
        """初始化
        Attributes:
            account:实例化哪个账户，哪个账户即为主操作账户。例:xxxx@gmail.com
            chain:链
        """

        # 提现所在链。例：BSC,ETH,SOL,TRX,MATIC
        chain = chain.upper()
        if chain in ['ETH', 'ERC20']:
            self.chain = 'ERC20'
        elif chain in ['TRC', 'TRC20']:
            self.chain = 'TRC20'
        elif chain in ['POLYGON',  'MATIC']:
            self.chain = 'Polygon'
        elif chain in ['AVAL', 'AVALANCHE']:
            self.chain = 'Avalanche C Chain'
        elif chain in ['ARB', 'ARBI', 'ARBITRUM', 'ARBITRUM ONE']:
            self.chain = 'Arbitrum one'
        elif chain in ['OP', 'OPTIMISM']:
            self.chain = 'Optimism'
        elif chain in ['ZKS', 'ZKSYNC']:
            self.chain = 'ZKSYNC'
        elif chain in ['BTC', 'BITCOIN']:
            self.chain = 'Bitcoin'
        elif chain in ['OK', 'OKC']:
            self.chain = 'OKC'
        
        self.account_apis = parse_file(okx_api_file)

        # 根据传参确定哪个账户是主操作账户，比如借贷、下单、转账等等
        self.okx = self.create_exchange(account)
        self.account = account

    @try_except_code
    def create_exchange(self, account):
        # 提现ip可设置多个，从中任选一个
        proxy_arr = self.account_apis[account]['main']['api_proxy']
        proxy = random.choice(proxy_arr)
        proxies = {"http": proxy, "https": proxy}
        # 根据传参确定哪个账户是主操作账户，比如借贷、下单、转账等等
        okx = ccxt.okex5({
            'apiKey': self.account_apis[account]['main']['api_key'],
            'secret': self.account_apis[account]['main']['api_secret'],
            'password': self.account_apis[account]['main']['api_password'],
            'enableRateLimit': True,  # 启用请求限速
            'proxies': proxies,
        })
        return okx

    @try_except_code
    def fetch_balance(self, coin):
        coin = coin.upper()
        # 默认是交易账户trading或spot，资金账户 funding， 'margin', 'futures', 'swap'
        all_balance = self.okx.fetch_balance(params={"type": "funding"})
        coin_balance = all_balance[coin]['free'] if coin in all_balance else float(0)
        print('账户', self.account, '现有', coin_balance, coin)
        return coin_balance

    @try_except_code
    def transfer(self, coin, amount, from_account, to_account, transfer_type, sub_account):
        """

        Attributes:
            coin: 划转币种
            amount: 划转数量
            from_account: 转出账户.如交易账户trading或18
            to_account: 转入账户.如资金账户funding或6
            transfer_type: 划转类型. 0:账户内划转 | 1:母账户转子账户(仅适用于母账户APIKey) | 2:子账户转母账户(仅适用于母账户APIKey)
            sub_account: 子账户序号.transfer_type不为0时设置
        """
        amount = float(amount)
        coin = coin.upper()
        # account_types = self.okx.options['accountsByType']) # okx所有的账户类型
        # print(account_types) # {'spot': '1', 'future': '3', 'futures': '3', 'margin': '5', 'funding': '6', 'swap': '9', 'option': '12', 'trading': '18'}
        if from_account not in ['spot', '1', 'future', 'futures', '3', 'margin', '5', 'funding', '6', 'swap', '9', 'option', '12', 'trading', '18']:
            print('账户类型错误。只允许 spot|1|future|futures|3|margin|5|funding|6|swap|9|option|12|trading|18')
            return
        if to_account not in ['spot', '1', 'future', 'futures', '3', 'margin', '5', 'funding', '6', 'swap', '9', 'option', '12', 'trading', '18']:
            print('账户类型错误。只允许 spot|1|future|futures|3|margin|5|funding|6|swap|9|option|12|trading|18')
            return
        # okx支持划转类型 0：账户内划转 1：母账户转子账户(仅适用于母账户APIKey) 2：子账户转母账户(仅适用于母账户APIKey) 3：子账户转母账户(仅适用于子账户APIKey) 4：子账户转子账户(仅适用于子账户APIKey，且目标账户需要是同一母账户下的其他子账户)
        # 3和4需要子账户api，切换账户麻烦，通过1和2能实现一样的功能。
        if transfer_type not in [0, 1, 2]:
            print('划转类型错误。只允许0|1|2')
            return
        if sub_account not in ['1', '2', '3', '4', '5']:
            print("子账户序号错误。只允许'1'|'2'|'3'|'4'|'5'")
            return
        if transfer_type != 0:
            sub_account_name = self.account_apis[self.account][f'sub{sub_account}']['sub_account_name']
        else:
            sub_account_name = ''
        self.okx.transfer(coin, amount, fromAccount=from_account, toAccount=to_account, params = {"type": transfer_type, "subAcct":sub_account_name})

    @try_except_code
    def withdraw(self, coin ,amount, address):
        """提现。要求:提现权限必须设置ip、提币地址必须设置为免验证地址

        ccxt统一api: 
            fetch_balance(): 查询账户信息
            withdraw(): 提现
        
        ccxt隐式api:
            private_get_asset_currencies: 查询手续费 根据okx 获取代币列表 api: GET /api/v5/asset/currencies 生成

        Attributes:
            coin: 提现币种
            amount: 提现数量
            address: 提现地址。外部地址为真实地址(例:0x...),内部地址为哪个账户(例:xxx@gmail.com)
        """
        amount = float(amount)
        coin = coin.upper()
        if coin == 'BTC' and self.chain == 'OKC':
            chain = 'BTCK-OKC' # 处理BTC查询时特殊情况，链是BTCK-OKC
        if coin == 'ETH' and self.chain == 'OKC':
            chain = 'ETHK-OKC' # 处理ETH查询时特殊情况，链是ETHK-OKC
        else:
            chain = f'{coin}-{self.chain}'
        # 判断传递的地址是不是合法的手机号或邮箱。如果是，代表内部地址
        if is_valid_contact(address):
            withdraw_type = '内部转账'
            dest = 3 # dest设置为3表示内部转账
            coin_transaction_fee_of_chain = 0
        elif is_valid_address(address):
            withdraw_type = '链上提现'
            dest = 4 # dest设置为4表示链上提币
            coin_chains = []
            # 获取转账手续费。调用的是获取所有币种信息的端点GET /api/v5/asset/currencies，返回一个包含所有币种信息的字典，包括支持的所有币种名称、精度、最小交易数量、提现手续费等信息
            # 方法1:ccxt隐式api private_get_asset_currencies,直接调用okx端点
            # 方法2:ccxt统一api exchange.fetch_currencies()[asset],但有些链进行了处理，比如提ETH用ERC20报错需要改成ETH，SAND使用ERC20报错
            # 方法3:ccxt统一api fetch_transaction_fees['withdraw'][coin][chain],币安支持此方法获取转账手续费。ok不支持，不知未来会不会支持            
            coin_info = self.okx.private_get_asset_currencies(params={'ccy':coin})
            for data in coin_info['data']:
                coin_chains.append(data['chain'])
                if data['chain']==chain: # 查找与指定链一致的数据
                    coin_transaction_fee_of_chain=float(data['minFee']) #提币费用
                    withdraw_precision = int(data['wdTickSz']) #提币精度            
            if chain not in coin_chains:
                print(f'链{coin}-{self.chain}错误,请确认')
                return
            # 先将浮点数转换为 Decimal 类型，然后获取小数点后的位数
            amount_decimals = abs(Decimal(str(amount)).as_tuple().exponent)
            if amount_decimals > withdraw_precision:
                print('超出提现精度,请确认')
                return
        else:
            print('提现地址输入错误。请确认')
            return
        coin_balance = self.fetch_balance(coin)
        # 判断账户余额够不够
        if amount > coin_balance:
            print('提现金额超出余额，请先充值或者减少提现数量')
            return
        if (amount + coin_transaction_fee_of_chain) > coin_balance:
            print('账户余额不够手续费，会从提币数量中扣除，实际收到的数量会小于转账数量')
        # 提现。okx链上提现的手续费优先从账户余额扣除,如不够扣除,会从提币数量中扣除.
        # okx旧版api密码为交易密码,目前已取消。但ccxt没有更新,参数还需要设置,随便设置为0就行'pwd':0
        withdraw = self.okx.withdraw(coin, amount, address, tag=None, params={'chain':chain, 'dest':dest, "fee": coin_transaction_fee_of_chain, 'pwd':0})
        print(f'转出方:{self.account}\n接收方:{address}\n提现币种:{coin}\n提现数量:{amount}\n提现方式:{withdraw_type}\n提现网络:{chain}\n提现手续费:{coin_transaction_fee_of_chain}')
            
if __name__ == '__main__':

    data = my_format_data(start_num=1, end_num=1)

    for d in data:
        print(d)
        
        # 参数：account、chain
        # chain:bsc,erc20(提erc20代币用),eth(提ETH用),trx,sol,omni,bep2
        okx = OKXUtil('gaohongxiang69@gmail.com', 'eth')
        
        # 查询余额
        # okx.fetch_balance('usdt')

        # 转账
        # 参数 coin ,amount, address
        # okx.withdraw('usdc', 1, d['address'])
    exit()
    
    
    # okx = OKXUtil('gaohongxiang69@gmail.com', 'eth')
    # to_account = 'gaoxiang@gmail.com'
    
    # 内部转账
    # 参数 coin ,amount, address
    # okx.withdraw('usdc', 1, to_account)
    
    # 划转
    # 参数：coin, amount, from_account, to_account, transfer_type=0, sub_account=''
    # from_account, to_account取值：spot|1|future|futures|3|margin|5|funding|6|swap|9|option|12|trading|18。常用就是funding|6资金账户、trading|18交易账户
    # transfer_type取值： 0：账户内划转 1：母账户转子账户(仅适用于母账户APIKey) 2：子账户转母账户(仅适用于母账户APIKey)# 
    # sub_account取值：子账户序号字符串'1'|'2'|'3'|'4'|'5'
    # okx.transfer('blur', 10, from_account='funding', to_account='funding', transfer_type=2, sub_account='1')