from hoshino import Service , R
import json
import asyncio
from os import path
from hoshino import aiorequests
import time
import nonebot
from hoshino.priv import *

messageLengthLimit=0
push_uids = {}
push_times = {}

sv = Service('bili-dynamic', help_='''
B站动态推送插件
'''.strip())

async def broadcast(msg,groups=None,sv_name=None):
    bot = nonebot.get_bot()
    #当groups指定时，在groups中广播；当groups未指定，但sv_name指定，将在开启该服务的群广播
    svs = Service.get_loaded_services()
    if not groups and sv_name not in svs:
        raise ValueError(f'不存在服务 {sv_name}')
    if sv_name:
        enable_groups = await svs[sv_name].get_enable_groups()
        send_groups = enable_groups.keys() if not groups else groups
    else:
        send_groups = groups
    for gid in send_groups:
        try:
            await bot.send_group_msg(group_id=gid,message=msg)
            await asyncio.sleep(0.5)
        except Exception as e:
            sv.logger.info(e)

def getImageCqCode(path):
    return '[CQ:image,file={imgUrl}]'.format(imgUrl=path)

def getLimitedMessage(originMsg):
    if messageLengthLimit>0 and len(originMsg)>messageLengthLimit:
        return originMsg[0:messageLengthLimit]+'……'
    else:
        return originMsg

def loadConfig():
    global push_uids
    global push_times
    global messageLengthLimit
    config_path = path.join(path.dirname(__file__),'config.json')
    with open(config_path,'r',encoding='utf8')as fp:
        conf = json.load(fp)
        messageLengthLimit=conf['message_length_limit']
        keys = conf['uid_bind'].keys()
        for uid in keys:
            push_uids[uid] = conf['uid_bind'][uid]
            push_times[uid] = int(time.time())
        sv.logger.info('B站动态推送配置文件加载成功')

def saveConfig():
    config_path = path.join(path.dirname(__file__),'config.json')
    with open(config_path,'r+',encoding='utf8')as fp:
        conf = json.load(fp)
        keys = push_uids.keys()
        conf['uid_bind'].clear()
        for uid in keys:
            conf['uid_bind'][uid] = push_uids[uid]
        fp.seek(0)
        fp.truncate()
        fp.seek(0)
        json.dump(conf,fp,indent=4)
        


@sv.on_prefix('订阅动态')
async def subscribe_dynamic(bot, ev):
    if push_uids=={}:
        loadConfig()
    if not check_priv(ev, SUPERUSER):
        await bot.send(ev, '仅有SUPERUSER可以订阅动态')
        return
    text = str(ev.message).strip()
    if not text:
        await bot.send(ev, "请按照格式发送", at_sender=True)
        return
    if not ' ' in text:#仅当前群组
        if not text in push_uids:
            push_uids[text] = [str(ev.group_id)]
        else:
            push_uids[text].append(str(ev.group_id))
    else:
        subUid=text.split(' ')[0]
        subGroup=text.split(' ')[1]
        if not subUid in push_uids:
            push_uids[subUid] = [subGroup]
        else:
            push_uids[subUid].append(subGroup)
    saveConfig()
    await bot.send(ev, '订阅成功')

