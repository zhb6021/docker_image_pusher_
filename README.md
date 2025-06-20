# Docker Images Pusher

使用Github Action将DockerHub镜像转存到阿里云私有仓库，供国内服务器使用，免费易用

视频教程：https://www.bilibili.com/video/BV1Zn4y19743/

作者：**技术爬爬虾**<br>
B站，抖音，Youtube全网同名，转载请注明作者<br>

## 使用方式


### 配置阿里云
登录阿里云容器镜像服务<br>
https://cr.console.aliyun.com/<br>
启用个人实例，创建一个命名空间（**ALIYUN_NAME_SPACE**）
![](/doc/命名空间.png)

访问凭证–>获取环境变量<br>
用户名（**ALIYUN_REGISTRY_USER**)<br>
密码（**ALIYUN_REGISTRY_PASSWORD**)<br>
仓库地址（**ALIYUN_REGISTRY**）<br>

![](/doc/用户名密码.png)


### Fork本项目
Fork本项目<br>
进入您自己的项目，点击Action，启用Github Action功能
配置环境变量，进入Settings->Secret and variables->Actions->New Repository secret
![](doc/配置环境变量.png)
将上一步的 ALIYUN_NAME_SPACE，ALIYUN_REGISTRY_USER，ALIYUN_REGISTRY_PASSWORD，ALIYUN_REGISTRY
的值配置成环境变量

### 添加镜像
打开images.txt文件，添加你想要的镜像，可以带tag，也可以不用(默认latest)<br>
也可添加--platform xxxxx 或 --platform=xxxxx 参数指定镜像架构<br>
![](doc/images.png)
文件提交后，自动进入Github Action构建


### 使用镜像
回到阿里云，镜像仓库，点击任意镜像，可查看镜像状态。(可以改成公开，拉取镜像免登录)
![](doc/开始使用.png)

在国内服务器pull镜像：<br>
```
docker pull registry.cn-hangzhou.aliyuncs.com/shrimp-images/alpine
```
registry.cn-hangzhou.aliyuncs.com 即 ALIYUN_REGISTRY<br>
shrimp-images 即 ALIYUN_NAME_SPACE<br>
alpine 即images.txt里面填的镜像<br>

## 命令行脚本: `main.py`

该脚本提供了一个命令行界面，用于将 Docker Hub 上的 Docker 镜像备份到指定的私有仓库。它会获取镜像标签，拉取镜像，为目标仓库重新标记镜像，推送它们，并记录已备份的镜像以避免重复操作。

### 先决条件

*   Python 3.7+ (由于使用了 `asyncio` 和 `aiohttp`)。
*   在脚本执行的机器上已安装并正在运行 Docker。
*   可以访问 Docker Hub 的网络 (用于获取公共镜像)。
*   拥有目标私有 Docker 仓库的凭据和访问权限 (例如，腾讯云 CCR、阿里云 ACR、Docker Hub 私有仓库等)。

### 依赖项

该脚本需要以下 Python 包:
*   `aiohttp`

您可以使用 pip 安装它:
```bash
pip install aiohttp
```

### 配置

配置通过环境变量管理凭据和目标仓库详细信息，通过命令行参数管理操作参数。

#### 环境变量 (必需)

在运行脚本之前 **必须** 设置这些环境变量。如果缺少任何一个，脚本将退出。

*   `TARGET_REGISTRY_URL`: 您的目标私有仓库的 URL。
    *   示例: `ccr.ccs.tencentyun.com` 或 `registry.aliyuncs.com` 或 `docker.io` (用于 Docker Hub)。
*   `TARGET_NAMESPACE`: 您的目标私有仓库中用于存储镜像的命名空间。
    *   示例: `my-docker-backups` 或 `myusername` (如果使用 Docker Hub 作为目标)。
*   `DOCKER_USERNAME`: 用于向 `TARGET_REGISTRY_URL` 进行身份验证的用户名。
*   `DOCKER_PASSWORD`: 用于向 `TARGET_REGISTRY_URL` 进行身份验证的密码。

#### 命令行参数

这些参数是可选的，用于控制脚本的执行:

*   `--num-tags` (`-n`): 为每个镜像获取和处理的最新标签数量。
    *   默认值: `5`
*   `--record-file` (`-r`): 用于记录已备份镜像以防止重复处理的文件路径。
    *   默认值: `backed_up_images.txt`
*   `--image-urls` (`-u`): 以逗号分隔的 Docker Hub 镜像 URL 字符串，用于指定要处理的镜像。
    *   示例: `"https://hub.docker.com/_/nginx/tags,https://hub.docker.com/r/prom/prometheus/tags"`
    *   如果未提供，脚本将使用 `main.py` 中硬编码的默认镜像 URL 列表。

