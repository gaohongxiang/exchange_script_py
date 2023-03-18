"""
okx api文档: https://www.okx.com/docs-v5/zh/#overview
ccxt文档: https://docs.ccxt.com/en/latest/index.html
"""
import sys, os, requests, json, random
from decimal import Decimal
import ccxt
sys.path.append(os.getcwd()) # 根目录
from config import *
from utils_.utils import *
from utils_.onepassword import parse_file
from formatdata import *

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
        
        # 账户类型
        # account_types = self.okx.options['accountsByType'] # okx所有的账户类型
        # print(account_types) # {'spot': '1', 'future': '3', 'futures': '3', 'margin': '5', 'funding': '6', 'swap': '9', 'option': '12', 'trading': '18'}
        # okx统一账户各细分账户: funding资金账户，trading交易账户，earn金融账户
        
        # 支持的方法
        # print(dir(self.okx)) 

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
            'proxies': proxies,
            'enableRateLimit': True,  # 启用请求限速
            'options': {'adjustForTimeDifference': True}, # 自动调整时间戳以适应本地计算机的时区差异
            
        })
        return okx

    @try_except_code
    def fetch_balance(self, coin):
        coin = coin.upper()
        # funding资金账户，trading交易账户，earn金融账户
        all_balance = self.okx.fetch_balance(params={"type": "funding"})
        coin_balance = all_balance[coin]['free'] if coin in all_balance else float(0)
        print('账户', self.account, '现有', coin_balance, coin)
        return coin_balance

    @try_except_code
    def transfer(self, coin, amount, from_account, to_account, transfer_type, sub_account):
        """划转。可以账户内划转，也可以子母账户间划转。子账户间划转可以用子转母、母转子的方式实现。

        ccxt提供一个transfer的方法,用于划转。应该是调用的POST /api/v5/asset/transfer这个端点。此端点可以主账户内划转、母转子、子转母、子转子。子转子需要子账户api。没有使用。
        子转子可以通过子转母转子的方式实现。另外okx还提供一个子账户划转端点POST /api/v5/asset/subaccount/transfer。此端点使用的是母账户的api,可以自己写一下
        有一个点比较好奇的是,okx有两个划转端点,transfer怎么处理.

        ccxt统一api: 
            transfer(): 划转

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
        resp = self.okx.transfer(coin, amount, fromAccount=from_account, toAccount=to_account, params = {"type": transfer_type, "subAcct":sub_account_name})
        print(f"划转成功,详情:{resp['info']}")

    @try_except_code
    def withdraw(self, coin ,amount, address):
        """提现。要求:提现权限必须设置ip、提币地址必须设置为免验证地址,一次可最多20个

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
            dest = 4 # dest设置为4表示链上提现
            coin_chains = []
            # 获取币种信息，包括支持的所有币种名称、精度、最小交易数量、提现手续费等信息。调用的是获取所有币种信息的端点GET /api/v5/asset/currencies，返回一个包含所有币种信息的字典
            # 方法1:ccxt隐式api private_get_asset_currencies,直接调用okx端点
            # 方法2:ccxt统一api exchange.fetch_currencies()[asset],但有些链进行了处理，比如提ETH用ERC20报错需要改成ETH，SAND使用ERC20报错
            # 方法3:ccxt统一api fetch_transaction_fees['withdraw'][coin][chain],币安支持此方法获取转账手续费。ok不支持，不知未来会不会支持            
            coin_info = self.okx.private_get_asset_currencies(params={'ccy':coin}) # 此端点可以接受参数，只返回coin信息
            for data in coin_info['data']:
                coin_chains.append(data['chain'])
                if data['chain'] == chain: # 查找与指定链一致的数据
                    coin_transaction_fee_of_chain = float(data['minFee']) #提币费用。ccxt返回的是费用字符串
                    withdraw_precision = int(data['wdTickSz']) #提币精度。ccxt返回的是位数字符串
                    # 先将浮点数转换为 Decimal 类型，然后获取小数点后的位数
                    amount_decimals = abs(Decimal(str(amount)).as_tuple().exponent)
                    if amount_decimals > withdraw_precision:
                        print('超出提现精度,请确认')
                        return
                    min_withdraw_amount = float(data['minWd'])
                    if amount < min_withdraw_amount:
                        print('提现数量小于提现最小值', min_withdraw_amount)
                        return
            if chain not in coin_chains:
                print(f'链{coin}-{self.chain}错误,请确认')
                return
        else:
            print('提现地址输入错误。请确认')
            return
        coin_balance = self.fetch_balance(coin)
        # 判断账户余额够不够
        if (amount + coin_transaction_fee_of_chain) > coin_balance:
            print('提现金额超出余额，请先充值或者减少提现数量')
            return
        # 提现。okx链上提现的手续费优先从账户余额扣除,如不够扣除,会从提币数量中扣除.
        # dest: 3内部转账 4链上提现
        # okx旧版api密码为交易密码,目前已取消。但ccxt没有更新,参数还需要设置,随便设置为0就行'pwd':0
        withdraw = self.okx.withdraw(coin, amount, address, tag=None, params={'chain':chain, 'dest':dest, "fee": coin_transaction_fee_of_chain, 'pwd':0})
        print(f'转出方:{self.account}\n接收方:{address}\n提现币种:{coin}\n提现数量:{amount}\n提现方式:{withdraw_type}\n提现网络:{chain}\n提现手续费:{coin_transaction_fee_of_chain}\n到账数量:{amount}')

    @try_except_code
    def create_order(self, order_symbol, order_type, order_side, order_amount, order_price=None):
        """下单.只交易现货的限价/市价的买卖单.合约不玩

        ccxt统一api: 
            create_order()

        Attributes:
            order_symbol:交易对。ccxt统一格式。例:'ETH/USDT'
            order_type: limit/market
            order_side: 买/卖
            order_amount:买入数量
            order_price:买入/卖出价格.is_limit为True时设置
        return:
            订单信息。返回内容的数据结构:https://github.com/ccxt/ccxt/wiki/Manual#placing-orders
        """
        order_symbol = order_symbol.upper()
        order_amount = float(order_amount)
        order_value = order_amount * order_price
        min_amount, min_order_value = self.order_limit(order_symbol)
        if order_amount < min_amount or (min_order_value is not None and order_value < min_order_value):
            print(f'下单数量小于最低限制{min_amount} 或 下单金额小于最低限制{min_order_value}')
            return
        # tdMode 交易模式 保证金模式：isolated：逐仓 ；cross：全仓  非保证金模式：cash：非保证金.默认应该是cash,不写结果也一样
        order_info = self.okx.create_order(order_symbol, order_type, order_side, order_amount, order_price, params={"tdMode":"cash"})
        # print(order_info)
        order_price = order_info['price'] if order_type == 'market' else order_price
        print(f"下单成功\n交易对: {order_symbol}\n类型: {order_type}\n方向: {order_side}\n数量: {order_amount}\n价格: {order_price}\n订单时间: {order_info['datetime']}\n订单ID: {order_info['id']}")

    @try_except_code
    def fetch_order_by_id(self, id, symbol):
        """根据订单id查询订单信息

        ccxt统一api: 
            fetch_order()

        Attributes:
            id:订单id
            symbol:交易对。例:'ETH/USDT' # 理论上通过id就可以了。但是有些交易所需要填交易对。ccxt应该是统一了格式
        return:
            订单信息
        """
        symbol = symbol.upper()
        order_info = self.okx.fetch_order(id, symbol)
        print(order_info)
        print(f"订单时间: {order_info['datetime']}\n订单价格: {order_info['price']}\n订单剩余成交: {order_info['remaining']}\n订单状态: {order_info['status']}")
   
    @try_except_code
    def fetch_open_orders(self, symbol, limit=10):
        """查询开放订单

        ccxt统一api: 
            fetch_open_orders()

        Attributes:
            symbol:交易对。例:'ETH/USDT'
            limit:返回几条数据。默认10条
        return:
            订单信息
        """
        symbol = symbol.upper()
        order_info = self.okx.fetch_open_orders(symbol, limit)  # limit参数控制返回最近的几条
        # print(order_info)
        for i in order_info:
            print(f"订单时间: {i['datetime']}\n订单id: {i['id']}\n订单价格: {i['price']}\n订单剩余成交: {i['remaining']}\n订单状态: {i['status']}")
            print('-----------------------------------')

    @try_except_code
    def edit_order(self, order_id, order_symbol, order_type, order_side, order_amount, order_price, is_auto_cancel=False):
        """修改订单

        ccxt统一api: 
            edit_order()

        Attributes:
            order_id: 订单id
            order_symbol:交易对。ccxt统一格式。例:'ETH/USDT'
            order_type: 市价/限价
            order_side: 买/卖
            order_amount:买入数量
            order_price:买入/卖出价格
            is_auto_cancel: 修改订单失败时是否自动撤单
        return:
            订单信息。
        """
        order_symbol = order_symbol.upper()
        order_amount = float(order_amount)
        order_value = order_amount * order_price
        min_amount, min_order_value = self.order_limit(order_symbol)
        if order_amount < min_amount or (min_order_value is not None and order_value < min_order_value):
            print(f'下单数量小于最低限制{min_amount} 或 下单金额小于最低限制{min_order_value}')
            return
        # 下单时，CCXT底层的create_order函数已经做了价格转换的处理。自动调用price_to_precision函数，将价格转换为交易所支持的精度格式，再传递给交易所执行下单操作。
        # 修改订单时，CCXT底层的edit_order函数并没有进行价格转换处理。这是因为，修改订单需要传递多个参数，其中价格只是其中的一个参数，而edit_order函数无法确定哪个参数是价格。因此，需要开发者自己在调用edit_order函数之前，先将价格转换为交易所支持的精度格式，再传递给edit_order函数执行修改订单操作。
        order_price = self.okx.price_to_precision(order_symbol, order_price)
        order_price = float(order_price)
        # cxlOnFail 修改失败时是否撤销订单
        updated_order = self.okx.edit_order(order_id, order_symbol, order_type, order_side, order_amount, order_price, params={"cxlOnFail":is_auto_cancel})
        # print(updated_order)
        order_price = updated_order['price'] if order_type == 'market' else order_price
        print(f"修改订单成功\n交易对: {order_symbol}\n类型: {order_type}\n方向: {order_side}\n数量: {order_amount}\n价格: {order_price}\n订单时间: {updated_order['datetime']}\n订单ID: {updated_order['id']}")

    @try_except_code
    def order_limit(self, symbol):
        symbol = symbol.upper()
        self.okx.load_markets()  # 加载市场信息
        markets_info = self.okx.markets
        min_amount = markets_info[symbol]['limits']['amount']['min']
        min_order_value = markets_info[symbol]['limits']['cost']['min']
        return min_amount, min_order_value

    @try_except_code
    def cancel_order(self, id, symbol):
        """撤单

        ccxt统一api: 
            cancel_order()
            fetch_order()

        Attributes:
            id:订单id
            symbol:交易对。例:'ETH/USDT'
        return:
            订单信息
        """
        symbol = symbol.upper()
        order_info = self.okx.cancel_order(id, symbol)
        # print(order_info)
        # 撤单之后查询状态
        order_info = self.okx.fetch_order(id, symbol)
        print(order_info['status'])

