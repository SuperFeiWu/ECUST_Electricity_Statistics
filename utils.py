"""
工具函数模块
"""

import requests


def sendMsgToWechat(token: str, title: str, content: str, template: str = "html") -> None:
    """
    发送消息到微信 (PushPlus)

    Args:
        token: PushPlus Token
        title: 消息标题
        content: 消息内容
        template: 模板类型 (html, txt, markdown, json)
    """
    url = "http://www.pushplus.plus/send"
    data = {
        "token": token,
        "title": title,
        "content": content,
        "template": template,
    }
    response = requests.post(url, json=data)
    if response.status_code == 200:
        result = response.json()
        if result.get("code") == 200:
            print("PushPlus 发送成功")
        else:
            print(f"PushPlus 发送失败: {result.get('msg')}")
    else:
        print(f"PushPlus 请求失败: {response.status_code}")
