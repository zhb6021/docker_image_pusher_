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

## Command-Line Script: `main.py`

This script provides a command-line interface to back up Docker images from Docker Hub to a specified private registry. It fetches image tags, pulls the images, re-tags them for the target registry, pushes them, and keeps a record of backed-up images to avoid redundant operations.

### Prerequisites

*   Python 3.7+ (due to `asyncio` and `aiohttp`).
*   Docker installed and running on the machine where the script is executed.
*   Network access to Docker Hub (for fetching public images).
*   Credentials and access to a target private Docker registry (e.g., Tencent Cloud CCR, Alibaba Cloud ACR, Docker Hub private repos, etc.).

### Dependencies

The script requires the following Python package:
*   `aiohttp`

You can install it using pip:
```bash
pip install aiohttp
```

### Configuration

Configuration is managed via environment variables for credentials and target registry details, and command-line arguments for operational parameters.

#### Environment Variables (Mandatory)

These environment variables **must** be set before running the script. The script will exit if any of them are missing.

*   `TARGET_REGISTRY_URL`: The URL of your target private registry.
    *   Example: `ccr.ccs.tencentyun.com` or `registry.aliyuncs.com` or `docker.io` (for Docker Hub).
*   `TARGET_NAMESPACE`: The namespace within your target private registry where images will be stored.
    *   Example: `my-docker-backups` or `myusername` (if using Docker Hub as the target).
*   `DOCKER_USERNAME`: Your username for authenticating with the `TARGET_REGISTRY_URL`.
*   `DOCKER_PASSWORD`: Your password for authenticating with the `TARGET_REGISTRY_URL`.

#### Command-line Arguments

These arguments are optional and provide control over the script's execution:

*   `--num-tags` (`-n`): The number of latest tags to fetch and process for each image.
    *   Default: `5`
*   `--record-file` (`-r`): Path to the file used for recording backed-up images to prevent re-processing.
    *   Default: `backed_up_images.txt`
*   `--image-urls` (`-u`): A comma-separated string of Docker Hub image URLs to process. This allows you to specify which images to back up.
    *   Example: `"https://hub.docker.com/_/nginx/tags,https://hub.docker.com/r/prom/prometheus/tags"`
    *   If not provided, the script uses a default list of image URLs hardcoded in `main.py`.

### Running the Script

1.  **Set Environment Variables:**
    ```bash
    export TARGET_REGISTRY_URL="your-registry.example.com"
    export TARGET_NAMESPACE="your-namespace"
    export DOCKER_USERNAME="your-registry-username"
    export DOCKER_PASSWORD="your-registry-password"
    ```

2.  **Execute `main.py`:**
    ```bash
    python main.py [OPTIONS]
    ```
    For example, to back up the 3 latest tags for `alpine` and `redis`:
    ```bash
    python main.py -n 3 -u "https://hub.docker.com/_/alpine/tags,https://hub.docker.com/_/redis/tags"
    ```
    To use the default image list and fetch 5 tags per image:
    ```bash
    python main.py
    ```

    The script will log its progress to the standard output, including information about fetching tags, pulling, tagging, pushing images, and any errors encountered.

### How it Works

The script performs the following steps:

1.  **Configuration Loading:** Reads environment variables and parses command-line arguments.
2.  **Docker Login:** Logs into the target Docker registry using the provided credentials. Exits if login fails.
3.  **Image Processing Loop:** For each source image URL specified:
    a.  **Fetch Tags:** Retrieves the specified number of latest tags from Docker Hub using its API.
    b.  **Tag Processing Loop:** For each fetched tag:
        i.  **Check Backup Record:** Consults the record file (e.g., `backed_up_images.txt`) to see if the specific image and tag combination has already been backed up. If yes, skips to the next tag.
        ii. **Pull:** If not backed up, pulls the image from Docker Hub (e.g., `nginx:latest`).
        iii. **Tag:** Re-tags the pulled image for the target private registry (e.g., `your-registry.example.com/your-namespace/nginx:latest`).
        iv. **Push:** Pushes the newly tagged image to the target private registry.
        v.  **Record Backup:** If all previous steps (pull, tag, push) are successful, adds an entry for the image and tag to the record file.

### Record File

*   The record file (default: `backed_up_images.txt`) stores a list of image and tag combinations that have been successfully backed up.
*   Each line in the file has the format: `image_name_on_hub:tag`
    *   Example: `nginx:1.25` or `prom/prometheus:v2.40.0`
*   This file ensures that the script does not re-process images and tags that have already been backed up, saving time and resources.

### Error Handling

*   The script logs all operations, including errors, to the console using Python's `logging` module.
*   It will exit immediately if critical configuration (environment variables) is missing or if the initial login to the target Docker registry fails.
*   For errors encountered during the processing of a specific image or tag (e.g., pull failure, push failure), the script will log the error and attempt to continue with the next tag or image URL.
