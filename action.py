#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@FILE    :   action.py
@DSEC    :   网易云音乐签到刷歌脚本
@AUTHOR  :   Secriy
@DATE    :   2020/08/25
@VERSION :   2.1
'''

import os
import sys
import requests
import base64
import json
import hashlib
import binascii
import codecs
import argparse
import random
import time
from Crypto.Cipher import AES


class Encrypt:
    def __init__(self):
        self.modulus = '00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615bb7b725152b3ab17a876aea8a5aa76d2e417629ec4ee341f56135fccf695280104e0312ecbda92557c93870114af6c9d05c4f7f0c3685b7a46bee255932575cce10b424d813cfe4875d3e82047b97ddef52741d546b8e289dc6935b3ece0462db0a22b8e7'
        self.nonce = '0CoJUm6Qyw8W8jud'
        self.pubKey = '010001'

    # Random String Generator
    def createSecretKey(self, size):
        return str(binascii.hexlify(os.urandom(size))[:16], encoding='utf-8')

    # AES Encrypt
    def aesEncrypt(self, text, secKey):
        pad = 16 - len(text) % 16
        text = text + pad * chr(pad)
        encryptor = AES.new(secKey.encode('utf8'), 2, b'0102030405060708')
        ciphertext = encryptor.encrypt(text.encode('utf8'))
        ciphertext = str(base64.b64encode(ciphertext), encoding='utf-8')
        return ciphertext

    # RSA Encrypt
    def rsaEncrypt(self, text, pubKey, modulus):
        text = text[::-1]
        rs = int(text.encode('utf-8').hex(), 16)**int(pubKey, 16) % int(
            modulus, 16)
        return format(rs, 'x').zfill(256)

    def encrypt(self, text):
        secKey = self.createSecretKey(16)
        encText = self.aesEncrypt(self.aesEncrypt(text, self.nonce), secKey)
        encSecKey = self.rsaEncrypt(secKey, self.pubKey, self.modulus)
        return {'params': encText, 'encSecKey': encSecKey}


class CloudMusic:
    def __init__(self):
        self.session = requests.Session()
        self.enc = Encrypt()
        self.headers = {
            "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36",
            "Referer": "http://music.163.com/",
            "Accept-Encoding": "gzip, deflate",
        }

    def login(self, phone, password):
        loginUrl = "https://music.163.com/weapi/login/cellphone"
        self.loginData = self.enc.encrypt(
            json.dumps({
                'phone': phone,
                'countrycode': '86',
                'password': password,
                'rememberLogin': 'true'
            }))
        headers = {
            "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36",
            "Referer":
            "http://music.163.com/",
            "Accept-Encoding":
            "gzip, deflate",
            "Cookie":
            "os=pc; osver=Microsoft-Windows-10-Professional-build-10586-64bit; appver=2.0.3.131777; channel=netease; __remember_me=true;"
        }
        res = self.session.post(url=loginUrl,
                                data=self.loginData,
                                headers=headers)
        ret = json.loads(res.text)
        if ret['code'] == 200:
            self.cookie = res.cookies
            self.csrf = requests.utils.dict_from_cookiejar(
                self.cookie)['__csrf']
            self.nickname = ret["profile"]["nickname"]
            self.beforeCount = self.getLevel()["nowPlayCount"]

            retext = "\"{nickname}\" 登录成功，当前等级：{level}\n\n".format(
                nickname=self.nickname, level=self.getLevel()
                ["level"]) + "距离升级还需听{beforeCount}首歌".format(
                    beforeCount=self.getLevel()["nextPlayCount"] -
                    self.getLevel()["nowPlayCount"])
            return retext
        else:
            return ("登录失败 " + str(ret['code']) + "：" + ret['message'])
            exit()

    def getLevel(self):
        url = "https://music.163.com/weapi/user/level?csrf_token=" + self.csrf
        res = self.session.post(url=url,
                                data=self.loginData,
                                headers=self.headers)
        ret = json.loads(res.text)
        return ret["data"]

    # def refresh(self):
    #     url = "https://music.163.com/weapi/login/token/refresh?csrf_token=" + self.csrf
    #     res = self.session.post(url=url,
    #                             data=self.loginData,
    #                             headers=self.headers)
    #     ret = json.loads(res.text)
    #     print(ret)
    #     return ret["code"]

    def sign(self):
        signUrl = "https://music.163.com/weapi/point/dailyTask"
        res = self.session.post(url=signUrl,
                                data=self.enc.encrypt('{"type":0}'),
                                headers=self.headers)
        ret = json.loads(res.text)
        if ret['code'] == 200:
            return ("签到成功，经验+" + str(ret['point']))
        elif ret['code'] == -2:
            return ("今天已经签到过了")
        else:
            return ("签到失败 " + str(ret['code']) + "：" + ret['message'])

    def task(self, custom):
        url = "https://music.163.com/weapi/v6/playlist/detail?csrf_token=" + self.csrf
        recommendUrl = "https://music.163.com/weapi/v1/discovery/recommend/resource"
        if not custom:
            res = self.session.post(url=recommendUrl,
                                    data=self.enc.encrypt('{"csrf_token":"' +
                                                          self.csrf + '"}'),
                                    headers=self.headers)
            ret = json.loads(res.text)
            if ret['code'] != 200:
                print("获取推荐歌曲失败 " + str(ret['code']) + "：" + ret['message'])
            else:
                lists = ret['recommend']
                musicLists = [(d['id']) for d in lists]
        else:
            musicLists = custom
        musicId = []
        for m in musicLists:
            res = self.session.post(url=url,
                                    data=self.enc.encrypt(
                                        json.dumps({
                                            'id': m,
                                            'n': 1000,
                                            'csrf_token': self.csrf
                                        })),
                                    headers=self.headers)
            ret = json.loads(res.text)
            for i in ret['playlist']['trackIds']:
                musicId.append(i['id'])
        # print("歌单大小：{musicCount}首\n".format(musicCount=len(musicId)))
        postData = json.dumps({
            'logs':
            json.dumps(
                list(
                    map(
                        lambda x: {
                            'action': 'play',
                            'json': {
                                'download': 0,
                                'end': 'playend',
                                'id': x,
                                'sourceId': '',
                                'time': 240,
                                'type': 'song',
                                'wifi': 0
                            }
                        },
                        random.sample(
                            musicId,
                            420 if len(musicId) > 420 else len(musicId)))))
        })
        res = self.session.post(
            url="http://music.163.com/weapi/feedback/weblog",
            data=self.enc.encrypt(postData))
        ret = json.loads(res.text)
        if ret['code'] == 200:
            return ("刷听歌量成功")
        else:
            return ("刷听歌量失败 " + str(ret['code']) + "：" + ret['message'])
            exit(ret['code'])

    # Server Chan Turbo
    def server_chan_turbo(self, sendkey, text):
        url = 'https://sctapi.ftqq.com/%s.send' % sendkey
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        content = {"title": "网易云打卡脚本", "desp": text}
        ret = requests.post(url, headers=headers, data=content)
        print(ret.text)


def getArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("phone", help="your Phone Number")
    parser.add_argument("password", help="MD5 value of the password")
    parser.add_argument("-s",
                        dest="SCKEY",
                        nargs='*',
                        help="SCKEY of the Server Chan")
    parser.add_argument("-l", dest="PLAYLIST", nargs='*', help="your playlist")
    args = parser.parse_args()

    return {
        'phone': args.phone,
        'password': args.password,
        'sckey': args.SCKEY,
        'playlist': args.PLAYLIST
    }


# Server酱推送提醒


def pushMessage(data):
    if SCKEY != "":
        return requests.post(f"https://sc.ftqq.com/{SCKEY}.send", data=data)
    else:
        return False

if __name__ == "__main__":
    # Get Args
    info = getArgs()
    # Start
    app = CloudMusic()
    print(30 * "=")
    # Login
    res_login = app.login(info['phone'], info['password'])
    # Sign In
    res_sign = app.sign()
    # Music Task
    res_task = app.task(info['playlist'])
    # Print Response
    res = res_login + "\n\n" + res_sign + "\n\n" + res_task
    print(res)
    print(30 * "=")
    try:
        pushMessage({
            "text": f"网易云音乐 {res}",
            "desp": time.strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as err:
        print("Server酱调用失败：" + err)
    print(30 * "=")
