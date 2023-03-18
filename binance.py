"""
binance api文档:https://binance-docs.github.io/apidocs/spot/cn/#45fa4e00db
ccxt文档: https://docs.ccxt.com/en/latest/index.html
"""
import sys, os, requests, json, random, re
from decimal import Decimal
import ccxt
sys.path.append(os.getcwd()) # 根目录
from config import *
from utils_.utils import *
from utils_.onepassword import parse_file
from formatdata import *

class BinanceUtil():

    @try_except_code
    def __init__(self, account, chain):
        """初始化
        Attributes:
            account:实例化哪个账户，哪个账户即为主操作账户。例:xxxx@gmail.com
            chain:链
        """
        
        # 提现所在链,大写。例：BSC,ETH,SOL,TRX,MATIC
        chain = chain.upper()
        if chain in ['ETH', 'ERC20']:
            self.chain = 'ETH'
        elif chain in ['BSC', 'BEP20']:
            self.chain = 'BSC'
        elif chain in ['TRC', 'TRC20', 'TRX']:
            self.chain = 'TRX'
        elif chain in ['POLYGON',  'MATIC']:
            self.chain = 'MATIC'
        elif chain in ['AVAL', 'AVALANCHE']:
            self.chain = 'AVAX'
        elif chain in ['ARB', 'ARBITRUM', 'ARBITRUM ONE']:
            self.chain = 'ARBITRUM'
        elif chain in ['OP', 'OPTIMISM']:
            self.chain = 'OPTIMISM'
       
        self.account_apis = parse_file(binance_api_file)

        # 根据传参确定哪个账户是主操作账户，比如借贷、下单、转账等等
        self.binance = self.create_exchange(account)
        self.account = account
        
        # 账户类型
        # account_types = self.binance.options['accountsByType'] # binance所有的账户类型
        # print(account_types) # {'main': 'MAIN', 'spot': 'MAIN', 'funding': 'FUNDING', 'margin': 'MARGIN', 'cross': 'MARGIN', 'future': 'UMFUTURE', 'delivery': 'CMFUTURE', 'linear': 'UMFUTURE', 'inverse': 'CMFUTURE'}
        # main、spot现货账户（默认），funding资金账户，margin、cross逐仓/全仓杠杆账户，futures、delivery、linear、inverse合约账户

        # 支持的方法
        # print(dir(self.binance)) 
        
        # self.get_network_list()

    @try_except_code
    def create_exchange(self, account):
        # 提现ip可设置多个，从中任选一个.提到init函数中如果有需要发请求的地方可以直接用
        proxy_arr = self.account_apis[account]['main']['api_proxy']
        proxy = random.choice(proxy_arr)
        proxies = {"http": proxy, "https": proxy}
        # 根据传参确定哪个账户是主操作账户，比如借贷、下单、转账等等
        binance = ccxt.binance({
            'apiKey': self.account_apis[account]['main']['api_key'],
            'secret': self.account_apis[account]['main']['api_secret'],
            'proxies': proxies,
            'enableRateLimit': True,  # 启用请求速率限制
            'options': {'adjustForTimeDifference': True}, # 自动调整时间戳以适应本地计算机的时区差异
        })
        return binance

    @try_except_code
    def last_price(self, symbol, price, time_):
        """价格预警

        ccxt统一api: 
            fetch_ticker(): 查询交易对信息

        Attributes:
            symbol:交易对。例:IMX/USDT
            price:预警价格
            time_:间隔时间
        """
        while True:
            symbol = symbol.upper()
            ticker = self.binance.fetch_ticker(symbol)
            token_price =float(ticker['last'])# 币安最新成交价
            # print(token_price)
            if token_price <float(price):
                content = symbol+"价格已跌破"+str(price)+"，最新成交价："+str(token_price)
                print(content)
                dingding_notice(content)
                break
            time.sleep(time_)     

    @try_except_code
    def fetch_balance(self, coin):
        coin = coin.upper()
        # spot现货账户，funding资金账户，margin、is_margin逐仓/全仓杠杆账户
        all_balance = self.binance.fetch_balance(params={"type": "spot"})
        coin_balance = all_balance[coin]['free']
        print('账户', self.account, '现有', coin_balance, coin)
        return coin_balance
        
    @try_except_code
    def withdraw(self, coin ,amount, address):
        """提现。提现数量即为到账数量
        
        要求: 必须设置ip才有提现权限

        关于内部转账：币安内部转账不能用邮箱，需要用区块链地址，跟外部转账一样，先收手续费。他们维护一个用户的区块链地址，如果此地址在他们的用户地址表里，那么就把手续费再退给你。
        一个很明显的缺点:不是自己控制的账户不能通过邮箱来转换区块链地址了,因为需要调用接口来获取区块链地址。只有自己控制的账户才可以传邮箱实现内部转账了。而且麻烦,需要每个账户都创建api
        如果想内部转账给别人,只能使用相关币种网络的区块链地址。。。他们有个BinancePay可以通过邮箱转账给别人。但是api是商用的,没办法使用
        1、自己的小号内部转账可以使用邮箱或手机号,前提是开启api.
        2、别人的号内部转账无法使用邮箱或手机号,必须使用币种区块链地址
        3、内部转账时方法最后显示的手续费不准,只是显示问题,实际手续费为0(因为它是先收后退的,判断是不是内部地址是币安内部逻辑,无法获取)
        
        ccxt统一api: 
            fetch_balance(): 查询账户信息
            fetch_deposit_address(): 获取地址
            fetch_transaction_fees(): 获取交易手续费
            withdraw(): 提现
        
        Attributes:
            coin: 提现币种
            amount: 提现数量
            address: 提现地址。外部地址为真实地址(例:0x...),内部地址为哪个账户(例:xxx@gmail.com)
        """
        coin = coin.upper()
        amount = float(amount)
        # 判断传递的地址是不是合法的手机号或邮箱。代表内部地址，此账户必须是自己控制的账户，因为需要使用api调用接口获取区块链地址
        if is_valid_contact(address):
            withdraw_type = '内部转账'
            current_binance = self.create_exchange(address)
            address = current_binance.fetch_deposit_address(coin, params={"network": self.chain})['address']
        # 判断是不是区块链地址。这个地址可能是内部地址也可能是外部地址。给别人内部转账时也需要用区块链地址
        elif is_valid_address(address):
            withdraw_type = '链上提现'
        else:
            print('提现地址输入错误。请确认')
            return
        # 获取币种信息，包括支持的所有币种名称、精度、最小交易数量、提现手续费等信息。调用的是获取所有币种信息的端点GET /sapi/v1/capital/config/getall (HMAC SHA256)，返回一个包含所有币种信息的字典
        # 方法1:ccxt隐式api sapi_get_capital_config_getall,直接调用binance端点
        # 方法2:ccxt统一api exchange.fetch_currencies()[asset]
        # 方法3:ccxt统一api fetch_transaction_fees
        coin_info = self.binance.fetch_currencies()[coin]
        for data in coin_info['info']['networkList']:
            if data['network'] == self.chain:
                withdraw_integer_multiple = data['withdrawIntegerMultiple'] # 精度。ccxt返回'0.000000001'这样的字符串
                withdraw_integer_multiple = abs(Decimal(withdraw_integer_multiple).as_tuple().exponent) # 获取小数位数
                amount_decimals = abs(Decimal(str(amount)).as_tuple().exponent) # 获取小数位数
                if amount_decimals > withdraw_integer_multiple:
                    print('超出提现精度,请确认')
                    return
                min_withdraw_amount = float(data['withdrawMin']) # 提现最小值 ccxt返回字符串
                if amount < min_withdraw_amount:
                    print('提现数量小于提现最小值', min_withdraw_amount)
                    return
        # 手续费 ccxt返回float。如果是内部提现，先收转账手续费，再退。。。
        coin_transaction_fee_of_chain = coin_info['fees'][self.chain]
        # # fetch_transaction_fee方法
        # all_coins_info = self.binance.fetch_transaction_fee(code=coin, params={'network':self.chain}) # 参数无效，还是会返回所有的信息
        # for coins_info in all_coins_info['info']:
        #     if coins_info['coin'] == coin:
        #         for coin_info in coins_info['networkList']:
        #             if coin_info['network'] == self.chain:
        #                 withdraw_integer_multiple = coin_info['withdrawIntegerMultiple'] # 精度。ccxt返回'0.000000001'这样的字符串
        #                 withdraw_integer_multiple = abs(Decimal(withdraw_integer_multiple).as_tuple().exponent) # 获取小数位数
        #                 amount_decimals = abs(Decimal(str(amount)).as_tuple().exponent) # 获取小数位数
        #                 if amount_decimals > withdraw_integer_multiple:
        #                     print('超出提现精度,请确认')
        #                     return
        #                 min_withdraw_amount = float(coin_info['withdrawMin']) # 提现最小值 ccxt返回字符串
        #                 if amount < min_withdraw_amount:
        #                     print('提现数量小于提现最小值', min_withdraw_amount)
        #                     return
        # # 手续费。ccxt处理过了，专门返回各币种手续费.ccxt返回float。如果是内部提现，先收转账手续费，再退。。。
        # coin_transaction_fee_of_chain = all_coins_info['withdraw'][coin][self.chain]
        coin_balance = self.fetch_balance(coin)
        # 判断账户余额够不够
        if (amount + coin_transaction_fee_of_chain) > coin_balance:
            print('提现金额超出余额，请先充值或者减少提现数量')
            return
        # 币安手续费由接收方出（提现资金里扣）。转出金额设置为 amount + coin_transaction_fee_of_chain
        # 如果链上提现，那么接收方扣除手续费coin_transaction_fee_of_chain，到账amount
        # 如果内部转账，免费，但是需要先收后退。transactionFeeFlag设置为False，手续费归转出方（设置为True手续费归接收方）。接收方扣除手续费coin_transaction_fee_of_chain，到账amount
        # walletType: 从那个账户提现。0为现货账户（默认），1为资金账户。
        withdraw = self.binance.withdraw(coin, amount + coin_transaction_fee_of_chain, address, tag=None, params={"network": self.chain, 'transactionFeeFlag':False, 'walletType': 0})
        # 内部转账时这个手续费显示不准。应该为0。没有币安内部地址表，无法判断。
        print(f'转出方:{self.account}\n接收方:{address}\n提现币种:{coin}\n提现数量:{amount+coin_transaction_fee_of_chain}\n提现方式:{withdraw_type}\n提现网络:{self.chain}\n提现手续费:{coin_transaction_fee_of_chain}\n到账数量:{amount}')
    
    @try_except_code
    def transfer(self, coin, amount, from_account, to_account, from_symbol='', to_symbol=''):
        """划转。可以账户内划转，也可以子母账户间划转
        要求: 需要开启api的'允许万向划转'功能
        POST /sapi/v1/asset/transfer (HMAC SHA256)
        Attributes:
            coin: 划转币种
            amount: 划转数量
            from_account: 转出账户.如交易账户trading或18
            to_account: 转入账户.如资金账户funding或6
        """
        coin = coin.upper()
        amount = float(amount)
        from_symbol = from_symbol.upper()
        to_symbol = to_symbol.upper()
        # type：主要用到的MAIN_FUNDING现货账户转到资金账户,FUNDING_MAIN资金账户转到现货账户,MAIN_MARGIN现货账户转到杠杆账户,MARGIN_MAIN杠杆账户转到现货账户,MARGIN_FUNDING杠杆账户转入资金账户,FUNDING_MARGIN资金账户转入杠杆账户
        if from_account in ['spot', 'main'] and to_account == 'funding':
            params = {"type": "MAIN_FUNDING"} # 现货账户转到资金账户
            self.binance.transfer(coin, amount, fromAccount=from_account, toAccount=to_account, params = params)
        elif from_account == 'funding' and to_account in ['spot', 'main']:
            params = {"type": "FUNDING_MAIN"} # 资金账户转到现货账户
            self.binance.transfer(coin, amount, fromAccount=from_account, toAccount=to_account, params = params)
        elif from_account in ['spot', 'main'] and to_account == 'margin':
            params = {"type": "MAIN_MARGIN"} # 现货账户转到全仓杠杆账户
            self.binance.transfer(coin, amount, fromAccount=from_account, toAccount=to_account, params = params)
        elif from_account == 'margin' and to_account in ['spot', 'main']:
            params = {"type": "MARGIN_MAIN"} # 全仓杠杆账户转到现货账户
            self.binance.transfer(coin, amount, fromAccount=from_account, toAccount=to_account, params = params)
        elif from_account == 'funding' and to_account == 'margin':
            params = {"type": "FUNDING_MARGIN"} # 资金账户转入全仓杠杆账户
            self.binance.transfer(coin, amount, fromAccount=from_account, toAccount=to_account, params = params)
        elif from_account == 'margin' and to_account == 'funding':
            params = {"type": "MARGIN_FUNDING"} # 全仓杠杆账户转到资金账户
            self.binance.transfer(coin, amount, fromAccount=from_account, toAccount=to_account, params = params)
        elif from_account == 'margin' and to_account == 'isolated_margin':
            params = {"type": "MARGIN_ISOLATEDMARGIN", "toSymbol": to_symbol} # 全仓杠杆账户转到逐仓杠杆账户
            self.binance.transfer(coin, amount, fromAccount=from_account, toAccount=to_account, params = params)
        elif from_account == 'isolated_margin' and to_account == 'margin':
            params = {"type": "ISOLATEDMARGIN_MARGIN", "fromSymbol": from_symbol} # 逐仓杠杆账户转到全仓杠杆账户
            self.binance.transfer(coin, amount, fromAccount=from_account, toAccount=to_account, params = params)
        elif from_account == 'isolated_margin' and to_account == 'isolated_margin':
            params = {"type": "ISOLATEDMARGIN_ISOLATEDMARGIN", "fromSymbol": from_symbol, "toSymbol": to_symbol} # 逐仓杠杆账户转到逐仓杠杆账户
            self.binance.transfer(coin, amount, fromAccount=from_account, toAccount=to_account, params = params)
        elif from_account in ['spot', 'main'] and to_account == 'isolated_margin':
            # 现货账户转到逐仓杠杆账户.万向划转不支持现货和逐仓账户之间划转.调用杠杆逐仓账户划转端口
            # POST /sapi/v1/margin/isoated/transfer (HMAC SHA256)
            self.binance.sapi_post_margin_isolated_transfer(params={'asset': coin,'symbol': to_symbol, 'transFrom': 'ISOLATED_MARGIN', 'transTo': 'SPOT', 'amount': amount})
        elif from_account == 'isolated_margin' and to_account in ['spot', 'main']:
            # 逐仓杠杆账户转到现货账户
            # POST /sapi/v1/margin/isoated/transfer (HMAC SHA256)
            self.binance.sapi_post_margin_isolated_transfer(params={'asset': coin,'symbol': from_symbol, 'transFrom': 'SPOT', 'transTo': 'ISOLATED_MARGIN', 'amount': amount})
        print(f"划转方向: {from_account}账户 -> {to_account}账户\n划转币种: {coin}\n划转数量: {amount}")
    
    @try_except_code
    def margin_loan(self, loan_currency, once_loan_amount, remind_amount, risk_level=4, is_isolated=False, loan_asset='USDT'):
        """币安杠杆账户借款

        once_loan_amount是一次借贷的数量,remind_amount是最终借贷数量
        如果可借资产充足的话,可设置once_loan_amount跟remind_amount一样,一次借完.
        如果可借资产不足的话,比如有活动时热门资产,一般都不好借.需要小额多次去尝试借贷.once_loan_amount一次借贷的量要小于remind_amount最终借贷数量

        ccxt隐式api:
            sapi_post_margin_loan() 杠杆账户借贷 根据币安api: POST /sapi/v1/margin/loan (HMAC SHA256) 生成

        Attributes:
            loan_currency:借款币种
            once_loan_amount:一次借贷数量。如果资产不够，一下子借太多容易爆仓
            remind_amount:借到一定数量触发钉钉提醒
            risk_level:未转出时的风险率,默认为4.借款之后还要转出,才是最后的风险率。这里设置为4,控制转出后风险率在3左右
            is_isolated:借款方式,False为全仓(默认),True为逐仓
            loan_asset:抵押资产,逐仓用
        return:
            free_amount: 借贷数量
        """
        loan_currency = loan_currency.upper()
        once_loan_amount = float(once_loan_amount)
        remind_amount = float(remind_amount)
        loan_asset = loan_asset.upper()
        while True:
            data = self.margin_account_info(loan_currency, is_isolated, loan_asset)
            if data == None:
                return
            symbol = data['symbol']
            margin_level = data['margin_level']
            free_amount = data['free_amount']
            # print(symbol, margin_level, free_amount)
            # 如果账户里有超出借贷数量的余额就别借了,发钉钉提醒
            if free_amount >= remind_amount:
                type_ = '全仓' if is_isolated == False else '逐仓'
                content = f"币安账户:{self.account}\n{type_}借{loan_currency}\n已借未转出数量: {free_amount}\n当前风险率: {margin_level}"
                print(content)
                dingding_notice(content) # 钉钉提醒
                break
            # 风险控制，不能爆仓
            if margin_level < risk_level:
                content = f"币安账户:{self.account}\n{type_}借{loan_currency}\n已借未转出数量: {free_amount}\n当前风险率: {margin_level}\n借贷超过指定风险率,程序停止"
                print(content)
                dingding_notice(content) # 钉钉提醒
                break
            # 如果资产不够，一下子借太多容易爆仓
            max_amount = self.get_margin_maxborrowable_account(loan_currency, is_isolated, symbol)
            if once_loan_amount > max_amount: 
                content = f"最大可借数量不足，请补充资产或降低每次借贷数量"
                print(content)
                dingding_notice(content) # 钉钉提醒
                break
            # 借款
            params = {'asset': loan_currency,'amount': once_loan_amount} if not is_isolated else {'asset': loan_currency,'amount': once_loan_amount,'symbol': symbol,'isIsolated': 'TRUE'}  
            response = self.binance.sapi_post_margin_loan(params)
            if 'tranId' in response:
                print(f"借款 {once_loan_amount} {loan_currency} 成功！")
            else:
                print(f"借款 {once_loan_amount} {loan_currency} 失败！错误信息：{response['msg']},继续尝试借贷")
        # print(free_amount)
        return free_amount
  

    @try_except_code
    def margin_account_info(self, coin, is_isolated=False, asset=''):
        """查询币安杠杆账户信息

        ccxt统一api: 
            fetch_balance(params={'type': 'margin'}) 查询杠杆账户信息(全仓用) type默认现货账户, margin为杠杆账户, future为合约账户
        ccxt隐式api:
            sapi_get_margin_isolated_account() 查询逐仓杠杆账户信息 根据币安api: GET /sapi/v1/margin/isolated/account (HMAC SHA256) 生成

        Attributes:
            coin:借款币种
            is_isolated:借款方式,False为全仓(默认),True为逐仓
            asset:抵押资产,逐仓用
        return:
            margin_level:账户当前风险率
            free_amount:账户当前已借可用数量
        """
        coin = coin.upper()
        asset = asset.upper()
        margin_symbol = f'{coin}{asset}'
        reversed_margin_symbol = f'{asset}{coin}'
        if not is_isolated: # 查询全仓杠杆账户信息
            margin_account = self.binance.fetch_balance(params={'type': 'margin'}) # type默认现货账户， margin为全仓杠杆账户， future为合约账户
            # print('账户信息', margin_account) 
            margin_coin_list = []
            for margin_coin_info in margin_account['info']['userAssets']:
                margin_coin_list.append(margin_coin_info['asset'])
            if coin not in margin_coin_list:
                print('全仓杠杆账户不存在',coin,'借贷币种,请核对')
                return None
            if float(margin_account['info']['totalAssetOfBtc']) == 0.0:
                print('全仓账户无可抵押资产,请先划转')
                return None
            margin_level = float(margin_account['info']['marginLevel'])
            # print('风险率', margin_level)
            free_amount = margin_account[coin]['free']
            # print('借到未转出数量',free_amount)
            symbol = ''
        else:# 查询逐仓逐仓账户信息
            # GET /sapi/v1/margin/isolated/allPairs (HMAC SHA256)
            margin_isolated_allpairs = self.binance.sapi_get_margin_isolated_allpairs()
            # print(margin_isolated_allpairs)
            margin_isolated_symbol_list = []
            for margin_isolated_symbol_info in margin_isolated_allpairs:
                margin_isolated_symbol_list.append(margin_isolated_symbol_info['symbol'])
            if margin_symbol not in margin_isolated_symbol_list and reversed_margin_symbol not in margin_isolated_symbol_list:
                print('逐仓杠杆账户不存在',margin_symbol,'借贷交易对,请核对')
                return None
            for data in margin_isolated_symbol_list:
                if data == margin_symbol or data == reversed_margin_symbol:
                    symbol = data
            #GET /sapi/v1/margin/isolated/account
            # 最多可以传5个symbol; 由","分隔的字符串表示. e.g. "BTCUSDT,BNBUSDT,ADAUSDT"
            margin_isolated_account = self.binance.sapi_get_margin_isolated_account(params={'symbols': symbol})
            # print('账户信息', margin_isolated_account)
            # 判断返回结果中哪个是抵押代币,如果抵押代币的余额为0,需要先充值资产
            if margin_isolated_account['assets'][0]['baseAsset']['asset'] == asset:
                if float(margin_isolated_account['assets'][0]['baseAsset']['free']) == 0.0:
                    print(f'{symbol} 借贷对没有抵押 {asset} 资产,请先划转')
                    return None
            elif margin_isolated_account['assets'][0]['quoteAsset']['asset'] == asset:
                if float(margin_isolated_account['assets'][0]['quoteAsset']['free']) == 0.0:
                    print(f'{symbol} 借贷对没有抵押 {asset} 资产,请先划转')
                    return None
            margin_level = float(margin_isolated_account['assets'][0]['marginLevel'])
            # print('风险率', margin_level)
            free_amount = float(margin_isolated_account['assets'][0]['baseAsset']['free'])
            # print('借到未转出数量',free_amount)
        # print(symbol, margin_level, free_amount)
        return {'symbol':symbol, 'margin_level':margin_level, 'free_amount':free_amount}

    @try_except_code
    def get_margin_maxborrowable_account(self, coin, is_isolated=False, symbol=''):
        """查询币安杠杆账户最大可借贷额度

        ccxt隐式api:
            sapi_get_margin_maxborrowable() 查询最大可借数量 根据币安api: GET /sapi/v1/margin/maxBorrowable 生成
        
        Attributes:
            coin:借款币种
            is_isolated:借款方式。默认全仓,False为逐仓
            asset:抵押币种。逐仓用,默认为抵押USDT
        return:
            max_amount:账户当前最大可借额度
        """
        coin = coin.upper()
        symbol = symbol.upper()
        # 逐仓全仓参数
        params = {'asset': coin} if not is_isolated else {'asset': coin,'isolatedSymbol': symbol}
        # print(params)
        # 拼接 最大可借贷额度 GET /sapi/v1/margin/maxBorrowable
        max_borrowable = self.binance.sapi_get_margin_maxborrowable(params)
        max_amount = float(max_borrowable['amount'])
        # 系统可借充足情况下用户账户当前最大可借额度
        print(f'账户 {self.account} {coin} 最大可借数量为：{max_amount}')
        return max_amount

    @try_except_code
    def transfer_from_sub_account(self, coin ,amount, sub_account):
        """子账户往母账户划转，只能转自己对应的母账户.子账户需要币安VIP1才能申请

        ccxt统一api: 
            fetch_balance(): 查询账户信息
        ccxt隐式api:
            sapi_post_sub_account_transfer_subToMaster() 向主账户主动划转 (仅适用子账户) 根据币安api: POST /sapi/v1/sub-account/transfer/subToMaster (HMAC SHA256) 生成

        Attributes:
            coin: 提现币种
            amount: 提现数量
            sub_account: 子账户.例:'1'
        """

        coin = coin.upper()
        amount = float(amount)
        current_sub_balance = ccxt.binance(self.account_apis[self.account]['sub'][sub_account])
        all_balance = current_sub_balance.fetch_balance()
        # print(all_balance)
        coin_balance = all_balance[coin]['free']
        print('账户', self.account,'的子账户',sub_account, '现有', coin_balance, coin)

        # 向主账户主动划转 (仅适用子账户)
        # POST /sapi/v1/sub-account/transfer/subToMaster (HMAC SHA256)
        withdraw = current_sub_balance.sapi_post_sub_account_transfer_subToMaster(params={'asset':coin,'amount':amount})
        # print(m2, withdraw)
        print('子账户',sub_account,'划转',amount,coin,'到主账户',self.account)

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
        # newOrderRespType ACK: 返回速度最快，不包含成交信息，信息量最少; RESULT:返回速度居中，返回吃单成交的少量信息; FULL: 返回速度最慢，返回吃单成交的详细信息
        order_info = self.binance.create_order(order_symbol, order_type, order_side, order_amount, order_price, params={'newOrderRespType':'ACK'})
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
        order_info = self.binance.fetch_order(id, symbol)
        # print(order_info)
        print(f"订单时间: {order_info['datetime']}\n订单价格: {order_info['price']}\n订单剩余成交: {order_info['remaining']}\n订单状态: {order_info['status']}")

    @try_except_code
    def fetch_orders_by_symbol(self, symbol, limit=10):
        """根据交易对查询订单信息

        ccxt统一api: 
            fetch_orders()

        Attributes:
            symbol:交易对。例:'ETH/USDT'
            limit:返回几条数据。默认10条
        return:
            订单信息
        """
        symbol = symbol.upper()
        order_info = self.binance.fetch_orders(symbol=symbol, limit=limit)  # limit参数控制返回最近的几条
        for i in order_info:
            print(f"订单时间: {i['datetime']}\n订单id: {i['id']}\n订单价格: {i['price']}\n订单剩余成交: {i['remaining']}\n订单状态: {i['status']}")
            print('-----------------------------------')
   
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
        order_info = self.binance.fetch_open_orders(symbol, limit)  # limit参数控制返回最近的几条
        # print(order_info)
        for i in order_info:
            print(f"订单时间: {i['datetime']}\n订单id: {i['id']}\n订单价格: {i['price']}\n订单剩余成交: {i['remaining']}\n订单状态: {i['status']}")
            print('-----------------------------------')
    
    @try_except_code
    def edit_order(self, order_id, order_symbol, order_type, order_side, order_amount, order_price, is_auto_reorder=False):
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
            is_auto_reorder: 如果撤消订单失败是否继续重新下单.币安修改订单好像是通过撤销订单再下单的方式完成的
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
        order_price = self.binance.price_to_precision(order_symbol, order_price)
        order_price = float(order_price)
        # 指定类型：STOP_ON_FAILURE - 如果撤消订单失败将不会继续重新下单。ALLOW_FAILURE - 不管撤消订单是否成功都会继续重新下单。
        cancelReplaceMode = 'ALLOW_FAILURE' if is_auto_reorder == True else 'STOP_ON_FAILURE'
        updated_order = self.binance.edit_order(order_id, order_symbol, order_type, order_side, order_amount, order_price, params={"cancelReplaceMode":cancelReplaceMode})
        # print(updated_order)
        order_price = updated_order['price'] if order_type == 'market' else order_price
        print(f"修改订单成功\n交易对: {order_symbol}\n类型: {order_type}\n方向: {order_side}\n数量: {order_amount}\n价格: {order_price}\n订单时间: {updated_order['datetime']}\n订单ID: {updated_order['id']}")

    @try_except_code
    def order_limit(self, symbol):
        symbol = symbol.upper()
        self.binance.load_markets()  # 加载市场信息
        markets_info = self.binance.markets
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
        order_info = self.binance.cancel_order(id, symbol)
        # print(order_info)
        # 撤单之后查询状态
        order_info = self.binance.fetch_order(id, symbol)
        print(order_info['status'])

