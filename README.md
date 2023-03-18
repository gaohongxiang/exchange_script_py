# 功能

- 内部转账
- 链上提现
- 账户内各类型划转。如交易账户划转到资金账户
- 子母账户间划转(限okx)。如子账户资金账户划转到母账户资金账户
- 下单、查单、撤单
- 借贷(限binance)
- 钉钉机器人提醒

# 前置条件
- python3，可通过anaconda安装
- 编辑器，如vscode
- 独立ip(创建api时需要用到)
- 交易所账号

## 说明
- python、编辑器问题需要自行搜索答案。
- 本程序在mac下测试，windows需要自行测试
- 如果报错找不到哪个包,就用`pip install 包名称`安装就好

# 文件结构
```
exchange_script
    binance.py # 币安交易所文件
    okx.py  # ok交易所文件
    config.py # 配置文件
    formatdata.py # 格式化地址文件
    README.md # 说明文档
    .gitignore # git版本控制系统文件，敏感数据不上传
    utils_
        onepassword.py  # 1Password文件
        utils.py # 功能性文件
    data
        binance.json # 币安账户api数据文件
        okx.json # ok账户api数据文件
        wallet.csv # 地址文件，外部转账用
```

# 准备数据文件

config.py

```
okx_api_file = './data/okx.json'
binance_api_file = './data/binance.json'
eth_wallet_file = './data/wallet.csv'
okx_address_file = './data/okx_address.csv'

# 钉钉机器人id(没加密)
ROBOTID = 'xxxxx'
```

wallet.csv
```
wallet
xxxxx
xxxxx
...
```

binance.json、okx.json详见文本加密部分


# api创建

## binance

- 提现权限必须设置ip，可以多个ip。这里是用的独立ip，请求时随机选一个ip。把ip设置到okx.json文件里，存socks5形式。ip没有加密，一是数据不是特别敏感，二是有时候ip不能用了，需要更换，如果加密到时候还需要解密才知道是哪个ip
- 划转功能用到了万向划转,需要开启万向划转权限

## okx

- 提现权限必须设置ip，可以多个ip。这里是用的独立ip，请求时随机选一个ip。把ip设置到okx.json文件里，存socks5形式。ip没有加密，一是数据不是特别敏感，二是有时候ip不能用了，需要更换，如果加密到时候还需要解密才知道是哪个ip
- 提现要求：提币地址必须设置为免验证地址。去官网一个个设置吧


# 文本加密

api数据属于敏感数据，肯定需要加密存储，最好是不存储在代码中。

1. 方案1：api加密存储，密钥也存储在配置中。但是密钥存储别人得到密钥后加密的api跟明文没区别。
2. 方案2：密钥不存储，每次运行程序都在终端输入。安全点，但是非常繁琐。
3. 方案3：使用1password存储api数据，密钥引用语法写配置文件，运行的时候解析配置文件，加载真正数据。api数据不会暴露在代码中，解析时用指纹授权。安全方便,但会增加一点通信时间.

本代码使用方案3，流程如下

1、根据文档安装1password GUI（图形用户界面、客户端）、1password CLI（命令行界面），连接两者，开启指纹。
- 1password文档：https://developer.1password.com/docs/cli/secrets-config-files

2、1password客户端创建一个保险库，存入自己的api数据。
- 路径`<vault-name>/<item-name>[/<section-name>]/<file-name>`
- 我的`<Blockchain>/<binance>|<okx>/<gaohongxiang69_gmail.com-main>/<api_key>` @特殊字符好像不支持，我换成了_。无所谓，自己知道就好

3、配置文件

`binance.json`
```
{
    "gaohongxiang69@gmail.com":{
        "main":{
            "api_key": "op://Blockchain/binance/gaohongxiang69_gmail.com-main/api_key",
            "api_secret": "op://Blockchain/binance/gaohongxiang69_gmail.com-main/api_secret",
            "api_proxy": ["socks5://qoytdppy:ahwms9ynfn71@45.114.15.37:6018"]
        },
        "sub1":{
            "api_key": "",
            "api_secret": "",
            "api_proxy": []
        }
    }
}
```

`okx.json`
```
{
    "gaohongxiang69@gmail.com":{
        "main":{
            "api_key": "op://Blockchain/okx/gaohongxiang69_gmail.com-main/api_key",
            "api_secret": "op://Blockchain/okx/gaohongxiang69_gmail.com-main/api_secret",
            "api_password": "op://Blockchain/okx/gaohongxiang69_gmail.com-main/api_password",
            "api_proxy": ["socks5://account:password@host:port"]
        },
        "sub1":{
            "sub_account_name":"gaohongxiang1",
            "api_key": "",
            "api_secret": "",
            "api_password": "",
            "api_proxy": []
        }
    }
}
```

4、解析

调用`onepassword.py`中的`parse_file`方法,将模版配置文件解析为真实的数据文件.使用指纹授权.

# 钉钉机器人提醒

某些场景需要用到提醒功能,比如借贷到一定数量后发消息提醒及时转出.需要用到钉钉机器人.添加好机器人后将机器人的id写在`config.py`文件中,使用时是调用的`dingding_notice`函数.

设置机器人可以参考这个文档:https://open.dingtalk.com/document/orgapp/custom-robot-access


# 示例

详见各文件示例