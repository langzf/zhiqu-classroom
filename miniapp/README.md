# 知趣课堂微信小程序

这是一个独立的微信小程序前端项目，默认复用现有后端：

- API: `https://zqback.yueying.cloud/api/v1`
- 登录: 微信小程序 `wx.login` 一键登录，后端用 code2Session 绑定 openid
- 核心能力: 学习首页、AI 会话、语音输入、语音播报、音色设置

## 导入方式

1. 打开微信开发者工具。
2. 选择导入项目。
3. 项目目录选择 `miniapp/`。
4. AppID 当前已绑定为 `wx7b118547fd1ed80c`。

## 域名配置

开发者工具本地调试已在 `project.config.json` 中关闭 URL 校验：

- `setting.urlCheck = false`

这只能用于本地调试。正式预览、真机调试和发布前，需要在微信小程序后台配置合法域名。

操作路径：

1. 微信公众平台进入当前小程序。
2. 进入 `开发管理`。
3. 打开 `开发设置`。
4. 在 `服务器域名` 中配置以下域名。

需要配置：

- request 合法域名: `https://zqback.yueying.cloud`
- uploadFile 合法域名: `https://zqback.yueying.cloud`
- downloadFile 合法域名: `https://zqback.yueying.cloud`

注意：微信后台域名只填协议和域名，不要填写 `/api/v1` 路径。

## 后端配置

后端需要配置真实小程序凭据：

- `WECHAT_MINIAPP_APPID`
- `WECHAT_MINIAPP_SECRET`
