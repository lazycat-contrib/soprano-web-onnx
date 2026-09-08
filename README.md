# Soprano Web ONNX · 懒猫微服

[上游项目](https://github.com/KevinAHM/soprano-web-onnx)的静态 LPK 打包仓库，仅发布到喵喵商店。

应用在浏览器中进行英语语音合成，无需模型 API Key 或服务端 GPU。模型和 JavaScript/WASM 运行库随安装包提供；访问设备负责推理，微服提供静态文件。支持 amd64 微服，最低 lzcos 1.5.0。

## 使用

通过微服的 HTTPS 应用入口打开，建议使用新版 Chrome 或 Edge。选择 CPU/WASM，输入英文并点击 Generate Audio。首次生成会从微服加载约 378 MB 模型到浏览器，速度取决于客户端的内存和处理器。WebGPU 是上游保留的可选入口，其可用性取决于客户端显卡与浏览器；打包流程验证 CPU/WASM。

## 来源与版本

所有下载和打包均在 GitHub Actions 完成，本地不拉取应用源码或模型：

1. 查询上游最新稳定 Release。
2. 下载该 Release 对应提交的 Source code 源码归档。
3. 下载同一个 Release 的三个 ONNX 模型附件，核对 Release SHA256、文件长度及源码中的 LFS 指针。
4. 从 npm 锁文件安装固定版本的 ONNX Runtime Web 和 Transformers.js，将浏览器运行库放入静态目录。移除外部字体请求，保留页面的字体回退。
5. 在 GitHub Runner 的 Chrome 中实际合成英文，确认生成非静音 PCM，且没有外部资源请求；测试通过后制作 LPK。
6. 上传版本化 GitHub Release 安装包，并把其 URL 和 SHA256 提交给喵喵商店。

`upstream.json` 锁定 Release tag、源码提交和模型摘要。**包版本与 tag 跟随上游最新 Release**：上游 `v0.1.0` → 包版本 `0.1.0` → 本仓库 tag `v0.1.0`，不自行递增补丁版本。已存在的同版本 Release 内容发生变化时会停止，避免覆盖已发布安装包。

## 手动更新

打开 Actions → **Update upstream and publish** → **Run workflow**。工作流更新最新 Release 锁定信息后触发构建发布。无新版本时复用已有安装包并验证摘要，商店已有版本则跳过。没有定时任务。

官方商店始终禁用。喵喵商店凭据来自组织授权的 `APPSTORE_URL`、`APPSTORE_TOKEN`，以及可选的 `PRIVATE_STORE_GROUP_CODES` Secrets；仓库不保存凭据。

包名：`community.lazycat.app.sopranowebonnx`。Logo 由用户提供；上游 Apache-2.0 许可证和浏览器运行库许可证随包保留。