@sv.on_prefix('取消订阅动态')
async def disubscribe_dynamic(bot, ev):
    if push_uids=={}:
        loadConfig()
    if not check_priv(ev, SUPERUSER):
        await bot.send(ev, '仅有SUPERUSER可以取消订阅动态')
        return
    text = str(ev.message).strip()
    if not text:
        await bot.send(ev, "请按照格式发送", at_sender=True)
        return
    if not ' ' in text:#仅当前群组
        sv.logger.info(text)
        sv.logger.info(push_uids.keys())
        if text in push_uids.keys():
            if str(ev.group_id) in push_uids[text]:
                if len(push_uids[text])==1:
                    push_uids.pop(text)
                else:
                    push_uids[text].remove(str(ev.group_id))
            else:
                await bot.send(ev, '取消订阅失败：未找到该订阅')
                return
        else:
            await bot.send(ev, '取消订阅失败：未找到该订阅')
            return
    else:
        subUid=text.split(' ')[0]
        subGroup=text.split(' ')[1]
        if subGroup=='all':
            if subUid in push_uids:
                push_uids.pop(subUid)
            else:
                await bot.send(ev, '取消订阅失败：未找到该订阅')
                return
        elif subUid in push_uids:
            if subGroup in push_uids[subUid]:
                if len(push_uids[subUid])==1:
                    push_uids.pop(subUid)
                else:
                    push_uids[subUid].remove(subGroup)
            else:
                await bot.send(ev, '取消订阅失败：未找到该订阅')
                return
        else:
            await bot.send(ev, '取消订阅失败：未找到该订阅')
            return
    saveConfig()
    await bot.send(ev, '取消订阅成功')

