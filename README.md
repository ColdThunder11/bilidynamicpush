# bilidynamicpush
一个用于推送哔哩哔哩动态的HoshinoBot插件   
## 使用方法
将本项目clone至HoshinoBot\hoshino\modules下，在__bot__.py中加入bilidynamicpush   
## 指令列表
| 指令 | 格式 | 备注 |
| ---------- | -------------- | -------------- |
| 订阅动态 | 订阅动态+空格+需要订阅的UID+空格+需要订阅的群（可选） | 如不输入订阅的群则为当前群，全部群订阅请输入all |
| 取消订阅动态 | 取消订阅动态+空格+需要取消订阅的UID+空格+需要取消订阅的群（可选） | 如不输入取消订阅的群则为当前群，取消全部群订阅请输入all |
| 重新载入动态推送配置 | 无 | 在不重载HoshinoBot的情况下重新载入修改后的配置文件 |
## 配置文件
可以直接修改config.json来配置推送设置，message_length_limit为对超长动态和视频简介的字数限制，0为不限制。uid_bind为推送列表字典，key为要推送的uid，value为要推送的群的数组，如果需要全部群推送请修改为\["all"\]。
## 一些说明
对于设置为全部推送（all）的情况，插件仅会对启用了该插件的群组进行推送，对于手动指定的群的推送，其推送状态不受插件启用与否的影响，如不需要请自行删除订阅。
## 支持情况
| 类型 |
| ----- |
| 纯文字动态 √ |
| 带图片动态 √ |
| 转发动态 √ |
| 视频 √ |
| 文章 √ |
| 音频 × |