### 运行脚本

1.  **设置环境变量:**
    ```bash
    export TARGET_REGISTRY_URL="your-registry.example.com"
    export TARGET_NAMESPACE="your-namespace"
    export DOCKER_USERNAME="your-registry-username"
    export DOCKER_PASSWORD="your-registry-password"
    ```

2.  **执行 `main.py`:**
    ```bash
    python main.py [选项]
    ```
    例如，备份 `alpine` 和 `redis` 的最新3个标签:
    ```bash
    python main.py -n 3 -u "https://hub.docker.com/_/alpine/tags,https://hub.docker.com/_/redis/tags"
    ```
    使用默认镜像列表并为每个镜像获取5个标签:
    ```bash
    python main.py
    ```

    脚本会将其进度记录到标准输出，包括获取标签、拉取、标记、推送镜像以及遇到的任何错误的信息。

### 工作原理

脚本执行以下步骤:

1.  **加载配置:** 读取环境变量并解析命令行参数。
2.  **Docker 登录:** 使用提供的凭据登录到目标 Docker 仓库。如果登录失败则退出。
3.  **镜像处理循环:** 对于指定的每个源镜像 URL:
    a.  **获取标签:** 使用其 API 从 Docker Hub 检索指定数量的最新标签。
    b.  **标签处理循环:** 对于获取的每个标签:
        i.  **检查备份记录:** 查询记录文件 (例如 `backed_up_images.txt`)，看是否已备份特定的镜像和标签组合。如果是，则跳到下一个标签。
        ii. **拉取 (Pull):** 如果未备份，则从 Docker Hub 拉取镜像 (例如 `nginx:latest`)。
        iii. **标记 (Tag):** 为目标私有仓库重新标记拉取的镜像 (例如 `your-registry.example.com/your-namespace/nginx:latest`)。
        iv. **推送 (Push):** 将新标记的镜像推送到目标私有仓库。
        v.  **记录备份:** 如果所有先前的步骤 (拉取、标记、推送) 都成功，则将镜像和标签的条目添加到记录文件。

### 记录文件

*   记录文件 (默认: `backed_up_images.txt`) 存储已成功备份的镜像和标签组合的列表。
*   文件中的每一行格式为: `镜像在Hub上的名称:标签`
    *   示例: `nginx:1.25` 或 `prom/prometheus:v2.40.0`
*   该文件确保脚本不会重复处理已备份的镜像和标签，从而节省时间和资源。

### 错误处理

*   脚本使用 Python 的 `logging` 模块将所有操作 (包括错误) 记录到控制台。
*   如果缺少关键配置 (环境变量) 或初始登录到目标 Docker 仓库失败，脚本将立即退出。
*   对于在处理特定镜像或标签期间遇到的错误 (例如，拉取失败、推送失败)，脚本将记录错误并尝试继续处理下一个标签或镜像 URL。

## 自动化每日备份工作流 (`.github/workflows/daily_image_backup.yml`)

该仓库包含一个 GitHub Actions 工作流，可自动每日执行 `main.py` 脚本以备份 Docker 镜像。

### 特性

- **定时执行:** 每天 UTC 时间 02:00 自动运行。
- **手动触发:** 也可以从 GitHub Actions 选项卡手动触发。
- **安全配置:** 使用 GitHub Actions Secrets 存储敏感信息，如仓库凭据。

### 工作流配置

要使用此工作流，您需要在您的 GitHub 仓库设置中配置以下 Secrets (`Settings > Secrets and variables > Actions > New repository secret`):

-   **`TARGET_REGISTRY_URL_SECRET`**: 您的目标私有仓库的 URL (例如, `ccr.ccs.tencentyun.com` 或 `registry.aliyuncs.com`)。
-   **`TARGET_NAMESPACE_SECRET`**: 您的目标私有仓库中用于存储镜像的命名空间 (例如, `my-docker-images` 或 `my-project`)。
-   **`DOCKER_USERNAME_SECRET`**: 用于向您的目标私有仓库进行身份验证的用户名。
-   **`DOCKER_PASSWORD_SECRET`**: 用于向您的目标私有仓库进行身份验证的密码。

### 工作原理

该工作流执行以下步骤:

1.  **检出 (Checks out)** 仓库代码。
2.  **设置 (Sets up)** Python 3.9 环境。
3.  **安装 (Installs)** 所需的 Python 依赖 (`aiohttp`)。
4.  **执行 (Executes)** `main.py` 脚本，并将配置的 Secrets作为环境变量传递给脚本。然后，脚本按照 "命令行脚本: `main.py`" 部分所述处理镜像备份逻辑。

脚本执行的日志可以在此工作流的 GitHub Actions 运行历史中查看。
