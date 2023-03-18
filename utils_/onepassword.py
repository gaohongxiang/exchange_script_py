import subprocess, json
from utils_.utils import try_except_code

@try_except_code
def parse_file(file_):
    """使用1password CLI命令行工具将模版文件解析为真实数据.需要指纹解锁
    Attributes:
            file_:1password模版文件
    """
    # 读取配置模板数据
    with open(file_, 'r', encoding='utf-8') as f:
        template = f.read()
    # 调用 op inject 命令并解析输出为 JSON 对象
    # input 参数需要传入字节类型的数据
    # stdout 参数指定子进程的标准输出流将被重定向到哪里。当指定为 subprocess.PIPE 时，子进程的标准输出会被捕获并返回给调用者，以便可以在 Python 脚本中进一步处理。
    output = subprocess.run(['op', 'inject'], input=template.encode(), stdout=subprocess.PIPE)
    data = json.loads(output.stdout.decode())
    return data

if __name__ == '__main__':
    parse_file('./data/okx.json')