if __name__ == '__main__':

    data = my_format_data(start_num=1, end_num=1)
    
    # for d in data:
    #     print(d)
    #     # 参数：account, chain
    #     # account：操作账户。chain：这里的chain两个地方用到，一个是binance文件，代表转账的链，另一个是transfer文件，代表主链
    #     # chain:BSC,ETH,SOL,TRX,MATIC,OPTIMISM
    #     binance = BinanceUtil('gaohongxiang69@gmail.com', 'bsc')
          
    #     # 链上提现
    #     # 参数：coin、amount、address(内部地址写account_1、account_2...程序根据api自动获取，外部地址写具体地址）
    #     # binance.withdraw('usdt', 10, d['address'])
    # exit()



    # 参数：account、chain
    binance = BinanceUtil('gaohongxiang69@gmail.com', 'eth')

    # binance.fetch_balance('usdt')

    # # 如果是内部转账(自己控制的账户直接写邮箱,给别人内部转账也需要写区块链地址)
    # binance.withdraw('usdt', 12, 'TN8mKX4uzBDyxtG7DXDFCcf9ioXrFQBpMM')

    # 资金划转
    # 参数：coin, amount, from_account, to_account, from_symbol, to_symbol
    # 账户类型：spot现货账户、funding资金账户、margin全仓杠杆账户、isolated_margin逐仓杠杆账户
    # binance.transfer('usdt', 10, 'spot', 'margin')
    # binance.transfer(coin='usdt', amount=10, from_account='spot', to_account='funding') # 现货账户到资金账户
    # binance.transfer(coin='usdt', amount=10, from_account='funding', to_account='spot') # 资金账户到现货账户
    # binance.transfer(coin='usdt', amount=10, from_account='spot', to_account='margin') # 现货账户到全仓杠杆账户
    # binance.transfer(coin='usdt', amount=10, from_account='margin', to_account='spot') # 全仓杠杆账户到现货账户
    # binance.transfer(coin='usdt', amount=10, from_account='funding', to_account='margin') # 资金账户到全仓杠杆账户
    # binance.transfer(coin='usdt', amount=10, from_account='margin', to_account='funding') # 全仓杠杆账户到资金账户
    # 逐仓杠杆账户是需要交易对的.划转时需要确认从哪个交易对转移哪个代币到哪个交易对
    # binance.transfer(coin='imx', amount=11.99996312, from_account='margin', to_account='isolated_margin', to_symbol='IMXUSDT') # 全仓杠杆账户到逐仓杠杆账户
    # binance.transfer(coin='imx', amount=12, from_account='isolated_margin', to_account='margin', from_symbol='IMXUSDT') # 逐仓杠杆账户到全仓杠杆账户
    # binance.transfer(coin='usdt', amount=10, from_account='isolated_margin', to_account='isolated_margin', from_symbol='ETHUSDT', to_symbol='IMXUSDT') # # 逐仓杠杆账户到逐仓杠杆账户
    # binance.transfer(coin='usdt', amount=10, from_account='spot', to_account='isolated_margin', to_symbol='IMXUSDT') # 现货账户到逐仓杠杆账户
    # binance.transfer(coin='usdt', amount=10, from_account='isolated_margin', to_account='spot', from_symbol='ETHUSDT') # 逐仓杠杆账户到现货账户
    


    # 杠杆账户借贷 loan_currency(借贷资产), once_loan_amount(一次借贷数量), remind_amount(最终借贷数量), risk_level=4(风险率), is_isolated=False(是否逐仓), loan_asset='USDT'(抵押资产,is_isolated=True时生效)
    # 如果once_loan_amount<remind_amount程序会多次借贷,直到满足remind_amount.如果once_loan_amount=remind_amount程序就只借贷一次
    # binance.margin_loan(loan_currency='imx', once_loan_amount=4, remind_amount=10, risk_level=4, is_isolated=True, loan_asset='usdt')

    # 获取杠杆账户信息
    # coin(借贷资产), is_isolated=False, asset=''(抵押资产,is_isolated=True时生效)
    # account = binance.margin_account_info(coin='eth', is_isolated=True, asset='usdt')
    # print(account)
    
    # coin(划转币种，借贷币种), is_margin=True（默认全仓）, asset=''（抵押币种）
    # binance.transfer_from_margin_to_spot('sand')
   

    
    # 下单 
    # 参数 order_symbol, order_type, order_side, order_amount, order_price=None
    # binance.create_order(order_symbol='IMX/USDT',order_type='limit', order_side='buy', order_amount=20, order_price=0.5)

    # 若币安买卖订单报错{"code":-1013,"msg":"Filter failure: MIN_NOTIONAL"}
    # 原因：不满足币安交易规则中最小交易金额限制

    # 查单
    # binance.fetch_order_by_id('277156603', 'IMX/USDT')
    # binance.fetch_orders_by_symbol('IMX/USDT')
    # binance.fetch_open_orders('IMX/USDT')

    # 修改订单
    # 参数 order_id, order_symbol, order_type(limit、market), order_side(buy、sell), order_amount, order_price, is_auto_reorder=False(如果撤销订单失败是否重新下单)
    # binance.edit_order(order_id='279170925', order_symbol='IMX/USDT', order_type='limit', order_side='buy', order_amount=20, order_price=0.6, is_auto_reorder=False)

    # 撤单
    # binance.cancel_order('279191058', 'IMX/USDT')
    