if __name__ == '__main__':

    data = my_format_data(start_num=1, end_num=1)

    # for d in data:
    #     print(d)
    #     # 参数：account、chain
    #     # chain:bsc,erc20(提erc20代币用),eth(提ETH用),trx,sol,omni,bep2
    #     okx = OKXUtil('gaohongxiang69@gmail.com', 'eth')
        
    #     # 查询余额
    #     okx.fetch_balance('usdt')

    #     # 链上提现
    #     # 参数 coin ,amount, address
    #     # okx.withdraw('usdc', 1, d['address'])
    # exit()
    


    okx = OKXUtil('gaohongxiang69@gmail.com', 'eth')
    # to_account = 'gaoxiang@gmail.com'
    
    # # 内部转账
    # # 参数 coin ,amount, address
    # okx.withdraw('usdc', 1, to_account)
    
    # 划转
    # 参数：coin, amount, from_account, to_account, transfer_type=0, sub_account=''
    # from_account, to_account取值：spot|1|future|futures|3|margin|5|funding|6|swap|9|option|12|trading|18。常用就是funding|6资金账户、trading|18交易账户
    # transfer_type取值： 0：账户内划转 1：母账户转子账户(仅适用于母账户APIKey) 2：子账户转母账户(仅适用于母账户APIKey)# 
    # sub_account取值：子账户序号字符串'1'|'2'|'3'|'4'|'5'
    # okx.transfer('blur', 10, from_account='funding', to_account='trading', transfer_type=0, sub_account='1')

    # 下单 
    # 参数 order_symbol, order_type, order_side, order_amount, order_price=None
    # okx.create_order(order_symbol='BLUR/USDT',order_type='limit', order_side='sell', order_amount=10, order_price=1)

    # 查单
    # okx.fetch_order_by_id('556492856299782145', 'BLUR/USDT')
    # okx.fetch_open_orders('BLUR/USDT')

    # 修改订单
    # 参数 order_id, order_symbol, order_type(limit、market), order_side(buy、sell), order_amount, order_price, is_auto_cancel=False(修改订单失败时是否自动撤单)
    # okx.edit_order(order_id='556505531448721408', order_symbol='BLUR/USDT', order_type='limit', order_side='sell', order_amount=10, order_price=2, is_auto_cancel=False)

    # 撤单
    # okx.cancel_order('556530521644630016', 'BLUR/USDT')