@sv.scheduled_job('cron', minute='*/2')
async def get_bili_dynamic():
    global push_times
    if push_uids=={}:
        loadConfig()
    uids = push_uids.keys()
    sv.logger.info('B站动态检查开始')
    for uid in uids:
        header = {
            'Referer': 'https://space.bilibili.com/{user_uid}/'.format(user_uid=uid)
        }
        try:
            resp = await aiorequests.get('https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/space_history?host_uid={user_uid}'.format(user_uid=uid), headers=header, timeout=20)
            res = await resp.json()
            cards=res['data']['cards']
            for card in cards:
                sendCQCode=[]
                uname=card['desc']['user_profile']['info']['uname']
                timestamp=card['desc']['timestamp']
                if timestamp < push_times[uid]:
                    #sv.logger.info(uname+'检查完成')
                    break
                dynamicId=card['desc']['dynamic_id']
                dynamicType=card['desc']['type']
                if dynamicType==2:#带图片动态
                    sendCQCode.append(uname)
                    sendCQCode.append('发表了动态：\n')
                    content=card['card']
                    contentJo = json.loads(content)
                    picturesCount=contentJo['item']['pictures_count']
                    trueContent =contentJo['item']['description']
                    trueContent = getLimitedMessage(trueContent)
                    sendCQCode.append(trueContent)
                    if picturesCount>0 and picturesCount<9:
                        pictureSrcs=[]
                        for pic in contentJo['item']['pictures']:
                            pictureSrcs.append(pic['img_src'])
                        for downPic in pictureSrcs:
                            sendCQCode.append(getImageCqCode(downPic))
                    sendCQCode.append('\nhttps://t.bilibili.com/{dynamicId}'.format(dynamicId=dynamicId))
                elif dynamicType==4:#纯文字动态
                    sendCQCode.append(uname)
                    sendCQCode.append('发表了动态：\n')
                    content=card['card']
                    contentJo = json.loads(content)
                    trueContent =contentJo['item']['content']
                    trueContent = getLimitedMessage(trueContent)
                    sendCQCode.append(trueContent)
                    sendCQCode.append('\nhttps://t.bilibili.com/{dynamicId}'.format(dynamicId=dynamicId))
                elif dynamicType==64:#文章
                    sendCQCode.append(uname)
                    sendCQCode.append('发布了文章：\n')
                    content=card['card']
                    contentJo = json.loads(content)
                    cvid=str(contentJo['id'])
                    title=contentJo['title']
                    summary=contentJo['summary']
                    coverImage=contentJo['image_urls'][0]
                    sendCQCode.append(title)
                    sendCQCode.append(getImageCqCode(coverImage))
                    sendCQCode.append('\n')
                    sendCQCode.append(summary)
                    sendCQCode.append('……')
                    sendCQCode.append('\nhttps://www.bilibili.com/read/cv{cvid}'.format(cvid=cvid))
                elif dynamicType==8:#投稿视频
                    sendCQCode.append(uname)
                    sendCQCode.append('投稿了视频：\n')
                    bvid=card['desc']['bvid']
                    content=card['card']
                    contentJo = json.loads(content)
                    title=contentJo['title']
                    coverImage=contentJo['pic']
                    videoDesc=contentJo['desc']
                    sendCQCode.append(title)
                    sendCQCode.append('\n')
                    sendCQCode.append(getImageCqCode(coverImage))
                    sendCQCode.append('\n')
                    videoDesc=getLimitedMessage(videoDesc)
                    sendCQCode.append(videoDesc)
                    sendCQCode.append('\n')
                    sendCQCode.append('\nhttps://www.bilibili.com/video/{bvid}'.format(bvid=bvid))
                elif dynamicType==1:#转发动态
                    sendCQCode.append(uname)
                    sendCQCode.append('转发了动态：\n')
                    content=card['card']
                    contentJo = json.loads(content)
                    currentContent=contentJo['item']['content']
                    sendCQCode.append(currentContent)
                    sendCQCode.append('\n')
                    originType=contentJo['item']['orig_type']
                    originContentJo=json.loads(contentJo['origin'])#
                    if originType==2:
                        originUser=originContentJo['user']['name']
                        sendCQCode.append('>>')
                        sendCQCode.append(originUser)
                        sendCQCode.append('：')
                        sendCQCode.append('\n')
                        originTrueContent =originContentJo['item']['description']
                        originTrueContent = getLimitedMessage(originTrueContent)
                        sendCQCode.append(originTrueContent)
                    elif originType==4:
                        originUser=originContentJo['user']['name']
                        sendCQCode.append('>>')
                        sendCQCode.append(originUser)
                        sendCQCode.append('：')
                        sendCQCode.append('\n')
                        trueContent =originContentJo['item']['content']
                        trueContent = getLimitedMessage(trueContent)
                        sendCQCode.append(trueContent)
                    elif originType==8:
                        bvid=card['desc']['origin']['bvid']
                        title=originContentJo['title']
                        coverImage=originContentJo['pic']
                        ownerName=originContentJo['owner']['name']
                        sendCQCode.append('>>')
                        sendCQCode.append(ownerName)
                        sendCQCode.append('的视频:')
                        sendCQCode.append(title)
                        sendCQCode.append('\n')
                        sendCQCode.append(getImageCqCode(coverImage))
                        sendCQCode.append('\n')
                        sendCQCode.append('>>')
                        sendCQCode.append(bvid)
                    elif originType==64:
                        title=originContentJo['title']
                        cvid=str(originContentJo['id'])
                        ownerName=originContentJo['author']['name']
                        sendCQCode.append('>>')
                        sendCQCode.append(ownerName)
                        sendCQCode.append('的文章:')
                        sendCQCode.append(title)
                        sendCQCode.append('\n')
                        sendCQCode.append('>>cv')
                        sendCQCode.append(cvid)
                    else:
                        sendCQCode.append('>>暂不支持的源动态类型，请进入动态查看')
                    sendCQCode.append('\nhttps://t.bilibili.com/{dynamicId}'.format(dynamicId=dynamicId))
                else:
                    sendCQCode.append(uname)
                    sendCQCode.append('发表了动态：\n')
                    sendCQCode.append('暂不支持该动态类型，请进入原动态查看')
                    sendCQCode.append('\nhttps://t.bilibili.com/{dynamicId}'.format(dynamicId=dynamicId))
                    sv.logger.info('type={type},暂不支持此类动态')
                msg=''.join(sendCQCode)
                if push_uids[uid][0]=='all':
                    await broadcast(msg,sv_name='bili-dynamic')
                else:
                    await broadcast(msg,push_uids[uid])
                time.sleep(1)
            push_times[uid]=int(time.time())
        except Exception as e:
            sv.logger.info('B站动态检查发生错误 '+e)
    sv.logger.info('B站动态检查结束')
        
@sv.on_fullmatch(('重新载入B站动态推送配置','重新载入动态推送配置'))
async def reload_config(bot, ev):
    if check_priv(ev, SUPERUSER):
        loadConfig()
        await bot.send(ev, '成功重新载入配置')
